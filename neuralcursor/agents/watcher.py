"""
File System Watcher: Monitors codebase changes and updates Neo4j graph.

Automatically detects:
1. New files → Create FileNode
2. Modified files → Update FileNode, extract CodeEntities
3. Deleted files → Archive FileNode and related entities
"""

import asyncio
import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from neuralcursor.brain.neo4j.client import Neo4jClient
from neuralcursor.brain.neo4j.models import (
    FileNode,
    CodeEntityNode,
    Relationship,
    RelationType,
)
from neuralcursor.settings import get_settings

logger = logging.getLogger(__name__)


class CodebaseWatcher(FileSystemEventHandler):
    """
    File system event handler for codebase monitoring.
    
    Triggers graph updates when files change.
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        project_root: str,
        debounce_seconds: float = 2.0,
    ):
        """
        Initialize watcher.
        
        Args:
            neo4j_client: Neo4j client
            project_root: Project root directory
            debounce_seconds: Debounce delay for file events
        """
        super().__init__()
        self.neo4j = neo4j_client
        self.project_root = Path(project_root)
        self.debounce_seconds = debounce_seconds
        self.pending_events: dict[str, float] = {}  # path -> timestamp

        # File extension to language mapping
        self.language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".rb": "ruby",
            ".php": "php",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
        }

    def _get_relative_path(self, absolute_path: str) -> str:
        """
        Get path relative to project root.
        
        Args:
            absolute_path: Absolute file path
            
        Returns:
            Relative path
        """
        return str(Path(absolute_path).relative_to(self.project_root))

    def _get_file_hash(self, file_path: str) -> str:
        """
        Compute SHA256 hash of file contents.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex digest of file hash
        """
        sha256 = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.warning(
                "file_hash_failed",
                extra={"path": file_path, "error": str(e)},
            )
            return ""

    def _should_process_file(self, file_path: str) -> bool:
        """
        Check if file should be processed.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file should be processed
        """
        path = Path(file_path)

        # Get ignore patterns from settings
        settings = get_settings()
        ignore_patterns = settings.watcher_ignore_patterns

        # Check against ignore patterns
        for pattern in ignore_patterns:
            if path.match(pattern):
                return False

        # Only process code files
        return path.suffix in self.language_map

    async def _process_file_change(self, file_path: str) -> None:
        """
        Process a file change event.
        
        Args:
            file_path: Path to changed file
        """
        try:
            relative_path = self._get_relative_path(file_path)

            # Check if file exists
            path_obj = Path(file_path)
            if not path_obj.exists():
                await self._handle_file_deleted(relative_path)
                return

            # Get file stats
            stat = path_obj.stat()
            file_size = stat.st_size
            last_modified = datetime.fromtimestamp(stat.st_mtime)
            file_hash = self._get_file_hash(file_path)
            language = self.language_map.get(path_obj.suffix, "unknown")

            # Check if FileNode already exists
            existing_query = """
            MATCH (f:File {file_path: $file_path})
            RETURN f.uid as uid, f.content_hash as hash
            """

            results = await self.neo4j.query(
                existing_query, {"file_path": relative_path}
            )

            if results:
                # File exists, check if hash changed
                existing_uid = results[0]["uid"]
                existing_hash = results[0].get("hash")

                if existing_hash != file_hash:
                    # File modified
                    await self._handle_file_modified(
                        existing_uid, relative_path, file_hash, last_modified
                    )
            else:
                # New file
                await self._handle_file_created(
                    relative_path, language, file_size, last_modified, file_hash
                )

        except Exception as e:
            logger.exception(
                "process_file_change_failed",
                extra={"path": file_path, "error": str(e)},
            )

    async def _handle_file_created(
        self,
        relative_path: str,
        language: str,
        size_bytes: int,
        last_modified: datetime,
        content_hash: str,
    ) -> None:
        """
        Handle new file creation.
        
        Args:
            relative_path: Relative file path
            language: Programming language
            size_bytes: File size
            last_modified: Last modified timestamp
            content_hash: File hash
        """
        file_node = FileNode(
            name=Path(relative_path).name,
            description=f"File: {relative_path}",
            file_path=relative_path,
            file_type=language,
            size_bytes=size_bytes,
            last_modified=last_modified,
            content_hash=content_hash,
        )

        uid = await self.neo4j.create_node(file_node)

        logger.info(
            "watcher_file_created",
            extra={"path": relative_path, "uid": uid, "language": language},
        )

    async def _handle_file_modified(
        self,
        file_uid: str,
        relative_path: str,
        new_hash: str,
        last_modified: datetime,
    ) -> None:
        """
        Handle file modification.
        
        Args:
            file_uid: UID of existing FileNode
            relative_path: Relative file path
            new_hash: New file hash
            last_modified: New modified timestamp
        """
        await self.neo4j.update_node(
            file_uid,
            {
                "content_hash": new_hash,
                "last_modified": last_modified.isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(
            "watcher_file_modified",
            extra={"path": relative_path, "uid": file_uid},
        )

        # TODO: Parse AST and update CodeEntity nodes
        # This would require language-specific parsers (tree-sitter, etc.)

    async def _handle_file_deleted(self, relative_path: str) -> None:
        """
        Handle file deletion.
        
        Args:
            relative_path: Relative file path
        """
        # Find and archive the FileNode
        query = """
        MATCH (f:File {file_path: $file_path})
        SET f.archived = true, f.archived_at = datetime()
        RETURN f.uid as uid
        """

        results = await self.neo4j.query(query, {"file_path": relative_path})

        if results:
            file_uid = results[0]["uid"]
            logger.info(
                "watcher_file_deleted",
                extra={"path": relative_path, "uid": file_uid},
            )

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation event."""
        if not event.is_directory and self._should_process_file(event.src_path):
            self.pending_events[event.src_path] = asyncio.get_event_loop().time()

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification event."""
        if not event.is_directory and self._should_process_file(event.src_path):
            self.pending_events[event.src_path] = asyncio.get_event_loop().time()

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion event."""
        if not event.is_directory and self._should_process_file(event.src_path):
            self.pending_events[event.src_path] = asyncio.get_event_loop().time()

    async def process_pending_events(self) -> None:
        """Process pending file events with debouncing."""
        current_time = asyncio.get_event_loop().time()
        to_process = []

        for file_path, timestamp in list(self.pending_events.items()):
            if current_time - timestamp >= self.debounce_seconds:
                to_process.append(file_path)
                del self.pending_events[file_path]

        # Process files
        for file_path in to_process:
            await self._process_file_change(file_path)


