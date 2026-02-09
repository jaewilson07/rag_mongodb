#!/usr/bin/env python
"""Run Brain Care routine (optimization + conflict detection + discovery)."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.settings import load_settings
from src.memory_gateway.gateway import MemoryGateway
from src.maintenance.graph_optimizer import GraphOptimizer
from src.maintenance.conflict_detector import ConflictDetector
from src.maintenance.discovery_agent import DiscoveryAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("NeuralCursor Brain Care Routine")
    logger.info("=" * 60)
    
    try:
        settings = load_settings()
        logger.info("✓ Settings loaded")
        
        async with MemoryGateway(settings) as gateway:
            logger.info("✓ Memory gateway initialized")
            
            # Initialize maintenance components
            optimizer = GraphOptimizer(gateway)
            conflict_detector = ConflictDetector(gateway)
            discovery_agent = DiscoveryAgent(gateway)
            
            # Run optimization
            logger.info("\n" + "=" * 60)
            logger.info("STEP 1: Graph Optimization")
            logger.info("=" * 60)
            opt_summary = await optimizer.run_brain_care_cycle()
            print("\n✓ Optimization complete:")
            print(f"  - Duplicates merged: {opt_summary['duplicates_merged']}")
            print(f"  - Stale decisions: {opt_summary['stale_decisions_found']}")
            print(f"  - Broken links fixed: {opt_summary['broken_links_fixed']}")
            print(f"  - Projects archived: {opt_summary['projects_archived']}")
            print(f"  - Orphans removed: {opt_summary['orphaned_nodes_removed']}")
            
            # Run conflict detection
            logger.info("\n" + "=" * 60)
            logger.info("STEP 2: Conflict Detection")
            logger.info("=" * 60)
            conflict_report = await conflict_detector.get_conflict_report()
            print("\n" + conflict_report)
            
            # Run discovery
            logger.info("\n" + "=" * 60)
            logger.info("STEP 3: Pattern Discovery")
            logger.info("=" * 60)
            discovery_report = await discovery_agent.get_discovery_report()
            print("\n" + discovery_report)
            
            # Get recommendations
            logger.info("\n" + "=" * 60)
            logger.info("STEP 4: Recommendations")
            logger.info("=" * 60)
            recommendations = await optimizer.get_optimization_recommendations()
            if recommendations:
                print("\n📌 Recommendations:")
                for rec in recommendations:
                    print(f"  - {rec}")
            else:
                print("\n✅ No recommendations. System is in good health!")
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ Brain Care complete!")
            logger.info("=" * 60)
            
    except Exception as e:
        logger.exception("Brain Care routine failed", extra={"error": str(e)})
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
