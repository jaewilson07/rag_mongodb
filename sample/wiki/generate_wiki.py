"""Sample script to generate a knowledge wiki from ingested documents.

Demonstrates the wiki structure generation pipeline:
1. Queries MongoDB for ingested documents
2. Uses LLM to organize into sections and pages
3. Prints the resulting structure

Usage:
    uv run python sample/wiki/generate_wiki.py
    uv run python sample/wiki/generate_wiki.py --title "API Reference"
    uv run python sample/wiki/generate_wiki.py --source-type web

Requirements:
    - MongoDB with ingested documents
    - LLM API key for structure generation
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.server.services.wiki import WikiService
from mdrag.settings import load_settings
from utils import check_api_keys, check_mongodb, print_pre_flight_results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a knowledge wiki structure from ingested data.",
    )
    parser.add_argument(
        "--title",
        default="Knowledge Base Wiki",
        help="Wiki title (default: Knowledge Base Wiki)",
    )
    parser.add_argument(
        "--source-type",
        default=None,
        help="Filter by source_type (web, gdrive, upload)",
    )
    return parser.parse_args()


async def _run() -> None:
    args = _parse_args()
    
    # Pre-flight checks
    settings = load_settings()
    checks = {
        "MongoDB": await check_mongodb(settings),
        "API Keys": check_api_keys(settings, require_llm=True, require_embedding=False),
    }
    
    if not print_pre_flight_results(checks):
        return
    
    service = WikiService()

    filters = {}
    if args.source_type:
        filters["source_type"] = args.source_type

    print(f"Generating wiki: {args.title}")
    if filters:
        print(f"Filters: {filters}")
    print()

    structure = await service.generate_structure(
        title=args.title,
        filters=filters,
    )

    print(f"Wiki ID: {structure['id']}")
    print(f"Title: {structure['title']}")
    print(f"Description: {structure['description']}")
    print(f"Sections: {len(structure.get('sections', []))}")
    print(f"Pages: {len(structure.get('pages', []))}")
    print()

    for section in structure.get("sections", []):
        print(f"  [{section['id']}] {section['title']}")
        for page_id in section.get("pages", []):
            page = next(
                (p for p in structure["pages"] if p["id"] == page_id), None
            )
            if page:
                importance = page.get("importance", "medium")
                sources = len(page.get("sourceDocuments", []))
                print(f"    - {page['title']} ({importance}, {sources} sources)")

    print()
    print("Full structure JSON:")
    print(json.dumps(structure, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(_run())
