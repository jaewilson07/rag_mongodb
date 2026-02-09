"""Shared embedding client for ingestion and query layers."""

from __future__ import annotations

from typing import Iterable, List, Optional
import logging

import openai

from mdrag.settings import Settings, load_settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """OpenAI-compatible embedding client with shared settings and truncation."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        model: Optional[str] = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.model = model or self.settings.embedding_model
        self._client: Optional[openai.AsyncOpenAI] = None

        self._model_configs = {
            "text-embedding-3-small": {"dimensions": 1536, "max_tokens": 8191},
            "text-embedding-3-large": {"dimensions": 3072, "max_tokens": 8191},
            "text-embedding-ada-002": {"dimensions": 1536, "max_tokens": 8191},
        }
        self._config = self._model_configs.get(
            self.model,
            {"dimensions": self.settings.embedding_dimension, "max_tokens": 8191},
        )

    async def initialize(self) -> None:
        if not self._client:
            self._client = openai.AsyncOpenAI(
                api_key=self.settings.embedding_api_key,
                base_url=self.settings.embedding_base_url,
            )
            logger.info(
                "embedding_client_initialized model=%s dimension=%s",
                self.model,
                self._config["dimensions"],
            )

    @property
    def config(self) -> dict:
        return self._config

    def _truncate(self, text: str) -> str:
        # Rough estimation: 4 chars per token
        max_chars = self._config["max_tokens"] * 4
        if len(text) > max_chars:
            return text[:max_chars]
        return text

    async def embed_text(self, text: str) -> List[float]:
        await self.initialize()
        response = await self._client.embeddings.create(
            model=self.model,
            input=self._truncate(text),
        )
        return response.data[0].embedding

    async def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        await self.initialize()
        processed = [self._truncate(text) for text in texts]
        response = await self._client.embeddings.create(
            model=self.model,
            input=processed,
        )
        return [item.embedding for item in response.data]

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("embedding_client_closed")

    def embedding_dimension(self) -> int:
        return int(self._config["dimensions"])