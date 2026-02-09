"""Sample script to generate content for a single wiki page.

Demonstrates streaming page content generation via RAG:
1. Searches for relevant chunks using the page title
2. Streams LLM-generated markdown content to stdout

Usage:
    uv run python sample/wiki/generate_page.py --title "Architecture Overview"
    uv run python sample/wiki/generate_page.py --title "Data Flow" --wiki "My Project"

Requirements:
    - MongoDB with vector and text indexes
    - LLM API key for content generation
    - Embedding API key for search
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.server.services.wiki import WikiService
from mdrag.settings import load_settings
from utils import check_api_keys, check_mongodb, print_pre_flight_results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate content for a single wiki page via RAG.",
    )
    parser.add_argument(
        "--title",
        default="Architecture Overview",
        help="Page title to generate content for",
    )
    parser.add_argument(
        "--wiki",
        default="Knowledge Base",
        help="Parent wiki title for context",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    
    # Pre-flight checks
    settings = load_settings()
    checks = {
        "MongoDB": await check_mongodb(settings),
        "API Keys": check_api_keys(settings, require_llm=True, require_embedding=True),
    }
    
    if not print_pre_flight_results(checks):
        return
    
    service = WikiService()

    print(f"Generating wiki page: {args.title}")
    print(f"Wiki context: {args.wiki}")
    print("=" * 60)
    print()

    async for chunk in service.stream_page_content(
        page_id="sample-page",
        page_title=args.title,
        source_documents=[],
        wiki_title=args.wiki,
    ):
        print(chunk, end="", flush=True)

    print()
    print()
    print("=" * 60)
    print("Page generation complete.")


if __name__ == "__main__":
    asyncio.run(_run())
