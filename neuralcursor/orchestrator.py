"""
Main orchestrator for NeuralCursor services.

Manages:
1. Gateway server
2. MCP server
3. Librarian agent
4. File watcher
5. Optimizer (weekly)
6. Conflict detector
7. Synthesizer
8. GPU monitoring
"""

import asyncio
import logging
import signal
from typing import Optional

from neuralcursor.agents.conflict_detector import ConflictDetector
from neuralcursor.agents.librarian import LibrarianAgent
from neuralcursor.agents.optimizer import GraphOptimizer
from neuralcursor.agents.synthesizer import CrossProjectSynthesizer
from neuralcursor.agents.watcher import FileSystemWatcherService
from neuralcursor.brain.mongodb.client import MongoDBClient, MongoDBConfig
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig
from neuralcursor.monitoring.gpu_monitor import get_monitor
from neuralcursor.settings import get_settings

logger = logging.getLogger(__name__)


class NeuralCursorOrchestrator:
    """
    Main orchestrator for all NeuralCursor services.
    
    Manages lifecycle of all components.
    """

    def __init__(self):
        """Initialize orchestrator."""
        self.settings = get_settings()
        self.neo4j: Optional[Neo4jClient] = None
        self.mongodb: Optional[MongoDBClient] = None

        # Agents
        self.librarian: Optional[LibrarianAgent] = None
        self.watcher: Optional[FileSystemWatcherService] = None
        self.optimizer: Optional[GraphOptimizer] = None
        self.conflict_detector: Optional[ConflictDetector] = None
        self.synthesizer: Optional[CrossProjectSynthesizer] = None

        # Monitoring
        self.gpu_monitor = get_monitor()

        # Shutdown flag
        self._shutdown = False

    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info("neuralcursor_initialization_started")

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
                uri=self.settings.mongodb_connection_string,
                database=self.settings.mongodb_database,
            )
            self.mongodb = MongoDBClient(mongodb_config)
            await self.mongodb.connect()

            # Initialize agents
            self.librarian = LibrarianAgent(self.neo4j, self.mongodb)
            self.watcher = FileSystemWatcherService(self.neo4j)
            self.optimizer = GraphOptimizer(self.neo4j)
            self.conflict_detector = ConflictDetector(self.neo4j)
            self.synthesizer = CrossProjectSynthesizer(self.neo4j)

            logger.info("neuralcursor_initialized")

        except Exception as e:
            logger.exception("neuralcursor_initialization_failed", extra={"error": str(e)})
            raise

    async def start_all_services(self) -> None:
        """Start all background services."""
        logger.info("neuralcursor_services_starting")

        tasks = []

        # Start GPU monitoring
        if self.settings.monitoring_enabled:
            await self.gpu_monitor.start_monitoring(
                interval_seconds=self.settings.monitoring_interval_seconds
            )
            logger.info("gpu_monitoring_started")

        # Start file watcher
        if self.settings.watcher_enabled:
            await self.watcher.start()
            logger.info("file_watcher_started")

        # Start librarian (background distillation)
        if self.librarian:
            task = asyncio.create_task(
                self.librarian.run_distillation_loop(interval_seconds=300, batch_size=5)
            )
            tasks.append(task)
            logger.info("librarian_agent_started")

        # Start weekly optimizer
        if self.optimizer:
            task = asyncio.create_task(self.optimizer.run_weekly_cycle(interval_days=7))
            tasks.append(task)
            logger.info("optimizer_started")

        logger.info("neuralcursor_services_started")

        # Keep running until shutdown
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("neuralcursor_services_cancelled")

    async def stop_all_services(self) -> None:
        """Stop all services gracefully."""
        logger.info("neuralcursor_shutdown_started")

        # Stop monitoring
        if self.gpu_monitor:
            await self.gpu_monitor.stop_monitoring()

        # Stop file watcher
        if self.watcher:
            await self.watcher.stop()

        # Close connections
        if self.neo4j:
            await self.neo4j.close()

        if self.mongodb:
            await self.mongodb.close()

        logger.info("neuralcursor_shutdown_completed")

    def handle_shutdown_signal(self, sig) -> None:
        """Handle shutdown signal."""
        logger.info("shutdown_signal_received", extra={"signal": sig})
        self._shutdown = True

    async def run(self) -> None:
        """Run the orchestrator."""
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig, lambda: self.handle_shutdown_signal(sig)
            )

        try:
            await self.initialize()
            await self.start_all_services()

        except KeyboardInterrupt:
            logger.info("neuralcursor_interrupted")

        finally:
            await self.stop_all_services()


async def main():
    """Main entry point."""
    orchestrator = NeuralCursorOrchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    asyncio.run(main())
