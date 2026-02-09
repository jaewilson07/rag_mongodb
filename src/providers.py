"""Backward compatibility: re-export from mdrag.integrations.llm.providers."""

from mdrag.integrations.llm.providers import (
    get_embedding_model,
    get_llm_model,
    get_model_info,
    validate_llm_configuration,
)

__all__ = [
    "get_embedding_model",
    "get_llm_model",
    "get_model_info",
    "validate_llm_configuration",
]
