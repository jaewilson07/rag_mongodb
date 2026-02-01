"""Sample script to ingest a Crawl4AI URL into MongoDB RAG."""

from __future__ import annotations

import argparse
import asyncio

from mdrag.ingestion.ingest import DocumentIngestionPipeline, IngestionConfig  # type: ignore[import-not-found]
from mdrag.ingestion.sources.crawl4ai_source import (  # type: ignore[import-not-found]
    Crawl4AIIngestionSource,
)

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
    parser.add_argument(
        "--page-index",
        type=int,
        default=0,
        help="Select which page to ingest from a deep crawl",
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
        source = Crawl4AIIngestionSource(
            url=args.url,
            deep=bool(args.deep),
            max_depth=args.max_depth,
            page_index=args.page_index,
        )
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
