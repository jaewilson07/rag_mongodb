"""Validate source_url fields stored in vector database."""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from pymongo import AsyncMongoClient

from src.settings import load_settings


async def main() -> None:
    settings = load_settings()
    client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client[settings.mongodb_database]
    chunks = db[settings.mongodb_collection_chunks]

    invalid = []
    cursor = chunks.find({"source_type": {"$in": ["web", "gdrive"]}})
    async for chunk in cursor:
        source_url = chunk.get("source_url") or ""
        parsed = urlparse(source_url)
        if not (parsed.scheme == "https" and parsed.netloc):
            invalid.append({"chunk_id": str(chunk.get("_id")), "source_url": source_url})

    await client.close()

    if invalid:
        print(f"Invalid source_url entries: {len(invalid)}")
        for item in invalid:
            print(f"- {item['chunk_id']}: {item['source_url']}")
        raise SystemExit(1)

    print("All source_url entries are valid.")


if __name__ == "__main__":
    asyncio.run(main())
