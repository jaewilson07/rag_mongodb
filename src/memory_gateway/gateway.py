"""Memory Gateway - Unified interface for NeuralCursor Second Brain."""

import logging
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure

from src.integrations.neo4j.client import Neo4jClient
from src.integrations.neo4j.models import (
    Area,
    CodeEntity,
    Decision,
    NodeType,
    Project,
    Requirement,
    Resource,
)
from src.integrations.neo4j.queries import SecondBrainQueries
from src.settings import Settings

from .models import (
    ArchitecturalContext,
    ArchitecturalQuery,
    GraphStats,
    MemoryOperation,
    MemoryRequest,
    MemoryResponse,
    MemoryType,
    WorkingSet,
)

logger = logging.getLogger(__name__)


class MemoryGateway:
    """
    Unified gateway for Neo4j (structural) and MongoDB (episodic) memory.
    
    This is the "Context Bridge" that ensures MemGPT and the MCP server
    communicate with a unified data state.
    """

    def __init__(self, settings: Settings):
        """
        Initialize memory gateway.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.neo4j_client = Neo4jClient(settings)
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize both database connections."""
        # Connect to Neo4j
        await self.neo4j_client.connect()
        
        # Connect to MongoDB
        self.mongo_client = AsyncIOMotorClient(self.settings.mongodb_connection_string)
        try:
            await self.mongo_client.admin.command("ping")
            logger.info("memory_gateway_mongodb_connected")
        except ConnectionFailure as e:
            logger.exception("memory_gateway_mongodb_failed", extra={"error": str(e)})
            raise
        
        self._initialized = True
        logger.info("memory_gateway_initialized")

    async def close(self) -> None:
        """Close database connections."""
        await self.neo4j_client.close()
        if self.mongo_client:
            self.mongo_client.close()
        self._initialized = False
        logger.info("memory_gateway_closed")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def execute(self, request: MemoryRequest) -> MemoryResponse:
        """
        Execute a memory operation.
        
        Args:
            request: Memory operation request
            
        Returns:
            Memory operation response
        """
        if not self._initialized:
            raise RuntimeError("MemoryGateway not initialized. Call initialize() first.")

        try:
            if request.memory_type == MemoryType.STRUCTURAL:
                result = await self._execute_structural(request)
            elif request.memory_type == MemoryType.EPISODIC:
                result = await self._execute_episodic(request)
            elif request.memory_type == MemoryType.HYBRID:
                result = await self._execute_hybrid(request)
            else:
                raise ValueError(f"Unknown memory type: {request.memory_type}")

            return MemoryResponse(
                success=True,
                memory_type=request.memory_type,
                operation=request.operation,
                data=result,
                metadata=request.metadata or {},
            )
        except Exception as e:
            logger.exception(
                "memory_gateway_operation_failed",
                extra={
                    "operation": request.operation,
                    "memory_type": request.memory_type,
                    "error": str(e),
                },
            )
            return MemoryResponse(
                success=False,
                memory_type=request.memory_type,
                operation=request.operation,
                error=str(e),
                metadata=request.metadata or {},
            )

    async def _execute_structural(self, request: MemoryRequest) -> Any:
        """Execute Neo4j graph operation."""
        if request.operation == MemoryOperation.CREATE:
            return await self._create_graph_node(request)
        elif request.operation == MemoryOperation.READ:
            return await self.neo4j_client.get_node(request.entity_id, request.entity_type)
        elif request.operation == MemoryOperation.UPDATE:
            return await self.neo4j_client.update_node(request.entity_id, request.data)
        elif request.operation == MemoryOperation.DELETE:
            return await self.neo4j_client.delete_node(request.entity_id)
        elif request.operation == MemoryOperation.QUERY:
            return await self._query_graph(request)
        elif request.operation == MemoryOperation.TRAVERSE:
            return await self._traverse_graph(request)
        else:
            raise ValueError(f"Unknown operation: {request.operation}")

    async def _execute_episodic(self, request: MemoryRequest) -> Any:
        """Execute MongoDB document operation."""
        db = self.mongo_client[self.settings.mongodb_database]
        collection = db[request.entity_type or "documents"]

        if request.operation == MemoryOperation.CREATE:
            result = await collection.insert_one(request.data)
            return {"inserted_id": str(result.inserted_id)}
        elif request.operation == MemoryOperation.READ:
            doc = await collection.find_one({"_id": request.entity_id})
            return doc
        elif request.operation == MemoryOperation.UPDATE:
            result = await collection.update_one(
                {"_id": request.entity_id}, {"$set": request.data}
            )
            return {"modified_count": result.modified_count}
        elif request.operation == MemoryOperation.DELETE:
            result = await collection.delete_one({"_id": request.entity_id})
            return {"deleted_count": result.deleted_count}
        elif request.operation == MemoryOperation.QUERY:
            cursor = collection.find(request.filters or {}).limit(request.limit or 10)
            docs = await cursor.to_list(length=request.limit or 10)
            return docs
        else:
            raise ValueError(f"Unknown operation: {request.operation}")

    async def _execute_hybrid(self, request: MemoryRequest) -> Any:
        """Execute hybrid query across both databases."""
        # Execute structural query
        structural_result = await self._execute_structural(request)
        
        # Execute episodic query
        episodic_result = await self._execute_episodic(request)
        
        return {
            "structural": structural_result,
            "episodic": episodic_result,
        }

    async def _create_graph_node(self, request: MemoryRequest) -> str:
        """Create a graph node based on entity type."""
        entity_type = request.entity_type or request.data.get("node_type")
        
        if entity_type == NodeType.PROJECT:
            node = Project(**request.data)
        elif entity_type == NodeType.AREA:
            node = Area(**request.data)
        elif entity_type == NodeType.DECISION:
            node = Decision(**request.data)
        elif entity_type == NodeType.REQUIREMENT:
            node = Requirement(**request.data)
        elif entity_type == NodeType.CODE_ENTITY:
            node = CodeEntity(**request.data)
        elif entity_type == NodeType.RESOURCE:
            node = Resource(**request.data)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        uuid = await self.neo4j_client.create_node(node)
        return uuid

    async def _query_graph(self, request: MemoryRequest) -> List[Dict[str, Any]]:
        """Execute Cypher query on graph."""
        if request.query:
            return await self.neo4j_client.execute_cypher(request.query, request.filters)
        else:
            raise ValueError("Query string required for QUERY operation")

    async def _traverse_graph(self, request: MemoryRequest) -> List[Dict[str, Any]]:
        """Traverse graph from starting node."""
        # Implementation depends on traversal type
        # For now, use execute_cypher with traversal query
        return await self._query_graph(request)

    async def get_architectural_context(
        self, query: ArchitecturalQuery
    ) -> ArchitecturalContext:
        """
        Get complete architectural context for code or entity.
        
        This is the core "Why does this code exist?" query.
        
        Args:
            query: Architectural query parameters
            
        Returns:
            Complete architectural context
        """
        if not self._initialized:
            raise RuntimeError("MemoryGateway not initialized. Call initialize() first.")

        context = ArchitecturalContext()

        if query.file_path:
            # Query: Why does this code exist?
            cypher_query, params = SecondBrainQueries.find_why_code_exists(
                query.file_path, query.line_number
            )
            results = await self.neo4j_client.execute_cypher(cypher_query, params)
            
            if results:
                context.file_path = query.file_path
                # Parse results and populate context
                for result in results:
                    if "dec" in result:
                        context.decisions.append(dict(result["dec"]))
                    if "req" in result:
                        context.requirements.append(dict(result["req"]))
                    if "res" in result:
                        context.resources.append(dict(result["res"]))

        elif query.entity_uuid:
            # Get entity context
            if query.include_history:
                cypher_query, params = SecondBrainQueries.find_decision_history(
                    query.entity_uuid
                )
                results = await self.neo4j_client.execute_cypher(cypher_query, params)
                context.decision_history = results

        return context

    async def get_working_set(self) -> WorkingSet:
        """
        Get current working set for active development.
        
        Returns:
            Working set with active projects and files
        """
        if not self._initialized:
            raise RuntimeError("MemoryGateway not initialized. Call initialize() first.")

        working_set = WorkingSet()

        # Get active projects
        cypher_query, params = SecondBrainQueries.find_active_project_files()
        results = await self.neo4j_client.execute_cypher(cypher_query, params)
        
        if results:
            working_set.active_projects = list(set(r["project_uuid"] for r in results))
            working_set.active_files = [r["file_path"] for r in results[:20]]  # Top 20

        return working_set

    async def get_graph_stats(self) -> GraphStats:
        """
        Get statistics about the knowledge graph.
        
        Returns:
            Graph statistics
        """
        if not self._initialized:
            raise RuntimeError("MemoryGateway not initialized. Call initialize() first.")

        stats = GraphStats()

        # Count nodes by label
        count_query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        """
        results = await self.neo4j_client.execute_cypher(count_query)
        
        for result in results:
            label = result.get("label", "Unknown")
            count = result.get("count", 0)
            stats.node_counts[label] = count
            stats.total_nodes += count

        # Count relationships
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        """
        results = await self.neo4j_client.execute_cypher(rel_query)
        
        for result in results:
            rel_type = result.get("type", "Unknown")
            count = result.get("count", 0)
            stats.relationship_counts[rel_type] = count
            stats.total_relationships += count

        # Count active projects
        active_query = """
        MATCH (p:Project {status: 'active'})
        RETURN count(p) as count
        """
        results = await self.neo4j_client.execute_cypher(active_query)
        stats.active_projects = results[0]["count"] if results else 0

        return stats
