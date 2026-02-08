"""Sample script to crawl a URL and save it as a reading with summary.

Combines the Crawl4AI crawler with the readings pipeline to demonstrate
the full save-and-research flow from a CLI context.

Usage:
    uv run python sample/crawl4ai/crawl_and_save.py --url https://docs.python.org/3/
    uv run python sample/crawl4ai/crawl_and_save.py --url https://news.ycombinator.com --tags tech,news
"""

from __future__ import annotations

import argparse
import asyncio

from mdrag.server.services.readings import ReadingsService

DEFAULT_URL = "https://example.com"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl a URL and save as a reading with AI summary.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="URL to crawl and save")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--deep", action="store_true", help="Enable deep crawl")
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    print(f"Crawling and saving: {args.url}")
    service = ReadingsService()
    result = await service.save_reading(url=args.url, tags=tags)

    print(f"\nStatus: {result.get('status')}")
    print(f"Title: {result.get('title')}")
    print(f"Words: {result.get('word_count', 0)}")
    print(f"\nSummary:\n{result.get('summary', 'N/A')}")

    key_points = result.get("key_points", [])
    if key_points:
        print("\nKey Points:")
        for i, p in enumerate(key_points, 1):
            print(f"  {i}. {p}")

    related = result.get("related_links", [])
    if related:
        print(f"\nRelated ({len(related)}):")
        for link in related:
            print(f"  - {link.get('title')}: {link.get('url')}")


if __name__ == "__main__":
    asyncio.run(_run())
