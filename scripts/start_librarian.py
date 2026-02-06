#!/usr/bin/env python
"""Start the Librarian agent for continuous knowledge distillation."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.settings import load_settings
from src.memory_gateway.gateway import MemoryGateway
from src.librarian_agent.agent import LibrarianAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("NeuralCursor Librarian Agent")
    logger.info("=" * 60)
    
    try:
        settings = load_settings()
        logger.info("✓ Settings loaded")
        
        async with MemoryGateway(settings) as gateway:
            logger.info("✓ Memory gateway initialized")
            
            librarian = LibrarianAgent(settings, gateway)
            logger.info("✓ Librarian agent created")
            
            logger.info("=" * 60)
            logger.info("Starting continuous distillation...")
            logger.info("Processing MongoDB → Neo4j every 30 minutes")
            logger.info("Press Ctrl+C to stop")
            logger.info("=" * 60)
            
            await librarian.run_continuous(interval_minutes=30)
            
    except KeyboardInterrupt:
        logger.info("\n✓ Librarian agent stopped by user")
    except Exception as e:
        logger.exception("Librarian agent failed", extra={"error": str(e)})
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
