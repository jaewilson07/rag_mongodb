"""Sample script to ingest a Google Drive file into MongoDB RAG."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from mdrag.ingestion.ingest import IngestionWorkflow
from mdrag.ingestion.models import GoogleDriveCollectionRequest, IngestionConfig
from mdrag.ingestion.sources import GoogleDriveCollector
from mdrag.mdrag_logging.service_logging import get_logger
from mdrag.settings import load_settings

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
    if not settings.google_service_account_file:
        await logger.warning(
            "Missing Google service account credentials. Set GOOGLE_SERVICE_ACCOUNT_FILE."
        )
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
