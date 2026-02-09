# Sample Scripts

This directory contains **37 sample scripts** demonstrating various capabilities of the MongoDB RAG Agent. Each sample is a self-contained script showing how to use specific features, integrations, or patterns.

## Quick Start

```bash
# Setup environment
uv venv
uv sync

# Configure .env (see Configuration section below)
cp .env.example .env
# Edit .env with your credentials

# Run a sample
uv run python sample/mongodb/check_indexes.py
```

## Directory Structure

```
sample/
├── utils/              # Pre-flight check utilities
├── wiki/               # Wiki generation and chat
├── readings/           # Save & research URLs
├── youtube/            # YouTube extraction
├── crawl4ai/           # Web crawling
├── rag/                # RAG query and testing
├── retrieval/          # Search pipeline testing
├── searxng/            # SearXNG integration
├── docling/            # Document processing
├── google_drive/       # Google Drive integration
├── mongodb/            # MongoDB utilities
├── ingestion/          # Ingestion validation
└── eval/               # Evaluation scripts
```

## External Service Dependencies

### Required for All Samples (except standalone utilities)

| Service | Default URL | Setup Required | Used By |
|---------|-------------|----------------|---------|
| **MongoDB Atlas** | `MONGODB_URI` from .env | Vector + text indexes | All (except YouTube, darwinxml_demo) |
| **LLM API** | `LLM_BASE_URL` from .env | API key in .env | Wiki, Readings, RAG, Query |
| **Embedding API** | `EMBEDDING_BASE_URL` from .env | API key in .env | RAG, Query, Search |

### Optional Services (required by specific samples)

| Service | Default URL | Setup Required | Used By |
|---------|-------------|----------------|---------|
| **SearXNG** | `http://localhost:7080` | Docker or standalone | Readings, Crawl4AI |
| **Redis** | `redis://localhost:6379/0` | Docker or standalone | Readings ingestion jobs |
| **Playwright** | N/A | `playwright install` | Crawl4AI scripts |
| **Google Drive API** | N/A | Service account or OAuth | Google Drive scripts |

## Configuration

### Required Environment Variables

Create a `.env` file in the project root with these variables:

```bash
# MongoDB (Required)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=rag_db
MONGODB_COLLECTION_DOCUMENTS=documents
MONGODB_COLLECTION_CHUNKS=chunks
MONGODB_VECTOR_INDEX=vector_index
MONGODB_TEXT_INDEX=text_index

# LLM (Required for agent/wiki/readings)
LLM_PROVIDER=openrouter
LLM_API_KEY=sk-or-v1-...
LLM_MODEL=anthropic/claude-haiku-4.5
LLM_BASE_URL=https://openrouter.ai/api/v1

# Embeddings (Required for search/RAG)
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_DIMENSION=1536

# SearXNG (Optional - for readings/crawl4ai)
SEARXNG_URL=http://localhost:7080

# Redis (Optional - for readings job queue)
REDIS_URL=redis://localhost:6379/0

# Google Drive (Optional - for google_drive samples)
# Option 1: Service Account
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
GOOGLE_IMPERSONATE_SUBJECT=user@example.com  # Optional

# Option 2: OAuth Tokens
GDOC_CLIENT=<client_json>
GDOC_TOKEN=<token_json>
GOOGLE_CLIENT_ID=<client_id>
GOOGLE_CLIENT_SECRET=<client_secret>
```

### MongoDB Atlas Setup

**CRITICAL**: Vector and text search indexes must be created in Atlas UI (cannot be created programmatically).

1. Navigate to your cluster in Atlas UI
2. Click "Search" → "Create Search Index"
3. Create vector index:
   - **Index Name**: `vector_index` (must match `MONGODB_VECTOR_INDEX` in .env)
   - **Collection**: `chunks`
   - **Field**: `embedding`
   - **Type**: `vector`
   - **Dimensions**: `1536` (or match your embedding model)
   - **Similarity**: `cosine`

4. Create text search index:
   - **Index Name**: `text_index` (must match `MONGODB_TEXT_INDEX` in .env)
   - **Collection**: `chunks`
   - **Analyzer**: `lucene.standard`
   - **Dynamic mapping**: enabled

5. Verify indexes:
   ```bash
   uv run python sample/mongodb/check_indexes.py
   ```

## Service Setup

### Docker Services (SearXNG, Redis)

Start services using docker-compose:

