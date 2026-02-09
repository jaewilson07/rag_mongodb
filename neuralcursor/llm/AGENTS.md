# LLM Orchestration - Dual GPU Management

## Overview

The LLM module orchestrates local language models across dual NVIDIA 3090 GPUs, ensuring zero-cloud latency for reasoning and embedding tasks. It provides a unified interface for both reasoning (GPU 0) and embedding (GPU 1) operations.

## Architecture

```
llm/
├── __init__.py
└── orchestrator.py     # Dual GPU orchestration and load balancing
```

## Dual GPU Strategy

### GPU 0: Reasoning LLM
- **Model**: DeepSeek-Coder-33B or similar large parameter model
- **Purpose**: Complex reasoning, summarization, conflict detection
- **VRAM**: ~20GB
- **Port**: 8000 (vLLM server)

### GPU 1: Embedding Model
- **Model**: BGE-M3 or similar embedding model
- **Purpose**: Text embeddings, semantic search, RAG
- **VRAM**: ~4GB
- **Port**: 8001 (vLLM server)

## Configuration

```bash
# Reasoning LLM (GPU 0)
NEURALCURSOR_REASONING_LLM_HOST=http://localhost:8000
NEURALCURSOR_REASONING_LLM_MODEL=deepseek-coder-33b

# Embedding Model (GPU 1)
NEURALCURSOR_EMBEDDING_LLM_HOST=http://localhost:8001
NEURALCURSOR_EMBEDDING_LLM_MODEL=bge-m3
NEURALCURSOR_EMBEDDING_DIMENSIONS=1024

# GPU Configuration
NEURALCURSOR_GPU_REASONING_DEVICE=cuda:0
NEURALCURSOR_GPU_EMBEDDING_DEVICE=cuda:1
NEURALCURSOR_VRAM_LIMIT_REASONING_GB=20
NEURALCURSOR_VRAM_LIMIT_EMBEDDING_GB=4
```

## Usage

### Initialize Orchestrator

```python
from neuralcursor.llm.orchestrator import get_orchestrator

orchestrator = get_orchestrator()  # Singleton instance

# Check health
health = await orchestrator.health_check()
print(f"Status: {health['status']}")
print(f"Reasoning LLM: {health['reasoning_llm_healthy']}")
print(f"Embedding LLM: {health['embedding_llm_healthy']}")
```

### Generate Reasoning

```python
from neuralcursor.llm.orchestrator import LLMRequest

request = LLMRequest(
    prompt="Analyze this architectural decision and explain the rationale...",
    max_tokens=2048,
    temperature=0.7
)

response = await orchestrator.generate_reasoning(request)

print(f"Response: {response.text}")
print(f"Tokens: {response.tokens_used}")
print(f"Latency: {response.latency_ms}ms")
```

### Generate Embeddings

```python
from neuralcursor.llm.orchestrator import EmbeddingRequest

# Single text
request = EmbeddingRequest(
    text="JWT authentication implementation guide"
)

response = await orchestrator.generate_embeddings(request)
embedding = response.embeddings[0]  # [0.1, 0.2, 0.3, ...]

print(f"Dimensions: {response.dimensions}")
print(f"Latency: {response.latency_ms}ms")

# Batch (recommended for multiple texts)
request = EmbeddingRequest(
    text=[
        "JWT authentication",
        "OAuth2 implementation",
        "API security best practices"
    ]
)

response = await orchestrator.generate_embeddings(request)
embeddings = response.embeddings  # List of 3 embeddings
```

## Starting LLM Servers

### Reasoning LLM (GPU 0)

```bash
# Using vLLM
python -m vllm.entrypoints.openai.api_server \
  --model deepseek-ai/deepseek-coder-33b-instruct \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9 \
  --device cuda:0 \
  --port 8000 \
  --max-model-len 8192
```

### Embedding Model (GPU 1)

```bash
# Using vLLM or sentence-transformers
python -m vllm.entrypoints.openai.api_server \
  --model BAAI/bge-m3 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.5 \
  --device cuda:1 \
  --port 8001
```

## Design Patterns

### Pattern 1: Reasoning with Retry

