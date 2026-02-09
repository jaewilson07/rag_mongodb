"""
Dual GPU orchestration for reasoning and embedding LLMs.

GPU 0: High-parameter Reasoning LLM (DeepSeek-Coder-33B)
GPU 1: Embedding & RAG tasks (BGE-M3)
"""

import logging
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from neuralcursor.settings import get_settings

logger = logging.getLogger(__name__)


class LLMRequest(BaseModel):
    """Request to the LLM."""

    prompt: str
    max_tokens: int = Field(default=2048)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = Field(default=False)


class EmbeddingRequest(BaseModel):
    """Request for text embeddings."""

    text: str | list[str]
    model: Optional[str] = None


class LLMResponse(BaseModel):
    """Response from the LLM."""

    text: str
    tokens_used: int
    latency_ms: float


class EmbeddingResponse(BaseModel):
    """Response from embedding model."""

    embeddings: list[list[float]]
    dimensions: int
    latency_ms: float


class DualGPUOrchestrator:
    """
    Orchestrates LLM requests across dual 3090 GPUs.
    
    GPU 0 handles complex reasoning queries.
    GPU 1 handles embedding generation and lightweight RAG tasks.
    """

    def __init__(self):
        """Initialize orchestrator with settings."""
        self.settings = get_settings()
        self._reasoning_client = httpx.AsyncClient(
            base_url=self.settings.reasoning_llm_host,
            timeout=300.0,  # 5 minute timeout for complex reasoning
        )
        self._embedding_client = httpx.AsyncClient(
            base_url=self.settings.embedding_llm_host,
            timeout=60.0,
        )

    async def close(self) -> None:
        """Close HTTP clients."""
        await self._reasoning_client.aclose()
        await self._embedding_client.aclose()

    async def generate_reasoning(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response from reasoning LLM (GPU 0).
        
        Args:
            request: LLM request
            
        Returns:
            LLM response
        """
        import time

        start_time = time.time()

        try:
            # vLLM-compatible API call
            response = await self._reasoning_client.post(
                "/v1/completions",
                json={
                    "model": self.settings.reasoning_llm_model,
                    "prompt": request.prompt,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": request.stream,
                },
            )

            response.raise_for_status()
            data = response.json()

            latency_ms = (time.time() - start_time) * 1000

            # Extract text from vLLM response
            text = data["choices"][0]["text"]
            tokens_used = data["usage"]["total_tokens"]

            logger.info(
                "reasoning_llm_response",
                extra={
                    "latency_ms": latency_ms,
                    "tokens": tokens_used,
                    "model": self.settings.reasoning_llm_model,
                },
            )

            return LLMResponse(
                text=text,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.exception("reasoning_llm_failed", extra={"error": str(e)})
            raise

    async def generate_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings from embedding model (GPU 1).
        
        Args:
            request: Embedding request
            
        Returns:
            Embedding response
        """
        import time

        start_time = time.time()

        try:
            # Convert single text to list
            texts = [request.text] if isinstance(request.text, str) else request.text

            # Use OpenAI-compatible embedding endpoint
            response = await self._embedding_client.post(
                "/v1/embeddings",
                json={
                    "model": request.model or self.settings.embedding_llm_model,
                    "input": texts,
                },
            )

            response.raise_for_status()
            data = response.json()

            latency_ms = (time.time() - start_time) * 1000

            # Extract embeddings
            embeddings = [item["embedding"] for item in data["data"]]
            dimensions = len(embeddings[0]) if embeddings else 0

            logger.info(
                "embedding_generated",
                extra={
                    "latency_ms": latency_ms,
                    "texts_count": len(texts),
                    "dimensions": dimensions,
                },
            )

            return EmbeddingResponse(
                embeddings=embeddings,
                dimensions=dimensions,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.exception("embedding_generation_failed", extra={"error": str(e)})
            raise

    async def health_check(self) -> dict[str, Any]:
        """
        Check health of both LLM endpoints.
        
        Returns:
            Health status dictionary
        """
        reasoning_healthy = False
        embedding_healthy = False
        details: dict[str, Any] = {}

        # Check reasoning LLM
        try:
            response = await self._reasoning_client.get("/health")
            reasoning_healthy = response.status_code == 200
            details["reasoning_llm"] = response.json() if reasoning_healthy else {"status": "unhealthy"}
        except Exception as e:
            details["reasoning_llm"] = {"status": "unreachable", "error": str(e)}

        # Check embedding model
        try:
            response = await self._embedding_client.get("/health")
            embedding_healthy = response.status_code == 200
            details["embedding_llm"] = response.json() if embedding_healthy else {"status": "unhealthy"}
        except Exception as e:
            details["embedding_llm"] = {"status": "unreachable", "error": str(e)}

        return {
            "status": "healthy" if (reasoning_healthy and embedding_healthy) else "degraded",
            "reasoning_llm_healthy": reasoning_healthy,
            "embedding_llm_healthy": embedding_healthy,
            "details": details,
        }


# Global orchestrator instance
_orchestrator: Optional[DualGPUOrchestrator] = None


def get_orchestrator() -> DualGPUOrchestrator:
    """
    Get or create the global orchestrator instance.
    
    Returns:
        DualGPUOrchestrator instance
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DualGPUOrchestrator()
    return _orchestrator


async def close_orchestrator() -> None:
    """Close the global orchestrator."""
    global _orchestrator
    if _orchestrator:
        await _orchestrator.close()
        _orchestrator = None