```bash
docker-compose up -d

# Verify services
docker ps
curl http://localhost:7080/search?q=test&format=json
redis-cli ping
```

### Playwright (for Crawl4AI)

Install Playwright browsers:

```bash
playwright install
playwright install-deps  # Linux only: install system dependencies
```

### Google Drive API

**Option 1: Service Account (Recommended for automation)**

1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Set `GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/key.json` in .env
4. Share target folders/files with the service account email

**Option 2: OAuth (Recommended for personal use)**

1. Create OAuth 2.0 credentials in Google Cloud Console
2. Run the OAuth flow to get tokens
3. Set `GDOC_CLIENT` and `GDOC_TOKEN` in .env

See [sample/google_drive/single_file/README.md](google_drive/single_file/README.md) for detailed instructions.

## Sample Categories

### 1. MongoDB Utilities (No external services required)

Test MongoDB connection and configuration:

```bash
uv run python sample/mongodb/check_version.py
uv run python sample/mongodb/check_cluster_info.py
uv run python sample/mongodb/check_indexes.py
```

**Dependencies**: MongoDB only

### 2. Retrieval & Search (MongoDB + indexes + embeddings)

Test search functions without LLM:

```bash
uv run python sample/rag/count_chunks.py
uv run python sample/retrieval/test_search.py
uv run python sample/retrieval/test_rag_pipeline.py
```

**Dependencies**: MongoDB with vector/text indexes, embedding API key

### 3. RAG Query & Agent (MongoDB + indexes + LLM + embeddings)

Test full RAG pipeline with LLM:

```bash
uv run python sample/rag/query_rag.py
uv run python sample/rag/test_agent_e2e.py
uv run python sample/rag/comprehensive_e2e_test.py
uv run python sample/rag/additional_tests.py
```

**Dependencies**: MongoDB with indexes, LLM API key, embedding API key

### 4. Wiki Generation (MongoDB + LLM)

Generate and interact with knowledge wikis:

```bash
uv run python sample/wiki/list_projects.py
uv run python sample/wiki/generate_wiki.py
uv run python sample/wiki/generate_page.py --title "Architecture"
uv run python sample/wiki/chat_wiki.py --question "How does auth work?"
```

**Dependencies**: MongoDB, LLM API key

### 5. Readings (All services)

Save and research URLs:

```bash
uv run python sample/readings/save_url.py --url "https://example.com"
uv run python sample/readings/list_readings.py
```

**Dependencies**: MongoDB, Redis, SearXNG, Crawl4AI, LLM API key

### 6. YouTube (Standalone - no services required)

Extract YouTube metadata and transcripts:

```bash
uv run python sample/youtube/extract_video.py --url "https://youtu.be/PAh870We7tI"
```

**Dependencies**: None (uses yt-dlp and youtube-transcript-api)

### 7. Web Crawling (Crawl4AI + Playwright)

Crawl and ingest web pages:

```bash
# First install Playwright
playwright install

# Then run samples
uv run python sample/crawl4ai/crawl4ai_ingest.py --url "https://example.com"
uv run python sample/crawl4ai/crawl_and_save.py --url "https://docs.python.org"
uv run python sample/crawl4ai/export_domo_release_notes.py
```

**Dependencies**: Playwright, Crawl4AI, MongoDB (for ingest scripts)

### 8. SearXNG (SearXNG only)

Query search engine and export results:

```bash
uv run python sample/searxng/query_searxng.py --query "AI developments"
```

**Dependencies**: SearXNG running at `SEARXNG_URL`

### 9. Document Ingestion (MongoDB + Docling)

Ingest and chunk documents:

```bash
uv run python sample/docling/docling_ingest.py
uv run python sample/docling/chunk_pydantic_sample.py
uv run python sample/ingestion/validate_source_urls.py
```

**Dependencies**: MongoDB, Docling (transformers for embeddings)

### 10. Google Drive (Google Drive API + MongoDB)

Ingest Google Drive documents:

```bash
uv run python sample/google_drive/google_drive_ingest.py
```

**Dependencies**: Google Drive API credentials, MongoDB

### 11. Evaluation (MongoDB + LLM)

Run gold dataset evaluation:

```bash
uv run python sample/eval/run_gold_eval.py
```

**Dependencies**: MongoDB with test data, LLM API key

## Pre-flight Checks

Many samples include automatic pre-flight checks to verify external services are available. If a check fails, you'll see a helpful error message with setup instructions.

Example:

