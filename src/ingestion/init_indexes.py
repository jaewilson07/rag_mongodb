"""Initialize MongoDB search indexes for Docker deployment."""

import asyncio
import logging
import sys
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

from src.logging_config import configure_logging
from src.settings import Settings

logger = logging.getLogger(__name__)


async def create_vector_search_index(
    client: AsyncMongoClient, database: str, collection: str, index_name: str
) -> bool:
    """
    Create vector search index on the chunks collection.

    Args:
        client: MongoDB client
        database: Database name
        collection: Collection name
        index_name: Index name

    Returns:
        True if index was created or already exists, False otherwise
    """
    try:
        db = client[database]
        coll = db[collection]

        # Check if index already exists
        existing_indexes = await coll.list_indexes().to_list(length=None)
        for idx in existing_indexes:
            if idx.get("name") == index_name:
                logger.info(
                    "Vector search index '%s' already exists (database=%s collection=%s)",
                    index_name,
                    database,
                    collection,
                )
                return True

        # Create vector search index
        # Note: This requires MongoDB Enterprise with vector search support
        await db.command(
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

        logger.info(
            "Vector search index '%s' created successfully (database=%s collection=%s)",
            index_name,
            database,
            collection,
        )
        return True

    except OperationFailure as e:
        if "CommandNotFound" in str(e) or "not supported" in str(e).lower():
            logger.error(
                "Vector search not supported. MongoDB Enterprise Edition with vector search is required. error=%s",
                str(e),
            )
        else:
            logger.error(
                "Failed to create vector search index: %s (database=%s collection=%s)",
                str(e),
                database,
                collection,
            )
        return False
    except Exception as e:
        logger.error(
            "Unexpected error creating vector search index: %s (database=%s collection=%s)",
            str(e),
            database,
            collection,
        )
        return False


async def create_text_search_index(
    client: AsyncMongoClient, database: str, collection: str, index_name: str
) -> bool:
    """
    Create full-text search index on the chunks collection.

    Args:
        client: MongoDB client
        database: Database name
        collection: Collection name
        index_name: Index name

    Returns:
        True if index was created or already exists, False otherwise
    """
    try:
        db = client[database]
        coll = db[collection]

        # Check if index already exists
        existing_indexes = await coll.list_indexes().to_list(length=None)
        for idx in existing_indexes:
            if idx.get("name") == index_name:
                logger.info(
                    "Text search index '%s' already exists (database=%s collection=%s)",
                    index_name,
                    database,
                    collection,
                )
                return True

        # Create Atlas Search index
        # Note: This requires MongoDB Enterprise with Atlas Search support
        await db.command(
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

        logger.info(
            "Text search index '%s' created successfully (database=%s collection=%s)",
            index_name,
            database,
            collection,
        )
        return True

    except OperationFailure as e:
        if "CommandNotFound" in str(e) or "not supported" in str(e).lower():
            logger.error(
                "Atlas Search not supported. MongoDB Enterprise Edition with Atlas Search is required. error=%s",
                str(e),
            )
        else:
            logger.error(
                "Failed to create text search index: %s (database=%s collection=%s)",
                str(e),
                database,
                collection,
            )
        return False
    except Exception as e:
        logger.error(
            "Unexpected error creating text search index: %s (database=%s collection=%s)",
            str(e),
            database,
            collection,
        )
        return False


async def initialize_indexes() -> bool:
    """
    Initialize all required MongoDB indexes for the RAG system.

    Returns:
        True if all indexes were created successfully, False otherwise
    """
    configure_logging()
    settings = Settings()
    client = None

    try:
        # Connect to MongoDB
        logger.info("Connecting to MongoDB...")
        client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=10000)

        # Verify connection
        await client.admin.command("ping")
        logger.info("Connected to MongoDB successfully")

        # Get server version
        build_info = await client.admin.command("buildInfo")
        version = build_info.get("version", "unknown")
        logger.info(f"MongoDB version: {version}")

        # Create vector search index
        vector_success = await create_vector_search_index(
            client,
            settings.mongodb_database,
            settings.mongodb_collection_chunks,
            settings.mongodb_vector_index,
        )

        # Create text search index
        text_success = await create_text_search_index(
            client,
            settings.mongodb_database,
            settings.mongodb_collection_chunks,
            settings.mongodb_text_index,
        )

        if vector_success and text_success:
            logger.info("All indexes initialized successfully")
            return True
        else:
            logger.warning(
                "Some indexes failed to initialize. Check if you're using MongoDB Enterprise Edition."
            )
            logger.warning(
                "For development, you can use MongoDB Atlas which includes these features on the free tier."
            )
            return False

    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during index initialization: {e}")
        return False
    finally:
        if client:
            await client.close()
            logger.info("MongoDB connection closed")


async def main():
    """Main entry point for index initialization."""
    configure_logging()
    logger.info("Starting MongoDB index initialization...")

    success = await initialize_indexes()

    if success:
        logger.info("Index initialization completed successfully")
        sys.exit(0)
    else:
        logger.warning(
            "Index initialization completed with warnings. "
            "Vector and text search may not be available."
        )
        # Don't fail completely - allow the app to start
        # Users can fallback to MongoDB Atlas if needed
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
