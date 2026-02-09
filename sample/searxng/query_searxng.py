"""Sample script to query SearXNG and export results as Source markdown.

Usage:
    uv run python sample/searxng/query_searxng.py --query "AI developments"
    uv run python sample/searxng/query_searxng.py --query "python tutorials" --result-count 10

Requirements:
    - SearXNG service running (default: http://localhost:7080)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.integrations.models import Source, SourceFrontmatter
from utils import check_searxng, print_pre_flight_results

DEFAULT_QUERY = "what are the agentic ai capabilities of Domo's AI service layer"
DEFAULT_SEARXNG_URL = "http://localhost:7080"
DEFAULT_OUTPUT_DIRNAME = "EXPORTS"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query SearXNG and export results with Source frontmatter.",
    )
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Search query")
    parser.add_argument(
        "--searxng-url",
        default=DEFAULT_SEARXNG_URL,
        help="Base URL for SearXNG (default: http://localhost:7080)",
    )
    parser.add_argument(
        "--result-count",
        type=int,
        default=5,
        help="Number of results to export",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (defaults to sample/searxng/EXPORTS)",
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
    return parser.parse_args()


def _safe_filename(value: str, max_len: int = 80) -> str:
    cleaned = "".join(char if char.isalnum() else "-" for char in value.lower()).strip(
        "-"
    )
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    if not cleaned:
        cleaned = "result"
    return cleaned[:max_len]


async def _query_searxng(
    query: str,
    searxng_url: str,
    result_count: int,
    categories: str | None,
    engines: str | None,
) -> list[dict[str, Any]]:
    params = {
        "q": query,
        "format": "json",
        "pageno": 1,
    }
    if categories:
        params["categories"] = categories
    if engines:
        params["engines"] = engines

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{searxng_url.rstrip('/')}/search", params=params)
        response.raise_for_status()
        data = response.json()

    results = data.get("results", [])
    return results[: max(result_count, 0)]


def _build_source(
    result: dict[str, Any],
    *,
    query: str,
    fetched_at: str,
    rank: int,
    searxng_url: str,
) -> Source:
    title = result.get("title") or "Untitled"
    url = result.get("url") or ""
    content = result.get("content") or ""

    frontmatter = SourceFrontmatter(
        source_type="web",
        source_url=url,
        source_title=title,
        source_fetched_at=fetched_at,
        metadata={
            "query": query,
            "engine": result.get("engine"),
            "score": result.get("score"),
            "rank": rank,
            "searxng_url": searxng_url,
        },
    )

    body_lines = [f"# {title}", "", content.strip()] if content else [f"# {title}"]
    if url:
        body_lines.extend(["", f"Source: {url}"])

    return Source(
        frontmatter=frontmatter,
        content="\n".join(line for line in body_lines if line),
        metadata={"query": query, "rank": rank},
        links=[url] if url else [],
    )


async def _run_export(
    query: str,
    searxng_url: str,
    result_count: int,
    output_dir: Path,
    categories: str | None,
    engines: str | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        results = await _query_searxng(
            query=query,
            searxng_url=searxng_url,
            result_count=result_count,
            categories=categories,
            engines=engines,
        )
    except Exception as exc:
        error_frontmatter = SourceFrontmatter(
            source_type="web",
            source_url=searxng_url,
            source_title="SearXNG query failed",
            source_fetched_at=fetched_at,
            metadata={"query": query, "searxng_url": searxng_url, "error": str(exc)},
        )
        error_source = Source(
            frontmatter=error_frontmatter,
            content=f"SearXNG query failed for: {query}\n\nError: {exc}",
            metadata={"query": query, "error": str(exc)},
        )
        (output_dir / "error.md").write_text(
            error_source.to_markdown(),
            encoding="utf-8",
        )
        return
    if not results:
        empty_frontmatter = SourceFrontmatter(
            source_type="web",
            source_url=searxng_url,
            source_title="SearXNG - No results",
            source_fetched_at=fetched_at,
            metadata={"query": query, "searxng_url": searxng_url},
        )
        empty_source = Source(
            frontmatter=empty_frontmatter,
            content=f"No results returned for: {query}",
            metadata={"query": query},
        )
        (output_dir / "no-results.md").write_text(
            empty_source.to_markdown(),
            encoding="utf-8",
        )
        return

    for idx, result in enumerate(results, start=1):
        source = _build_source(
            result,
            query=query,
            fetched_at=fetched_at,
            rank=idx,
            searxng_url=searxng_url,
        )
        filename = f"{idx:02d}-{_safe_filename(source.frontmatter.source_title or 'result')}.md"
        (output_dir / filename).write_text(
            source.to_markdown(),
            encoding="utf-8",
        )


def main() -> None:
    args = _parse_args()
    sample_dir = Path(__file__).resolve().parent
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else sample_dir / DEFAULT_OUTPUT_DIRNAME
    )

    # Pre-flight check for SearXNG
    async def check_and_run():
        checks = {
            "SearXNG": await check_searxng(args.searxng_url),
        }

        if not print_pre_flight_results(checks):
            print("\n   Setup instructions:")
            print("   1. Start SearXNG: docker-compose up -d searxng")
            print(f"   2. Verify at: {args.searxng_url}")
            return

        await _run_export(
            query=args.query,
            searxng_url=args.searxng_url,
            result_count=args.result_count,
            output_dir=output_dir,
            categories=args.categories,
            engines=args.engines,
        )

    asyncio.run(check_and_run())


if __name__ == "__main__":
    main()
