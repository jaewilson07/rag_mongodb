"""Sample script to ingest a local file into MongoDB RAG.

Usage:
    uv run python sample/docling/docling_ingest.py
    uv run python sample/docling/docling_ingest.py --file-path /path/to/document.pdf

Requirements:
    - MongoDB for storage
    - Embedding API key for chunk embeddings
    - Docling + transformers for document processing
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.capabilities.ingestion.ingest import IngestionWorkflow
from mdrag.capabilities.ingestion.models import IngestionConfig, UploadCollectionRequest
from mdrag.capabilities.ingestion.sources import UploadCollector
from mdrag.config.settings import load_settings
from utils import check_api_keys, check_mongodb, print_pre_flight_results

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
    
    # Pre-flight checks
    settings = load_settings()
    checks = {
        "MongoDB": await check_mongodb(settings),
        "API Keys": check_api_keys(settings, require_llm=False, require_embedding=True),
    }
    
    if not print_pre_flight_results(checks):
        sys.exit(1)

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
