"""
Dependency injection for FastAPI gateway.
"""

import logging
from typing import AsyncGenerator

from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig
from neuralcursor.brain.mongodb.client import MongoDBClient, MongoDBConfig
from neuralcursor.settings import get_settings

logger = logging.getLogger(__name__)

# Global clients (initialized at startup)
_neo4j_client: Neo4jClient | None = None
_mongodb_client: MongoDBClient | None = None


async def init_clients() -> None:
    """Initialize database clients at application startup."""
    global _neo4j_client, _mongodb_client

    settings = get_settings()

    # Initialize Neo4j
    neo4j_config = Neo4jConfig(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    _neo4j_client = Neo4jClient(neo4j_config)
    await _neo4j_client.connect()

    # Initialize MongoDB
    mongodb_config = MongoDBConfig(
        uri=settings.mongodb_uri,
        database=settings.mongodb_database,
    )
    _mongodb_client = MongoDBClient(mongodb_config)
    await _mongodb_client.connect()

    logger.info("gateway_clients_initialized")


async def close_clients() -> None:
    """Close database clients at application shutdown."""
    global _neo4j_client, _mongodb_client

    if _neo4j_client:
        await _neo4j_client.close()
        _neo4j_client = None

    if _mongodb_client:
        await _mongodb_client.close()
        _mongodb_client = None

    logger.info("gateway_clients_closed")


async def get_neo4j_client() -> AsyncGenerator[Neo4jClient, None]:
    """
    FastAPI dependency for Neo4j client.
    
    Yields:
        Neo4j client instance
        
    Raises:
        RuntimeError: If client not initialized
    """
    if not _neo4j_client:
        raise RuntimeError("Neo4j client not initialized")
    yield _neo4j_client


async def get_mongodb_client() -> AsyncGenerator[MongoDBClient, None]:
    """
    FastAPI dependency for MongoDB client.
    
    Yields:
        MongoDB client instance
        
    Raises:
        RuntimeError: If client not initialized
    """
    if not _mongodb_client:
        raise RuntimeError("MongoDB client not initialized")
    yield _mongodb_client


class GatewayDependencies:
    """
    Container for all gateway dependencies.
    
    Similar to AgentDependencies in the existing RAG system.
    """

    def __init__(self, neo4j: Neo4jClient, mongodb: MongoDBClient):
        """
        Initialize gateway dependencies.
        
        Args:
            neo4j: Neo4j client
            mongodb: MongoDB client
        """
        self.neo4j = neo4j
        self.mongodb = mongodb


async def get_gateway_deps() -> AsyncGenerator[GatewayDependencies, None]:
    """
    FastAPI dependency for all gateway dependencies.
    
    Yields:
        Gateway dependencies container
    """
    if not _neo4j_client or not _mongodb_client:
        raise RuntimeError("Gateway clients not initialized")

    yield GatewayDependencies(neo4j=_neo4j_client, mongodb=_mongodb_client)
