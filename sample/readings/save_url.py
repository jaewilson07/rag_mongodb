"""Sample script to save a URL via the readings pipeline.

Demonstrates the full save-and-research workflow:
1. Crawl the URL (or extract YouTube transcript)
2. Generate AI summary with key points
3. Search for related content via SearXNG
4. Store in MongoDB and queue for RAG ingestion

Usage:
    uv run python sample/readings/save_url.py --url https://example.com
    uv run python sample/readings/save_url.py --url "https://youtu.be/PAh870We7tI"
    uv run python sample/readings/save_url.py --url "https://x.com/user/status/123" --tags ai,tech

Requirements:
    - MongoDB for storage
    - Redis for job queue
    - SearXNG for related content search
    - LLM API key for summarization
    - Crawl4AI + Playwright for web crawling
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.interfaces.api.services.readings import ReadingsService
from mdrag.config.settings import load_settings
from utils import (
    check_api_keys,
    check_mongodb,
    check_redis,
    check_rq_workers,
    check_searxng,
    print_pre_flight_results,
)

DEFAULT_URL = "https://example.com"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Save a URL: crawl, summarize, research, and ingest.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="URL to save")
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags (e.g., ai,tech,video)",
    )
    parser.add_argument(
        "--source-group",
        default=None,
        help="Source group (defaults to domain)",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    
    # Pre-flight checks
    settings = load_settings()
    redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379/0')
    searxng_url = getattr(settings, 'searxng_url', 'http://localhost:7080')
    
    checks = {
        "MongoDB": await check_mongodb(settings),
        "Redis": await check_redis(redis_url),
        "RQ Workers": check_rq_workers(redis_url),
        "SearXNG": await check_searxng(searxng_url),
        "API Keys": check_api_keys(settings, require_llm=True, require_embedding=False),
    }
    
    if not print_pre_flight_results(checks):
        print("\n   Setup instructions:")
        print("   1. Start services: docker-compose up -d redis searxng")
        print("   2. Start RQ worker: uv run rq worker default --url redis://localhost:6379/0")
        print("   3. Set LLM_API_KEY in .env")
        print("   4. For web crawling: playwright install")
        sys.exit(1)
    
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    print(f"Saving URL: {args.url}")
    if tags:
        print(f"Tags: {tags}")
    print()

    service = ReadingsService()
    result = await service.save_reading(
        url=args.url,
        tags=tags,
        source_group=args.source_group,
    )

    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Title: {result.get('title', 'Untitled')}")
    print(f"Media Type: {result.get('media_type', 'web')}")
    print(f"Word Count: {result.get('word_count', 0)}")
    print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(result.get("summary", "No summary available."))
    print()

    # Key points
    key_points = result.get("key_points", [])
    if key_points:
        print("KEY POINTS")
        print("-" * 40)
        for i, point in enumerate(key_points, 1):
            print(f"  {i}. {point}")
        print()

    # Related links
    related = result.get("related_links", [])
    if related:
        print("RELATED LINKS")
        print("-" * 40)
        for link in related:
            print(f"  - {link.get('title', 'Untitled')}")
            print(f"    {link.get('url', '')}")
            print(f"    {link.get('snippet', '')[:100]}...")
            print()

    # YouTube metadata
    yt = result.get("youtube")
    if yt:
        print("YOUTUBE METADATA")
        print("-" * 40)
        print(f"  Video ID: {yt.get('video_id', '')}")
        print(f"  Channel: {yt.get('channel', '')}")
        print(f"  Duration: {yt.get('duration_display', '')}")
        print(f"  Views: {yt.get('view_count', 0):,}")
        print(f"  Transcript: {'Yes' if yt.get('has_transcript') else 'No'}")
        chapters = yt.get("chapters", [])
        if chapters:
            print(f"  Chapters: {len(chapters)}")
            for ch in chapters[:5]:
                m, s = divmod(int(ch.get("start_time", 0)), 60)
                print(f"    [{m}:{s:02d}] {ch.get('title', '')}")
        print()

    # Ingestion job
    job_id = result.get("ingestion_job_id")
    if job_id:
        print(f"Ingestion Job ID: {job_id}")

    print()
    print("Full result JSON:")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(_run())
