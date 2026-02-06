"""Sample script to ingest a local file into MongoDB RAG."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from mdrag.ingestion.ingest import IngestionWorkflow
from mdrag.ingestion.models import IngestionConfig, UploadCollectionRequest
from mdrag.ingestion.sources import UploadCollector

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
    workflow = IngestionWorkflow(config=IngestionConfig())
    await workflow.initialize()
    try:
        collector = UploadCollector()
        results = await workflow.ingest_sources(
            await collector.collect(
                UploadCollectionRequest(
                    filename=Path(args.file_path).name,
                    file_path=args.file_path,
                )
            )
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
