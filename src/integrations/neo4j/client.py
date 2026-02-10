"""Neo4j client for NeuralCursor Second Brain knowledge graph."""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid as uuid_lib

from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable, AuthError

from mdrag.config.settings import Settings
from .models import (
    GraphNode,
    Project,
    Decision,
    GraphQuery,
    GraphQueryResult,
    NodeType,
    RelationType,
)
from .schema import PARASchema

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Async Neo4j client for managing the Second Brain knowledge graph.
    
    This client provides:
    - Connection management with retry logic
    - CRUD operations for PARA nodes
    - Graph traversal and query capabilities
    - Schema initialization and maintenance
    """

    def __init__(self, settings: Settings):
        """
        Initialize Neo4j client.
        
        Args:
            settings: Application settings with Neo4j configuration
        """
        self.settings = settings
        self._driver: Optional[AsyncDriver] = None
        self._connected = False

    async def connect(self) -> None:
        """
        Establish connection to Neo4j database.
        
        Raises:
            ServiceUnavailable: If Neo4j is not reachable
            AuthError: If authentication fails
        """
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_username, self.settings.neo4j_password),
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            self._connected = True
            logger.info(
                "neo4j_connection_established",
                extra={
                    "uri": self.settings.neo4j_uri,
                    "database": self.settings.neo4j_database,
                },
            )
        except ServiceUnavailable as e:
            logger.exception("neo4j_connection_failed_unavailable", extra={"error": str(e)})
            raise
        except AuthError as e:
            logger.exception("neo4j_connection_failed_auth", extra={"error": str(e)})
            raise

    async def close(self) -> None:
        """Close Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._connected = False
            logger.info("neo4j_connection_closed")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    async def initialize_schema(self) -> None:
        """
        Initialize Neo4j schema with constraints and indexes.
        
        This should be run once when setting up the database.
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        async with self._driver.session(database=self.settings.neo4j_database) as session:
            # Create constraints
            constraints = PARASchema.get_constraints()
            for constraint in constraints:
                try:
                    await session.run(constraint)
                    logger.info("neo4j_constraint_created", extra={"query": constraint})
                except Exception as e:
                    logger.warning(
                        "neo4j_constraint_creation_failed",
                        extra={"query": constraint, "error": str(e)},
                    )

            # Create indexes
            indexes = PARASchema.get_indexes()
            for index in indexes:
                try:
                    await session.run(index)
                    logger.info("neo4j_index_created", extra={"query": index})
                except Exception as e:
                    logger.warning(
                        "neo4j_index_creation_failed",
                        extra={"query": index, "error": str(e)},
                    )

        logger.info("neo4j_schema_initialized")

    async def create_node(
        self, node: GraphNode, labels: Optional[List[str]] = None
    ) -> str:
        """
        Create a new node in the graph.
        
        Args:
            node: Graph node model (Project, Area, Decision, etc.)
            labels: Optional additional labels beyond node type
            
        Returns:
            UUID of created node
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        # Generate UUID if not provided
        if not node.uuid:
            node.uuid = str(uuid_lib.uuid4())

        # Build labels
        node_labels = [node.node_type]
        if labels:
            node_labels.extend(labels)
        labels_str = ":".join(node_labels)

        # Convert node to properties dict
        properties = node.model_dump(exclude={"node_type"})
        properties["created_at"] = properties["created_at"].isoformat()
        properties["updated_at"] = properties["updated_at"].isoformat()

        # Handle specific datetime fields
        if isinstance(node, Project) and node.deadline:
            properties["deadline"] = node.deadline.isoformat()
        elif isinstance(node, Decision):
            properties["decided_at"] = node.decided_at.isoformat()

        query = f"""
        CREATE (n:{labels_str} $properties)
        RETURN n.uuid as uuid
        """

        async with self._driver.session(database=self.settings.neo4j_database) as session:
            result = await session.run(query, properties=properties)
            record = await result.single()
            logger.info(
                "neo4j_node_created",
                extra={"node_type": node.node_type, "uuid": record["uuid"]},
            )
            return record["uuid"]

    async def get_node(self, uuid: str, node_type: Optional[NodeType] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve a node by UUID.
        
        Args:
            uuid: Node UUID
            node_type: Optional node type filter
            
        Returns:
            Node properties dict or None if not found
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        label_filter = f":{node_type.value}" if node_type else ""
        query = f"""
        MATCH (n{label_filter} {{uuid: $uuid}})
        RETURN n
        """

        async with self._driver.session(database=self.settings.neo4j_database) as session:
            result = await session.run(query, uuid=uuid)
            record = await result.single()
            if record:
                return dict(record["n"])
            return None

    async def update_node(self, uuid: str, properties: Dict[str, Any]) -> bool:
        """
        Update node properties.
        
        Args:
            uuid: Node UUID
            properties: Properties to update
            
        Returns:
            True if node was updated, False if not found
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        properties["updated_at"] = datetime.utcnow().isoformat()

        query = """
        MATCH (n {uuid: $uuid})
        SET n += $properties
        RETURN n.uuid as uuid
        """

        async with self._driver.session(database=self.settings.neo4j_database) as session:
            result = await session.run(query, uuid=uuid, properties=properties)
            record = await result.single()
            if record:
                logger.info("neo4j_node_updated", extra={"uuid": uuid})
                return True
            return False

    async def delete_node(self, uuid: str) -> bool:
        """
        Delete a node and its relationships.
        
        Args:
            uuid: Node UUID
            
        Returns:
            True if node was deleted, False if not found
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        query = """
        MATCH (n {uuid: $uuid})
        DETACH DELETE n
        RETURN count(n) as deleted_count
        """

        async with self._driver.session(database=self.settings.neo4j_database) as session:
            result = await session.run(query, uuid=uuid)
            record = await result.single()
            deleted = record["deleted_count"] > 0
            if deleted:
                logger.info("neo4j_node_deleted", extra={"uuid": uuid})
            return deleted

    async def create_relationship(
        self,
        source_uuid: str,
        target_uuid: str,
        relation_type: RelationType,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Create a relationship between two nodes.
        
        Args:
            source_uuid: Source node UUID
            target_uuid: Target node UUID
            relation_type: Relationship type
            properties: Optional relationship properties
            
        Returns:
            True if relationship was created
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        rel_props = properties or {}
        rel_props["created_at"] = datetime.utcnow().isoformat()

        query = f"""
        MATCH (source {{uuid: $source_uuid}})
        MATCH (target {{uuid: $target_uuid}})
        CREATE (source)-[r:{relation_type.value} $properties]->(target)
        RETURN id(r) as rel_id
        """

        async with self._driver.session(database=self.settings.neo4j_database) as session:
            result = await session.run(
                query,
                source_uuid=source_uuid,
                target_uuid=target_uuid,
                properties=rel_props,
            )
            record = await result.single()
            if record:
                logger.info(
                    "neo4j_relationship_created",
                    extra={
                        "relation_type": relation_type.value,
                        "source": source_uuid,
                        "target": target_uuid,
                    },
                )
                return True
            return False

    async def query_graph(self, query_params: GraphQuery) -> GraphQueryResult:
        """
        Query the graph with filters and traversal parameters.
        
        Args:
            query_params: Graph query parameters
            
        Returns:
            Query result with nodes and relationships
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        # Build WHERE clause from filters
        where_clauses = []
        for key, value in query_params.filters.items():
            where_clauses.append(f"n.{key} = ${key}")

        where_str = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        label_str = f":{query_params.node_type.value}" if query_params.node_type else ""

        query = f"""
        MATCH (n{label_str})
        {where_str}
        RETURN n
        LIMIT $limit
        """

        nodes = []
        async with self._driver.session(database=self.settings.neo4j_database) as session:
            result = await session.run(query, **query_params.filters, limit=query_params.limit)
            async for record in result:
                nodes.append(dict(record["n"]))

        # Get relationships if requested
        relationships = []
        if query_params.include_relationships and nodes:
            uuids = [node["uuid"] for node in nodes]
            rel_query = """
            MATCH (source)-[r]->(target)
            WHERE source.uuid IN $uuids AND target.uuid IN $uuids
            RETURN source.uuid as source, type(r) as type, target.uuid as target, properties(r) as props
            """
            async with self._driver.session(database=self.settings.neo4j_database) as session:
                result = await session.run(rel_query, uuids=uuids)
                async for record in result:
                    relationships.append(dict(record))

        return GraphQueryResult(
            nodes=nodes,
            relationships=relationships,
            metadata={"total": len(nodes), "query_params": query_params.model_dump()},
        )

    async def execute_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw Cypher query.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records
        """
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected. Call connect() first.")

        results = []
        async with self._driver.session(database=self.settings.neo4j_database) as session:
            result = await session.run(query, parameters or {})
            async for record in result:
                results.append(dict(record))

        logger.info("neo4j_cypher_executed", extra={"query": query[:100]})
        return results
