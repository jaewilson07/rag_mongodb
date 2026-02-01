"""Google Drive service facade providing unified high-level interface.

This module combines authentication, search, and export operations into
a single facade for easier use. Follows the Facade design pattern.
"""

import asyncio
from pathlib import Path
from typing import Literal

from ...mdrag_logging.service_logging import get_logger, log_service_class

from .classes import (
    GoogleAuth,
    GoogleDoc,
    GoogleDrive,
)
from .models import GoogleDocumentTab, GoogleDriveFile, SearchResult
from ..models import Source

logger = get_logger(__name__)


@log_service_class
class GoogleDriveService:
    """Unified service for Google Drive search, document export, and file download operations."""

    def __init__(
        self,
        credentials_json: str | None = None,
        token_json: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        """
        Initialize the Google Drive service.

        Supports multiple credential formats:
        1. JSON strings (GDOC_CLIENT and GDOC_TOKEN env vars)
        2. Separate client_id and client_secret (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, etc.)

        Args:
            credentials_json: OAuth client configuration JSON (from GDOC_CLIENT env var)
            token_json: Serialized token JSON (from GDOC_TOKEN env var)
            client_id: OAuth client ID (alternative to JSON)
            client_secret: OAuth client secret (alternative to JSON)

        Raises:
            ValueError: If credentials are missing or invalid
        """
        self.authenticator = GoogleAuth(
            credentials_json=credentials_json,
            token_json=token_json,
            client_id=client_id,
            client_secret=client_secret,
        )
        self.api = GoogleDrive(self.authenticator)
        self.docs_api = GoogleDoc(self.authenticator)

    async def search_files(
        self,
        query: str,
        top_n: int = 10,
        folder_id: str | None = None,
        folder_name: str | None = None,
        on_duplicates: Literal["error", "newest"] = "error",
    ) -> SearchResult:
        """
        Search Google Drive for files matching a query.

        Args:
            query: Search query string (Drive query syntax or keywords)
            top_n: Maximum number of results to return
            folder_id: Optional folder ID to restrict search to
            folder_name: Optional folder name to restrict search to
            on_duplicates: How to handle duplicate folder names

        Returns:
            SearchResult with matching files
        """
        await logger.info(
            "gdrive_search_start",
            action="gdrive_search_start",
            query=query,
            top_n=top_n,
            folder_id=folder_id,
            folder_name=folder_name,
            on_duplicates=on_duplicates,
        )
        result = await self.api.search.search(
            query=query,
            top_n=top_n,
            folder_id=folder_id,
            folder_name=folder_name,
            on_duplicates=on_duplicates,
        )
        await logger.info(
            "gdrive_search_complete",
            action="gdrive_search_complete",
            result_count=len(result.files),
        )
        return result

    async def search_document_ids(
        self,
        query: str,
        top_n: int = 10,
        folder_id: str | None = None,
        folder_name: str | None = None,
        on_duplicates: Literal["error", "newest"] = "error",
    ) -> list[str]:
        """
        Search for documents and return a list of document IDs.

        Args:
            query: Search query string
            top_n: Maximum number of results
            folder_id: Optional folder ID to search within
            folder_name: Optional folder name to search within
            on_duplicates: How to handle duplicate folder names

        Returns:
            List of document IDs
        """
        await logger.info(
            "gdrive_search_ids_start",
            action="gdrive_search_ids_start",
            query=query,
            top_n=top_n,
            folder_id=folder_id,
            folder_name=folder_name,
            on_duplicates=on_duplicates,
        )
        results = await self.api.search.search_ids(
            query=query,
            top_n=top_n,
            folder_id=folder_id,
            folder_name=folder_name,
            on_duplicates=on_duplicates,
        )
        await logger.info(
            "gdrive_search_ids_complete",
            action="gdrive_search_ids_complete",
            result_count=len(results),
        )
        return results

    async def search_documents(
        self,
        query: str,
        top_n: int = 10,
        folder_id: str | None = None,
        folder_name: str | None = None,
        on_duplicates: Literal["error", "newest"] = "error",
    ) -> list[GoogleDriveFile]:
        """
        Search for documents and return full file metadata.

        Args:
            query: Search query string
            top_n: Maximum number of results
            folder_id: Optional folder ID to search within
            folder_name: Optional folder name to search within
            on_duplicates: How to handle duplicate folder names

        Returns:
            List of GoogleDriveFile objects
        """
        result = await self.search_files(
            query=query,
            top_n=top_n,
            folder_id=folder_id,
            folder_name=folder_name,
            on_duplicates=on_duplicates,
        )
        return result.files

    async def download_file(self, file_id: str) -> bytes:
        """
        Download a file from Google Drive as binary data.

        This method is useful for downloading binary files like LoRA models,
        images, or other non-text files.

        Args:
            file_id: File ID in Google Drive

        Returns:
            File content as bytes

        Raises:
            ValueError: If download fails
        """
        await logger.info(
            "gdrive_download_start",
            action="gdrive_download_start",
            file_id=file_id,
        )
        content = await self.api.export.download_file(file_id)
        await logger.info(
            "gdrive_download_complete",
            action="gdrive_download_complete",
            file_id=file_id,
            size_bytes=len(content),
        )
        return content

    async def export_as_markdown(
        self,
        document_id: str,
        include_metadata: bool = True,
        output_path: str | Path | None = None,
    ) -> Source:
        """Export a Google Drive document as markdown with YAML frontmatter.

        Args:
            document_id: The Google Drive document ID
            include_metadata: Whether to include YAML frontmatter with metadata
            output_path: Optional path to write the markdown file to

        Returns:
            Source payload including frontmatter and markdown content

        Raises:
            ValueError: If document cannot be exported or doesn't exist
        """
        await logger.info(
            "gdrive_export_markdown_start",
            action="gdrive_export_markdown_start",
            document_id=document_id,
            include_metadata=include_metadata,
        )
        source = await self.api.export.export_as_markdown(
            file_id=document_id,
            include_metadata=include_metadata,
            output_path=output_path,
        )
        await logger.info(
            "gdrive_export_markdown_complete",
            action="gdrive_export_markdown_complete",
            document_id=document_id,
        )
        return source

    async def export_tabs(self, document_id: str) -> list[GoogleDocumentTab]:
        """Export a Google Doc into per-tab markdown sections.

        Returns a list of GoogleDocumentTab models, one per split tab.
        """
        await logger.info(
            "gdrive_export_tabs_start",
            action="gdrive_export_tabs_start",
            document_id=document_id,
        )
        tabs = await self.docs_api.export_tabs(document_id)
        await logger.info(
            "gdrive_export_tabs_complete",
            action="gdrive_export_tabs_complete",
            document_id=document_id,
            tab_count=len(tabs),
        )
        return tabs

    async def export_tabs_to_directory(
        self,
        document_id: str,
        output_dir: str | Path,
        *,
        include_metadata_on_fallback: bool = True,
    ) -> list[Path]:
        """Export a Google Doc into per-tab markdown files on disk."""
        await logger.info(
            "gdrive_export_tabs_dir_start",
            action="gdrive_export_tabs_dir_start",
            document_id=document_id,
            output_dir=str(output_dir),
        )
        paths = await self.docs_api.export_tabs_to_directory(
            document_id,
            output_dir,
            include_metadata_on_fallback=include_metadata_on_fallback,
        )
        await logger.info(
            "gdrive_export_tabs_dir_complete",
            action="gdrive_export_tabs_dir_complete",
            document_id=document_id,
            file_count=len(paths),
        )
        return paths

    async def export_folder_recursive(
        self,
        folder_id: str,
        output_dir: str | Path,
    ) -> list[Path]:
        """Recursively export Drive folder contents to markdown files.

        Args:
            folder_id: Google Drive folder ID
            output_dir: Directory to write markdown files

        Returns:
            List of paths written
        """
        await logger.info(
            "gdrive_export_folder_start",
            action="gdrive_export_folder_start",
            folder_id=folder_id,
            output_dir=str(output_dir),
        )
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        queue = [folder_id]
        written: list[Path] = []

        while queue:
            current_folder = queue.pop(0)
            results = await self.api.execute_query(
                query=f"'{current_folder}' in parents and trashed=false",
                fields="files(id, name, mimeType, webViewLink)",
                page_size=1000,
                order_by="modifiedTime desc",
            )

            for item in results.get("files", []):
                mime_type = item.get("mimeType")
                if mime_type == "application/vnd.google-apps.folder":
                    queue.append(item["id"])
                    continue

                try:
                    if mime_type == "application/vnd.google-apps.document":
                        tab_paths = await self.export_tabs_to_directory(
                            document_id=item["id"],
                            output_dir=output_dir,
                        )
                        written.extend(tab_paths)
                        continue

                    source = await self.export_as_markdown(document_id=item["id"])
                except Exception:
                    await logger.warning(
                        "gdrive_export_item_failed",
                        action="gdrive_export_item_failed",
                        file_id=item.get("id"),
                        mime_type=mime_type,
                    )
                    continue

                filename = f"{self.api.export._clean_name(item.get('name') or item['id'])}.md"
                output_path = output_dir / filename
                await asyncio.to_thread(
                    output_path.write_text,
                    source.to_markdown(),
                    encoding="utf-8",
                )
                written.append(output_path)

        await logger.info(
            "gdrive_export_folder_complete",
            action="gdrive_export_folder_complete",
            folder_id=folder_id,
            file_count=len(written),
        )

        return written


__all__ = ["GoogleDriveService"]
