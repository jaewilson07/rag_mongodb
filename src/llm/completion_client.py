"""Backward compatibility: re-export from mdrag.integrations.llm.completion_client."""

from mdrag.integrations.llm.completion_client import (
    LLMCompletionClient,
    get_llm_init_kwargs,
)

__all__ = ["LLMCompletionClient", "get_llm_init_kwargs"]