class FileSystemWatcherService:
    """
    Service that runs the file system watcher.
    """

    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize watcher service.
        
        Args:
            neo4j_client: Neo4j client
        """
        self.neo4j = neo4j_client
        self.settings = get_settings()
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[CodebaseWatcher] = None
        self._running = False

    async def start(self) -> None:
        """Start the file system watcher."""
        if not self.settings.watcher_enabled:
            logger.info("watcher_disabled")
            return

        self.event_handler = CodebaseWatcher(
            neo4j_client=self.neo4j,
            project_root=self.settings.project_root,
            debounce_seconds=self.settings.watcher_debounce_seconds,
        )

        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            self.settings.project_root,
            recursive=True,
        )

        self.observer.start()
        self._running = True

        logger.info(
            "watcher_started",
            extra={"project_root": self.settings.project_root},
        )

        # Start event processing loop
        asyncio.create_task(self._event_processing_loop())

    async def stop(self) -> None:
        """Stop the file system watcher."""
        self._running = False

        if self.observer:
            self.observer.stop()
            self.observer.join()

        logger.info("watcher_stopped")

    async def _event_processing_loop(self) -> None:
        """Background loop to process pending events."""
        while self._running:
            if self.event_handler:
                await self.event_handler.process_pending_events()

            await asyncio.sleep(0.5)  # Check twice per second
