"""Initialize MongoDB Atlas Search indexes - simplified version."""

import asyncio
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Add src to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from mdrag.config.settings import load_settings


async def create_vector_search_index(
    client: AsyncIOMotorClient,
    database: str,
    collection: str,
    index_name: str,
) -> bool:
    """Create vector search index on the chunks collection."""
    try:
        db = client[database]
        coll = db[collection]

        # Check if index already exists
        existing_indexes = await coll.list_indexes().to_list(length=None)
        for idx in existing_indexes:
            if idx.get("name") == index_name:
                print(f"✓ Vector index '{index_name}' already exists")
                return True

        # Create vector search index
        result = await db.command(
            {
                "createSearchIndexes": collection,
                "indexes": [
                    {
                        "name": index_name,
                        "type": "vectorSearch",
                        "definition": {
                            "fields": [
                                {
                                    "type": "vector",
                                    "path": "embedding",
                                    "numDimensions": 1536,
                                    "similarity": "cosine",
                                }
                            ]
                        },
                    }
                ],
            }
        )

        print(f"✓ Vector index '{index_name}' created successfully")
        print(f"  Result: {result}")
        return True

    except OperationFailure as e:
        if "CommandNotFound" in str(e) or "not supported" in str(e).lower():
            print(f"❌ Vector search not supported: {e}")
        else:
            print(f"❌ Failed to create vector index: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error creating vector index: {e}")
        return False


async def create_text_search_index(
    client: AsyncIOMotorClient,
    database: str,
    collection: str,
    index_name: str,
) -> bool:
    """Create full-text search index on the chunks collection."""
    try:
        db = client[database]
        coll = db[collection]

        # Check if index already exists
        existing_indexes = await coll.list_indexes().to_list(length=None)
        for idx in existing_indexes:
            if idx.get("name") == index_name:
                print(f"✓ Text index '{index_name}' already exists")
                return True

        # Create Atlas Search index
        result = await db.command(
            {
                "createSearchIndexes": collection,
                "indexes": [
                    {
                        "name": index_name,
                        "type": "search",
                        "definition": {
                            "mappings": {
                                "dynamic": False,
                                "fields": {
                                    "content": {
                                        "type": "string",
                                        "analyzer": "lucene.standard",
                                    }
                                },
                            }
                        },
                    }
                ],
            }
        )

        print(f"✓ Text index '{index_name}' created successfully")
        print(f"  Result: {result}")
        return True

    except OperationFailure as e:
        if "CommandNotFound" in str(e) or "not supported" in str(e).lower():
            print(f"❌ Atlas Search not supported: {e}")
        else:
            print(f"❌ Failed to create text index: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error creating text index: {e}")
        return False


async def main():
    """Main entry point for index initialization."""
    print("=" * 60)
    print("MongoDB Atlas Search Index Initialization")
    print("=" * 60)

    settings = load_settings()
    client = None

    try:
        # Connect to MongoDB
        print("\n1. Connecting to MongoDB...")
        print(
            f"   URI: {settings.mongodb_uri.split('@')[1] if '@' in settings.mongodb_uri else settings.mongodb_uri}"
        )
        client = AsyncIOMotorClient(
            settings.mongodb_uri, serverSelectionTimeoutMS=10000
        )

        # Verify connection
        await client.admin.command("ping")
        print("   ✓ Connected successfully")

        # Get server version
        build_info = await client.admin.command("buildInfo")
        version = build_info.get("version", "unknown")
        print(f"   MongoDB version: {version}")

        # Check collections exist
        db = client[settings.mongodb_database]
        collections = await db.list_collection_names()
        print(f"\n2. Database: {settings.mongodb_database}")
        print(
            f"   Collections: {collections if collections else 'None (will be created on first insert)'}"
        )

        # Create indexes on chunks collection
        print(
            f"\n3. Creating indexes on '{settings.mongodb_collection_chunks}' collection..."
        )

        vector_success = await create_vector_search_index(
            client,
            settings.mongodb_database,
            settings.mongodb_collection_chunks,
            settings.mongodb_vector_index,
        )

        text_success = await create_text_search_index(
            client,
            settings.mongodb_database,
            settings.mongodb_collection_chunks,
            settings.mongodb_text_index,
        )

        print("\n" + "=" * 60)
        if vector_success and text_success:
            print("✓ All indexes initialized successfully")
            print("=" * 60)
            return 0
        else:
            print("⚠ Some indexes failed to initialize")
            print("Note: This is expected if not using MongoDB Atlas Local/Enterprise")
            print("=" * 60)
            return 0  # Don't fail - allow app to start

    except ConnectionFailure as e:
        print(f"\n❌ Failed to connect to MongoDB: {e}")
        print("\nTroubleshooting:")
        print("  1. Check MongoDB is running: docker ps | grep mongodb")
        print("  2. Check connection string in .env file")
        print("  3. Verify MongoDB credentials")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        if client:
            client.close()
            print("\nMongoDB connection closed")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
