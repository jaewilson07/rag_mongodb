"""LLM completion client with provider-defined temperature handling.

Temperature is a provider capability, not a workflow concern. The client
builds completion kwargs based on the injected provider config.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import openai
from openai import AsyncOpenAI

from mdrag.config.settings import Settings

logger = logging.getLogger(__name__)


def _provider_supports_temperature(settings: Settings) -> bool:
    """True if this provider supports custom temperature. OpenRouter rejects it."""
    provider = (settings.llm_provider or "").lower()
    url = (settings.llm_base_url or "") or ""
    if "openrouter" in provider or "openrouter.ai" in url:
        return False
    return True


def _completion_kwargs(settings: Settings, **extra: Any) -> Dict[str, Any]:
    """Build kwargs for chat.completions.create. Provider decides temperature."""
    kwargs: Dict[str, Any] = {"model": settings.llm_model, **extra}
    if _provider_supports_temperature(settings) and settings.llm_temperature is not None:
        kwargs["temperature"] = settings.llm_temperature
    return kwargs


def get_llm_init_kwargs(
    settings: Settings,
    provider_supports_temperature: Optional[bool] = None,
) -> Dict[str, Any]:
    """Return temperature kwargs for LLM init (ChatOpenAI, etc.). Provider decides.

    When provider_supports_temperature is None, use provider detection (OpenRouter -> False).
    When True (e.g. vLLM), always include temperature when set.
    When False, never include.
    """
    supports = (
        provider_supports_temperature
        if provider_supports_temperature is not None
        else _provider_supports_temperature(settings)
    )
    if supports and settings.llm_temperature is not None:
        return {"temperature": settings.llm_temperature}
    return {}


class LLMCompletionClient:
    """
    OpenAI-compatible completion client with provider-aware request building.

    Temperature is included only when the provider supports it (e.g. Ollama, vLLM).
    OpenRouter and similar reject custom temperature; it is omitted.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
            )
        return self._client

    async def create(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        **extra: Any,
    ) -> Any:
        """Create chat completion. Provider handles temperature internally."""
        kwargs = _completion_kwargs(self.settings, messages=messages, stream=stream, **extra)
        return await self.client.chat.completions.create(**kwargs)

    async def close(self) -> None:
        """Close the underlying client."""
        if self._client:
            await self._client.close()
            self._client = None
