"""Providers compatibility shim - re-exports from mdrag.integrations.llm.providers."""

from mdrag.integrations.llm.providers import (
    get_llm_model,
    get_embedding_model,
    get_model_info,
    validate_llm_configuration,
)

__all__ = [
    "get_llm_model",
    "get_embedding_model",
    "get_model_info",
    "validate_llm_configuration",
]
