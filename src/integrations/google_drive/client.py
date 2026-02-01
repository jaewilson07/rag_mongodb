"""Async Google Drive client using service account credentials."""

from __future__ import annotations

import asyncio
import io
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from ...mdrag_logging.service_logging import get_logger
from .classes.config import (
    DEFAULT_FIELDS,
    DEFAULT_ORDER_BY,
    GOOGLE_DOC_MIME_TYPE,
    GOOGLE_SLIDES_MIME_TYPE,
)

logger = get_logger(__name__)


class AsyncGoogleDriveClient:
    """Minimal async Google Drive client for ingestion use cases."""

    def __init__(self, service_account_file: str | None, subject: str | None = None) -> None:
        if not service_account_file:
            raise ValueError("Google service account file is required")

        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        if subject:
            credentials = credentials.with_subject(subject)

        self._service = build("drive", "v3", credentials=credentials)

    async def get_file(self, file_id: str, fields: str = "*") -> dict[str, Any]:
        """Return Drive file metadata."""
        await logger.debug(
            "gdrive_get_file_start",
            action="gdrive_get_file_start",
            file_id=file_id,
        )
        return await asyncio.to_thread(
            lambda: self._service.files().get(fileId=file_id, fields=fields).execute()
        )

    async def export_file(self, file_id: str, mime_type: str) -> bytes:
        """Export a Google Workspace file as the requested MIME type."""
        await logger.info(
            "gdrive_export_file_start",
            action="gdrive_export_file_start",
            file_id=file_id,
            mime_type=mime_type,
        )
        request = await asyncio.to_thread(
            lambda: self._service.files().export_media(fileId=file_id, mimeType=mime_type)
        )

        def _download_sync() -> bytes:
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                _status, done = downloader.next_chunk()
            return file_content.getvalue()

        content = await asyncio.to_thread(_download_sync)
        await logger.info(
            "gdrive_export_file_complete",
            action="gdrive_export_file_complete",
            file_id=file_id,
            size_bytes=len(content),
        )
        return content

    async def download_file(self, file_id: str) -> bytes:
        """Download a file as binary data."""
        await logger.info(
            "gdrive_download_file_start",
            action="gdrive_download_file_start",
            file_id=file_id,
        )
        request = await asyncio.to_thread(
            lambda: self._service.files().get_media(fileId=file_id)
        )

        def _download_sync() -> bytes:
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                _status, done = downloader.next_chunk()
            return file_content.getvalue()

        content = await asyncio.to_thread(_download_sync)
        await logger.info(
            "gdrive_download_file_complete",
            action="gdrive_download_file_complete",
            file_id=file_id,
            size_bytes=len(content),
        )
        return content

    async def list_files_in_folder(self, folder_id: str) -> list[dict[str, str]]:
        """List files within a Google Drive folder."""
        await logger.info(
            "gdrive_list_folder_start",
            action="gdrive_list_folder_start",
            folder_id=folder_id,
        )
        query = f"'{folder_id}' in parents and trashed = false"
        files: list[dict[str, str]] = []
        page_token: str | None = None

        while True:
            response = await asyncio.to_thread(
                lambda: self._service.files()
                .list(
                    q=query,
                    fields=f"nextPageToken,{DEFAULT_FIELDS}",
                    orderBy=DEFAULT_ORDER_BY,
                    pageToken=page_token,
                )
                .execute()
            )
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        await logger.info(
            "gdrive_list_folder_complete",
            action="gdrive_list_folder_complete",
            folder_id=folder_id,
            file_count=len(files),
        )
        return files

    @staticmethod
    def is_google_workspace_mime(mime_type: str) -> bool:
        return mime_type in {GOOGLE_DOC_MIME_TYPE, GOOGLE_SLIDES_MIME_TYPE}


__all__ = ["AsyncGoogleDriveClient"]