```
❌ MongoDB check failed
   Message: MongoDB connection failed: connection timeout
   
   Setup instructions:
   1. Verify MONGODB_URI in .env
   2. Check network connectivity
   3. Ensure IP is allowlisted in Atlas
```

To add pre-flight checks to a new sample:

```python
from sample.utils import check_mongodb, check_api_keys, print_pre_flight_results
from mdrag.settings import load_settings

async def main():
    settings = load_settings()
    
    # Run checks
    checks = {
        "MongoDB": await check_mongodb(settings),
        "API Keys": check_api_keys(settings, require_llm=True, require_embedding=True),
    }
    
    # Print results and exit if failed
    if not print_pre_flight_results(checks):
        return 1
    
    # Continue with sample logic...
```

## Troubleshooting

### MongoDB Connection Errors

**Error**: `ServerSelectionTimeoutError: connection timeout`

**Solutions**:
1. Verify `MONGODB_URI` in .env is correct
2. Check your IP is allowlisted in Atlas Network Access
3. Ensure Atlas cluster is running (not paused)

### Missing Indexes

**Error**: `PlanExecutor error during aggregation :: caused by :: 291 index not found`

**Solutions**:
1. Create indexes in Atlas UI (see MongoDB Atlas Setup above)
2. Verify index names match .env settings:
   ```bash
   uv run python sample/mongodb/check_indexes.py
   ```

### Playwright Errors

**Error**: `Browser executable not found`

**Solutions**:
```bash
playwright install
playwright install-deps  # Linux: install system dependencies
```

### SearXNG Not Available

**Error**: `SearXNG connection failed: connection refused`

**Solutions**:
```bash
# Start SearXNG container
docker-compose up -d searxng

# Verify
curl http://localhost:7080/search?q=test&format=json
```

### Redis Connection Failed

**Error**: `Redis connection failed: connection refused`

**Solutions**:
```bash
# Start Redis container
docker-compose up -d redis

# Verify
redis-cli ping
```

### Google Drive Authentication

**Error**: `Google Drive credentials not configured`

**Solutions**:
1. Service Account: Set `GOOGLE_SERVICE_ACCOUNT_FILE` path in .env
2. OAuth: Set `GDOC_CLIENT` and `GDOC_TOKEN` in .env
3. See [sample/google_drive/single_file/README.md](google_drive/single_file/README.md) for setup

### API Key Errors

**Error**: `Missing API keys: LLM_API_KEY, EMBEDDING_API_KEY`

**Solutions**:
1. Set `LLM_API_KEY` in .env (required for agent/wiki samples)
2. Set `EMBEDDING_API_KEY` in .env (required for search/RAG samples)
3. Verify keys are valid and have sufficient credits

## Adding New Samples

When adding a new sample script:

1. **Create the script** in the appropriate category folder
2. **Add docstring** with `Usage:` section showing run command
3. **Add pre-flight checks** if external services are required
4. **Update [changelog.md](changelog.md)** with script description and run command
5. **Test the script** with real services to ensure it works
6. **Document dependencies** in this README if introducing new patterns

Example sample template:

```python
"""Brief description of what this sample does.

Usage:
    uv run python sample/category/script_name.py [--options]

Requirements:
    - MongoDB with vector/text indexes
    - LLM API key
"""

import asyncio
import argparse
from sample.utils import check_mongodb, check_api_keys, print_pre_flight_results
from mdrag.settings import load_settings


async def main() -> None:
    """Main sample logic."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--option", help="Option description")
    args = parser.parse_args()
    
    # Pre-flight checks
    settings = load_settings()
    checks = {
        "MongoDB": await check_mongodb(settings),
        "API Keys": check_api_keys(settings, require_llm=True),
    }
    
    if not print_pre_flight_results(checks):
        return
    
    # Sample logic here...
    print("Sample completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
```

## Additional Resources

- **[AGENTS.md](../AGENTS.md)**: Agent behavioral protocols and development guidelines
- **[CLAUDE.md](../CLAUDE.md)**: Development instructions and common pitfalls
- **[docs/design-patterns/](../docs/design-patterns/)**: Architecture patterns and best practices
- **[sample/AGENTS.md](AGENTS.md)**: Sample-specific patterns and conventions

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review error messages for specific setup instructions
3. Verify all dependencies are installed: `uv sync`
4. Check service health: `docker ps` and `curl` endpoints
5. Review relevant documentation in `docs/` folder
