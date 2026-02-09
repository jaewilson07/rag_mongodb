"""
MemGPT agent wrapper for NeuralCursor.

Manages working memory with autonomous context paging to Neo4j/MongoDB.
"""

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from neuralcursor.brain.neo4j.client import Neo4jClient
from neuralcursor.brain.mongodb.client import MongoDBClient
from neuralcursor.settings import get_settings

logger = logging.getLogger(__name__)


class WorkingMemoryState(BaseModel):
    """Current state of working memory."""

    core_memory: dict[str, Any] = Field(
        default_factory=dict,
        description="High-priority items kept in active context",
    )
    working_set: list[str] = Field(
        default_factory=list,
        description="UIDs of recently accessed nodes",
    )
    active_project: Optional[str] = Field(None, description="Currently active project UID")
    context_window_usage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Current context window usage (0-1)",
    )


class MemoryOperation(BaseModel):
    """A memory operation executed by MemGPT."""

    operation_type: str = Field(..., description="save, retrieve, page, archive")
    target: str = Field(..., description="Target node UID or collection")
    data: Optional[dict[str, Any]] = Field(None)
    success: bool = Field(default=True)
    message: Optional[str] = Field(None)


class MemGPTAgent:
    """
    MemGPT agent that manages working memory and context paging.
    
    Core responsibilities:
    1. Monitor context window usage
    2. Automatically page important data to Neo4j/MongoDB
    3. Keep recently accessed items in "working set"
    4. Archive cold data while maintaining searchability
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        mongodb_client: MongoDBClient,
    ):
        """
        Initialize MemGPT agent.
        
        Args:
            neo4j_client: Neo4j client for graph storage
            mongodb_client: MongoDB client for episodic memory
        """
        self.neo4j = neo4j_client
        self.mongodb = mongodb_client
        self.settings = get_settings()

        # Initialize working memory
        self.state = WorkingMemoryState()

    async def save_to_memory(
        self,
        content: str,
        memory_type: str = "episodic",
        metadata: Optional[dict[str, Any]] = None,
    ) -> MemoryOperation:
        """
        Save content to appropriate memory layer.
        
        Episodic → MongoDB (for chat logs, temporary notes)
        Structural → Neo4j (for decisions, requirements, code entities)
        
        Args:
            content: Content to save
            memory_type: "episodic" or "structural"
            metadata: Additional metadata
            
        Returns:
            Memory operation result
        """
        try:
            if memory_type == "episodic":
                # Save to MongoDB
                from neuralcursor.brain.mongodb.client import ChatMessage

                # Create a chat message entry
                message = ChatMessage(
                    role="system",
                    content=content,
                    metadata=metadata or {},
                )

                # Use a default session ID for non-conversation saves
                session_id = metadata.get("session_id", "memgpt-default")
                await self.mongodb.save_chat_message(session_id, message)

                return MemoryOperation(
                    operation_type="save",
                    target="mongodb/episodic",
                    data={"session_id": session_id},
                    success=True,
                    message="Saved to episodic memory",
                )

            elif memory_type == "structural":
                # Save to Neo4j - requires creating a proper node
                # This is handled by specific methods for each node type
                return MemoryOperation(
                    operation_type="save",
                    target="neo4j/structural",
                    success=False,
                    message="Use specific node creation methods for structural memory",
                )

            else:
                return MemoryOperation(
                    operation_type="save",
                    target="unknown",
                    success=False,
                    message=f"Unknown memory type: {memory_type}",
                )

        except Exception as e:
            logger.exception("memgpt_save_failed", extra={"error": str(e)})
            return MemoryOperation(
                operation_type="save",
                target=memory_type,
                success=False,
                message=str(e),
            )

    async def retrieve_from_memory(
        self,
        query: str,
        memory_type: str = "both",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant memories matching query.
        
        Args:
            query: Search query
            memory_type: "episodic", "structural", or "both"
            limit: Maximum results
            
        Returns:
            List of matching memories
        """
        results: list[dict[str, Any]] = []

        try:
            if memory_type in ["episodic", "both"]:
                # Search MongoDB resources
                resources = await self.mongodb.search_resources(query, limit=limit)
                for res in resources:
                    results.append(
                        {
                            "source": "mongodb",
                            "type": "resource",
                            "data": res.model_dump(),
                        }
                    )

            if memory_type in ["structural", "both"]:
                # Search Neo4j using full-text search
                cypher = """
                CALL db.index.fulltext.queryNodes('node_search', $query)
                YIELD node, score
                RETURN properties(node) as props, labels(node) as labels, score
                ORDER BY score DESC
                LIMIT $limit
                """

                graph_results = await self.neo4j.query(
                    cypher, {"query": query, "limit": limit}
                )

                for record in graph_results:
                    results.append(
                        {
                            "source": "neo4j",
                            "type": "node",
                            "data": record["props"],
                            "labels": record["labels"],
                            "score": record["score"],
                        }
                    )

        except Exception as e:
            logger.exception("memgpt_retrieve_failed", extra={"error": str(e)})

        return results

    async def page_to_long_term(self, node_uid: str) -> MemoryOperation:
        """
        Page a node from working memory to long-term storage.
        
        Marks the node as "archived" but keeps it searchable.
        
        Args:
            node_uid: UID of node to archive
            
        Returns:
            Memory operation result
        """
        try:
            # Update node to mark as archived (but still in Neo4j)
            updated = await self.neo4j.update_node(
                node_uid,
                {
                    "archived": True,
                    "archived_from_working_set": True,
                },
            )

            if updated:
                # Remove from working set
                if node_uid in self.state.working_set:
                    self.state.working_set.remove(node_uid)

                logger.info("memgpt_paged_to_long_term", extra={"uid": node_uid})

                return MemoryOperation(
                    operation_type="page",
                    target=node_uid,
                    success=True,
                    message="Paged to long-term memory",
                )
            else:
                return MemoryOperation(
                    operation_type="page",
                    target=node_uid,
                    success=False,
                    message="Node not found",
                )

        except Exception as e:
            logger.exception("memgpt_page_failed", extra={"error": str(e)})
            return MemoryOperation(
                operation_type="page",
                target=node_uid,
                success=False,
                message=str(e),
            )

    async def manage_working_set(
        self, context_window_size: int = 10000
    ) -> dict[str, Any]:
        """
        Manage working set based on context window usage.
        
        Automatically pages cold items when context is filling up.
        
        Args:
            context_window_size: Maximum context window in tokens
            
        Returns:
            Management operation summary
        """
        current_usage = len(self.state.working_set) * 100  # Rough estimate

        self.state.context_window_usage = min(
            current_usage / context_window_size, 1.0
        )

        operations = []

        # If context is > 80% full, page oldest items
        if self.state.context_window_usage > 0.8:
            items_to_page = int(len(self.state.working_set) * 0.3)  # Page 30%

            logger.info(
                "memgpt_context_high",
                extra={
                    "usage": self.state.context_window_usage,
                    "items_to_page": items_to_page,
                },
            )

            # Page oldest items (simple LRU strategy)
            for uid in self.state.working_set[:items_to_page]:
                op = await self.page_to_long_term(uid)
                operations.append(op.model_dump())

        return {
            "context_usage": self.state.context_window_usage,
            "working_set_size": len(self.state.working_set),
            "operations": operations,
        }

    async def add_to_working_set(self, node_uid: str) -> None:
        """
        Add a node to the working set (mark as recently accessed).
        
        Args:
            node_uid: UID of node to add
        """
        if node_uid not in self.state.working_set:
            self.state.working_set.append(node_uid)

        # Trigger working set management
        await self.manage_working_set()

    async def get_active_context(self) -> dict[str, Any]:
        """
        Get the current active context for Cursor.
        
        Returns:
            Active context summary
        """
        active_nodes = []

        # Retrieve nodes in working set
        for uid in self.state.working_set[-10:]:  # Last 10 accessed
            node_data = await self.neo4j.get_node(uid)
            if node_data:
                active_nodes.append(node_data)

        # Get active project info
        active_project = None
        if self.state.active_project:
            active_project = await self.neo4j.get_node(self.state.active_project)

        return {
            "active_project": active_project,
            "recent_nodes": active_nodes,
            "working_set_size": len(self.state.working_set),
            "context_usage": self.state.context_window_usage,
        }
