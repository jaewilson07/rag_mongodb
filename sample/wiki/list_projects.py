"""Sample script to list wiki projects derived from ingested documents.

Demonstrates the project discovery pipeline that groups
documents by source_type from MongoDB.

Usage:
    uv run python sample/wiki/list_projects.py
"""

from __future__ import annotations

import asyncio

from mdrag.server.services.wiki import WikiService


async def _run() -> None:
    service = WikiService()
    projects = await service.list_projects()

    if not projects:
        print("No projects found. Ingest some documents first.")
        return

    print(f"Found {len(projects)} wiki project(s):\n")
    for p in projects:
        print(f"  [{p['id']}] {p['title']}")
        print(f"    {p['description']}")
        print(f"    Pages: {p['pageCount']}  Sources: {p['sourceCount']}")
        print()


if __name__ == "__main__":
    asyncio.run(_run())
