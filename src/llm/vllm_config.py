"""vLLM configuration for dual 3090 GPU orchestration."""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class GPUAllocation(str, Enum):
    """GPU allocation strategy."""

    REASONING = "reasoning"  # GPU 0: Heavy reasoning models
    EMBEDDING = "embedding"  # GPU 1: Embeddings and RAG


class VLLMConfig(BaseModel):
    """
    Configuration for vLLM model serving.
    
    Dual 3090 Strategy:
    - GPU 0: DeepSeek-Coder-33B for graph extraction and reasoning
    - GPU 1: BGE-M3 for embeddings and fast RAG retrieval
    """

    # Reasoning LLM (GPU 0)
    reasoning_model: str = Field(
        default="deepseek-ai/deepseek-coder-33b-instruct",
        description="High-parameter reasoning model for graph extraction",
    )
    reasoning_gpu_id: int = Field(default=0, description="GPU ID for reasoning model")
    reasoning_tensor_parallel: int = Field(
        default=1, description="Tensor parallelism for reasoning model"
    )
    reasoning_max_model_len: int = Field(
        default=8192, description="Max sequence length for reasoning model"
    )
    reasoning_dtype: str = Field(
        default="auto", description="Data type: auto, float16, bfloat16, int8, int4"
    )
    reasoning_quantization: Optional[str] = Field(
        None, description="Quantization method: awq, gptq, squeezellm, None"
    )
    reasoning_max_num_seqs: int = Field(
        default=256, description="Max number of sequences in batch"
    )
    
    # Embedding Model (GPU 1)
    embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="Embedding model for vector search",
    )
    embedding_gpu_id: int = Field(default=1, description="GPU ID for embedding model")
    embedding_tensor_parallel: int = Field(
        default=1, description="Tensor parallelism for embedding model"
    )
    embedding_max_model_len: int = Field(
        default=8192, description="Max sequence length for embedding model"
    )
    embedding_dtype: str = Field(
        default="float16", description="Data type for embedding model"
    )
    embedding_max_num_seqs: int = Field(
        default=512, description="Max batch size for embeddings"
    )
    
    # Server Configuration
    reasoning_host: str = Field(default="0.0.0.0", description="Reasoning server host")
    reasoning_port: int = Field(default=8000, description="Reasoning server port")
    embedding_host: str = Field(default="0.0.0.0", description="Embedding server host")
    embedding_port: int = Field(default=8001, description="Embedding server port")
    
    # Performance Tuning
    enable_prefix_caching: bool = Field(
        default=True, description="Enable KV cache prefix caching"
    )
    enable_chunked_prefill: bool = Field(
        default=True, description="Enable chunked prefill for long contexts"
    )
    swap_space: int = Field(default=4, description="CPU swap space in GB")
    gpu_memory_utilization: float = Field(
        default=0.90, description="GPU memory utilization (0.0-1.0)"
    )
    
    def get_reasoning_launch_command(self) -> List[str]:
        """
        Get vLLM launch command for reasoning model on GPU 0.
        
        Returns:
            List of command arguments
        """
        cmd = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.reasoning_model,
            "--host", self.reasoning_host,
            "--port", str(self.reasoning_port),
            "--tensor-parallel-size", str(self.reasoning_tensor_parallel),
            "--max-model-len", str(self.reasoning_max_model_len),
            "--dtype", self.reasoning_dtype,
            "--max-num-seqs", str(self.reasoning_max_num_seqs),
            "--gpu-memory-utilization", str(self.gpu_memory_utilization),
            "--swap-space", str(self.swap_space),
        ]
        
        if self.enable_prefix_caching:
            cmd.append("--enable-prefix-caching")
        
        if self.enable_chunked_prefill:
            cmd.append("--enable-chunked-prefill")
        
        if self.reasoning_quantization:
            cmd.extend(["--quantization", self.reasoning_quantization])
        
        # Force specific GPU
        return [f"CUDA_VISIBLE_DEVICES={self.reasoning_gpu_id}"] + cmd
    
    def get_embedding_launch_command(self) -> List[str]:
        """
        Get vLLM launch command for embedding model on GPU 1.
        
        Returns:
            List of command arguments
        """
        cmd = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.embedding_model,
            "--host", self.embedding_host,
            "--port", str(self.embedding_port),
            "--tensor-parallel-size", str(self.embedding_tensor_parallel),
            "--max-model-len", str(self.embedding_max_model_len),
            "--dtype", self.embedding_dtype,
            "--max-num-seqs", str(self.embedding_max_num_seqs),
            "--gpu-memory-utilization", str(self.gpu_memory_utilization),
        ]
        
        if self.enable_prefix_caching:
            cmd.append("--enable-prefix-caching")
        
        # Force specific GPU
        return [f"CUDA_VISIBLE_DEVICES={self.embedding_gpu_id}"] + cmd


class VRAMMonitorConfig(BaseModel):
    """Configuration for VRAM monitoring dashboard."""

    update_interval_seconds: int = Field(
        default=5, description="Dashboard update interval"
    )
    alert_threshold_percent: float = Field(
        default=0.95, description="VRAM usage alert threshold"
    )
    log_metrics: bool = Field(default=True, description="Log metrics to file")
    metrics_file: str = Field(
        default="data/vram_metrics.jsonl", description="Metrics log file"
    )
