#!/usr/bin/env python
"""Start the Librarian agent for continuous knowledge distillation."""

import asyncio
import logging
import sys

from mdrag.librarian_agent import LibrarianAgent
from mdrag.capabilities.memory import MemoryGateway
from mdrag.settings import load_settings
from mdrag.validation import ValidationError, validate_mongodb, validate_neo4j

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

        # Validate MongoDB (source) and Neo4j (target) before starting
        try:
            await validate_mongodb(settings, strict=True)
            logger.info("✓ MongoDB validation passed")

            validate_neo4j(
                settings.neo4j_uri,
                settings.neo4j_username,
                settings.neo4j_password,
                settings.neo4j_database,
            )
            logger.info("✓ Neo4j validation passed")
        except ValidationError as e:
            logger.error(f"Validation failed:\n{e}")
            return 1

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
