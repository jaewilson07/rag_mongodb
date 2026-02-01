"""Sample script to ingest a Google Drive file into MongoDB RAG."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from mdrag.ingestion.docling.processor import DocumentProcessor  # type: ignore[import-not-found]
from mdrag.ingestion.ingest import DocumentIngestionPipeline, IngestionConfig  # type: ignore[import-not-found]
from mdrag.integrations.google_drive import GoogleDriveService  # type: ignore[import-not-found]
from mdrag.ingestion.sources.google_drive_source import GoogleDriveServiceAdapter  # type: ignore[import-not-found]
from mdrag.mdrag_logging.service_logging import get_logger  # type: ignore[import-not-found]

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
    pipeline = DocumentIngestionPipeline(
        config=IngestionConfig(),
        documents_folder="documents",
        clean_before_ingest=False,
    )

    missing = [
        name
        for name in (
            "GDOC_CLIENT",
            "GDOC_TOKEN",
        )
        if not os.getenv(name)
    ]
    if missing:
        await logger.warning(
            "Missing Google Drive credentials. Set these env vars in sample/.env: "
            + ", ".join(missing)
        )
        return

    gdrive_service = GoogleDriveService(
        credentials_json=os.getenv("GDOC_CLIENT"),
        token_json=os.getenv("GDOC_TOKEN"),
    )
    pipeline.processor = DocumentProcessor(
        settings=pipeline.settings,
        drive_client=GoogleDriveServiceAdapter(gdrive_service),
    )

    await pipeline.initialize()
    try:
        processed = await pipeline.processor.process_google_file(args.file_id)
        result = await pipeline._ingest_processed_document(processed)
        print("Ingestion complete")
        print(f"Document ID: {result.document_id}")
        print(f"Title: {result.title}")
        print(f"Chunks created: {result.chunks_created}")
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"- {error}")
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(_run())
