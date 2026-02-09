"""vLLM client for interacting with local model servers."""

import logging
from typing import Optional, List, Dict, Any
import httpx
from openai import AsyncOpenAI

from src.settings import Settings

logger = logging.getLogger(__name__)


class VLLMClient:
    """
    Client for interacting with vLLM model servers.
    
    Provides unified interface for:
    - Reasoning LLM (graph extraction, complex queries)
    - Embedding model (vector generation)
    """

    def __init__(self, settings: Settings):
        """
        Initialize vLLM client.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        
        if not settings.vllm_enabled:
            logger.warning("vllm_disabled", extra={"vllm_enabled": False})
            return
        
        # Reasoning client (GPU 0)
        self.reasoning_client = AsyncOpenAI(
            base_url=settings.vllm_reasoning_url,
            api_key="EMPTY",  # vLLM doesn't require API key
        )
        
        # Embedding client (GPU 1)
        self.embedding_client = AsyncOpenAI(
            base_url=settings.vllm_embedding_url,
            api_key="EMPTY",
        )
        
        logger.info(
            "vllm_clients_initialized",
            extra={
                "reasoning_url": settings.vllm_reasoning_url,
                "embedding_url": settings.vllm_embedding_url,
            },
        )

    async def generate_reasoning(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None,
    ) -> str:
        """
        Generate text using reasoning model.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop: Stop sequences
            
        Returns:
            Generated text
        """
        if not self.settings.vllm_enabled:
            raise RuntimeError("vLLM is not enabled. Set VLLM_ENABLED=true")
        
        try:
            response = await self.reasoning_client.completions.create(
                model=self.settings.vllm_reasoning_model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
            )
            
            text = response.choices[0].text
            logger.info(
                "vllm_reasoning_generated",
                extra={
                    "prompt_length": len(prompt),
                    "response_length": len(text),
                    "model": self.settings.vllm_reasoning_model,
                },
            )
            return text
        except Exception as e:
            logger.exception("vllm_reasoning_failed", extra={"error": str(e)})
            raise

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate chat completion using reasoning model.
        
        Args:
            messages: Chat messages in OpenAI format
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated response
        """
        if not self.settings.vllm_enabled:
            raise RuntimeError("vLLM is not enabled. Set VLLM_ENABLED=true")
        
        try:
            response = await self.reasoning_client.chat.completions.create(
                model=self.settings.vllm_reasoning_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            content = response.choices[0].message.content
            logger.info(
                "vllm_chat_generated",
                extra={
                    "messages_count": len(messages),
                    "response_length": len(content),
                },
            )
            return content
        except Exception as e:
            logger.exception("vllm_chat_failed", extra={"error": str(e)})
            raise

    async def generate_embeddings(
        self, texts: List[str], batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings using local embedding model.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        if not self.settings.vllm_enabled:
            raise RuntimeError("vLLM is not enabled. Set VLLM_ENABLED=true")
        
        embeddings = []
        
        try:
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                
                response = await self.embedding_client.embeddings.create(
                    model=self.settings.vllm_embedding_model,
                    input=batch,
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            
            logger.info(
                "vllm_embeddings_generated",
                extra={
                    "text_count": len(texts),
                    "embedding_dimension": len(embeddings[0]) if embeddings else 0,
                },
            )
            return embeddings
        except Exception as e:
            logger.exception("vllm_embeddings_failed", extra={"error": str(e)})
            raise

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of both vLLM servers.
        
        Returns:
            Dictionary with health status for each server
        """
        if not self.settings.vllm_enabled:
            return {"reasoning": False, "embedding": False, "vllm_enabled": False}
        
        health = {"vllm_enabled": True}
        
        # Check reasoning server
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.settings.vllm_reasoning_url}/health",
                    timeout=5.0,
                )
                health["reasoning"] = response.status_code == 200
        except Exception as e:
            logger.warning("vllm_reasoning_health_failed", extra={"error": str(e)})
            health["reasoning"] = False
        
        # Check embedding server
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.settings.vllm_embedding_url}/health",
                    timeout=5.0,
                )
                health["embedding"] = response.status_code == 200
        except Exception as e:
            logger.warning("vllm_embedding_health_failed", extra={"error": str(e)})
            health["embedding"] = False
        
        return health

    async def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about loaded models.
        
        Returns:
            Dictionary with model information
        """
        if not self.settings.vllm_enabled:
            return {"vllm_enabled": False}
        
        info = {
            "vllm_enabled": True,
            "reasoning": {
                "model": self.settings.vllm_reasoning_model,
                "url": self.settings.vllm_reasoning_url,
            },
            "embedding": {
                "model": self.settings.vllm_embedding_model,
                "url": self.settings.vllm_embedding_url,
            },
        }
        
        return info