```python
async def generate_with_retry(
    orchestrator,
    prompt: str,
    max_retries: int = 3
) -> str:
    """Generate with automatic retry on failure."""
    for attempt in range(max_retries):
        try:
            request = LLMRequest(prompt=prompt)
            response = await orchestrator.generate_reasoning(request)
            return response.text
            
        except Exception as e:
            logger.warning(f"Reasoning attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Pattern 2: Batch Embedding Generation

```python
async def generate_embeddings_batch(
    orchestrator,
    texts: list[str],
    batch_size: int = 32
) -> list[list[float]]:
    """Generate embeddings in batches for efficiency."""
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        request = EmbeddingRequest(text=batch)
        response = await orchestrator.generate_embeddings(request)
        
        all_embeddings.extend(response.embeddings)
    
    return all_embeddings
```

### Pattern 3: Streaming Responses

```python
async def generate_streaming(
    orchestrator,
    prompt: str
) -> AsyncGenerator[str, None]:
    """Generate reasoning with streaming output."""
    request = LLMRequest(
        prompt=prompt,
        stream=True
    )
    
    # Note: Requires vLLM streaming support
    async for chunk in orchestrator.generate_reasoning_stream(request):
        yield chunk
```

### Pattern 4: Temperature Tuning

```python
# For factual extraction (low temperature)
request = LLMRequest(
    prompt="Extract the key decision from this text...",
    temperature=0.2,  # More deterministic
    max_tokens=500
)

# For creative generation (high temperature)
request = LLMRequest(
    prompt="Generate alternative approaches...",
    temperature=0.9,  # More creative
    max_tokens=1000
)
```

## Response Models

### LLMResponse

```python
from neuralcursor.llm.orchestrator import LLMResponse

response = LLMResponse(
    text="The architectural decision was made because...",
    tokens_used=450,
    latency_ms=1250.5
)
```

### EmbeddingResponse

```python
from neuralcursor.llm.orchestrator import EmbeddingResponse

response = EmbeddingResponse(
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    dimensions=1024,
    latency_ms=45.2
)
```

## Performance Optimization

### GPU Memory Management

```bash
# Adjust memory utilization based on VRAM
--gpu-memory-utilization 0.9  # Use 90% of available VRAM

# For multiple models on same GPU
--gpu-memory-utilization 0.4  # Leave room for other models
```

### Model Quantization

```bash
# 4-bit quantization (reduces VRAM, slight quality loss)
--quantization awq

# 8-bit quantization (balanced)
--quantization gptq
```

### Batch Size Tuning

```python
# Embeddings: Larger batches = better throughput
request = EmbeddingRequest(text=batch_of_32_texts)

# Reasoning: Single requests for lower latency
request = LLMRequest(prompt=single_prompt)
```

## Health Monitoring

### Check LLM Availability

```python
health = await orchestrator.health_check()

if health['status'] != 'healthy':
    logger.error("LLM services degraded", extra=health['details'])
    
    # Alert or fallback logic
    if not health['reasoning_llm_healthy']:
        # Use cloud API as fallback?
        pass
```

### VRAM Monitoring

Integrated with monitoring module:

```python
from neuralcursor.monitoring.gpu_monitor import get_monitor

monitor = get_monitor()
status = monitor.get_system_status()

for gpu in status.gpus:
    if gpu.device_id == 0:  # Reasoning GPU
        print(f"GPU 0 VRAM: {gpu.used_memory_gb:.1f}GB / {gpu.total_memory_gb:.1f}GB")
    elif gpu.device_id == 1:  # Embedding GPU
        print(f"GPU 1 VRAM: {gpu.used_memory_gb:.1f}GB / {gpu.total_memory_gb:.1f}GB")
```

See [../monitoring/AGENTS.md](../monitoring/AGENTS.md) for monitoring details.

## Error Handling

```python
import logging
from httpx import HTTPError, TimeoutException

logger = logging.getLogger(__name__)

try:
    response = await orchestrator.generate_reasoning(request)
    
except TimeoutException as e:
    logger.exception("llm_timeout", extra={"error": str(e)})
    # Request took too long (> 300s)
    
except HTTPError as e:
    logger.exception("llm_http_error", extra={
        "status_code": e.response.status_code,
        "error": str(e)
    })
    # vLLM server error
    
