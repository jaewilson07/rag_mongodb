"""Sample script to ingest a local file into MongoDB RAG."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from mdrag.ingestion.ingest import DocumentIngestionPipeline, IngestionConfig  # type: ignore[import-not-found]
from mdrag.ingestion.sources.upload_source import (  # type: ignore[import-not-found]
    UploadIngestionSource,
)

DEFAULT_FILE = Path(__file__).resolve().parent / "pydantic.txt"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a local file into MongoDB RAG.",
    )
    parser.add_argument(
        "--file-path",
        default=str(DEFAULT_FILE),
        help="Path to local file to ingest",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    pipeline = DocumentIngestionPipeline(
        config=IngestionConfig(),
        documents_folder="documents",
        clean_before_ingest=False,
    )

    await pipeline.initialize()
    try:
        source = UploadIngestionSource(file_path=args.file_path)
        processed = source.fetch_and_convert()
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
