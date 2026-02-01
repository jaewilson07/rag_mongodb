# Single Google Doc Download Sample

This sample demonstrates how to download a single Google Doc with support for multi-tab documents.

## Features

- Downloads a specific Google Doc by ID
- Detects and exports multi-tab documents as separate markdown files
- Falls back to PDF export for single-tab documents or if tab parsing fails
- Uses OAuth or service account authentication

## Usage

1. Set up your credentials in the `.env` file at the sample root:
   ```bash
   # Option 1: OAuth token (recommended)
   GDOC_TOKEN='{"access_token": "...", ...}'
   
   # Option 2: Service account
   GOOGLE_SERVICE_ACCOUNT_FILE="/path/to/service-account.json"
   GOOGLE_IMPERSONATE_SUBJECT="user@example.com"  # Optional
   ```

2. Run the script:
   ```bash
   uv run sample/google_drive/single_file/download_single_doc.py
   ```

3. Check the `EXPORTS/` directory for the downloaded files

## Output Structure

### Single-tab or no tabs
```
EXPORTS/
  Document_Name.pdf
```

### Multi-tab document
```
EXPORTS/
  {file_id}-Document_Name/
    tab-00-Introduction.md
    tab-01-Methods.md
    tab-02-Results.md
```

## Modifying for Your Document

To download a different document, edit the `FILE_ID` constant in `download_single_doc.py`:

```python
# Extract ID from URL: https://docs.google.com/document/d/{FILE_ID}/edit
FILE_ID = "your-document-id-here"
```
