"""Sample script to ingest a Google Drive file into MongoDB RAG.

Usage:
    uv run python sample/google_drive/google_drive_ingest.py
    uv run python sample/google_drive/google_drive_ingest.py --file-id "1h7HGpc41HzOHtdcXs6YLpBojYLHVEWxeOAZQTTw7qds"

Requirements:
    - MongoDB for storage
    - Google Drive API credentials (service account or OAuth)
    - Embedding API key for chunk embeddings
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.ingestion.ingest import IngestionWorkflow
from mdrag.ingestion.models import GoogleDriveCollectionRequest, IngestionConfig
from mdrag.ingestion.sources import GoogleDriveCollector
from mdrag.mdrag_logging.service_logging import get_logger
from mdrag.settings import load_settings
from utils import (
    check_api_keys,
    check_google_credentials,
    check_mongodb,
    print_pre_flight_results,
)

DEFAULT_FILE_ID = "1h7HGpc41HzOHtdcXs6YLpBojYLHVEWxeOAZQTTw7qds"
SCRIPT_DIR = Path(__file__).parent
logger = get_logger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a Google Drive file into MongoDB RAG.",
    )
    parser.add_argument(
        "--file-id",
        default=DEFAULT_FILE_ID,
        help="Google Drive file ID to ingest",
    )
    return parser.parse_args()


async def _run() -> None:
    load_dotenv(SCRIPT_DIR.parent.parent / ".env")
    args = _parse_args()
    settings = load_settings()

    # Pre-flight checks
    checks = {
        "MongoDB": await check_mongodb(settings),
        "Google Credentials": check_google_credentials(settings),
        "API Keys": check_api_keys(settings, require_llm=False, require_embedding=True),
    }

    if not print_pre_flight_results(checks):
        print("\n   Setup instructions:")
        print("   1. Create service account in Google Cloud Console")
        print("   2. Download JSON key and set GOOGLE_SERVICE_ACCOUNT_FILE in .env")
        sys.exit(1)
        print("   3. Share target files/folders with service account email")
        print("   4. Set EMBEDDING_API_KEY in .env")
        return

    workflow = IngestionWorkflow(config=IngestionConfig(), settings=settings)
    await workflow.initialize()
    try:
        collector = GoogleDriveCollector(settings=settings)
        results = await workflow.ingest_collector(
            collector,
            GoogleDriveCollectionRequest(file_ids=[args.file_id]),
        )
        for result in results:
            print("Ingestion complete")
            print(f"Document UID: {result.document_uid}")
            print(f"Title: {result.title}")
            print(f"Chunks created: {result.chunks_created}")
            if result.errors:
                print("Errors:")
                for error in result.errors:
                    print(f"- {error}")
    finally:
        await workflow.close()


if __name__ == "__main__":
    asyncio.run(_run())
