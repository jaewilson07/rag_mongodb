"""
MongoDB client for episodic memory management.

Integrates with existing MongoDB RAG system for document chunks and extends
it with chat log capture and resource storage.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MongoDBConfig(BaseModel):
    """Configuration for MongoDB connection."""

    uri: str
    database: str = "neuralcursor"
    collection_chunks: str = "chunks"
    collection_documents: str = "documents"
    collection_chats: str = "chats"
    collection_resources: str = "resources"
    collection_sessions: str = "sessions"


class ChatMessage(BaseModel):
    """Individual message in a conversation."""

    role: str = Field(..., description="user, assistant, system, tool")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationSession(BaseModel):
    """A conversation session with the agent."""

    session_id: str = Field(..., description="Unique session identifier")
    project_context: Optional[str] = Field(None, description="Active project context")
    messages: list[ChatMessage] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalResource(BaseModel):
    """External resource (YouTube video, article, etc.)."""

    resource_id: str = Field(..., description="Unique resource identifier")
    resource_type: str = Field(..., description="youtube, article, documentation, code")
    title: str = Field(..., description="Resource title")
    url: Optional[str] = Field(None, description="Original URL")
    content: Optional[str] = Field(None, description="Full text content")
    summary: Optional[str] = Field(None, description="AI-generated summary")
    embedding: Optional[list[float]] = Field(None, description="Content embedding")
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MongoDBClient:
    """
    Async MongoDB client for episodic memory.
    
    Manages chat logs, document chunks, and external resources.
    """

    def __init__(self, config: MongoDBConfig):
        """
        Initialize MongoDB client.
        
        Args:
            config: MongoDB connection configuration
        """
        self.config = config
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """
        Establish connection to MongoDB.
        
        Raises:
            Exception: If connection fails
        """
        try:
            self._client = AsyncIOMotorClient(self.config.uri)

            # Verify connection
            await self._client.admin.command("ping")
            self._db = self._client[self.config.database]

            logger.info(
                "mongodb_connected",
                extra={"database": self.config.database},
            )

            # Create indexes
            await self._create_indexes()

        except Exception as e:
            logger.exception("mongodb_connection_failed", extra={"error": str(e)})
            raise

    async def close(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            logger.info("mongodb_connection_closed")

    async def _create_indexes(self) -> None:
        """Create necessary indexes for efficient queries."""
        if not self._db:
            raise RuntimeError("MongoDB not connected")

        # Chat sessions index
        await self._db[self.config.collection_sessions].create_index("session_id", unique=True)
        await self._db[self.config.collection_sessions].create_index("last_activity")
        await self._db[self.config.collection_sessions].create_index("project_context")

        # Resources index
        await self._db[self.config.collection_resources].create_index("resource_id", unique=True)
        await self._db[self.config.collection_resources].create_index("resource_type")
        await self._db[self.config.collection_resources].create_index("tags")

        logger.info("mongodb_indexes_created")

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """
        Get the MongoDB database instance.
        
        Returns:
            Motor database instance
            
        Raises:
            RuntimeError: If not connected
        """
        if not self._db:
            raise RuntimeError("MongoDB client not connected. Call connect() first.")
        return self._db

    async def save_chat_message(self, session_id: str, message: ChatMessage) -> None:
        """
        Save a chat message to a conversation session.
        
        Args:
            session_id: Session identifier
            message: Chat message to save
        """
        await self.db[self.config.collection_sessions].update_one(
            {"session_id": session_id},
            {
                "$push": {"messages": message.model_dump()},
                "$set": {"last_activity": datetime.utcnow()},
                "$setOnInsert": {
                    "started_at": datetime.utcnow(),
                    "project_context": None,
                    "metadata": {},
                },
            },
            upsert=True,
        )

        logger.info("chat_message_saved", extra={"session_id": session_id, "role": message.role})

    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """
        Retrieve a conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Conversation session or None if not found
        """
        doc = await self.db[self.config.collection_sessions].find_one({"session_id": session_id})

        if not doc:
            return None

        return ConversationSession(**doc)

    async def get_recent_sessions(self, limit: int = 10, project_context: Optional[str] = None) -> list[ConversationSession]:
        """
        Get recent conversation sessions.
        
        Args:
            limit: Maximum number of sessions to return
            project_context: Optional filter by project
            
        Returns:
            List of conversation sessions
        """
        query = {}
        if project_context:
            query["project_context"] = project_context

        cursor = (
            self.db[self.config.collection_sessions]
            .find(query)
            .sort("last_activity", -1)
            .limit(limit)
        )

        sessions = []
        async for doc in cursor:
            sessions.append(ConversationSession(**doc))

        return sessions

    async def save_resource(self, resource: ExternalResource) -> str:
        """
        Save an external resource.
        
        Args:
            resource: External resource to save
            
        Returns:
            Resource ID
        """
        await self.db[self.config.collection_resources].update_one(
            {"resource_id": resource.resource_id},
            {"$set": resource.model_dump()},
            upsert=True,
        )

        logger.info(
            "resource_saved",
            extra={"resource_id": resource.resource_id, "type": resource.resource_type},
        )

        return resource.resource_id

    async def search_resources(
        self, query: str, resource_type: Optional[str] = None, limit: int = 10
    ) -> list[ExternalResource]:
        """
        Search resources by text query.
        
        Args:
            query: Search query
            resource_type: Optional filter by resource type
            limit: Maximum results to return
            
        Returns:
            List of matching resources
        """
        # Build search filter
        search_filter: dict[str, Any] = {
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"summary": {"$regex": query, "$options": "i"}},
                {"tags": {"$in": [query.lower()]}},
            ]
        }

        if resource_type:
            search_filter["resource_type"] = resource_type

        cursor = (
            self.db[self.config.collection_resources]
            .find(search_filter)
            .limit(limit)
        )

        resources = []
        async for doc in cursor:
            resources.append(ExternalResource(**doc))

        return resources

    async def get_sessions_for_distillation(self, min_messages: int = 5) -> list[ConversationSession]:
        """
        Get conversation sessions that are ready for distillation by the Librarian agent.
        
        Args:
            min_messages: Minimum number of messages required
            
        Returns:
            List of sessions ready for distillation
        """
        # Find sessions with enough messages that haven't been distilled yet
        pipeline = [
            {
                "$match": {
                    "metadata.distilled": {"$ne": True},
                    "$expr": {"$gte": [{"$size": "$messages"}, min_messages]},
                }
            },
            {"$sort": {"last_activity": 1}},  # Oldest first
            {"$limit": 10},
        ]

        cursor = self.db[self.config.collection_sessions].aggregate(pipeline)

        sessions = []
        async for doc in cursor:
            sessions.append(ConversationSession(**doc))

        return sessions

    async def mark_session_distilled(self, session_id: str, conversation_node_uid: str) -> None:
        """
        Mark a session as distilled and link to Neo4j conversation node.
        
        Args:
            session_id: Session identifier
            conversation_node_uid: UID of the Neo4j ConversationNode
        """
        await self.db[self.config.collection_sessions].update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "metadata.distilled": True,
                    "metadata.distilled_at": datetime.utcnow(),
                    "metadata.conversation_node_uid": conversation_node_uid,
                }
            },
        )

        logger.info(
            "session_distilled",
            extra={"session_id": session_id, "node_uid": conversation_node_uid},
        )
