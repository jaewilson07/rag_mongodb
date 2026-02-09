"""
MCP tools exposed to Cursor IDE.

Tools allow Cursor to:
1. Query the architectural graph
2. Retrieve past decisions
3. Search resources and documentation
4. Find relationships between code entities
"""

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from neuralcursor.brain.memgpt.agent import MemGPTAgent
from neuralcursor.brain.mongodb.client import MongoDBClient
from neuralcursor.brain.neo4j.client import Neo4jClient
from neuralcursor.brain.neo4j.models import RelationType

logger = logging.getLogger(__name__)


class QueryGraphRequest(BaseModel):
    """Request to query the architectural graph."""

    query: str = Field(..., description="Natural language or Cypher query")
    node_types: Optional[list[str]] = Field(
        None, description="Filter by node types (Project, Decision, etc.)"
    )
    max_results: int = Field(default=10, ge=1, le=50)


class RetrieveDecisionsRequest(BaseModel):
    """Request to retrieve past architectural decisions."""

    context: str = Field(..., description="Context or code area to search")
    limit: int = Field(default=5, ge=1, le=20)


class SearchResourcesRequest(BaseModel):
    """Request to search external resources."""

    query: str = Field(..., description="Search query")
    resource_types: Optional[list[str]] = Field(
        None, description="youtube, article, documentation"
    )
    limit: int = Field(default=10, ge=1, le=50)


class FindRelationshipsRequest(BaseModel):
    """Request to find relationships for a code entity."""

    file_path: str = Field(..., description="File path or entity name")
    relationship_types: Optional[list[str]] = Field(
        None, description="Filter by relationship types"
    )
    max_depth: int = Field(default=3, ge=1, le=5)


