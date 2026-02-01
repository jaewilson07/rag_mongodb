# MongoDB RAG Agent - Intelligent Knowledge Base Search

Agentic RAG system combining MongoDB Atlas Vector Search with Pydantic AI for intelligent document retrieval.

## Features

- **Hybrid Search**: Combines semantic vector search with full-text keyword search using Reciprocal Rank Fusion (RRF)
  - Manual RRF implementation provides same quality as MongoDB's `$rankFusion` (which is in preview)
  - Concurrent execution for minimal latency overhead
- **Multi-Format Ingestion**: PDF, Word, PowerPoint, Excel, HTML, Markdown, Audio transcription
- **Intelligent Chunking**: Docling HybridChunker preserves document structure and semantic boundaries
- **Conversational CLI**: Rich-based interface with real-time streaming and tool call visibility
- **Multiple LLM Support**: OpenAI, OpenRouter, Ollama, Gemini
- **Cost Effective**: Runs entirely on MongoDB Atlas free tier (M0)

## Prerequisites

- Python 3.10+
- **ONE of the following database options:**
  - **MongoDB Atlas** account (free M0 tier works perfectly!)
  - **Docker Desktop** (for self-hosted MongoDB)
- LLM provider API key (OpenAI, OpenRouter, etc.)
- Embedding provider API key (OpenAI or OpenRouter recommended)
- UV package manager

## Quick Start

