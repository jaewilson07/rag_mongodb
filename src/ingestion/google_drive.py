"""Google Drive/Docs ingestion helpers."""

from __future__ import annotations

import io
from typing import Iterable

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"
GOOGLE_SLIDES_MIME_TYPE = "application/vnd.google-apps.presentation"
GOOGLE_DOCX_EXPORT = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
GOOGLE_PDF_EXPORT = "application/pdf"


class GoogleDriveClient:
    """Google Drive client wrapper for service-account access."""

    def __init__(self, service_account_file: str, subject: str | None = None) -> None:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=GOOGLE_DRIVE_SCOPES,
        )
        if subject:
            credentials = credentials.with_subject(subject)

        self._service = build(
            "drive",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    def list_files_in_folder(self, folder_id: str) -> list[dict[str, str]]:
        """List files contained in a Google Drive folder."""
        files: list[dict[str, str]] = []
        page_token: str | None = None

        while True:
            response = (
                self._service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
                    pageToken=page_token,
                )
                .execute()
            )
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return files

    def get_file(self, file_id: str) -> dict[str, str]:
        """Fetch file metadata."""
        return (
            self._service.files()
            .get(
                fileId=file_id,
                fields=(
                    "id, name, mimeType, modifiedTime, size, webViewLink"
                ),
            )
            .execute()
        )

    def download_file(self, file_id: str) -> bytes:
        """Download a Drive file as bytes."""
        request = self._service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()

    def export_file(self, file_id: str, mime_type: str) -> bytes:
        """Export a Google Docs file to the requested mime type."""
        request = self._service.files().export_media(fileId=file_id, mimeType=mime_type)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()


def parse_csv_values(values: str | Iterable[str] | None) -> list[str]:
    """Parse comma-separated values or iterables into a list."""
    if values is None:
        return []
    if isinstance(values, str):
        return [value.strip() for value in values.split(",") if value.strip()]
    return [value.strip() for value in values if value.strip()]