except Exception as e:
    logger.exception("llm_unexpected_error", extra={"error": str(e)})
    raise
```

## Testing

### Unit Tests

```python
import pytest
from neuralcursor.llm.orchestrator import DualGPUOrchestrator, LLMRequest

@pytest.mark.asyncio
async def test_reasoning_generation():
    """Test reasoning LLM generation."""
    orchestrator = DualGPUOrchestrator()
    
    request = LLMRequest(
        prompt="What is 2+2?",
        max_tokens=100,
        temperature=0.1
    )
    
    response = await orchestrator.generate_reasoning(request)
    
    assert response.text
    assert response.tokens_used > 0
    assert response.latency_ms > 0
    assert "4" in response.text

@pytest.mark.asyncio
async def test_embedding_generation():
    """Test embedding generation."""
    orchestrator = DualGPUOrchestrator()
    
    request = EmbeddingRequest(text="test text")
    response = await orchestrator.generate_embeddings(request)
    
    assert len(response.embeddings) == 1
    assert response.dimensions > 0
    assert len(response.embeddings[0]) == response.dimensions
```

### Integration Tests

```python
@pytest.mark.integration
async def test_dual_gpu_concurrent():
    """Test concurrent usage of both GPUs."""
    orchestrator = DualGPUOrchestrator()
    
    # Run reasoning and embedding concurrently
    reasoning_task = orchestrator.generate_reasoning(
        LLMRequest(prompt="Explain this...")
    )
    
    embedding_task = orchestrator.generate_embeddings(
        EmbeddingRequest(text="Some text")
    )
    
    reasoning_result, embedding_result = await asyncio.gather(
        reasoning_task,
        embedding_task
    )
    
    assert reasoning_result.text
    assert len(embedding_result.embeddings) == 1
```

## Troubleshooting

### vLLM Server Won't Start

```bash
# Check GPU availability
nvidia-smi

# Check port conflicts
lsof -i :8000
lsof -i :8001

# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# View vLLM logs
python -m vllm.entrypoints.openai.api_server ... 2>&1 | tee vllm.log
```

### Out of Memory (OOM) Errors

```bash
# Reduce memory utilization
--gpu-memory-utilization 0.7  # Down from 0.9

# Use quantization
--quantization awq

# Reduce max sequence length
--max-model-len 4096  # Down from 8192
```

### Slow Inference

```python
# Check latency
response = await orchestrator.generate_reasoning(request)
if response.latency_ms > 5000:  # > 5 seconds
    logger.warning("slow_inference", extra={
        "latency_ms": response.latency_ms,
        "tokens": response.tokens_used
    })

# Monitor VRAM usage
status = monitor.get_system_status()
for gpu in status.gpus:
    if gpu.memory_utilization_percent > 95:
        logger.warning("gpu_near_capacity", extra={
            "device_id": gpu.device_id,
            "utilization": gpu.memory_utilization_percent
        })
```

## Alternative Configurations

### Single GPU Setup

```python
# Both models on GPU 0
NEURALCURSOR_GPU_REASONING_DEVICE=cuda:0
NEURALCURSOR_GPU_EMBEDDING_DEVICE=cuda:0

# Adjust VRAM limits
NEURALCURSOR_VRAM_LIMIT_REASONING_GB=16
NEURALCURSOR_VRAM_LIMIT_EMBEDDING_GB=4
```

### Cloud API Fallback

```python
class HybridOrchestrator(DualGPUOrchestrator):
    """Orchestrator with cloud fallback."""
    
    async def generate_reasoning(self, request):
        try:
            # Try local first
            return await super().generate_reasoning(request)
        except Exception as e:
            logger.warning("local_llm_failed, falling_back_to_cloud")
            # Fallback to OpenAI/Anthropic
            return await self._cloud_generate(request)
```

## Related Documentation

- [orchestrator.py](./orchestrator.py) - Full orchestrator implementation
- [../monitoring/AGENTS.md](../monitoring/AGENTS.md) - GPU monitoring
- [../agents/AGENTS.md](../agents/AGENTS.md) - Agents using LLM
- [../AGENTS.md](../AGENTS.md) - Root documentation