Choose your deployment option:
- [Option A: MongoDB Atlas (Cloud - Recommended)](#option-a-mongodb-atlas-cloud)
- [Option B: Docker Self-Hosted](#option-b-docker-self-hosted)

---

## Option A: MongoDB Atlas (Cloud)

---

## Option A: MongoDB Atlas (Cloud)

**Best for**: Production deployments, hassle-free setup, automatic scaling

### 1. Install UV Package Manager

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone and Setup Project

```bash
git clone https://github.com/coleam00/MongoDB-RAG-Agent.git
cd MongoDB-RAG-Agent

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # Unix/Mac
.venv\Scripts\activate     # Windows
uv sync
```

### 3. Set Up MongoDB Atlas

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) and create a free account
2. Click **"Create"** → Choose **M0 Free** tier → Select region → Click **"Create Deployment"**
3. **Quickstart Wizard** appears - configure security:
   - **Database User**: Create username and password (save these!)
   - **Network Access**: Click "Add My Current IP Address"
4. Click **"Connect"** → **"Drivers"** → Copy your connection string
   - Format: `mongodb+srv://username:<password>@cluster.mongodb.net/?appName=YourApp`
   - Replace `<password>` with your actual password

**Note**: Database (`rag_db`) and collections (`documents`, `chunks`) will be created automatically when you run ingestion in step 6.

### 4. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` with your credentials:
- **MONGODB_URI**: Connection string from step 3
- **LLM_API_KEY**: Your LLM provider API key (OpenRouter, OpenAI, etc.)
- **EMBEDDING_API_KEY**: Your API key for embeddings (such as OpenAI or OpenRouter)

### 5. Validate Configuration

```bash
uv run python -m src.test_config
```

You should see: `[OK] ALL CONFIGURATION CHECKS PASSED`

### 6. Run Ingestion Pipeline

```bash
# Add your documents to the documents/ folder
uv run python -m src.ingestion.ingest -d ./documents
```

This will:
- Process your documents (PDF, Word, PowerPoint, Excel, Markdown, etc.)
- Chunk them intelligently
- Generate embeddings
- Store everything in MongoDB (`rag_db.documents` and `rag_db.chunks`)

### 7. Create Search Indexes in MongoDB Atlas

**Important**: Only create these indexes AFTER running ingestion - you need data in your `chunks` collection first.

In MongoDB Atlas, go to **Database** → **Search and Vector Search** → **Create Search Index**

**1. Vector Search Index**
- Pick: **"Vector Search"**
- Database: `rag_db`
- Collection: `chunks`
- Index name: `vector_index`
- JSON:
```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1536,
      "similarity": "cosine"
    }
  ]
}
```

**2. Atlas Search Index**
- Click **"Create Search Index"** again
- Pick: **"Atlas Search"**
- Database: `rag_db`
- Collection: `chunks`
- Index name: `text_index`
- JSON:
```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "content": {
        "type": "string",
        "analyzer": "lucene.standard"
      }
    }
  }
}
```

Wait 1-5 minutes for both indexes to build (status: "Building" → "Active").

### 8. Run the Agent

```bash
uv run python -m src.cli
```

Now you can ask questions and the agent will search your knowledge base!

---

## Option B: Docker Self-Hosted

**Best for**: Development, testing, full control over infrastructure

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- LLM and Embedding API keys (OpenAI, OpenRouter, etc.)

### 1. Clone the Repository

```bash
git clone https://github.com/coleam00/MongoDB-RAG-Agent.git
cd MongoDB-RAG-Agent
```

### 2. Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and set your API keys:
```bash
# LLM Configuration
LLM_PROVIDER=openrouter
LLM_API_KEY=your-api-key-here
LLM_MODEL=anthropic/claude-haiku-4.5

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your-openai-api-key-here
EMBEDDING_MODEL=text-embedding-3-small
```

**Note**: MongoDB connection is pre-configured in `docker-compose.yml` - no need to set `MONGODB_URI`.

### 3. Add Your Documents

```bash
# Add documents to the documents/ folder
cp /path/to/your/docs/*.pdf ./documents/
```

### 4. Start the Services

```bash
# Build and start MongoDB + RAG Agent (includes mongot for Atlas Search)
docker-compose up -d

# Optional helper script
python start_services.py

# View logs
docker-compose logs -f rag-agent
```

This will:
1. Start MongoDB Enterprise 8.0 with vector search support
2. Automatically create vector and text search indexes
3. Wait for you to ingest documents

**Port conventions (host → container):**
- MongoDB: 7017 → 27017
- Mongot (Atlas Search): 7027 → 27027
- SearXNG: 7080 → 8080

### 5. Run Document Ingestion

```bash
# Inside the Docker container
docker-compose exec rag-agent python -m src.ingestion.ingest -d ./documents
```

Or run from host with mounted volumes:
```bash
docker-compose exec rag-agent python -m src.ingestion.ingest -d /app/documents
```

### 6. Start the Interactive Agent

```bash
docker-compose exec rag-agent python -m src.cli
```

### Docker Commands Reference

```bash
# Start services (MongoDB + mongot + SearXNG)
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f rag-agent
docker-compose logs -f mongodb

# Restart services
docker-compose restart

# Remove all data (including MongoDB volumes)
docker-compose down -v

# Rebuild after code changes
docker-compose up -d --build
```

### Troubleshooting Docker Setup

**Issue**: `SearchNotEnabled` / `code=31082` when running search
- **Cause**: `$search` and `$vectorSearch` require Atlas Search (cloud) or a local `mongot` sidecar.
- **Solution**:
  - **Atlas**: Use Option A and create the `vector_index` and `text_index` in Atlas UI.
  - **Docker**: Ensure `docker-compose up -d` is running and mongot is reachable on port 7027.

**Issue**: "Vector search not supported"
- **Cause**: Using MongoDB Community Edition instead of Enterprise
- **Solution**: The `docker-compose.yml` uses `mongodb/mongodb-enterprise-server:8.0-ubuntu2204`. Ensure you're using this image.
- **Alternative**: Use MongoDB Atlas (Option A) which includes these features on the free tier

**Issue**: "Connection refused" or "MongoDB not ready"
- **Cause**: MongoDB container not fully started
- **Solution**: Wait 30 seconds for MongoDB to initialize, or check health: `docker-compose ps`

**Issue**: "Indexes not created automatically"
- **Cause**: MongoDB Enterprise license or feature not available
- **Solution**: Check logs: `docker-compose logs mongodb`. Consider using MongoDB Atlas for development.

---

## Project Structure

```
MongoDB-RAG-Agent/
├── src/                           # MongoDB implementation (COMPLETE)
│   ├── settings.py               # ✅ Configuration management
│   ├── providers.py              # ✅ LLM/embedding providers
│   ├── dependencies.py           # ✅ MongoDB connection & AgentDependencies
│   ├── test_config.py            # ✅ Configuration validation
│   ├── tools.py                  # ✅ Search tools (semantic, text, hybrid RRF)
│   ├── agent.py                  # ✅ Pydantic AI agent with search tools
│   ├── cli.py                    # ✅ Rich-based conversational CLI
│   ├── prompts.py                # ✅ System prompts
│   └── ingestion/
│       ├── docling/
│       │   ├── chunker.py         # ✅ Docling HybridChunker wrapper
│       │   └── processor.py       # ✅ Docling document conversion
│       ├── embedder.py            # ✅ Batch embedding generation
│       └── ingest.py              # ✅ MongoDB ingestion pipeline
├── server/                         # Maintenance scripts
│   └── maintenance/
│       └── init_indexes.py         # Index initialization (Docker/self-hosted)
├── examples/                      # PostgreSQL reference (DO NOT MODIFY)
│   ├── agent.py                  # Reference: Pydantic AI agent patterns
│   ├── tools.py                  # Reference: PostgreSQL search tools
│   └── cli.py                    # Reference: Rich CLI interface
├── sample/                         # Validation and example scripts
│   ├── rag/                        # Agent E2E checks
│   ├── retrieval/                  # Search/pipeline validation
│   ├── ingestion/                  # Ingestion validation utilities
│   ├── mongodb/                    # Cluster/index inspection
│   └── eval/                       # Gold dataset evaluation
├── tests/                          # Pytest checks
├── documents/                     # Document folder (13 sample documents included)
├── .claude/                       # Project documentation
│   ├── PRD.md                    # Product requirements
│   └── reference/                # MongoDB/Docling/Agent patterns
└── pyproject.toml                # UV package configuration
```

## Technology Stack

- **Database**: MongoDB Atlas or MongoDB Enterprise 8.0+ (Vector Search + Full-Text Search)
- **Deployment**: Docker Compose or Cloud (Atlas)
- **Agent Framework**: Pydantic AI 0.1.0+
- **Document Processing**: Docling 2.14+ (PDF, Word, PowerPoint, Excel, Audio)
- **Async Driver**: PyMongo 4.10+ with native async API
- **CLI**: Rich 13.9+ (terminal formatting and streaming)
- **Package Manager**: UV 0.5.0+ (fast dependency management)

## Hybrid Search Implementation

This project uses **manual Reciprocal Rank Fusion (RRF)** to combine vector and text search results, providing the same quality as MongoDB's `$rankFusion` operator while working on the **free M0 tier** (since $rankFusion is in preview it isn't available on the M0 tier).

### How It Works

1. **Semantic Search** (`$vectorSearch`): Finds conceptually similar content using vector embeddings
2. **Text Search** (`$search`): Finds keyword matches with fuzzy matching for typos
3. **RRF Merging**: Combines results using the formula: `RRF_score = Σ(1 / (60 + rank))`
   - Documents appearing in both searches get higher combined scores
   - Automatic deduplication
   - Standard k=60 constant (proven effective across datasets)

### Performance

- **Latency**: ~350-600ms per query (both searches run concurrently)
- **Accuracy**: 100% success rate on validation tests
- **Cost**: $0/month (works on free M0 tier)

## Usage Examples

### Interactive CLI

```bash
uv run python -m src.cli
```

**Example conversation:**
```
You: What is NeuralFlow AI's revenue goal for 2025?

  [Calling tool] search_knowledge_base
    Query: NeuralFlow AI's revenue goal for 2025
    Type: hybrid
    Results: 5
  [Search completed successfully]
