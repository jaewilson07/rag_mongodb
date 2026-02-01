"""Google Drive integration for searching, exporting, and downloading files.

This service provides a unified interface for:
- Searching files in Google Drive
- Exporting documents as markdown with optional metadata
- Downloading binary files (e.g., LoRA models)
- Resolving folder names to IDs
"""

from .classes import (
    DEFAULT_FOLDER_ID,
    GoogleAuth,
    GoogleDoc,
    GoogleDrive,
)
from .classes.config import (
    GOOGLE_DOC_MIME_TYPE,
    GOOGLE_PDF_EXPORT,
    GOOGLE_SLIDES_MIME_TYPE,
)
from .client import AsyncGoogleDriveClient
from .models import GoogleDocumentTab, GoogleDriveFile, SearchResult
from .service import GoogleDriveService


def parse_csv_values(value: str | None) -> list[str] | None:
    """Parse comma-separated values into a list of non-empty strings."""
    if not value:
        return None
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
        cleaned = [item for item in items if item]
        return cleaned or None
    return None

__all__ = [
    "AsyncGoogleDriveClient",
    "DEFAULT_FOLDER_ID",
    "GOOGLE_DOC_MIME_TYPE",
    "GOOGLE_PDF_EXPORT",
    "GOOGLE_SLIDES_MIME_TYPE",
    "GoogleAuth",
    "GoogleDoc",
    "GoogleDocumentTab",
    "GoogleDrive",
    "GoogleDriveFile",
    "GoogleDriveService",
    "SearchResult",
    "parse_csv_values",
]
