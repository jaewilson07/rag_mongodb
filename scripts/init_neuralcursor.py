#!/usr/bin/env python
"""Initialize NeuralCursor Second Brain infrastructure."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.settings import load_settings
from src.integrations.neo4j.client import Neo4jClient
from src.integrations.neo4j.schema import PARASchema
from src.memory_gateway.gateway import MemoryGateway
from src.llm.vram_monitor import VRAMMonitor, create_vram_dashboard_html
from src.llm.vllm_config import VRAMMonitorConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def initialize_neo4j(settings):
    """Initialize Neo4j schema with constraints and indexes."""
    logger.info("Initializing Neo4j schema...")
    
    async with Neo4jClient(settings) as client:
        await client.initialize_schema()
        logger.info("✓ Neo4j schema initialized successfully")


async def initialize_memory_gateway(settings):
    """Initialize and test memory gateway."""
    logger.info("Initializing memory gateway...")
    
    async with MemoryGateway(settings) as gateway:
        # Test connectivity
        stats = await gateway.get_graph_stats()
        logger.info(f"✓ Memory gateway initialized. Total nodes: {stats.total_nodes}")


async def initialize_vram_monitor():
    """Initialize VRAM monitoring."""
    logger.info("Initializing VRAM monitor...")
    
    config = VRAMMonitorConfig()
    monitor = VRAMMonitor(config)
    
    await monitor.initialize()
    metrics = await monitor.get_all_metrics()
    
    if "error" in metrics:
        logger.warning(f"⚠ VRAM monitor initialization failed: {metrics['error']}")
        logger.info("Install nvidia-ml-py for GPU monitoring: pip install nvidia-ml-py")
    else:
        logger.info(f"✓ VRAM monitor initialized. Found {len(metrics['gpus'])} GPU(s)")
        
        # Create dashboard HTML
        await create_vram_dashboard_html()
        logger.info("✓ VRAM dashboard HTML created at data/vram_dashboard.html")
    
    await monitor.shutdown()


async def main():
    """Main initialization routine."""
    logger.info("=" * 60)
    logger.info("NeuralCursor Second Brain - Infrastructure Initialization")
    logger.info("=" * 60)
    
    try:
        settings = load_settings()
        logger.info("✓ Settings loaded successfully")
    except Exception as e:
        logger.error(f"✗ Failed to load settings: {e}")
        logger.error("Make sure .env file is configured correctly")
        return 1
    
    try:
        # Initialize Neo4j
        await initialize_neo4j(settings)
        
        # Initialize memory gateway
        await initialize_memory_gateway(settings)
        
        # Initialize VRAM monitor
        await initialize_vram_monitor()
        
        logger.info("=" * 60)
        logger.info("✓ NeuralCursor initialization complete!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Start vLLM servers (if using local models):")
        logger.info("   python scripts/start_vllm.py")
        logger.info("")
        logger.info("2. Run ingestion to populate knowledge graph:")
        logger.info("   uv run python -m src.ingestion.ingest -d ./documents")
        logger.info("")
        logger.info("3. Start the MCP server:")
        logger.info("   python scripts/start_mcp_server.py")
        logger.info("")
        logger.info("4. Open VRAM dashboard:")
        logger.info("   open data/vram_dashboard.html")
        logger.info("")
        
        return 0
        
    except Exception as e:
        logger.exception("Initialization failed", extra={"error": str(e)})
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
