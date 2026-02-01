"""Google Drive ingestion source implementing the IngestionSource protocol."""

import asyncio
import io
from typing import Any

from googleapiclient.http import MediaIoBaseDownload

from .ingestion_source import IngestionSource
from ..docling.processor import DocumentProcessor, ProcessedDocument
from ...settings import load_settings
from ...integrations.google_drive.service import GoogleDriveService


class GoogleDriveServiceAdapter:
    """Adapter to provide the async drive client interface via GoogleDriveService."""

    def __init__(self, service: GoogleDriveService) -> None:
        self.service = service

    async def get_file(self, file_id: str, fields: str = "*") -> dict[str, Any]:
        return await self.service.api.get_file_metadata(file_id, fields=fields)

    async def export_file(self, file_id: str, mime_type: str) -> bytes:
        request = await self.service.api.export_as_media(file_id, mime_type)

        def _download_sync() -> bytes:
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                _status, done = downloader.next_chunk()
            return file_content.getvalue()

        return await asyncio.to_thread(_download_sync)

    async def download_file(self, file_id: str) -> bytes:
        return await self.service.download_file(file_id)

    async def list_files_in_folder(self, folder_id: str) -> list[dict[str, str]]:
        results = await self.service.api.execute_query(
            query=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType, webViewLink)",
            page_size=1000,
            order_by="modifiedTime desc",
        )
        return results.get("files", [])


class GoogleDriveIngestionSource(IngestionSource):
    def __init__(
        self,
        file_id: str,
        namespace: dict[str, Any] | None = None,
        *,
        gdrive_service: GoogleDriveService | None = None,
        credentials_json: str | None = None,
        token_json: str | None = None,
    ) -> None:
        self.file_id = file_id
        self.namespace = namespace or {}
        self.settings = load_settings()

        service = gdrive_service or GoogleDriveService(
            credentials_json=credentials_json,
            token_json=token_json,
        )
        self.gdrive_service = service
        self.processor = DocumentProcessor(
            self.settings,
            drive_client=GoogleDriveServiceAdapter(service),
        )

    def fetch_and_convert(self, **kwargs) -> ProcessedDocument:
        """
        Fetches a Google Drive file and returns a ProcessedDocument for ingestion.
        """
        # This is a sync wrapper for the async processor
        import asyncio
        import concurrent.futures

        async def _run() -> ProcessedDocument:
            return await self.processor.process_google_file(
                self.file_id,
                self.namespace,
            )

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_run())

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(_run())).result()
