"""MCP tools for Cursor IDE integration."""

import logging
from typing import Optional, Any

from mdrag.capabilities.memory.gateway import MemoryGateway
from mdrag.capabilities.memory.models import ArchitecturalQuery
from mdrag.integrations.neo4j.queries import SecondBrainQueries
from mdrag.integrations.neo4j.models import NodeType

logger = logging.getLogger(__name__)


class MCPTools:
    """
    MCP tools exposed to Cursor IDE.

    These tools allow Cursor to:
    - Query the architectural knowledge graph
    - Retrieve past decisions and their rationale
    - Search across resources (videos, docs, code)
    - Get project context
    """

    def __init__(self, memory_gateway: MemoryGateway):
        """
        Initialize MCP tools.

        Args:
            memory_gateway: Memory gateway instance
        """
        self.gateway = memory_gateway

    async def query_architectural_graph(
        self,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        entity_uuid: Optional[str] = None,
        query_text: Optional[str] = None,
    ) -> str:
        """
        Query the architectural knowledge graph.

        This is the primary tool for answering "Why does this code exist?"

        Args:
            file_path: File path to query about
            line_number: Line number in file
            entity_uuid: Specific entity UUID
            query_text: Natural language query

        Returns:
            Mermaid diagram or Markdown explanation
        """
        try:
            query = ArchitecturalQuery(
                file_path=file_path,
                line_number=line_number,
                entity_uuid=entity_uuid,
                query_text=query_text,
                include_history=True,
                include_resources=True,
            )

            context = await self.gateway.get_architectural_context(query)

            # Format as Mermaid diagram
            if file_path:
                return self._format_architectural_diagram(context, file_path)
            else:
                return self._format_architectural_text(context)

        except Exception as e:
            logger.exception("mcp_architectural_query_failed", extra={"error": str(e)})
            return f"Error querying architectural graph: {e}"

    def _format_architectural_diagram(
        self, context: Any, file_path: str
    ) -> str:
        """
        Format architectural context as Mermaid diagram.

        Args:
            context: Architectural context
            file_path: File path

        Returns:
            Mermaid diagram in Markdown
        """
        diagram = [
            "```mermaid",
            "graph TD",
            f'    FILE["{file_path}"]',
        ]

        # Add decisions
        for idx, dec in enumerate(context.decisions[:5]):
            dec_id = f"DEC{idx}"
            dec_name = dec.get("name", "Unknown Decision")
            diagram.append(f'    {dec_id}["{dec_name}"]')
            diagram.append(f"    {dec_id} --> FILE")

        # Add requirements
        for idx, req in enumerate(context.requirements[:5]):
            req_id = f"REQ{idx}"
            req_name = req.get("name", "Unknown Requirement")
            diagram.append(f'    {req_id}["{req_name}"]')
            if context.decisions:
                diagram.append(f"    {req_id} --> DEC0")

        # Add resources
        for idx, res in enumerate(context.resources[:3]):
            res_id = f"RES{idx}"
            res_name = res.get("name", "Resource")
            diagram.append(f'    {res_id}["{res_name}"]')
            if context.decisions:
                diagram.append(f"    {res_id} -.-> DEC0")

        diagram.append("```")

        # Add detailed explanation
        explanation = [
            "",
            f"## Architectural Context for `{file_path}`",
            "",
        ]

        if context.decisions:
            explanation.append("### Decisions:")
            for dec in context.decisions:
                explanation.append(f"- **{dec.get('name')}**: {dec.get('rationale', 'No rationale provided')}")
            explanation.append("")

        if context.requirements:
            explanation.append("### Requirements:")
            for req in context.requirements:
                explanation.append(f"- {req.get('name')}: {req.get('description', 'No description')}")
            explanation.append("")

        if context.resources:
            explanation.append("### Inspirations:")
            for res in context.resources:
                url = res.get('url', 'No URL')
                explanation.append(f"- [{res.get('name')}]({url})")
            explanation.append("")

        return "\n".join(diagram + explanation)

    def _format_architectural_text(self, context: Any) -> str:
        """
        Format architectural context as text.

        Args:
            context: Architectural context

        Returns:
            Markdown formatted text
        """
        output = ["# Architectural Context", ""]

        if context.decisions:
            output.append("## Decisions:")
            for dec in context.decisions:
                output.append(f"### {dec.get('name')}")
                output.append(f"**Rationale**: {dec.get('rationale', 'N/A')}")
                if dec.get('alternatives_considered'):
                    output.append(f"**Alternatives**: {', '.join(dec.get('alternatives_considered', []))}")
                output.append("")

        if context.requirements:
            output.append("## Requirements:")
            for req in context.requirements:
                output.append(f"### {req.get('name')}")
                output.append(f"{req.get('description', 'No description')}")
                output.append(f"**Priority**: {req.get('priority', 'medium')}")
                output.append("")

        return "\n".join(output)

    async def retrieve_past_decisions(
        self, code_entity_uuid: Optional[str] = None, project_uuid: Optional[str] = None
    ) -> str:
        """
        Retrieve past decisions for code or project.

        Args:
            code_entity_uuid: Code entity UUID
            project_uuid: Project UUID

        Returns:
            Formatted decision history
        """
        try:
            if code_entity_uuid:
                query, params = SecondBrainQueries.find_decision_history(code_entity_uuid)
            elif project_uuid:
                query, params = SecondBrainQueries.find_project_context(project_uuid)
            else:
                return "Error: Must provide either code_entity_uuid or project_uuid"

            results = await self.gateway.neo4j_client.execute_cypher(query, params)

            if not results:
                return "No decision history found."

            output = ["# Decision History", ""]

            for result in results:
                if "dec" in result:
                    dec = result["dec"]
                    output.append(f"## {dec.get('name', 'Unknown Decision')}")
                    output.append(f"**Rationale**: {dec.get('rationale', 'N/A')}")
                    output.append(f"**Date**: {dec.get('decided_at', 'Unknown')}")

                    if result.get("previous_decisions"):
                        output.append("**Previous Decisions**:")
                        for prev_dec in result["previous_decisions"]:
                            output.append(f"  - {prev_dec.get('name', 'Unknown')}")

                    if result.get("inspirations"):
                        output.append("**Inspired By**:")
                        for res in result["inspirations"]:
                            output.append(f"  - {res.get('name', 'Unknown')}: {res.get('url', 'No URL')}")

                    output.append("")

            return "\n".join(output)

        except Exception as e:
            logger.exception("mcp_retrieve_decisions_failed", extra={"error": str(e)})
            return f"Error retrieving decisions: {e}"

    async def search_resources(
        self, query: str, resource_type: Optional[str] = None, limit: int = 10
    ) -> str:
        """
        Search across resources (videos, docs, articles).

        Args:
            query: Search query
            resource_type: Filter by type (video, article, etc.)
            limit: Maximum results

        Returns:
            Formatted search results
        """
        try:
            # Build Cypher query
            type_filter = f"r.resource_type = '{resource_type}'" if resource_type else "true"

            cypher_query = f"""
            MATCH (r:Resource)
            WHERE {type_filter}
              AND (r.name CONTAINS $query OR r.description CONTAINS $query)
            OPTIONAL MATCH (r)-[:INSPIRED_BY]->(d:Decision)
            RETURN r, collect(d) as decisions
            LIMIT $limit
            """

            results = await self.gateway.neo4j_client.execute_cypher(
                cypher_query,
                {"query": query, "limit": limit},
            )

            if not results:
                return f"No resources found matching '{query}'"

            output = [f"# Resource Search Results for: {query}", ""]

            for result in results:
                resource = result.get("r", {})
                decisions = result.get("decisions", [])

                output.append(f"## {resource.get('name', 'Unknown Resource')}")
                output.append(f"**Type**: {resource.get('resource_type', 'unknown')}")

                if resource.get('url'):
                    output.append(f"**URL**: {resource.get('url')}")

                if resource.get('description'):
                    output.append(f"**Description**: {resource.get('description')}")

                if resource.get('key_points'):
                    output.append("**Key Points**:")
                    for point in resource.get('key_points', []):
                        output.append(f"  - {point}")

                if decisions:
                    output.append("**Inspired Decisions**:")
                    for dec in decisions:
                        output.append(f"  - {dec.get('name', 'Unknown')}")

                output.append("")

            return "\n".join(output)

        except Exception as e:
            logger.exception("mcp_search_resources_failed", extra={"error": str(e)})
            return f"Error searching resources: {e}"

    async def get_active_project_context(self) -> str:
        """
        Get context for all active projects.

        Returns:
            Formatted project list
        """
        try:
            working_set = await self.gateway.get_working_set()

            if not working_set.active_projects:
                return "No active projects in working set."

            output = ["# Active Projects", ""]

            for project_uuid in working_set.active_projects:
                node = await self.gateway.neo4j_client.get_node(
                    project_uuid, NodeType.PROJECT
                )

                if node:
                    output.append(f"## {node.get('name', 'Unknown Project')}")
                    output.append(f"**Status**: {node.get('status', 'unknown')}")

                    if node.get('description'):
                        output.append(f"**Description**: {node.get('description')}")

                    if node.get('goals'):
                        output.append("**Goals**:")
                        for goal in node.get('goals', []):
                            output.append(f"  - {goal}")

                    output.append("")

            # Add recently touched files
            output.append("## Recently Active Files:")
            for file_path in working_set.active_files[:10]:
                output.append(f"- `{file_path}`")

            return "\n".join(output)

        except Exception as e:
            logger.exception("mcp_get_project_context_failed", extra={"error": str(e)})
            return f"Error getting project context: {e}"

    async def find_cross_project_patterns(
        self, entity_type: str = "function", min_usage: int = 2
    ) -> str:
        """
        Find code patterns used across multiple projects.

        Args:
            entity_type: Type of entity (function, class, module)
            min_usage: Minimum number of projects

        Returns:
            Formatted pattern list
        """
        try:
            query, params = SecondBrainQueries.find_cross_project_patterns(
                entity_type, min_usage
            )

            results = await self.gateway.neo4j_client.execute_cypher(query, params)

            if not results:
                return f"No cross-project patterns found for {entity_type}"

            output = [f"# Cross-Project Patterns ({entity_type})", ""]

            for result in results:
                entity_name = result.get("entity_name", "Unknown")
                file_path = result.get("file_path", "Unknown")
                usage_count = result.get("usage_count", 0)

                output.append(f"## `{entity_name}`")
                output.append(f"**Location**: `{file_path}`")
                output.append(f"**Used in {usage_count} projects**")
                output.append("")

            return "\n".join(output)

        except Exception as e:
            logger.exception("mcp_cross_project_patterns_failed", extra={"error": str(e)})
            return f"Error finding patterns: {e}"

    async def get_graph_statistics(self) -> str:
        """
        Get statistics about the knowledge graph.

        Returns:
            Formatted statistics
        """
        try:
            stats = await self.gateway.get_graph_stats()

            output = [
                "# Knowledge Graph Statistics",
                "",
                f"**Total Nodes**: {stats.total_nodes}",
                f"**Total Relationships**: {stats.total_relationships}",
                f"**Active Projects**: {stats.active_projects}",
                f"**Archived Projects**: {stats.archived_projects}",
                "",
                "## Node Breakdown:",
            ]

            for node_type, count in stats.node_counts.items():
                output.append(f"- {node_type}: {count}")

            output.append("")
            output.append("## Relationship Breakdown:")

            for rel_type, count in stats.relationship_counts.items():
                output.append(f"- {rel_type}: {count}")

            return "\n".join(output)

        except Exception as e:
            logger.exception("mcp_graph_stats_failed", extra={"error": str(e)})
            return f"Error getting statistics: {e}"
