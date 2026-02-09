"""Sample script to generate content for a single wiki page.

Demonstrates streaming page content generation via RAG:
1. Searches for relevant chunks using the page title
2. Streams LLM-generated markdown content to stdout

Usage:
    uv run python sample/wiki/generate_page.py --title "Architecture Overview"
    uv run python sample/wiki/generate_page.py --title "Data Flow" --wiki "My Project"
"""

from __future__ import annotations

import argparse
import asyncio

from mdrag.server.services.wiki import WikiService


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
