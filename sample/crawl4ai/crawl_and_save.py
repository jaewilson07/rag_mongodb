"""Sample script to crawl a URL and save it as a reading with summary.

Combines the Crawl4AI crawler with the readings pipeline to demonstrate
the full save-and-research flow from a CLI context.

Usage:
    uv run python sample/crawl4ai/crawl_and_save.py --url https://docs.python.org/3/
    uv run python sample/crawl4ai/crawl_and_save.py --url https://news.ycombinator.com --tags tech,news

Requirements:
    - MongoDB for storage
    - Redis for job queue
    - SearXNG for related content search
    - LLM API key for summarization
    - Playwright runtime for web crawling
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.server.services.readings import ReadingsService
from mdrag.settings import load_settings
from utils import (
    check_api_keys,
    check_mongodb,
    check_playwright,
    check_redis,
    check_searxng,
    print_pre_flight_results,
)

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

    # Pre-flight checks
    settings = load_settings()
    redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
    searxng_url = getattr(settings, "searxng_url", "http://localhost:7080")

    checks = {
        "MongoDB": await check_mongodb(settings),
        "Redis": await check_redis(redis_url),
        "SearXNG": await check_searxng(searxng_url),
        "Playwright": check_playwright(),
        "API Keys": check_api_keys(settings, require_llm=True, require_embedding=False),
    }

    if not print_pre_flight_results(checks):
        print("\n   Setup instructions:")
        print("   1. Start services: docker-compose up -d redis searxng")
        print("   2. Install Playwright: playwright install")
        print("   3. Set LLM_API_KEY in .env")
        return

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
