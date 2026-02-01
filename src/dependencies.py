"""Dependencies for MongoDB RAG Agent."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import logging
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from mdrag.settings import load_settings
from mdrag.retrieval.embeddings import EmbeddingClient

logger = logging.getLogger(__name__)


@dataclass
class AgentDependencies:
    """Dependencies injected into the agent context."""

    # Core dependencies
    mongo_client: Optional[AsyncMongoClient] = None
    db: Optional[Any] = None
    embedding_client: Optional[EmbeddingClient] = None
    settings: Optional[Any] = None

    # Session context
    session_id: Optional[str] = None
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    query_history: list = field(default_factory=list)
    last_search_error: Optional[str] = None
    last_search_error_code: Optional[int] = None

    async def initialize(self) -> None:
        """
        Initialize external connections.

        Raises:
            ConnectionFailure: If MongoDB connection fails
            ServerSelectionTimeoutError: If MongoDB server selection times out
            ValueError: If settings cannot be loaded
        """
        if not self.settings:
            self.settings = load_settings()
            logger.info(
                "settings_loaded database=%s",
                self.settings.mongodb_database,
            )

        # Initialize MongoDB client
        if not self.mongo_client:
            try:
                self.mongo_client = AsyncMongoClient(
                    self.settings.mongodb_uri, serverSelectionTimeoutMS=5000
                )
                self.db = self.mongo_client[self.settings.mongodb_database]

                # Verify connection with ping
                await self.mongo_client.admin.command("ping")
                logger.info(
                    "mongodb_connected database=%s documents=%s chunks=%s",
                    self.settings.mongodb_database,
                    self.settings.mongodb_collection_documents,
                    self.settings.mongodb_collection_chunks,
                )
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.exception("mongodb_connection_failed error=%s", str(e))
                raise

        # Initialize embedding client
        if not self.embedding_client:
            self.embedding_client = EmbeddingClient(settings=self.settings)
            await self.embedding_client.initialize()

    async def cleanup(self) -> None:
        """Clean up external connections."""
        if self.mongo_client:
            await self.mongo_client.close()
            self.mongo_client = None
            self.db = None
            logger.info("mongodb_connection_closed")
        if self.embedding_client:
            await self.embedding_client.close()
            self.embedding_client = None

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for text using OpenAI.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            Exception: If embedding generation fails
        """
        if not self.embedding_client:
            await self.initialize()

        # Return as list of floats - MongoDB stores as native array
        return await self.embedding_client.embed_text(text)

    def set_user_preference(self, key: str, value: Any) -> None:
        """
        Set a user preference for the session.

        Args:
            key: Preference key
            value: Preference value
        """
        self.user_preferences[key] = value

    def add_to_history(self, query: str) -> None:
        """
        Add a query to the search history.

        Args:
            query: Search query to add to history
        """
        self.query_history.append(query)
        # Keep only last 10 queries
        if len(self.query_history) > 10:
            self.query_history.pop(0)
