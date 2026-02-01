"""Sample script to recursively export Google Drive folder files to markdown."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from mdrag.mdrag_logging.service_logging import get_logger
from mdrag.integrations.google_drive import GoogleDriveService


logger = get_logger(__name__)

# Google Drive folder ID extracted from the URL
FOLDER_ID = "1MP-1gjdqATyZ30MlvFXLiUy_WyAkh8ly"

# Output directory relative to this script
SCRIPT_DIR = Path(__file__).parent
EXPORT_DIR = SCRIPT_DIR / "EXPORTS"

# Load .env from sample directory
load_dotenv(SCRIPT_DIR.parent.parent / ".env")


async def main() -> None:
    """Recursively export a Google Drive folder using GoogleDriveService."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    await logger.info(f"Export directory: {EXPORT_DIR.absolute()}")

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
        await logger.warning(
            "Missing Google Drive credentials. Set these env vars in sample/.env: "
            + ", ".join(missing)
        )
        return

    service = GoogleDriveService(
        credentials_json=os.getenv("GDOC_CLIENT"),
        token_json=os.getenv("GDOC_TOKEN"),
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )

    await logger.info(f"Processing folder: {FOLDER_ID}")
    written_paths = await service.export_folder_recursive(
        folder_id=FOLDER_ID,
        output_dir=EXPORT_DIR,
    )

    for path in written_paths:
        await logger.info(f"  ✓ Wrote: {path.relative_to(EXPORT_DIR)}")

    await logger.info(f"\n✓ Completed! Wrote {len(written_paths)} file(s)")
    await logger.info(f"Exported to: {EXPORT_DIR.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
