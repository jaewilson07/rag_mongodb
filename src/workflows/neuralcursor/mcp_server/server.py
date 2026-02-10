"""MCP server implementation for NeuralCursor."""

import logging
from typing import Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

from mdrag.config.settings import Settings
from mdrag.capabilities.memory.gateway import MemoryGateway
from .tools import MCPTools

logger = logging.getLogger(__name__)


class NeuralCursorMCPServer:
    """
    MCP server for NeuralCursor Second Brain.

    Exposes tools to Cursor IDE via Model Context Protocol:
    - query_architectural_graph
    - retrieve_past_decisions
    - search_resources
    - get_active_project_context
    - find_cross_project_patterns
    - get_graph_statistics
    """

    def __init__(self, settings: Settings):
        """
        Initialize MCP server.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.gateway: Optional[MemoryGateway] = None
        self.mcp_tools: Optional[MCPTools] = None
        self.server = Server("neuralcursor")

        # Register tool handlers
        self._register_tools()

    async def initialize(self) -> None:
        """Initialize memory gateway and tools."""
        self.gateway = MemoryGateway(self.settings)
        await self.gateway.initialize()

        self.mcp_tools = MCPTools(self.gateway)

        logger.info("mcp_server_initialized")

    def _register_tools(self) -> None:
        """Register all MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="query_architectural_graph",
                    description=(
                        "Query the architectural knowledge graph to understand why code exists. "
                        "Traces requirements → decisions → code entities. "
                        "Returns Mermaid diagrams and detailed explanations."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "File path to query about",
                            },
                            "line_number": {
                                "type": "integer",
                                "description": "Line number in file (optional)",
                            },
                            "entity_uuid": {
                                "type": "string",
                                "description": "Specific entity UUID (optional)",
                            },
                            "query_text": {
                                "type": "string",
                                "description": "Natural language query (optional)",
                            },
                        },
                    },
                ),
                Tool(
                    name="retrieve_past_decisions",
                    description=(
                        "Retrieve decision history for code entities or projects. "
                        "Shows rationale, alternatives considered, and evolution over time."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code_entity_uuid": {
                                "type": "string",
                                "description": "Code entity UUID (optional)",
                            },
                            "project_uuid": {
                                "type": "string",
                                "description": "Project UUID (optional)",
                            },
                        },
                    },
                ),
                Tool(
                    name="search_resources",
                    description=(
                        "Search across external resources (videos, articles, papers, tutorials). "
                        "Shows which decisions were inspired by which resources."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query",
                            },
                            "resource_type": {
                                "type": "string",
                                "description": "Filter by type: video, article, paper, tutorial (optional)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="get_active_project_context",
                    description=(
                        "Get context for all active projects. "
                        "Shows project goals, status, and recently touched files."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="find_cross_project_patterns",
                    description=(
                        "Find code patterns (functions, classes, modules) used across multiple projects. "
                        "Helps identify reusable utilities and common patterns."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entity_type": {
                                "type": "string",
                                "description": "Type: function, class, module (default: function)",
                                "default": "function",
                            },
                            "min_usage": {
                                "type": "integer",
                                "description": "Minimum number of projects (default: 2)",
                                "default": 2,
                            },
                        },
                    },
                ),
                Tool(
                    name="get_graph_statistics",
                    description=(
                        "Get statistics about the knowledge graph. "
                        "Shows node counts, relationship counts, and project status."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls."""
            if not self.mcp_tools:
                return [TextContent(type="text", text="Error: MCP server not initialized")]

            try:
                if name == "query_architectural_graph":
                    result = await self.mcp_tools.query_architectural_graph(
                        file_path=arguments.get("file_path"),
                        line_number=arguments.get("line_number"),
                        entity_uuid=arguments.get("entity_uuid"),
                        query_text=arguments.get("query_text"),
                    )
                elif name == "retrieve_past_decisions":
                    result = await self.mcp_tools.retrieve_past_decisions(
                        code_entity_uuid=arguments.get("code_entity_uuid"),
                        project_uuid=arguments.get("project_uuid"),
                    )
                elif name == "search_resources":
                    result = await self.mcp_tools.search_resources(
                        query=arguments.get("query", ""),
                        resource_type=arguments.get("resource_type"),
                        limit=arguments.get("limit", 10),
                    )
                elif name == "get_active_project_context":
                    result = await self.mcp_tools.get_active_project_context()
                elif name == "find_cross_project_patterns":
                    result = await self.mcp_tools.find_cross_project_patterns(
                        entity_type=arguments.get("entity_type", "function"),
                        min_usage=arguments.get("min_usage", 2),
                    )
                elif name == "get_graph_statistics":
                    result = await self.mcp_tools.get_graph_statistics()
                else:
                    result = f"Unknown tool: {name}"

                return [TextContent(type="text", text=result)]

            except Exception as e:
                logger.exception("mcp_tool_call_failed", extra={"tool": name, "error": str(e)})
                return [TextContent(type="text", text=f"Error: {e}")]

    async def run(self) -> None:
        """Run the MCP server."""
        logger.info("mcp_server_starting")

        # Use stdio transport for Cursor integration
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )

    async def close(self) -> None:
        """Close the MCP server."""
        if self.gateway:
            await self.gateway.close()
        logger.info("mcp_server_closed")
