"""Local LLM serving with vLLM for dual GPU orchestration."""

from .vllm_config import VLLMConfig, GPUAllocation
from .vllm_client import VLLMClient

__all__ = ["VLLMConfig", "GPUAllocation", "VLLMClient"]
