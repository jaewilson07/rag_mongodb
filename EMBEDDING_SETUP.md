# Embedding Configuration Guide

The MongoDB RAG Agent supports multiple embedding backends. Choose the option that best fits your setup.

## Quick Start Options

### Option 1: OpenAI API (Recommended for Production)

Fastest to set up, production-ready.

```bash
# .env configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=sk-your-actual-key-here
EMBEDDING_DIMENSION=1536
EMBEDDING_BASE_URL=https://api.openai.com/v1
```

**Pros:**
- Production-ready, highly reliable
- Excellent embedding quality
- Fast inference

**Cons:**
- Requires paid API key
- Internet access required
- Per-token cost

---

### Option 2: Local vLLM + Embedding Server (Recommended for Local Dev)

Run embeddings locally without external API keys.

#### Step 1: Add Embedding Service to Docker Compose

Create `docker-compose.embedding.yml`:

```yaml
services:
  embedding-server:
    image: qdrant/fastembed-server:latest
    ports:
      - "8001:8000"
    environment:
      - LOG_LEVEL=INFO
    networks:
      - rag_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

networks:
  rag_network:
    external: true
    name: ragagent_rag_network
```

#### Step 2: Configure .env

```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_API_KEY=not-needed
EMBEDDING_DIMENSION=384
EMBEDDING_BASE_URL=http://embedding-server:8000/v1
```

#### Step 3: Run with Both Services

```bash
# Start main services
docker-compose up -d

# In a separate terminal, add embedding service
docker-compose -f docker-compose.embedding.yml up -d embedding-server

# Verify both are running
docker ps | grep -E "(rag-agent|embedding)"
```

**Pros:**
- No API key required
- Local processing, no data leaves your machine
- Good performance for development
- Free to run locally

**Cons:**
- Requires docker
- Initial image download (~2GB)
- Embedding quality not as good as OpenAI (but good enough for dev)

---

### Option 3: Ollama Local Embeddings (Alternative)

Use Ollama for both LLM and embedding serving.

```bash
# Install Ollama: https://ollama.ai

# Pull embedding model
ollama pull nomic-embed-text

# Run embedding server
ollama serve
```

**.env configuration:**

```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_API_KEY=not-needed
EMBEDDING_DIMENSION=768
EMBEDDING_BASE_URL=http://localhost:11434/v1
```

**Pros:**
- Single unified interface for LLM + embeddings
- Easy to install and manage
- Good embedding quality

**Cons:**
- Requires separate Ollama installation
- Embedding server runs on different port than vLLM

---

### Option 4: HuggingFace Inference API (Free Tier)

Free API with HuggingFace account, no credit card.

```bash
# Sign up at https://huggingface.co
# Create an API token in https://huggingface.co/settings/tokens

# .env configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_API_KEY=hf_your-token-here
EMBEDDING_DIMENSION=384
EMBEDDING_BASE_URL=https://api-inference.huggingface.co/models/BAAI/bge-small-en-v1.5/v1
```

**Note:** HuggingFace Inference API may have rate limits on free tier.

---

## Embedding Models Comparison

| Model | Dimensions | Quality | Speed | Size |
|-------|-----------|---------|-------|------|
| text-embedding-3-small | 1536 | Excellent | Fast | N/A (API) |
| text-embedding-3-large | 3072 | Excellent | Fast | N/A (API) |
| BAAI/bge-small-en-v1.5 | 384 | Good | Fast | 33MB |
| BAAI/bge-base-en-v1.5 | 768 | Very Good | Medium | 139MB |
| nomic-embed-text | 768 | Good | Fast | 274MB |
| mxbai-embed-large | 1024 | Very Good | Slow | 669MB |

---

## Testing Your Setup

```bash
# Test embedding with a simple script
uv run python << 'EOF'
import asyncio
from mdrag.capabilities.retrieval.embeddings import EmbeddingClient
from mdrag.config.settings import load_settings

async def test_embedding():
    settings = load_settings()
    client = EmbeddingClient(settings=settings)

    try:
        # Test embedding generation
        embedding = await client.embed_text("This is a test sentence")
        print(f"✓ Embedding successful!")
        print(f"  Model: {client.model}")
        print(f"  Dimensions: {len(embedding)}")
        print(f"  Sample values: {embedding[:5]}")

        # Test batch embedding
        embeddings = await client.embed_texts([
            "First document",
            "Second document",
            "Third document"
        ])
        print(f"✓ Batch embedding successful!")
        print(f"  Generated {len(embeddings)} embeddings")

        await client.close()
    except Exception as e:
        print(f"✗ Embedding failed: {e}")

asyncio.run(test_embedding())
EOF
```

---

## Running the Ingestion Pipeline

Once embeddings are configured:

```bash
# Test with a single URL
uv run python sample/crawl4ai/crawl4ai_ingest.py --url https://example.com

# This will:
# 1. Fetch and crawl the URL
# 2. Extract content
# 3. Split into chunks
# 4. Generate embeddings for each chunk
# 5. Store in MongoDB with vector search enabled
```

---

## Troubleshooting

### "Embedding API validation failed"

**Problem:** Connection error when trying to validate embedding API

**Solutions:**
1. Check API key is correct: `echo $EMBEDDING_API_KEY`
2. Check base URL is accessible: `curl $EMBEDDING_BASE_URL/health`
3. Verify internet connection (if using cloud API)
4. Check firewall/proxy settings

### "Connection refused" with local service

**Problem:** Can't connect to local embedding server

**Solutions:**
1. Verify service is running: `docker ps | grep embedding`
2. Check port mapping: `docker port embedding-server`
3. Try direct curl: `curl http://localhost:8001/health`
4. Check network: `docker network ls | grep rag_network`

### "Model not found"

**Problem:** Embedding model doesn't exist

**Solutions:**
1. Verify model name is correct for your provider
2. Check model is available: `ollama list` (for Ollama) or provider's model catalog
3. Download/pull model if needed
4. Use a model from the comparison table above

---

## Production Recommendations

For production deployments:

1. **Use OpenAI or Cohere API** - Most reliable, best quality
2. **Keep API key in secrets management** - Don't commit to git
3. **Monitor embedding API costs** - Set up billing alerts
4. **Cache embeddings** - Avoid re-embedding same content
5. **Use batch APIs** - More cost-effective than single requests

## Development Recommendations

For local development:

1. **Use Qdrant FastEmbed server** - Easiest local setup
2. **Or use Ollama** - Great all-in-one solution
3. **Test with small batches** - Faster iteration
4. **Monitor memory usage** - Embedding models consume RAM

