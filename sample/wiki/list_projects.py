"""Sample script to list wiki projects derived from ingested documents.

Demonstrates the project discovery pipeline that groups
documents by source_type from MongoDB.

Usage:
    uv run python sample/wiki/list_projects.py

Requirements:
    - MongoDB with ingested documents
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.server.services.wiki import WikiService
from mdrag.settings import load_settings
from utils import check_mongodb, print_pre_flight_results


async def _run() -> None:
    # Pre-flight checks
    settings = load_settings()
    checks = {
        "MongoDB": await check_mongodb(settings),
    }
    
    if not print_pre_flight_results(checks):
        return
    
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
