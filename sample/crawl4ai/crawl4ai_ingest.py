"""Sample script to ingest a Crawl4AI URL into MongoDB RAG.

Usage:
    uv run python sample/crawl4ai/crawl4ai_ingest.py --url https://example.com
    uv run python sample/crawl4ai/crawl4ai_ingest.py --url https://example.com --deep --max-depth 2

Requirements:
    - MongoDB for storage
    - Playwright runtime for web crawling
    - Embedding API key for chunk embeddings
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.ingestion.ingest import IngestionWorkflow
from mdrag.ingestion.models import IngestionConfig, WebCollectionRequest
from mdrag.ingestion.sources import Crawl4AICollector
from mdrag.settings import load_settings
from utils import (
    check_api_keys,
    check_mongodb,
    check_playwright,
    print_pre_flight_results,
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
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    
    # Pre-flight checks
    settings = load_settings()
    checks = {
        "MongoDB": await check_mongodb(settings),
        "Playwright": check_playwright(),
        "API Keys": check_api_keys(settings, require_llm=False, require_embedding=True),
    }
    
    if not print_pre_flight_results(checks):
        print("\n   Setup instructions:")
        print("   1. Install Playwright: playwright install")
        print("   2. Set EMBEDDING_API_KEY in .env")
        sys.exit(1)
        return
    
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
