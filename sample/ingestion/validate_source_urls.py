"""Validate source_url fields stored in vector database.

Usage:
    uv run python sample/ingestion/validate_source_urls.py

Requirements:
    - MongoDB with ingested chunks from web or Google Drive sources
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

from pymongo import AsyncMongoClient

sys.path.insert(0, str(Path(__file__).parent.parent))
from mdrag.settings import load_settings
from utils import check_mongodb, print_pre_flight_results


async def main() -> None:
    settings = load_settings()

    # Pre-flight check
    checks = {
        "MongoDB": await check_mongodb(settings),
    }

    if not print_pre_flight_results(checks):
        return

    client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client[settings.mongodb_database]
    chunks = db[settings.mongodb_collection_chunks]

    invalid = []
    cursor = chunks.find({"source_type": {"$in": ["web", "gdrive"]}})
    async for chunk in cursor:
        source_url = chunk.get("source_url") or ""
        parsed = urlparse(source_url)
        if not (parsed.scheme == "https" and parsed.netloc):
            invalid.append(
                {"chunk_id": str(chunk.get("_id")), "source_url": source_url}
            )

    await client.close()

    if invalid:
        print(f"Invalid source_url entries: {len(invalid)}")
        for item in invalid:
            print(f"- {item['chunk_id']}: {item['source_url']}")
        raise SystemExit(1)

    print("All source_url entries are valid.")


if __name__ == "__main__":
    asyncio.run(main())
