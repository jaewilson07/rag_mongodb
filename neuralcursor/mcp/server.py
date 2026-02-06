"""
MCP Server implementation for Cursor IDE integration.

Exposes tools via Model Context Protocol for seamless
integration with Cursor's AI capabilities.
"""

import asyncio
import json
import logging
from typing import Any, Optional

import websockets
from websockets.server import WebSocketServerProtocol

from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig
from neuralcursor.brain.mongodb.client import MongoDBClient, MongoDBConfig
from neuralcursor.brain.memgpt.agent import MemGPTAgent
from neuralcursor.settings import get_settings
from .tools import (
    MCPTools,
    QueryGraphRequest,
    RetrieveDecisionsRequest,
    SearchResourcesRequest,
    FindRelationshipsRequest,
)

logger = logging.getLogger(__name__)


class MCPServer:
    """
    Model Context Protocol (MCP) server.
    
    Handles WebSocket connections from Cursor and routes
    tool calls to appropriate handlers.
    """

    def __init__(self):
        """Initialize MCP server."""
        self.settings = get_settings()
        self.neo4j: Optional[Neo4jClient] = None
        self.mongodb: Optional[MongoDBClient] = None
        self.memgpt: Optional[MemGPTAgent] = None
        self.tools: Optional[MCPTools] = None
        self.server: Optional[websockets.WebSocketServer] = None

    async def initialize(self) -> None:
        """Initialize database clients and tools."""
        try:
            # Initialize Neo4j
            neo4j_config = Neo4jConfig(
                uri=self.settings.neo4j_uri,
                username=self.settings.neo4j_username,
                password=self.settings.neo4j_password,
                database=self.settings.neo4j_database,
            )
            self.neo4j = Neo4jClient(neo4j_config)
            await self.neo4j.connect()

            # Initialize MongoDB
            mongodb_config = MongoDBConfig(
                uri=self.settings.mongodb_uri,
                database=self.settings.mongodb_database,
            )
            self.mongodb = MongoDBClient(mongodb_config)
            await self.mongodb.connect()

            # Initialize MemGPT agent
            self.memgpt = MemGPTAgent(self.neo4j, self.mongodb)

            # Initialize tools
            self.tools = MCPTools(self.neo4j, self.mongodb, self.memgpt)

            logger.info("mcp_server_initialized")

        except Exception as e:
            logger.exception("mcp_initialization_failed", extra={"error": str(e)})
            raise

    async def close(self) -> None:
        """Close connections."""
        if self.neo4j:
            await self.neo4j.close()
        if self.mongodb:
            await self.mongodb.close()

        logger.info("mcp_server_closed")

    async def handle_message(
        self, websocket: WebSocketServerProtocol, message: str
    ) -> dict[str, Any]:
        """
        Handle incoming MCP message.
        
        Args:
            websocket: WebSocket connection
            message: JSON message from Cursor
            
        Returns:
            Response dictionary
        """
        try:
            data = json.loads(message)
            tool_name = data.get("tool")
            params = data.get("params", {})

            logger.info(
                "mcp_tool_call",
                extra={"tool": tool_name, "params": params},
            )

            if not self.tools:
                return {"error": "Tools not initialized"}

            # Route to appropriate tool
            if tool_name == "query_architectural_graph":
                request = QueryGraphRequest(**params)
                result = await self.tools.query_architectural_graph(request)

            elif tool_name == "retrieve_past_decisions":
                request = RetrieveDecisionsRequest(**params)
                result = await self.tools.retrieve_past_decisions(request)

            elif tool_name == "search_resources":
                request = SearchResourcesRequest(**params)
                result = await self.tools.search_resources(request)

            elif tool_name == "find_relationships":
                request = FindRelationshipsRequest(**params)
                result = await self.tools.find_relationships(request)

            elif tool_name == "get_active_context":
                # Return current active context from MemGPT
                if self.memgpt:
                    result = await self.memgpt.get_active_context()
                else:
                    result = {"error": "MemGPT not initialized"}

            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            return {
                "tool": tool_name,
                "result": result,
                "success": "error" not in result,
            }

        except Exception as e:
            logger.exception("mcp_handle_message_failed", extra={"error": str(e)})
            return {"error": str(e), "success": False}

    async def handle_connection(self, websocket: WebSocketServerProtocol) -> None:
        """
        Handle WebSocket connection from Cursor.
        
        Args:
            websocket: WebSocket connection
        """
        client_address = websocket.remote_address
        logger.info("mcp_client_connected", extra={"address": client_address})

        try:
            async for message in websocket:
                response = await self.handle_message(websocket, message)
                await websocket.send(json.dumps(response))

        except websockets.exceptions.ConnectionClosed:
            logger.info("mcp_client_disconnected", extra={"address": client_address})

        except Exception as e:
            logger.exception(
                "mcp_connection_error",
                extra={"address": client_address, "error": str(e)},
            )

    async def start(self) -> None:
        """Start the MCP server."""
        if not self.settings.mcp_enabled:
            logger.info("mcp_server_disabled")
            return

        await self.initialize()

        self.server = await websockets.serve(
            self.handle_connection,
            self.settings.mcp_host,
            self.settings.mcp_port,
        )

        logger.info(
            "mcp_server_started",
            extra={
                "host": self.settings.mcp_host,
                "port": self.settings.mcp_port,
            },
        )

        # Keep server running
        await asyncio.Future()  # Run forever

    async def stop(self) -> None:
        """Stop the MCP server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        await self.close()
        logger.info("mcp_server_stopped")


async def main():
    """Run MCP server as standalone application."""
    server = MCPServer()

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("mcp_server_interrupted")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