class MCPTools:
    """
    Collection of tools exposed via MCP to Cursor.
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        mongodb_client: MongoDBClient,
        memgpt_agent: MemGPTAgent,
    ):
        """
        Initialize MCP tools.

        Args:
            neo4j_client: Neo4j client
            mongodb_client: MongoDB client
            memgpt_agent: MemGPT agent
        """
        self.neo4j = neo4j_client
        self.mongodb = mongodb_client
        self.memgpt = memgpt_agent

    async def query_architectural_graph(
        self, request: QueryGraphRequest
    ) -> dict[str, Any]:
        """
        Query the architectural knowledge graph.

        Returns nodes and relationships matching the query in Mermaid format.

        Args:
            request: Query request

        Returns:
            Graph data in various formats
        """
        try:
            # Search using full-text search
            cypher = """
            CALL db.index.fulltext.queryNodes('node_search', $query)
            YIELD node, score
            """

            # Add node type filter if specified
            if request.node_types:
                labels = "|".join(request.node_types)
                quoted_types = [f"'{t}'" for t in request.node_types]
                cypher += f" WHERE any(label IN labels(node) WHERE label IN [{','.join(quoted_types)}])"

            cypher += """
            RETURN properties(node) as props, labels(node) as labels, score
            ORDER BY score DESC
            LIMIT $limit
            """

            results = await self.neo4j.query(
                cypher,
                {"query": request.query, "limit": request.max_results},
            )

            # Format results
            nodes = []
            for record in results:
                nodes.append(
                    {
                        "uid": record["props"].get("uid"),
                        "type": record["labels"][0] if record["labels"] else "Unknown",
                        "name": record["props"].get("name", ""),
                        "description": record["props"].get("description"),
                        "relevance_score": record["score"],
                    }
                )

            # Generate Mermaid diagram
            mermaid = self._generate_mermaid(nodes)

            logger.info(
                "mcp_query_graph",
                extra={"query": request.query, "results_count": len(nodes)},
            )

            return {
                "nodes": nodes,
                "count": len(nodes),
                "mermaid_diagram": mermaid,
            }

        except Exception as e:
            logger.exception("mcp_query_graph_failed", extra={"error": str(e)})
            return {"error": str(e), "nodes": [], "count": 0}

    async def retrieve_past_decisions(
        self, request: RetrieveDecisionsRequest
    ) -> dict[str, Any]:
        """
        Retrieve past architectural decisions related to context.

        Args:
            request: Decision retrieval request

        Returns:
            List of relevant decisions with rationale
        """
        try:
            cypher = """
            MATCH (d:Decision)
            WHERE d.context CONTAINS $context OR d.decision CONTAINS $context
            RETURN properties(d) as decision
            ORDER BY d.created_at DESC
            LIMIT $limit
            """

            results = await self.neo4j.query(
                cypher,
                {"context": request.context, "limit": request.limit},
            )

            decisions = []
            for record in results:
                decision = record["decision"]
                decisions.append(
                    {
                        "uid": decision.get("uid"),
                        "name": decision.get("name"),
                        "context": decision.get("context"),
                        "decision": decision.get("decision"),
                        "rationale": decision.get("rationale"),
                        "consequences": decision.get("consequences", []),
                        "created_at": decision.get("created_at"),
                    }
                )

            logger.info(
                "mcp_retrieve_decisions",
                extra={"context": request.context, "decisions_count": len(decisions)},
            )

            return {
                "decisions": decisions,
                "count": len(decisions),
            }

        except Exception as e:
            logger.exception("mcp_retrieve_decisions_failed", extra={"error": str(e)})
            return {"error": str(e), "decisions": [], "count": 0}

    async def search_resources(self, request: SearchResourcesRequest) -> dict[str, Any]:
        """
        Search external resources (YouTube, articles, docs).

        Args:
            request: Resource search request

        Returns:
            List of relevant resources with summaries
        """
        try:
            # Search MongoDB resources
            resources = await self.mongodb.search_resources(
                query=request.query,
                resource_type=request.resource_types[0]
                if request.resource_types
                else None,
                limit=request.limit,
            )

            results = []
            for resource in resources:
                results.append(
                    {
                        "resource_id": resource.resource_id,
                        "type": resource.resource_type,
                        "title": resource.title,
                        "url": resource.url,
                        "summary": resource.summary,
                        "tags": resource.tags,
                    }
                )

            logger.info(
                "mcp_search_resources",
                extra={"query": request.query, "resources_count": len(results)},
            )

            return {
                "resources": results,
                "count": len(results),
            }

        except Exception as e:
            logger.exception("mcp_search_resources_failed", extra={"error": str(e)})
            return {"error": str(e), "resources": [], "count": 0}

    async def find_relationships(
        self, request: FindRelationshipsRequest
    ) -> dict[str, Any]:
        """
        Find relationships for a code entity or file.

        Shows dependencies, implementations, and related decisions.

        Args:
            request: Relationship finding request

        Returns:
            Graph of relationships
        """
        try:
            # Find the node by file path or name
            find_node_cypher = """
            MATCH (n)
            WHERE n.file_path = $path OR n.name CONTAINS $path
            RETURN n.uid as uid
            LIMIT 1
            """

            node_results = await self.neo4j.query(
                find_node_cypher, {"path": request.file_path}
            )

            if not node_results:
                return {
                    "error": f"No node found for: {request.file_path}",
                    "relationships": [],
                    "count": 0,
                }

            node_uid = node_results[0]["uid"]

            # Find relationships
            rel_filter = ""
            if request.relationship_types:
                rel_types = "|".join(request.relationship_types)
                rel_filter = f"[r:{rel_types}*1..{request.max_depth}]"
            else:
                rel_filter = f"[r*1..{request.max_depth}]"

            relationships_cypher = f"""
            MATCH path = (start {{uid: $uid}})-{rel_filter}-(connected)
            RETURN 
                [node in nodes(path) | {{uid: node.uid, name: node.name, type: labels(node)[0]}}] as nodes,
                [rel in relationships(path) | type(rel)] as relationship_types
            LIMIT 20
            """

            rel_results = await self.neo4j.query(
                relationships_cypher, {"uid": node_uid}
            )

            # Generate Mermaid diagram
            mermaid = self._generate_relationship_mermaid(rel_results)

            logger.info(
                "mcp_find_relationships",
                extra={"file_path": request.file_path, "paths_count": len(rel_results)},
            )

            return {
                "relationships": rel_results,
                "count": len(rel_results),
                "mermaid_diagram": mermaid,
                "source_uid": node_uid,
            }

        except Exception as e:
            logger.exception("mcp_find_relationships_failed", extra={"error": str(e)})
            return {"error": str(e), "relationships": [], "count": 0}

    def _generate_mermaid(self, nodes: list[dict[str, Any]]) -> str:
        """
        Generate Mermaid diagram from nodes.

        Args:
            nodes: List of node dictionaries

        Returns:
            Mermaid markdown string
        """
        mermaid_lines = ["graph TD"]

        for node in nodes[:10]:  # Limit to 10 nodes for readability
            uid = node.get("uid", "")[:8]  # Short UID
            name = node.get("name", "Unknown")[:30]  # Truncate name
            node_type = node.get("type", "")

            # Style by type
            style = ""
            if node_type == "Project":
                style = ":::projectStyle"
            elif node_type == "Decision":
                style = ":::decisionStyle"
            elif node_type == "CodeEntity":
                style = ":::codeStyle"

            mermaid_lines.append(f'    {uid}["{name}"] {style}')

        # Add styling
        mermaid_lines.extend(
            [
                "",
                "    classDef projectStyle fill:#4CAF50,color:#fff",
                "    classDef decisionStyle fill:#E91E63,color:#fff",
                "    classDef codeStyle fill:#00BCD4,color:#fff",
            ]
        )

        return "\n".join(mermaid_lines)

    def _generate_relationship_mermaid(self, paths: list[dict[str, Any]]) -> str:
        """
        Generate Mermaid diagram from relationship paths.

        Args:
            paths: List of path dictionaries

        Returns:
            Mermaid markdown string
        """
        mermaid_lines = ["graph TD"]
        added_edges = set()

        for path in paths[:5]:  # Limit paths
            nodes = path.get("nodes", [])
            rel_types = path.get("relationship_types", [])

            for i in range(len(nodes) - 1):
                from_node = nodes[i]
                to_node = nodes[i + 1]
                rel_type = rel_types[i] if i < len(rel_types) else "RELATES_TO"

                from_uid = from_node.get("uid", "")[:8]
                to_uid = to_node.get("uid", "")[:8]
                from_name = from_node.get("name", "")[:20]
                to_name = to_node.get("name", "")[:20]

                edge_key = f"{from_uid}->{to_uid}"
                if edge_key not in added_edges:
                    mermaid_lines.append(f'    {from_uid}["{from_name}"]')
                    mermaid_lines.append(f'    {to_uid}["{to_name}"]')
                    mermaid_lines.append(f"    {from_uid} -->|{rel_type}| {to_uid}")
                    added_edges.add(edge_key)

        return "\n".join(mermaid_lines)
