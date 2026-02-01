"""Check MongoDB indexes for the RAG system."""

import asyncio
from pymongo import AsyncMongoClient
from src.settings import load_settings


async def main():
    settings = load_settings()
    client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client[settings.mongodb_database]

    try:
        # List collections
        collections = await db.list_collection_names()
        print(f"Collections: {collections}")

        # Check documents collection indexes
        if settings.mongodb_collection_documents in collections:
            docs = db[settings.mongodb_collection_documents]
            doc_indexes = await docs.list_indexes().to_list(length=None)
            print(f"\nIndexes for '{settings.mongodb_collection_documents}':")
            for idx in doc_indexes:
                print(f"  - {idx.get('name')} keys={idx.get('key')}")

        # Check chunks collection indexes
        if settings.mongodb_collection_chunks in collections:
            chunks = db[settings.mongodb_collection_chunks]
            chunk_indexes = await chunks.list_indexes().to_list(length=None)
            print(f"\nIndexes for '{settings.mongodb_collection_chunks}':")
            for idx in chunk_indexes:
                print(f"  - {idx.get('name')} keys={idx.get('key')}")

    except Exception as e:
        print(f"Error checking indexes: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
