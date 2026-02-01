# Google Drive Service

Google Drive integration for searching, exporting, and downloading files.

## Overview

This service provides a unified interface for interacting with Google Drive:

- **File Search**: Search files in Google Drive by query, folder, or name
- **Document Export**: Export Google Docs as markdown with optional metadata
- **File Download**: Download binary files (e.g., LoRA models, images)
- **Folder Resolution**: Resolve folder names to IDs for easier navigation

## Features

- **OAuth2 Authentication**: Secure credential management with automatic token refresh
- **Search Operations**: Flexible search with folder filtering and duplicate handling
- **Document Export**: Export Google Docs as markdown with YAML frontmatter
- **Tab Export**: Split Google Docs into per-tab markdown sections
- **Binary Downloads**: Download any file type as bytes (useful for LoRA models)

## Architecture

```
GoogleDriveService (Facade)
    ├── GoogleAuth (OAuth credentials)
    ├── GoogleDrive (Drive API operations)
    └── GoogleDoc (Docs API operations, extends GoogleDrive)
```

## Configuration

**Environment Variables:**

The service supports two credential formats:

**Option 1: JSON Format**
- `GDOC_CLIENT`: OAuth client configuration JSON (from Google Cloud Console)
- `GDOC_TOKEN`: Serialized OAuth token JSON (with refresh token)

**Option 2: Separate Values (uses existing Google OAuth credentials)**
- `GOOGLE_CLIENT_ID` or `CLIENT_ID_GOOGLE_LOGIN`: OAuth client ID
- `GOOGLE_CLIENT_SECRET` or `CLIENT_SECRET_GOOGLE_LOGIN`: OAuth client secret
- `GDOC_TOKEN`: Serialized OAuth token JSON (with refresh token) - **Still required**

**Important:** You need an OAuth token (`GDOC_TOKEN`) to use the API. The client_id and client_secret are used to obtain/refresh the token. If you don't have a token yet, you'll need to run an OAuth flow to obtain one.

## Usage Example

```python
from server.projects.google_drive.service import GoogleDriveService

# Initialize service (reads from env vars)
service = GoogleDriveService()

# Search for files
results = service.search_files("lora", folder_name="My LoRAs")

# Download a file
file_data = service.download_file("file_id_here")

# Export a document
markdown = service.export_as_markdown("document_id_here")
```

## Integration with ComfyUI Workflow

The Google Drive service is integrated with the ComfyUI workflow system to support loading LoRA models from Google Drive:

```python
# In LoRASyncService
lora_path = await lora_sync_service.sync_from_google_drive(
    user_id=user_id,
    google_drive_file_id="file_id",
    lora_filename="my-lora.safetensors"
)
```

## API Classes

### GoogleDriveService
High-level facade for all Google Drive operations.

**Methods:**
- `search_files()`: Search for files
- `search_document_ids()`: Get list of document IDs
- `search_documents()`: Get full file metadata
- `download_file()`: Download binary file
- `export_as_markdown()`: Export document as markdown
- `export_tabs()`: Export document as tabbed markdown

### GoogleDrive
Low-level Drive API wrapper.

**Methods:**
- `execute_query()`: Execute raw Drive API query
- `get_file_metadata()`: Get file metadata
- `download_file()`: Download file as bytes
- `export_as_media()`: Get export request
- `get_file_media()`: Get download request
- `resolve_folder()`: Resolve folder name to ID
- `search()`: Search for files

### GoogleDoc
Docs API wrapper (extends GoogleDrive).

**Methods:**
- `get_by_id()`: Fetch document with optional tabs
- `get_tabs_metadata()`: Get tabs metadata
- `export_tabs()`: Export document as tabbed markdown

### GoogleAuth
OAuth credential management.

**Methods:**
- `get_credentials()`: Get OAuth credentials
- `refresh_if_needed()`: Refresh expired tokens

## Models

- **GoogleDriveFile**: Represents a file or folder in Google Drive
- **SearchResult**: Result of a search query
- **GoogleDocumentTab**: Represents a tab/section in a Google Doc

## Dependencies

- `google-auth`: OAuth2 authentication
- `google-api-python-client`: Google API client
- `markdownify`: HTML to markdown conversion
- `beautifulsoup4`: HTML parsing
- `pyyaml`: YAML frontmatter generation
