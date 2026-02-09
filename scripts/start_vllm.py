#!/usr/bin/env python
"""Launch vLLM servers for dual GPU orchestration."""

import asyncio
import logging
import sys
import subprocess
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.settings import load_settings
from src.llm.vllm_config import VLLMConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VLLMServerManager:
    """Manager for vLLM server processes."""

    def __init__(self, config: VLLMConfig):
        """
        Initialize server manager.
        
        Args:
            config: vLLM configuration
        """
        self.config = config
        self.reasoning_process: Optional[subprocess.Popen] = None
        self.embedding_process: Optional[subprocess.Popen] = None

    def start_reasoning_server(self) -> None:
        """Start reasoning model server on GPU 0."""
        logger.info("Starting reasoning model server (GPU 0)...")
        logger.info(f"Model: {self.config.reasoning_model}")
        logger.info(f"Port: {self.config.reasoning_port}")
        
        cmd = self.config.get_reasoning_launch_command()
        
        # Extract CUDA_VISIBLE_DEVICES
        env = {"CUDA_VISIBLE_DEVICES": str(self.config.reasoning_gpu_id)}
        cmd = cmd[1:]  # Remove env prefix
        
        logger.info(f"Command: {' '.join(cmd)}")
        
        self.reasoning_process = subprocess.Popen(
            cmd,
            env={**subprocess.os.environ, **env},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        logger.info(f"✓ Reasoning server started (PID: {self.reasoning_process.pid})")

    def start_embedding_server(self) -> None:
        """Start embedding model server on GPU 1."""
        logger.info("Starting embedding model server (GPU 1)...")
        logger.info(f"Model: {self.config.embedding_model}")
        logger.info(f"Port: {self.config.embedding_port}")
        
        cmd = self.config.get_embedding_launch_command()
        
        # Extract CUDA_VISIBLE_DEVICES
        env = {"CUDA_VISIBLE_DEVICES": str(self.config.embedding_gpu_id)}
        cmd = cmd[1:]  # Remove env prefix
        
        logger.info(f"Command: {' '.join(cmd)}")
        
        self.embedding_process = subprocess.Popen(
            cmd,
            env={**subprocess.os.environ, **env},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        logger.info(f"✓ Embedding server started (PID: {self.embedding_process.pid})")

    def stop_servers(self) -> None:
        """Stop all vLLM servers."""
        logger.info("Stopping vLLM servers...")
        
        if self.reasoning_process:
            self.reasoning_process.terminate()
            self.reasoning_process.wait(timeout=10)
            logger.info("✓ Reasoning server stopped")
        
        if self.embedding_process:
            self.embedding_process.terminate()
            self.embedding_process.wait(timeout=10)
            logger.info("✓ Embedding server stopped")

    async def monitor_servers(self) -> None:
        """Monitor server health."""
        logger.info("Monitoring servers (press Ctrl+C to stop)...")
        
        try:
            while True:
                # Check process health
                if self.reasoning_process and self.reasoning_process.poll() is not None:
                    logger.error("Reasoning server crashed!")
                    break
                
                if self.embedding_process and self.embedding_process.poll() is not None:
                    logger.error("Embedding server crashed!")
                    break
                
                await asyncio.sleep(5)
        except KeyboardInterrupt:
            logger.info("Received stop signal")
        finally:
            self.stop_servers()


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("NeuralCursor vLLM Server Manager")
    logger.info("=" * 60)
    
    try:
        settings = load_settings()
        
        if not settings.vllm_enabled:
            logger.error("vLLM is not enabled in settings")
            logger.info("Set VLLM_ENABLED=true in .env to enable local model serving")
            return 1
        
        config = VLLMConfig(
            reasoning_model=settings.vllm_reasoning_model,
            reasoning_port=int(settings.vllm_reasoning_url.split(":")[-1]),
            embedding_model=settings.vllm_embedding_model,
            embedding_port=int(settings.vllm_embedding_url.split(":")[-1]),
        )
        
        manager = VLLMServerManager(config)
        
        # Start servers
        manager.start_reasoning_server()
        logger.info("Waiting 10 seconds for reasoning server to initialize...")
        import time
        time.sleep(10)
        
        manager.start_embedding_server()
        logger.info("Waiting 10 seconds for embedding server to initialize...")
        time.sleep(10)
        
        logger.info("=" * 60)
        logger.info("✓ All vLLM servers started successfully")
        logger.info("=" * 60)
        logger.info(f"Reasoning API: {settings.vllm_reasoning_url}")
        logger.info(f"Embedding API: {settings.vllm_embedding_url}")
        logger.info("=" * 60)
        
        # Monitor until interrupted
        asyncio.run(manager.monitor_servers())
        
        return 0
        
    except Exception as e:
        logger.exception("Failed to start vLLM servers", extra={"error": str(e)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
