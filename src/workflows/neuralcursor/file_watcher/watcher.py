"""Filesystem watcher for automatic graph updates."""

import logging
import asyncio
from typing import Optional, Set
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

from mdrag.config.settings import Settings
from mdrag.capabilities.memory.gateway import MemoryGateway
from mdrag.capabilities.memory.models import MemoryRequest, MemoryType, MemoryOperation
from mdrag.integrations.neo4j.models import CodeEntity, NodeType
from .ast_parser import ASTParser

logger = logging.getLogger(__name__)


class CodeChangeHandler(FileSystemEventHandler):
    """
    Handler for code file changes.

    Detects file saves and triggers:
    1. AST parsing
    2. Entity extraction
    3. Neo4j graph updates
    4. Relationship updates
    """

    def __init__(
        self,
        memory_gateway: MemoryGateway,
        ast_parser: ASTParser,
        watch_extensions: Optional[Set[str]] = None,
    ):
        """
        Initialize change handler.

        Args:
            memory_gateway: Memory gateway instance
            ast_parser: AST parser instance
            watch_extensions: File extensions to watch (default: .py)
        """
        super().__init__()
        self.gateway = memory_gateway
        self.ast_parser = ast_parser
        self.watch_extensions = watch_extensions or {".py"}
        self._processing: Set[str] = set()
        self._last_processed: dict = {}

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory:
            asyncio.create_task(self._handle_file_change(event.src_path, "modified"))

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory:
            asyncio.create_task(self._handle_file_change(event.src_path, "created"))

    async def _handle_file_change(self, file_path: str, event_type: str) -> None:
        """
        Handle file change event.

        Args:
            file_path: Path to changed file
            event_type: Type of event (modified, created)
        """
        # Check if we should process this file
        if not self._should_process(file_path):
            return

        # Debounce - prevent processing same file multiple times rapidly
        if file_path in self._processing:
            return

        try:
            self._processing.add(file_path)

            logger.info(
                "file_watcher_change_detected",
                extra={"file": file_path, "event": event_type},
            )

            # Parse file
            entities = self.ast_parser.parse_file(file_path)

            if not entities:
                logger.info(
                    "file_watcher_no_entities",
                    extra={"file": file_path},
                )
                return

            # Update graph with entities
            for entity_data in entities:
                await self._update_graph_entity(entity_data)

            logger.info(
                "file_watcher_graph_updated",
                extra={"file": file_path, "entities": len(entities)},
            )

            self._last_processed[file_path] = datetime.utcnow()

        except Exception as e:
            logger.exception(
                "file_watcher_processing_failed",
                extra={"file": file_path, "error": str(e)},
            )
        finally:
            self._processing.discard(file_path)

    def _should_process(self, file_path: str) -> bool:
        """
        Check if file should be processed.

        Args:
            file_path: File path to check

        Returns:
            True if file should be processed
        """
        path = Path(file_path)

        # Check extension
        if path.suffix not in self.watch_extensions:
            return False

        # Skip certain directories
        skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
        if any(skip_dir in path.parts for skip_dir in skip_dirs):
            return False

        # Check if recently processed (within 5 seconds)
        last_time = self._last_processed.get(file_path)
        if last_time:
            time_diff = (datetime.utcnow() - last_time).total_seconds()
            if time_diff < 5:
                return False

        return True

    async def _update_graph_entity(self, entity_data: dict) -> None:
        """
        Update or create graph entity.

        Args:
            entity_data: Entity data from AST parser
        """
        try:
            # Check if entity already exists
            existing_query = """
            MATCH (c:CodeEntity {file_path: $file_path, name: $name})
            RETURN c
            """

            existing = await self.gateway.neo4j_client.execute_cypher(
                existing_query,
                {
                    "file_path": entity_data["file_path"],
                    "name": entity_data["name"],
                },
            )

            if existing:
                # Update existing entity
                entity_uuid = existing[0]["c"]["uuid"]
                await self.gateway.neo4j_client.update_node(
                    entity_uuid,
                    {
                        "description": entity_data.get("description"),
                        "line_number": entity_data.get("line_number"),
                        "ast_info": entity_data.get("ast_info", {}),
                        "updated_at": datetime.utcnow().isoformat(),
                    },
                )
                logger.info(
                    "file_watcher_entity_updated",
                    extra={"entity": entity_data["name"], "uuid": entity_uuid},
                )
            else:
                # Create new entity
                code_entity = CodeEntity(
                    name=entity_data["name"],
                    entity_type=entity_data["entity_type"],
                    file_path=entity_data["file_path"],
                    line_number=entity_data.get("line_number"),
                    description=entity_data.get("description"),
                    ast_info=entity_data.get("ast_info", {}),
                )

                request = MemoryRequest(
                    operation=MemoryOperation.CREATE,
                    memory_type=MemoryType.STRUCTURAL,
                    entity_type=NodeType.CODE_ENTITY,
                    data=code_entity.model_dump(),
                    metadata={"source": "file_watcher"},
                )

                response = await self.gateway.execute(request)

                if response.success:
                    logger.info(
                        "file_watcher_entity_created",
                        extra={"entity": entity_data["name"], "uuid": response.data},
                    )

        except Exception as e:
            logger.exception(
                "file_watcher_entity_update_failed",
                extra={"entity": entity_data, "error": str(e)},
            )


class FileWatcher:
    """
    Main file watcher for monitoring code changes.

    Monitors specified directories and automatically updates the knowledge graph
    when files are modified.
    """

    def __init__(self, settings: Settings, memory_gateway: MemoryGateway):
        """
        Initialize file watcher.

        Args:
            settings: Application settings
            memory_gateway: Memory gateway instance
        """
        self.settings = settings
        self.gateway = memory_gateway
        self.ast_parser = ASTParser()
        self.observer: Optional[Observer] = None
        self.watch_paths: Set[Path] = set()

    def add_watch_path(self, path: str) -> None:
        """
        Add a directory to watch.

        Args:
            path: Directory path to watch
        """
        watch_path = Path(path).resolve()
        if watch_path.exists() and watch_path.is_dir():
            self.watch_paths.add(watch_path)
            logger.info("file_watcher_path_added", extra={"path": str(watch_path)})
        else:
            logger.warning("file_watcher_invalid_path", extra={"path": path})

    async def start(self) -> None:
        """Start watching for file changes."""
        if not self.watch_paths:
            logger.warning("file_watcher_no_paths")
            return

        self.observer = Observer()
        event_handler = CodeChangeHandler(self.gateway, self.ast_parser)

        for watch_path in self.watch_paths:
            self.observer.schedule(
                event_handler,
                str(watch_path),
                recursive=True,
            )
            logger.info("file_watcher_watching", extra={"path": str(watch_path)})

        self.observer.start()
        logger.info("file_watcher_started")

    async def stop(self) -> None:
        """Stop watching for file changes."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("file_watcher_stopped")

    async def run_forever(self) -> None:
        """Run watcher until interrupted."""
        await self.start()

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("file_watcher_interrupted")
        finally:
            await self.stop()
