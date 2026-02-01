"""Configuration constants for Google Drive API operations."""

# Default folder ID for searches when no folder is specified
# This points to a shared DataCrew content folder
DEFAULT_FOLDER_ID = "13ICM72u7cnvCb0ATpVXdHWqxH1SmiG_Q"

# Default fields to retrieve when querying Drive API
DEFAULT_FIELDS = "files(id, name, mimeType, createdTime, modifiedTime, webViewLink, parents, size)"

# Default page size for API queries
DEFAULT_PAGE_SIZE = 10

# Default ordering for search results
DEFAULT_ORDER_BY = "modifiedTime desc"

# MIME types for common Google Workspace documents
GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"
GOOGLE_SHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES_MIME_TYPE = "application/vnd.google-apps.presentation"
GOOGLE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

# Export MIME types for different formats
EXPORT_MIME_TYPES = {
    "markdown": "text/plain",
    "html": "text/html",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Common export MIME types
GOOGLE_PDF_EXPORT = EXPORT_MIME_TYPES["pdf"]


__all__ = [
    "DEFAULT_FIELDS",
    "DEFAULT_FOLDER_ID",
    "DEFAULT_ORDER_BY",
    "DEFAULT_PAGE_SIZE",
    "EXPORT_MIME_TYPES",
    "GOOGLE_PDF_EXPORT",
    "GOOGLE_DOC_MIME_TYPE",
    "GOOGLE_FOLDER_MIME_TYPE",
    "GOOGLE_SHEET_MIME_TYPE",
    "GOOGLE_SLIDES_MIME_TYPE",
]
