"""Initialize MongoDB search indexes for Docker deployment."""

import asyncio
import sys
from pathlib import Path

from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

ROOT_DIR = Path(__file__).resolve().parents[2]


def _load_logging():
    from mdrag.mdrag_logging.service_logging import (  # type: ignore[reportMissingImports]
        get_logger,
        setup_logging,
    )

    return get_logger, setup_logging


async def create_vector_search_index(
    client: AsyncMongoClient,
    database: str,
    collection: str,
    index_name: str,
    logger,
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
        cursor = await coll.list_indexes()
        existing_indexes = await cursor.to_list(length=None)
        for idx in existing_indexes:
            if idx.get("name") == index_name:
                await logger.info(
                    "vector_index_exists",
                    action="vector_index_exists",
                    index_name=index_name,
                    database=database,
                    collection=collection,
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

        await logger.info(
            "vector_index_created",
            action="vector_index_created",
            index_name=index_name,
            database=database,
            collection=collection,
        )
        return True

    except OperationFailure as e:
        if "CommandNotFound" in str(e) or "not supported" in str(e).lower():
            await logger.error(
                "vector_index_not_supported",
                action="vector_index_not_supported",
                error=str(e),
            )
        else:
            await logger.error(
                "vector_index_create_failed",
                action="vector_index_create_failed",
                error=str(e),
                database=database,
                collection=collection,
            )
        return False
    except Exception as e:
        await logger.error(
            "vector_index_create_unexpected_error",
            action="vector_index_create_unexpected_error",
            error=str(e),
            error_type=type(e).__name__,
            database=database,
            collection=collection,
        )
        return False


async def create_text_search_index(
    client: AsyncMongoClient,
    database: str,
    collection: str,
    index_name: str,
    logger,
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
        cursor = await coll.list_indexes()
        existing_indexes = await cursor.to_list(length=None)
        for idx in existing_indexes:
            if idx.get("name") == index_name:
                await logger.info(
                    "text_index_exists",
                    action="text_index_exists",
                    index_name=index_name,
                    database=database,
                    collection=collection,
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

        await logger.info(
            "text_index_created",
            action="text_index_created",
            index_name=index_name,
            database=database,
            collection=collection,
        )
        return True

    except OperationFailure as e:
        if "CommandNotFound" in str(e) or "not supported" in str(e).lower():
            await logger.error(
                "text_index_not_supported",
                action="text_index_not_supported",
                error=str(e),
            )
        else:
            await logger.error(
                "text_index_create_failed",
                action="text_index_create_failed",
                error=str(e),
                database=database,
                collection=collection,
            )
        return False
    except Exception as e:
        await logger.error(
            "text_index_create_unexpected_error",
            action="text_index_create_unexpected_error",
            error=str(e),
            error_type=type(e).__name__,
            database=database,
            collection=collection,
        )
        return False


async def initialize_indexes(logger) -> bool:
    """
    Initialize all required MongoDB indexes for the RAG system.

    Returns:
        True if all indexes were created successfully, False otherwise
    """
    from mdrag.config.settings import Settings  # type: ignore[reportMissingImports]

    settings = Settings()
    client = None

    try:
        # Connect to MongoDB
        await logger.info("Connecting to MongoDB...")
        client = AsyncMongoClient(
            settings.mongodb_connection_string, serverSelectionTimeoutMS=10000
        )

        # Verify connection
        await client.admin.command("ping")
        await logger.info("Connected to MongoDB successfully")

        # Get server version
        build_info = await client.admin.command("buildInfo")
        version = build_info.get("version", "unknown")
        await logger.info(f"MongoDB version: {version}")

        # Create vector search index
        vector_success = await create_vector_search_index(
            client,
            settings.mongodb_database,
            settings.mongodb_collection_chunks,
            settings.mongodb_vector_index,
            logger,
        )

        # Create text search index
        text_success = await create_text_search_index(
            client,
            settings.mongodb_database,
            settings.mongodb_collection_chunks,
            settings.mongodb_text_index,
            logger,
        )

        if vector_success and text_success:
            await logger.info("All indexes initialized successfully")
            return True
        else:
            await logger.warning(
                "Some indexes failed to initialize. Check if you're using MongoDB Enterprise Edition."
            )
            await logger.warning(
                "For development, you can use MongoDB Atlas which includes these features on the free tier."
            )
            return False

    except ConnectionFailure as e:
        await logger.error(f"Failed to connect to MongoDB: {e}")
        return False
    except Exception as e:
        await logger.error(f"Unexpected error during index initialization: {e}")
        return False
    finally:
        if client:
            await client.close()
            await logger.info("MongoDB connection closed")


async def main():
    """Main entry point for index initialization."""
    get_logger, setup_logging = _load_logging()
    await setup_logging()
    logger = get_logger(__name__)

    await logger.info("Starting MongoDB index initialization...")

    success = await initialize_indexes(logger)

    if success:
        await logger.info("Index initialization completed successfully")
        sys.exit(0)
    else:
        await logger.warning(
            "Index initialization completed with warnings. "
            "Vector and text search may not be available."
        )
        # Don't fail completely - allow the app to start
        # Users can fallback to MongoDB Atlas if needed
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
