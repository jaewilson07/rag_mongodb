#!/usr/bin/env python
"""Start the filesystem watcher for automatic graph updates."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.settings import load_settings
from src.memory_gateway.gateway import MemoryGateway
from src.file_watcher.watcher import FileWatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("NeuralCursor File Watcher")
    logger.info("=" * 60)
    
    try:
        settings = load_settings()
        logger.info("✓ Settings loaded")
        
        async with MemoryGateway(settings) as gateway:
            logger.info("✓ Memory gateway initialized")
            
            watcher = FileWatcher(settings, gateway)
            
            # Add default watch paths
            workspace_root = Path.cwd()
            
            # Watch src directory
            src_path = workspace_root / "src"
            if src_path.exists():
                watcher.add_watch_path(str(src_path))
            
            # Allow custom paths from command line
            if len(sys.argv) > 1:
                for arg in sys.argv[1:]:
                    watcher.add_watch_path(arg)
            
            logger.info("=" * 60)
            logger.info("Watching for file changes...")
            logger.info("Press Ctrl+C to stop")
            logger.info("=" * 60)
            
            await watcher.run_forever()
            
    except KeyboardInterrupt:
        logger.info("\n✓ File watcher stopped by user")
    except Exception as e:
        logger.exception("File watcher failed", extra={"error": str(e)})
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
