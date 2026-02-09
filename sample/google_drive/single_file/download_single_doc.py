"""Sample script to download a single Google Doc with tabs exported as separate markdown files.

Usage:
    uv run python sample/google_drive/single_file/download_single_doc.py

Requirements:
    - Google Drive OAuth credentials (GDOC_CLIENT, GDOC_TOKEN, etc.)
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from mdrag.mdrag_logging.service_logging import get_logger
from utils import print_pre_flight_results

from mdrag.integrations.google_drive import GoogleDriveService

logger = get_logger(__name__)

# Google Doc file ID extracted from URL
FILE_ID = "1h7HGpc41HzOHtdcXs6YLpBojYLHVEWxeOAZQTTw7qds"

# Output directory relative to this script
SCRIPT_DIR = Path(__file__).parent
EXPORT_DIR = SCRIPT_DIR / "EXPORTS"

# Load .env from sample directory
load_dotenv(SCRIPT_DIR.parent.parent / ".env")


async def main() -> None:
    """Download and export a single Google Doc using the GoogleDriveService facade."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    await logger.info(f"Export directory: {EXPORT_DIR.absolute()}")

    # Pre-flight check for credentials
    missing = [
        name
        for name in (
            "GDOC_CLIENT",
            "GDOC_TOKEN",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
        )
        if not os.getenv(name)
    ]

    if missing:
        checks = {
            "Google OAuth": {
                "status": "error",
                "message": f"Missing credentials: {', '.join(missing)}",
            }
        }
        print_pre_flight_results(checks)
        print("\n   Setup instructions:")
        print("   1. Create OAuth 2.0 credentials in Google Cloud Console")
        print("   2. Run OAuth flow to get tokens")
        print(
            "   3. Set GDOC_CLIENT, GDOC_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET in .env"
        )
        print("   See sample/google_drive/single_file/README.md for detailed setup")
        return

    service = GoogleDriveService(
        credentials_json=os.getenv("GDOC_CLIENT"),
        token_json=os.getenv("GDOC_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )

    await logger.info(f"Starting export of file: {FILE_ID}")

    written_paths = await service.export_tabs_to_directory(FILE_ID, EXPORT_DIR)
    for path in written_paths:
        await logger.info(f"✓ Wrote: {path.relative_to(EXPORT_DIR)}")

    await logger.info(f"\n✓ Completed! Wrote {len(written_paths)} file(s)")

    await logger.info(f"Exported to: {EXPORT_DIR.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
