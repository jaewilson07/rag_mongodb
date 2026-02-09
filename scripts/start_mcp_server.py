#!/usr/bin/env python
"""Start the NeuralCursor MCP server for Cursor IDE integration."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.settings import load_settings
from src.mcp_server.server import NeuralCursorMCPServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    try:
        settings = load_settings()
        
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
