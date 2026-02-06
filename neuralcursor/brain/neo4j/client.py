"""
Neo4j client with connection management and CRUD operations.
"""

import logging
from typing import Any, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver
from pydantic import BaseModel

from .models import BaseNode, Relationship, NodeType, RelationType
from .schema import initialize_schema, validate_schema

logger = logging.getLogger(__name__)


class Neo4jConfig(BaseModel):
    """Configuration for Neo4j connection."""

    uri: str
    username: str
    password: str
    database: str = "neo4j"
    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: int = 60


class Neo4jClient:
    """
    Async Neo4j client for managing the logical brain.
    
    Provides CRUD operations for nodes and relationships with
    type-safe Pydantic models.
    """

    def __init__(self, config: Neo4jConfig):
        """
        Initialize Neo4j client.
        
        Args:
            config: Neo4j connection configuration
        """
        self.config = config
        self._driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        """
        Establish connection to Neo4j and initialize schema.
        
        Raises:
            Exception: If connection or schema initialization fails
        """
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password),
                max_connection_lifetime=self.config.max_connection_lifetime,
                max_connection_pool_size=self.config.max_connection_pool_size,
                connection_acquisition_timeout=self.config.connection_acquisition_timeout,
            )

            # Verify connection
            await self._driver.verify_connectivity()
            logger.info("neo4j_connected", extra={"uri": self.config.uri})

            # Initialize schema
            await initialize_schema(self._driver)
            logger.info("neo4j_schema_initialized")

        except Exception as e:
            logger.exception("neo4j_connection_failed", extra={"error": str(e)})
            raise

    async def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            await self._driver.close()
            logger.info("neo4j_connection_closed")

    @property
    def driver(self) -> AsyncDriver:
        """
        Get the Neo4j driver instance.
        
        Returns:
            Neo4j async driver
            
        Raises:
            RuntimeError: If not connected
        """
        if not self._driver:
            raise RuntimeError("Neo4j client not connected. Call connect() first.")
        return self._driver

    async def create_node(self, node: BaseNode) -> str:
        """
        Create a new node in the graph.
        
        Args:
            node: Node to create
            
        Returns:
            UID of created node
        """
        async with self.driver.session(database=self.config.database) as session:
            # Convert Pydantic model to dict, excluding None values
            node_dict = node.model_dump(exclude_none=True, exclude={"uid"})

            # Create node with label from node_type
            label = node.node_type.value
            query = f"""
            CREATE (n:{label})
            SET n = $props
            SET n.uid = toString(id(n))
            RETURN n.uid as uid
            """

            result = await session.run(query, props=node_dict)
            record = await result.single()

            uid = record["uid"]
            logger.info(
                "neo4j_node_created",
                extra={"node_type": node.node_type, "uid": uid, "name": node.name},
            )

            return uid

    async def get_node(self, uid: str, node_type: Optional[NodeType] = None) -> Optional[dict[str, Any]]:
        """
        Retrieve a node by UID.
        
        Args:
            uid: Node unique identifier
            node_type: Optional node type filter
            
        Returns:
            Node properties as dictionary, or None if not found
        """
        async with self.driver.session(database=self.config.database) as session:
            if node_type:
                label = node_type.value
                query = f"MATCH (n:{label} {{uid: $uid}}) RETURN properties(n) as props"
            else:
                query = "MATCH (n {uid: $uid}) RETURN properties(n) as props, labels(n) as labels"

            result = await session.run(query, uid=uid)
            record = await result.single()

            if not record:
                return None

            props = record["props"]
            if not node_type:
                props["labels"] = record["labels"]

            return props

    async def update_node(self, uid: str, updates: dict[str, Any]) -> bool:
        """
        Update node properties.
        
        Args:
            uid: Node unique identifier
            updates: Dictionary of properties to update
            
        Returns:
            True if node was updated, False if not found
        """
        async with self.driver.session(database=self.config.database) as session:
            query = """
            MATCH (n {uid: $uid})
            SET n += $updates
            SET n.updated_at = datetime()
            RETURN count(n) as updated
            """

            result = await session.run(query, uid=uid, updates=updates)
            record = await result.single()

            updated = record["updated"] > 0
            if updated:
                logger.info("neo4j_node_updated", extra={"uid": uid, "updates": list(updates.keys())})

            return updated

    async def delete_node(self, uid: str) -> bool:
        """
        Delete a node and all its relationships.
        
        Args:
            uid: Node unique identifier
            
        Returns:
            True if node was deleted, False if not found
        """
        async with self.driver.session(database=self.config.database) as session:
            query = """
            MATCH (n {uid: $uid})
            DETACH DELETE n
            RETURN count(n) as deleted
            """

            result = await session.run(query, uid=uid)
            record = await result.single()

            deleted = record["deleted"] > 0
            if deleted:
                logger.info("neo4j_node_deleted", extra={"uid": uid})

            return deleted

    async def create_relationship(self, relationship: Relationship) -> bool:
        """
        Create a relationship between two nodes.
        
        Args:
            relationship: Relationship to create
            
        Returns:
            True if relationship was created
        """
        async with self.driver.session(database=self.config.database) as session:
            rel_type = relationship.relation_type.value
            props = relationship.model_dump(exclude={"from_uid", "to_uid", "relation_type"})

            query = f"""
            MATCH (a {{uid: $from_uid}}), (b {{uid: $to_uid}})
            CREATE (a)-[r:{rel_type}]->(b)
            SET r = $props
            RETURN count(r) as created
            """

            result = await session.run(
                query, from_uid=relationship.from_uid, to_uid=relationship.to_uid, props=props
            )
            record = await result.single()

            created = record["created"] > 0
            if created:
                logger.info(
                    "neo4j_relationship_created",
                    extra={
                        "from": relationship.from_uid,
                        "to": relationship.to_uid,
                        "type": relationship.relation_type,
                    },
                )

            return created

    async def query(
        self, cypher: str, parameters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """
        Execute a raw Cypher query.
        
        Args:
            cypher: Cypher query string
            parameters: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        async with self.driver.session(database=self.config.database) as session:
            result = await session.run(cypher, parameters or {})
            records = [dict(record) async for record in result]
            return records

    async def get_schema_info(self) -> dict[str, Any]:
        """
        Get current schema validation information.
        
        Returns:
            Schema validation results
        """
        return await validate_schema(self.driver)

    async def find_node_by_name(
        self, name: str, node_type: Optional[NodeType] = None
    ) -> Optional[str]:
        """
        Find a node by name.
        
        Args:
            name: Node name to search for
            node_type: Optional node type filter
            
        Returns:
            UID of found node, or None if not found
        """
        async with self.driver.session(database=self.config.database) as session:
            if node_type:
                label = node_type.value
                query = f"MATCH (n:{label} {{name: $name}}) RETURN n.uid as uid LIMIT 1"
            else:
                query = "MATCH (n {name: $name}) RETURN n.uid as uid LIMIT 1"

            result = await session.run(query, name=name)
            record = await result.single()

            if not record:
                return None

            return record["uid"]

    async def get_related_nodes(
        self,
        uid: str,
        relation_type: RelationType,
        direction: str = "outgoing",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Get nodes related to a given node.
        
        Args:
            uid: Starting node UID
            relation_type: Type of relationship to traverse
            direction: "outgoing", "incoming", or "both"
            limit: Maximum number of results
            
        Returns:
            List of related node properties
        """
        async with self.driver.session(database=self.config.database) as session:
            rel_type_name = relation_type.value

            if direction == "outgoing":
                pattern = f"(start {{uid: $uid}})-[r:{rel_type_name}]->(related)"
            elif direction == "incoming":
                pattern = f"(start {{uid: $uid}})<-[r:{rel_type_name}]-(related)"
            else:  # both
                pattern = f"(start {{uid: $uid}})-[r:{rel_type_name}]-(related)"

            query = f"""
            MATCH {pattern}
            RETURN properties(related) as node,
                   labels(related) as labels,
                   properties(r) as relationship
            LIMIT $limit
            """

            result = await session.run(query, uid=uid, limit=limit)
            records = [dict(record) async for record in result]

            return records

    async def find_path(
        self, from_uid: str, to_uid: str, max_depth: int = 5, relation_types: Optional[list[RelationType]] = None
    ) -> list[dict[str, Any]]:
        """
        Find shortest path between two nodes.
        
        This enables multi-hop reasoning like:
        "Find the Requirement that led to this Decision which modified this CodeEntity"
        
        Args:
            from_uid: Starting node UID
            to_uid: Target node UID
            max_depth: Maximum path length
            relation_types: Optional list of relationship types to traverse
            
        Returns:
            List of paths with nodes and relationships
        """
        async with self.driver.session(database=self.config.database) as session:
            if relation_types:
                rel_filter = "|".join([rt.value for rt in relation_types])
                rel_pattern = f"[r:{rel_filter}*1..{max_depth}]"
            else:
                rel_pattern = f"[r*1..{max_depth}]"

            query = f"""
            MATCH path = shortestPath((start {{uid: $from_uid}})-{rel_pattern}-(end {{uid: $to_uid}}))
            RETURN [node in nodes(path) | properties(node)] as nodes,
                   [rel in relationships(path) | {{type: type(rel), props: properties(rel)}}] as relationships
            """

            result = await session.run(query, from_uid=from_uid, to_uid=to_uid)
            records = [dict(record) async for record in result]

            return records
