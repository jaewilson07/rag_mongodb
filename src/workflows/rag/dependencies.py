"""Dependencies for MongoDB RAG Agent."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from mdrag.integrations.llm.completion_client import LLMCompletionClient
from mdrag.capabilities.retrieval.embeddings import EmbeddingClient
from mdrag.config.settings import load_settings
from mdrag.core.validation import ValidationError, validate_mongodb
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class AgentDependencies:
    """Dependencies injected into the agent context."""

    # Core dependencies
    mongo_client: Optional[AsyncMongoClient] = None
    db: Optional[Any] = None
    embedding_client: Optional[EmbeddingClient] = None
    llm_client: Optional[LLMCompletionClient] = None
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
            ValidationError: If MongoDB schema (collections/indexes) is invalid
            ValueError: If settings cannot be loaded
        """
        if not self.settings:
            self.settings = load_settings()
            logger.info(
                "settings_loaded database=%s",
                self.settings.mongodb_database,
            )

        # Validate MongoDB connection and schema before creating client
        try:
            await validate_mongodb(self.settings, strict=True)
        except ValidationError as e:
            logger.exception("mongodb_validation_failed error=%s", str(e))
            raise

        # Initialize MongoDB client
        if not self.mongo_client:
            try:
                self.mongo_client = AsyncMongoClient(
                    self.settings.mongodb_connection_string, serverSelectionTimeoutMS=5000
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

        # Initialize LLM completion client (provider-aware temperature)
        if not self.llm_client:
            self.llm_client = LLMCompletionClient(settings=self.settings)

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
        if self.llm_client:
            await self.llm_client.close()
            self.llm_client = None

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
        # Keep last 10 queries
        if len(self.query_history) > 10:
            self.query_history.pop(0)
