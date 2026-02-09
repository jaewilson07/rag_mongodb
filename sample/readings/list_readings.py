"""Sample script to list saved readings from MongoDB.

Usage:
    uv run python sample/readings/list_readings.py
    uv run python sample/readings/list_readings.py --limit 10
"""

from __future__ import annotations

import argparse
import asyncio

from mdrag.server.services.readings import ReadingsService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List saved readings from the knowledge base.",
    )
    parser.add_argument(
        "--limit", type=int, default=20, help="Number of readings to show"
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    service = ReadingsService()
    result = await service.list_readings(limit=args.limit)

    readings = result.get("readings", [])
    total = result.get("total", 0)

    if not readings:
        print("No readings saved yet. Use save_url.py to save your first link.")
        return

    print(f"Saved readings ({len(readings)} of {total}):\n")
    for r in readings:
        media = r.get("media_type", "web")
        icon = "▶" if media == "youtube" else "●"
        title = r.get("title", "Untitled")[:60]
        domain = r.get("domain", "")
        saved = r.get("saved_at", "")[:10]
        tags = ", ".join(r.get("tags", []))

        print(f"  {icon} [{r['id']}] {title}")
        print(f"    {domain}  {saved}  {tags}")
        summary = r.get("summary", "")[:120]
        if summary:
            print(f"    {summary}...")
        print()


if __name__ == "__main__":
    asyncio.run(_run())
