# Troubleshooting Guide

## "Summary generation failed" - Connection Error

### Error Details
```
openai.APIConnectionError: Connection error.
Error Type: APIConnectionError
LLM Base URL: http://localhost:8000/v1
LLM Provider: openai
```

### Root Cause
The LLM service configured in `.env` is not running. The application is trying to connect to `http://localhost:8000/v1` but no service is listening on that port.

### Solutions

#### Option 1: Use OpenAI API (Recommended for Testing)

Update `.env`:
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-your-real-openai-key
LLM_BASE_URL=https://api.openai.com/v1
```

Then:
```bash
# Verify API key is valid
echo $LLM_API_KEY

# Test again
uv run python sample/crawl4ai/crawl_and_save.py --url https://example.com
```

#### Option 2: Run vLLM Locally (Docker)

```bash
# Start vLLM service
docker run --gpus all -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3-0.6B \
  --max-model-len 8192

# Or use docker-compose
docker-compose -f docker-compose.vllm.yml up -d vllm-glm

# Verify service is running
curl http://localhost:8000/health

# Test the pipeline
uv run python sample/crawl4ai/crawl_and_save.py --url https://example.com
```

#### Option 3: Use OpenRouter (Cloud-based, No GPU Required)

1. Sign up at https://openrouter.ai
2. Create API key
3. Update `.env`:
```bash
LLM_PROVIDER=openai
LLM_MODEL=anthropic/claude-3-haiku
LLM_API_KEY=sk-or-v1-your-openrouter-key
LLM_BASE_URL=https://openrouter.ai/api/v1
```

4. Test:
```bash
uv run python sample/crawl4ai/crawl_and_save.py --url https://example.com
```

#### Option 4: Use Ollama (All-in-one Local)

```bash
# Install ollama from https://ollama.ai

# Pull model
ollama pull mistral

# Run ollama in separate terminal
ollama serve

# Update .env
LLM_PROVIDER=openai
LLM_MODEL=mistral
LLM_API_KEY=not-needed
LLM_BASE_URL=http://localhost:11434/v1

# Test
uv run python sample/crawl4ai/crawl_and_save.py --url https://example.com
```

## Common Issues & Solutions

### Issue: "Embedding API validation failed"

**Cause:** Embedding service not running or misconfigured

**Solutions:**
```bash
# Option 1: Use OpenAI embeddings
# Update .env with valid EMBEDDING_API_KEY

# Option 2: Start local embedding server
docker-compose -f docker-compose.embedding.yml up -d embedding-server

# Option 3: Use Ollama for embeddings
ollama pull nomic-embed-text
# Then configure .env pointing to localhost:11434
```

### Issue: "MongoDB: Authentication failed"

**Cause:** Incorrect MongoDB credentials in `.env`

**Solution:**
```bash
# Check MongoDB is running
docker ps | grep mongodb

# Verify credentials match docker-compose
# .env should have:
MONGODB_USERNAME=admin
MONGODB_PASSWORD=admin123
MONGODB_HOST=localhost
MONGODB_PORT=7017

# Test connection
python -c "
import asyncio
from mdrag.config.settings import load_settings
from pymongo import AsyncMongoClient

async def test():
    settings = load_settings()
    client = AsyncMongoClient(settings.mongodb_connection_string, serverSelectionTimeoutMS=5000)
    await client.admin.command('ping')
    print('✓ MongoDB connection successful')
    await client.close()

asyncio.run(test())
"
```

### Issue: "Connection refused" to SearXNG

**Cause:** SearXNG service not running

**Solution:**
```bash
# Check if running
docker ps | grep searxng

# Start if not running
docker-compose up -d searxng

# Verify it's accessible
curl http://localhost:7080/search?q=test&format=json
```

### Issue: No logging output for errors

**Solution:** The application now logs detailed error information including:
- Error type (e.g., APIConnectionError, ConnectionError)
- URL and context where error occurred
- Configuration being used (API base URL, model, provider)
- Full traceback for debugging

Check logs by running with:
```bash
# Show debug logs
export PYTHONUNBUFFERED=1
uv run python sample/crawl4ai/crawl_and_save.py --url https://example.com 2>&1 | grep -E "ERROR|error_type|Error"
```

## Testing Each Component

### Test MongoDB Connection
```bash
uv run python scripts/test_embedding.py
```

### Test LLM Service
```bash
# Create a simple test
uv run python << 'EOF'
import asyncio
from mdrag.config.settings import load_settings
from mdrag.integrations.llm.completion_client import LLMCompletionClient

async def test_llm():
    settings = load_settings()
    client = LLMCompletionClient(settings=settings)

    try:
        response = await client.create(
            messages=[{"role": "user", "content": "Hello, respond with 'OK'"}]
        )
        print(f"✓ LLM working: {response.choices[0].message.content}")
    except Exception as e:
        print(f"✗ LLM error: {type(e).__name__}: {e}")
        print(f"  Provider: {settings.llm_provider}")
        print(f"  Base URL: {settings.llm_base_url}")
        print(f"  Model: {settings.llm_model}")

asyncio.run(test_llm())
EOF
```

### Test SearXNG
```bash
uv run python << 'EOF'
import httpx
import asyncio
from mdrag.config.settings import load_settings

async def test_searxng():
    settings = load_settings()
    url = settings.searxng_url

    if not url:
        print("✗ SearXNG URL not configured")
        return

    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.get(
                f"{url}/search",
                params={"q": "test", "format": "json"}
            )
            print(f"✓ SearXNG working: {len(response.json())} results")
        except Exception as e:
            print(f"✗ SearXNG error: {type(e).__name__}: {e}")
            print(f"  URL: {url}")

asyncio.run(test_searxng())
EOF
```

### Test Full Pipeline
```bash
# Simple URL test
uv run python sample/crawl4ai/crawl_and_save.py --url https://example.com

# More complex test
uv run python sample/crawl4ai/crawl_and_save.py --url https://github.com
```

## Detailed Error Messages

All errors now include:
- **Error Type**: The specific exception class (e.g., `APIConnectionError`, `ValidationError`)
- **URL/Context**: What operation was being performed
- **Configuration**: What settings were being used
- **Traceback**: Full Python stack trace for debugging
- **Service Details**: Which service/endpoint was being accessed

This allows you to quickly identify:
1. What went wrong (error type)
2. Where it went wrong (URL, operation)
3. How to fix it (configuration shown)
4. Why it went wrong (traceback)

## Getting Help

If you still can't resolve an issue:

1. **Gather information:**
   ```bash
   # Check service status
   docker ps

   # Check logs
   docker logs rag-agent
   docker logs searxng

   # Check .env configuration
   grep -E "PROVIDER|URL|API_KEY" .env
   ```

2. **Test components individually:**
   - MongoDB: Use test_mongodb() script
   - LLM: Use test_llm() code above
   - Embeddings: Use scripts/test_embedding.py
   - SearXNG: Use test_searxng() code above

3. **Enable debug logging:**
   ```bash
   export DEBUG=true
   uv run python sample/crawl4ai/crawl_and_save.py --url <url>
   ```

