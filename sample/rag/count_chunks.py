"""Sample script to count chunks stored in MongoDB RAG."""

from __future__ import annotations

import asyncio

from mdrag.settings import load_settings
from pymongo import AsyncMongoClient


async def _run() -> None:
    settings = load_settings()
    client = AsyncMongoClient(settings.mongodb_connection_string)
    try:
        db = client[settings.mongodb_database]
        chunks_collection = db[settings.mongodb_collection_chunks]
        documents_collection = db[settings.mongodb_collection_documents]

        chunk_count = await chunks_collection.count_documents({})
        document_count = await documents_collection.count_documents({})

        print("MongoDB RAG counts")
        print(f"Documents: {document_count}")
        print(f"Chunks: {chunk_count}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(_run())
