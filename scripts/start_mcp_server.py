#!/usr/bin/env python
"""Start the NeuralCursor MCP server for Cursor IDE integration."""

import asyncio
import logging
import sys

from mdrag.mcp_server import NeuralCursorMCPServer
from mdrag.settings import load_settings
from mdrag.validation import ValidationError, validate_neo4j

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    try:
        settings = load_settings()

        # Validate Neo4j connection before starting
        try:
            validate_neo4j(
                settings.neo4j_uri,
                settings.neo4j_username,
                settings.neo4j_password,
                settings.neo4j_database,
            )
            logger.info("✓ Neo4j validation passed")
        except ValidationError as e:
            logger.error(f"Neo4j validation failed:\n{e}")
            return 1

        server = NeuralCursorMCPServer(settings)
        await server.initialize()

        logger.info("=" * 60)
        logger.info("NeuralCursor MCP Server")
        logger.info("Ready for Cursor IDE integration")
        logger.info("=" * 60)

        await server.run()

    except KeyboardInterrupt:
        logger.info("\nMCP server stopped by user")
    except Exception as e:
        logger.exception("MCP server failed", extra={"error": str(e)})
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
