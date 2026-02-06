"""Sample script to ingest a Crawl4AI URL into MongoDB RAG."""

from __future__ import annotations

import argparse
import asyncio

from mdrag.ingestion.ingest import IngestionWorkflow
from mdrag.ingestion.models import IngestionConfig, WebCollectionRequest
from mdrag.ingestion.sources import Crawl4AICollector

DEFAULT_URL = "https://example.com"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a web page via Crawl4AI into MongoDB RAG.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="URL to crawl")
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Enable deep crawl (defaults to single page)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum depth for deep crawl",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    workflow = IngestionWorkflow(config=IngestionConfig())
    await workflow.initialize()
    try:
        collector = Crawl4AICollector()
        results = await workflow.ingest_collector(
            collector,
            WebCollectionRequest(
                url=args.url,
                deep=bool(args.deep),
                max_depth=args.max_depth,
            ),
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
