"""Sample script to ingest a SearXNG result into MongoDB RAG."""

from __future__ import annotations

import argparse
import asyncio

from mdrag.ingestion.ingest import DocumentIngestionPipeline, IngestionConfig  # type: ignore[import-not-found]
from mdrag.ingestion.sources.searxng_source import (  # type: ignore[import-not-found]
    SearXNGIngestionSource,
)

DEFAULT_QUERY = "latest AI agent updates"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query SearXNG and ingest a result URL into MongoDB RAG.",
    )
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Search query")
    parser.add_argument(
        "--result-index",
        type=int,
        default=0,
        help="Which result index to ingest (0-based)",
    )
    parser.add_argument(
        "--result-count",
        type=int,
        default=5,
        help="Number of results to fetch from SearXNG",
    )
    parser.add_argument(
        "--categories",
        default=None,
        help="Optional SearXNG categories filter (general, news, etc.)",
    )
    parser.add_argument(
        "--engines",
        default=None,
        help="Comma-separated list of engines to use",
    )
    parser.add_argument(
        "--searxng-url",
        default=None,
        help="Override the SearXNG base URL",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    engines = [engine.strip() for engine in args.engines.split(",")] if args.engines else None

    pipeline = DocumentIngestionPipeline(
        config=IngestionConfig(),
        documents_folder="documents",
        clean_before_ingest=False,
    )

    await pipeline.initialize()
    try:
        source = SearXNGIngestionSource(
            query=args.query,
            result_index=args.result_index,
            result_count=args.result_count,
            categories=args.categories,
            engines=engines,
            searxng_url=args.searxng_url,
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
