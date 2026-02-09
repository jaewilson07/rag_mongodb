"""Backward compatibility: re-export from mdrag.integrations.llm."""

from mdrag.integrations.llm import (
    GPUAllocation,
    VLLMClient,
    VLLMConfig,
)
from mdrag.integrations.llm.completion_client import (
    LLMCompletionClient,
    get_llm_init_kwargs,
)

__all__ = [
    "GPUAllocation",
    "LLMCompletionClient",
    "VLLMClient",
    "VLLMConfig",
    "get_llm_init_kwargs",
]
