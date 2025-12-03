# Product Requirements Document: MongoDB Agentic RAG Agent

## Executive Summary

The MongoDB Agentic RAG Agent is an intelligent document retrieval and question-answering system that combines semantic vector search with full-text keyword search to deliver highly relevant responses from a knowledge base. Built on MongoDB Atlas Vector Search and Pydantic AI, this system enables users to interact conversationally with their document collections through an intelligent agent that can perform both conceptual queries and precise keyword searches.

The core innovation lies in leveraging MongoDB's native `$rankFusion` operator for hybrid search, which seamlessly combines vector embeddings with traditional full-text search using Reciprocal Rank Fusion. This approach provides superior retrieval accuracy compared to single-method search systems. The ingestion pipeline uses Docling for multi-format document processing and intelligent chunking that preserves document structure and semantic boundaries.

The MVP focuses on delivering a production-ready CLI-based conversational agent capable of ingesting documents from multiple formats (PDF, Word, PowerPoint, Excel, HTML, Markdown, Audio), storing them in MongoDB with proper vector embeddings, and providing accurate retrieval through hybrid search. The system maintains a clear separation between source documents and their embedded chunks, enabling proper attribution and traceability.

## Mission

**Empower users to extract actionable insights from their document collections through intelligent, context-aware conversational search powered by MongoDB and modern AI techniques.**

### Core Principles

1. **Retrieval Accuracy First**: Hybrid search combining semantic understanding with keyword precision ensures the most relevant information surfaces for every query
2. **Document Fidelity**: Preserve original document structure, metadata, and source attribution throughout the ingestion and retrieval pipeline
3. **Production-Ready Architecture**: Build on MongoDB Atlas's enterprise-grade vector search capabilities with proper error handling, connection pooling, and scalability considerations
4. **Developer-Friendly**: Clear separation of concerns, type-safe code with Pydantic, and extensible architecture for future enhancements
5. **Transparent Operation**: Users can see tool calls in real-time, understand search strategies, and trace answers back to source documents

## Target Users

### Primary User Persona: Technical Knowledge Worker

**Profile:**
- Software engineers, researchers, technical writers, and data scientists
- Comfortable with CLI tools and environment configuration
- Manages large collections of technical documentation, research papers, or internal knowledge bases
- Needs quick, accurate answers from document collections without manual searching

**Technical Comfort Level:**
- Can run Python scripts and set up virtual environments
- Comfortable with environment variables and configuration files
- Has access to MongoDB Atlas or can set up a cluster
- Familiar with API keys and service configuration

**Key Needs:**
- Fast semantic search across document collections (conceptual queries)
- Precise keyword matching for technical terms and specific facts
- Multi-format document support (PDFs, Word docs, presentations, audio transcripts)
- Source attribution for all retrieved information
- Conversational interface that doesn't require query syntax

**Pain Points:**
- Traditional keyword search misses conceptually similar content
- Pure semantic search sometimes misses exact technical terms
- Manually searching through hundreds of documents is time-consuming
- Need to maintain document provenance for citations and verification
- Existing solutions lock them into proprietary platforms

## MVP Scope

### In Scope: Core Functionality

**Document Ingestion**
- ✅ Multi-format document processing via Docling (PDF, DOCX, PPTX, XLSX, HTML, Markdown, TXT)
- ✅ Audio transcription support using Whisper ASR via Docling (MP3, WAV, M4A, FLAC)
- ✅ Intelligent hybrid chunking preserving document structure and semantic boundaries
- ✅ Automatic embedding generation using OpenAI-compatible embedding models
- ✅ Two-collection storage pattern (documents + chunks with references)
- ✅ Metadata extraction from documents (frontmatter, document properties)
- ✅ Batch processing with progress tracking
- ✅ Clean database option before ingestion

**Search & Retrieval**
- ✅ Semantic vector search using MongoDB `$vectorSearch` aggregation
- ✅ Full-text keyword search using MongoDB `$search` with fuzzy matching
- ✅ Hybrid search combining both methods via `$rankFusion` operator
- ✅ Configurable result count (default: 5, max: 50)
- ✅ Source document attribution in search results
- ✅ Similarity/relevance scoring for all results

**Agent & Interaction**
- ✅ Pydantic AI agent with tool-based architecture
- ✅ Conversational CLI with Rich-based formatting
- ✅ Real-time streaming of agent responses
- ✅ Tool call visibility (users see when searches are performed)
- ✅ Message history for contextual conversations
- ✅ Natural language query understanding
- ✅ Automatic search strategy selection (semantic vs hybrid)

**Technical Infrastructure**
- ✅ MongoDB Atlas integration with Motor async driver
- ✅ Vector search index configuration and management
- ✅ Full-text search index configuration
- ✅ Connection pooling and async operations
- ✅ Environment-based configuration with Pydantic Settings
- ✅ Multiple LLM provider support (OpenAI, OpenRouter, Ollama, Gemini)
- ✅ Error handling and graceful degradation
- ✅ UV package manager for fast, reliable dependency management

### Out of Scope: Future Enhancements

**Advanced Features**
- ❌ Web-based UI (MVP is CLI-only)
- ❌ Multi-user authentication and authorization
- ❌ Real-time document updates and change tracking
- ❌ Custom embedding model fine-tuning
- ❌ Metadata filtering in search queries
- ❌ Search result re-ranking based on user feedback
- ❌ Query analytics and usage tracking

**Integration & Deployment**
- ❌ Docker containerization
- ❌ API server for external integrations
- ❌ Webhook support for automated ingestion
- ❌ Cloud deployment scripts (AWS, GCP, Azure)
- ❌ Kubernetes manifests
- ❌ CI/CD pipeline configuration

**Advanced Search**
- ❌ Multi-hop reasoning across documents
- ❌ Citation graph analysis
- ❌ Cross-document entity linking
- ❌ Temporal search (filter by date ranges)
- ❌ Geospatial search integration
- ❌ Image and table content search

**Data Management**
- ❌ Incremental ingestion (only new/updated documents)
- ❌ Document versioning and history
- ❌ Automatic chunk optimization based on retrieval patterns
- ❌ Embedding model migration tools
- ❌ Backup and restore utilities

## User Stories

### Primary User Stories

**US-1: Document Ingestion**
> As a **technical knowledge worker**, I want to **ingest a folder of mixed-format documents into the system**, so that **I can query them conversationally without manually converting formats**.

**Example:** User has a folder with 50 PDF research papers, 10 Word documents, and 5 PowerPoint presentations. They run `uv run python -m examples.ingestion.ingest -d ./my_docs` and all documents are processed, chunked, embedded, and stored in MongoDB automatically.

**US-2: Semantic Search**
> As a **researcher**, I want to **search for documents by concept or theme**, so that **I can find relevant information even when I don't know the exact keywords**.

**Example:** User asks "What are best practices for scaling microservices?" The agent performs semantic search and retrieves relevant chunks even from documents that use terms like "distributed systems architecture" or "service mesh patterns."

**US-3: Precise Keyword Search**
> As a **software engineer**, I want to **find exact technical terms or API names**, so that **I can quickly locate specific implementation details**.

**Example:** User asks "How do I use the $rankFusion operator?" The hybrid search ensures the exact term "$rankFusion" is matched, returning precise documentation even if semantically similar concepts exist elsewhere.

**US-4: Conversational Interaction**
> As a **knowledge worker**, I want to **interact with the system through natural conversation**, so that **I don't need to learn query syntax or search operators**.

**Example:** User types "Hi, can you help me understand vector databases?" The agent responds conversationally without performing unnecessary searches, then searches when the user asks specific questions.

**US-5: Source Attribution**
> As a **researcher**, I want to **see which documents my answers came from**, so that **I can verify information and cite sources properly**.

**Example:** After receiving an answer, user sees "Based on 3 documents: technical-guide.pdf (relevance: 0.89), architecture-overview.docx (relevance: 0.82), meeting-notes.txt (relevance: 0.76)".

**US-6: Audio Content Processing**
> As a **content manager**, I want to **search through meeting recordings and podcasts**, so that **I can find discussions on specific topics without manual transcription**.

**Example:** User ingests a folder of MP3 meeting recordings. Docling automatically transcribes them using Whisper, chunks the transcripts, and makes them searchable alongside text documents.

**US-7: Real-Time Transparency**
> As a **power user**, I want to **see what searches are being performed**, so that **I understand how the agent is finding information**.

**Example:** When user asks a question, CLI shows: "🔍 Calling tool: search_knowledge_base" → "Query: best practices microservices" → "Type: hybrid" → "Results: 5" → Then streams the synthesized answer.

**US-8: System Configuration**
> As a **developer**, I want to **easily configure the system for different LLM and embedding providers**, so that **I can use my preferred services or switch providers as needed**.

**Example:** User sets environment variables for OpenRouter API instead of OpenAI, and the system works identically with Claude or GPT models without code changes.

## Technology Stack

### Package Management
- **UV** (`0.5.x+`): Modern, fast Python package manager and environment manager
  - Replaces pip + virtualenv with unified tooling
  - Significantly faster dependency resolution (10-100x faster than pip)
  - Built-in virtual environment management
  - Lock file support (`uv.lock`) for reproducible builds
  - Commands: `uv venv`, `uv pip install`, `uv pip sync`, `uv run`
  - Installation: `curl -LsSf https://astral.sh/uv/install.sh | sh` (Unix) or `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows)

### Core Python Dependencies

**AI & LLM**
- `pydantic-ai` (^0.1.0): Agent framework with tool support and streaming
- `pydantic` (^2.10.0): Data validation and settings management
- `pydantic-settings` (^2.7.0): Environment-based configuration
- `openai` (^1.58.0): OpenAI API client (used for embeddings and LLM calls)

**Database**
- `motor` (^3.7.0): Async MongoDB driver for Python
- `pymongo` (^4.10.0): MongoDB Python driver (motor dependency)

**Document Processing**
- `docling` (^2.14.0): Multi-format document converter with Whisper ASR support
- `docling-core` (^2.4.0): Core Docling types and utilities
- `transformers` (^4.47.0): HuggingFace transformers for tokenization

**CLI & UI**
- `rich` (^13.9.0): Terminal formatting and progress bars
- `click` (^8.1.8): Command-line interface framework

**Utilities**
- `python-dotenv` (^1.0.1): Environment variable loading
- `asyncio` (built-in): Async operations
- `aiofiles` (^24.1.0): Async file operations

### Optional Dependencies

**Audio Transcription** (for Docling ASR)
- `whisper` or Docling's built-in Whisper Turbo integration
- Automatically handled by Docling when processing audio files

**Development**
- `pytest` (^8.3.0): Testing framework
- `pytest-asyncio` (^0.24.0): Async test support
- `black` (^24.10.0): Code formatting
- `ruff` (^0.8.0): Fast linting

### Third-Party Services

**MongoDB Atlas** (Required)
- Atlas cluster with MongoDB v8.0+ for `$rankFusion` support
- Vector Search index enabled on cluster
- Atlas Search index for full-text search
- Minimum tier: M10 (recommended for production)
- Free tier (M0) supported for development/testing

**LLM Providers** (Choose One)
- **OpenAI** (recommended): GPT-4o, GPT-4o-mini, text-embedding-3-small
- **OpenRouter**: Unified access to Claude, GPT, Gemini, and open-source models
- **Ollama**: Local models (qwen2.5, llama3, etc.)
- **Google Gemini**: Gemini 1.5 Pro/Flash

**Embedding Providers** (Choose One)
- **OpenAI** (default): text-embedding-3-small (1536 dims), text-embedding-3-large (3072 dims)
- **Voyage AI**: voyage-3, voyage-3-lite
- **Ollama**: Local embedding models (nomic-embed-text, etc.)

### System Requirements

- **Python**: 3.10+ (3.11+ recommended for better async performance)
- **Memory**: 4GB minimum, 8GB+ recommended (for Docling processing)
- **Storage**: 500MB for dependencies, additional space for document storage
- **OS**: Linux, macOS, Windows (WSL recommended for Windows)
- **Network**: Internet connection for MongoDB Atlas and LLM/embedding APIs

### Version Matrix

| Component | Minimum Version | Recommended | Notes |
|-----------|----------------|-------------|-------|
| Python | 3.10 | 3.11+ | Type hints, async improvements |
| UV | 0.5.0 | Latest | Package management |
| MongoDB | 8.0 | 8.1+ | Required for $rankFusion |
| Pydantic AI | 0.1.0 | Latest | Agent framework |
| Docling | 2.14.0 | Latest | Document processing |
| Motor | 3.7.0 | Latest | Async MongoDB driver |

## Security & Configuration

### Environment Configuration

All sensitive configuration stored in `.env` file (gitignored):

```bash
# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DATABASE=rag_db
MONGODB_COLLECTION_DOCUMENTS=documents
MONGODB_COLLECTION_CHUNKS=chunks

# MongoDB Indexes
MONGODB_VECTOR_INDEX=vector_index
MONGODB_TEXT_INDEX=text_index

# LLM Provider Configuration
LLM_PROVIDER=openrouter
LLM_API_KEY=sk-or-v1-your-key-here
LLM_MODEL=anthropic/claude-haiku-4.5
LLM_BASE_URL=https://openrouter.ai/api/v1

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=sk-your-openai-key-here
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_BASE_URL=https://api.openai.com/v1

# Search Configuration
DEFAULT_MATCH_COUNT=10
MAX_MATCH_COUNT=50
DEFAULT_TEXT_WEIGHT=0.3

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
```

### Security Scope

**In Scope for MVP:**
- ✅ Environment variable-based secrets management
- ✅ MongoDB Atlas connection with authentication
- ✅ API key validation on startup
- ✅ Connection pooling with timeout limits
- ✅ Input validation via Pydantic models
- ✅ No plaintext secrets in code or logs
- ✅ `.env` file in `.gitignore`

**Out of Scope (Future Enhancements):**
- ❌ Multi-user authentication/authorization
- ❌ Role-based access control (RBAC)
- ❌ Secrets management service integration (Vault, AWS Secrets Manager)
- ❌ Encryption at rest (relies on MongoDB Atlas encryption)
- ❌ Audit logging
- ❌ Rate limiting per user
- ❌ API key rotation

### Configuration Management

**Settings Hierarchy:**
1. Environment variables (`.env` file)
2. System environment variables
3. Default values in `settings.py`

**Pydantic Settings Pattern:**
```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    mongodb_uri: str = Field(..., description="MongoDB connection string")
    llm_api_key: str = Field(..., description="LLM provider API key")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
```

### Deployment Considerations

**Development:**
- Use `.env` file for local configuration
- MongoDB Atlas free tier (M0) acceptable
- Ollama for local LLM testing (optional)

**Production:**
- Environment variables set at system/container level
- MongoDB Atlas M10+ cluster with backups enabled
- Connection pooling configured for expected load
- Monitor API rate limits and costs
- Log sanitization to prevent secret leakage

## Success Criteria

### MVP Success Definition

The MVP is considered successful when users can:
1. Ingest 100+ documents of mixed formats without manual intervention
2. Perform hybrid search queries with <2 second response time
3. Receive accurate, sourced answers from the knowledge base
4. See clear attribution to source documents
5. Configure the system with different LLM providers
6. Use the system through an intuitive CLI interface

### Functional Requirements

**Document Ingestion:**
- ✅ Process PDF, Word, PowerPoint, Excel, HTML, Markdown files
- ✅ Transcribe audio files (MP3, WAV, M4A, FLAC)
- ✅ Chunk documents with context preservation
- ✅ Generate embeddings for all chunks
- ✅ Store in MongoDB with proper indexing
- ✅ Complete ingestion of 100 documents in <10 minutes

**Search Accuracy:**
- ✅ Semantic search returns conceptually relevant results
- ✅ Hybrid search finds exact keyword matches
- ✅ Top 5 results include correct answer >80% of the time
- ✅ Source attribution present for all results
- ✅ Relevance scores correlate with user perception

**Agent Performance:**
- ✅ Query response time <2 seconds for searches
- ✅ Streaming responses appear within 500ms
- ✅ Tool calls visible to user in real-time
- ✅ Conversation history maintained across session
- ✅ Handles errors gracefully without crashes

**System Reliability:**
- ✅ Ingestion pipeline handles format errors without stopping
- ✅ MongoDB connection retries on timeout
- ✅ LLM API failures return helpful error messages
- ✅ System can run continuously for 8+ hours without degradation
- ✅ Concurrent searches don't block each other

### Quality Indicators

**Code Quality:**
- Type hints on all functions
- Pydantic models for all data structures
- Unit tests for search functions
- Async/await properly used throughout
- No secrets in codebase

**User Experience:**
- CLI provides clear feedback during operations
- Progress bars for long-running ingestion
- Tool call transparency helps user understanding
- Error messages suggest corrective actions
- Documentation covers setup and common issues

**Performance:**
- Vector search candidates: 100 per query
- Batch embedding generation: 100 chunks/batch
- MongoDB connection pool: 10-20 connections
- Memory usage: <2GB during normal operation
- CPU: Minimal during idle, spikes during ingestion

## Implementation Phases

### Phase 1: Core Infrastructure

**Goal:** Establish MongoDB connection, basic data models, and configuration system

**Deliverables:**
- ✅ Project structure with UV package management
- ✅ MongoDB client with Motor async driver
- ✅ Settings system with Pydantic
- ✅ Environment variable configuration
- ✅ Connection pooling and error handling
- ✅ Basic logging setup
- ✅ MongoDB connection utilities

**Validation Criteria:**
- Can connect to MongoDB Atlas
- Settings load from `.env` file
- Connection maintains stable async operations
- Proper error handling for connection failures

**Key Files:**
- `pyproject.toml` (UV configuration)
- `src/settings.py`
- `src/providers.py` (LLM/embedding client setup)
- `.env.example`

---

### Phase 2: Document Ingestion Pipeline

**Goal:** Build complete ingestion pipeline from documents to embedded chunks in MongoDB

**Deliverables:**
- ✅ Docling integration for multi-format conversion
- ✅ HybridChunker wrapper preserving document structure
- ✅ Embedding generator with batch processing
- ✅ MongoDB inserter for documents and chunks
- ✅ Document/chunk two-collection pattern
- ✅ Metadata extraction and storage
- ✅ CLI for ingestion with progress tracking
- ✅ Audio transcription support

**Validation Criteria:**
- Successfully processes 100+ mixed-format documents
- Chunks average 400-600 tokens (fits embedding limits)
- Document-chunk relationships properly established
- Embeddings generated for all chunks
- Ingestion completes without crashes on errors
- Progress visible to user

**Key Files:**
- `src/ingestion/chunker.py` (adapted from examples)
- `src/ingestion/embedder.py` (adapted from examples)
- `src/ingestion/ingest.py` (MongoDB implementation)
- `src/ingestion/__init__.py`

---

### Phase 3: Search Implementation

**Goal:** Implement semantic and hybrid search tools using MongoDB aggregation pipelines

**Deliverables:**
- ✅ Semantic search using `$vectorSearch`
- ✅ Hybrid search using `$rankFusion`
- ✅ Document lookup for source attribution
- ✅ Score extraction and normalization
- ✅ Fuzzy matching configuration
- ✅ SearchResult Pydantic models
- ✅ Error handling for missing indexes
- ✅ Tool function wrappers for agent

**Validation Criteria:**
- Semantic search returns relevant results
- Hybrid search combines vector + text scores
- Source document info included in results
- Queries complete in <2 seconds
- Top 5 results include correct answer >80% of the time
- Graceful handling of empty results

**Key Files:**
- `src/tools.py` (MongoDB implementation)
- `src/models.py` (SearchResult and other Pydantic models)

---

### Phase 4: Agent & CLI

**Goal:** Build Pydantic AI agent and conversational CLI interface

**Deliverables:**
- ✅ Pydantic AI agent with search tools
- ✅ StateDeps dependency injection
- ✅ System prompts for agent behavior
- ✅ MongoDB dependencies class
- ✅ Rich-based CLI with streaming
- ✅ Tool call visibility
- ✅ Message history management
- ✅ Special commands (info, clear, exit)
- ✅ Error handling and user feedback

**Validation Criteria:**
- Agent responds conversationally
- Search tools called appropriately
- Streaming responses appear in real-time
- Tool calls visible to user
- Conversation context maintained
- Handles multiple LLM providers

**Key Files:**
- `src/agent.py` (adapted from examples)
- `src/cli.py` (adapted from examples)
- `src/dependencies.py` (MongoDB implementation)
- `src/prompts.py` (adapted from examples)

---

### Phase 5: Testing & Documentation

**Goal:** Ensure system reliability, create user documentation, and validate against success criteria

**Deliverables:**
- ✅ Unit tests for search functions
- ✅ Integration tests for ingestion pipeline
- ✅ Test fixtures with sample documents
- ✅ README with setup instructions
- ✅ Environment configuration guide
- ✅ MongoDB Atlas setup tutorial
- ✅ Troubleshooting guide
- ✅ Performance benchmarks
- ✅ Example queries and expected results

**Validation Criteria:**
- All tests pass consistently
- Documentation enables new user setup in <30 minutes
- Performance meets criteria (response time, throughput)
- System handles edge cases gracefully
- Common issues have documented solutions

**Key Files:**
- `README.md`
- `docs/SETUP.md`
- `docs/MONGODB_ATLAS.md`
- `docs/TROUBLESHOOTING.md`
- `tests/` directory

## Leveraging Existing Examples

### Using the Examples Folder as Reference

**IMPORTANT**: The `examples/` folder contains a **production-quality Postgres-based RAG implementation** that serves as reference material. **DO NOT MODIFY** files in the `examples/` folder. Instead, copy relevant code to new files in the `src/` directory and adapt them for MongoDB.

**Implementation Approach:**
- Examples folder remains untouched as reference
- Create new `src/` directory for MongoDB implementation
- Copy patterns and code from examples, adapt for MongoDB
- Maintain same architecture and design patterns

**What to Copy from Examples (with adaptations):**

1. **Ingestion Pipeline (`examples/ingestion/` → `src/ingestion/`):**
   - ✅ **Copy** `chunker.py`: Docling HybridChunker wrapper (minimal changes needed)
   - ✅ **Copy** `embedder.py`: Batch embedding generation (works as-is)
   - ✅ **Copy** `ingest.py`: Document processing logic, **adapt** database operations to MongoDB

2. **Agent Architecture (`examples/agent.py` → `src/agent.py`):**
   - ✅ **Copy** Pydantic AI agent structure with StateDeps pattern
   - ✅ **Copy** Tool registration and streaming logic
   - ✅ **Adapt** import paths to use new `src/` modules

3. **CLI Interface (`examples/cli.py` → `src/cli.py`):**
   - ✅ **Copy** Rich-based conversational interface (works as-is)
   - ✅ **Copy** Streaming and tool call visibility logic
   - ✅ **Adapt** import paths to use new `src/` modules

4. **Configuration (`examples/settings.py` → `src/settings.py`):**
   - ✅ **Copy** Pydantic Settings structure
   - ✅ **Adapt** to add MongoDB-specific fields (URI, database, collections, indexes)
   - ✅ **Remove** PostgreSQL-specific fields (DATABASE_URL, pool settings)

5. **Providers (`examples/providers.py` → `src/providers.py`):**
   - ✅ **Copy** directly (works as-is for LLM/embedding providers)

6. **Prompts (`examples/prompts.py` → `src/prompts.py`):**
   - ✅ **Copy** directly (works as-is)

**What to Build New (MongoDB-specific):**

1. **Dependencies (`src/dependencies.py`):**
   - ❌ **Build new** using Motor AsyncIOMotorClient instead of asyncpg
   - ❌ MongoDB connection management with proper async init/cleanup
   - ❌ Embedding format as Python list (not pgvector string)

2. **Search Tools (`src/tools.py`):**
   - ❌ **Build new** using MongoDB aggregation pipelines
   - ❌ Implement `$vectorSearch` for semantic search
   - ❌ Implement `$rankFusion` for hybrid search
   - ❌ Use `$lookup` for document metadata joins

3. **Data Models (`src/models.py`):**
   - ❌ **Build new** with Pydantic models for MongoDB documents
   - ❌ SearchResult, DocumentChunk, Document models with BSON/ObjectId support

**Development Workflow:**

1. **Phase 1**: Create `src/` directory structure, set up UV, copy settings/providers
2. **Phase 2**: Build MongoDB dependencies and connection management
3. **Phase 3**: Implement MongoDB search tools with aggregation pipelines
4. **Phase 4**: Copy and adapt ingestion pipeline for MongoDB
5. **Phase 5**: Copy and adapt agent/CLI with updated imports
6. **Phase 6**: Test end-to-end and document

**Key Advantages:**

1. **Reference Preservation**: Examples folder remains as working reference
2. **Proven Patterns**: Copy battle-tested agent, CLI, and ingestion logic
3. **Clean Separation**: Clear distinction between PostgreSQL reference and MongoDB implementation
4. **Type Safety**: Maintain Pydantic models throughout
5. **Reduced Risk**: Focus changes only on database layer

## Appendix

### Related Documents & Resources

**Official MongoDB Documentation:**
- [MongoDB Atlas Vector Search RAG Guide](https://www.mongodb.com/docs/atlas/atlas-vector-search/rag/?language-no-interface=python&embedding-model=voyage&llm=openai) - Complete RAG implementation guide with Python examples
- [MongoDB Hybrid Search with $rankFusion](https://www.mongodb.com/docs/atlas/atlas-vector-search/hybrid-search/vector-search-with-full-text-search/) - Official documentation for hybrid search combining vector and full-text search
- [MongoDB Vector Search Documentation](https://www.mongodb.com/docs/atlas/atlas-vector-search/) - Full vector search reference

**Implementation Examples:**
- [Pydantic AI + MongoDB Agent Cookbook](https://github.com/mongodb-developer/GenAI-Showcase/blob/main/notebooks/agents/ai_agent_with_pydanticai_and_mongodb.ipynb) - Production example of building AI agents with Pydantic AI and MongoDB

**Framework Documentation:**
- [Pydantic AI Documentation](https://ai.pydantic.dev/) - Agent framework documentation
- [Docling Documentation](https://docling.dev/) - Document processing library
- [UV Package Manager](https://github.com/astral-sh/uv) - Modern Python package manager

### Key Dependencies

**Pydantic AI:**
- Repository: https://github.com/pydantic/pydantic-ai
- Documentation: https://ai.pydantic.dev/
- Version: ^0.1.0

**MongoDB Motor:**
- Repository: https://github.com/mongodb/motor
- Documentation: https://motor.readthedocs.io/
- Version: ^3.7.0

**Docling:**
- Repository: https://github.com/DS4SD/docling
- Documentation: https://docling.dev/
- Version: ^2.14.0

**UV:**
- Repository: https://github.com/astral-sh/uv
- Documentation: https://docs.astral.sh/uv/
- Installation: https://astral.sh/uv/install

### MongoDB Atlas Setup Quick Reference

**1. Create Cluster:**
- Sign up at https://www.mongodb.com/cloud/atlas/register
- Create M10+ cluster (M0 free tier works for development)
- Select closest region for latency

**2. Configure Network Access:**
- Add IP address (0.0.0.0/0 for development, specific IPs for production)
- Or use VPC peering for secure access

**3. Create Database User:**
- Database Access → Add New Database User
- Use strong password, save to `.env` file
- Grant "Read and Write" permissions

**4. Create Vector Search Index:**
```javascript
// In Atlas UI: Database → Collections → Search Indexes → Create Index
{
  "name": "vector_index",
  "type": "vectorSearch",
  "definition": {
    "fields": [
      {
        "type": "vector",
        "path": "embedding",
        "numDimensions": 1536,
        "similarity": "cosine"
      }
    ]
  }
}
```

**5. Create Full-Text Search Index:**
```javascript
{
  "name": "text_index",
  "type": "search",
  "definition": {
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
}
```

**6. Get Connection String:**
- Cluster → Connect → Connect your application
- Copy connection string
- Replace `<password>` with actual password
- Add to `.env` as `MONGODB_URI`

### Project Structure

```
MongoDB-RAG-Agent/
├── .claude/
│   ├── PRD.md                          # This document
│   ├── commands/                       # Custom slash commands
│   └── reference/                      # MongoDB/Docling/Agent patterns
├── .github/                            # (Future) CI/CD workflows
├── examples/                           # PostgreSQL reference (DO NOT MODIFY)
│   ├── agent.py                        # Reference: Pydantic AI agent
│   ├── cli.py                          # Reference: CLI interface
│   ├── dependencies.py                 # Reference: PostgreSQL dependencies
│   ├── providers.py                    # Reference: LLM providers
│   ├── prompts.py                      # Reference: System prompts
│   ├── settings.py                     # Reference: PostgreSQL settings
│   ├── tools.py                        # Reference: PostgreSQL search tools
│   └── ingestion/                      # Reference: PostgreSQL ingestion
│       ├── chunker.py
│       ├── embedder.py
│       └── ingest.py
├── src/                                # MongoDB implementation (NEW)
│   ├── __init__.py
│   ├── agent.py                        # Pydantic AI agent (adapted)
│   ├── cli.py                          # CLI interface (adapted)
│   ├── dependencies.py                 # MongoDB dependencies (new)
│   ├── models.py                       # Pydantic models (new)
│   ├── providers.py                    # LLM providers (copied)
│   ├── prompts.py                      # System prompts (copied)
│   ├── settings.py                     # MongoDB settings (adapted)
│   ├── tools.py                        # MongoDB search tools (new)
│   └── ingestion/
│       ├── __init__.py
│       ├── chunker.py                  # HybridChunker (copied)
│       ├── embedder.py                 # Embedding generation (copied)
│       └── ingest.py                   # MongoDB ingestion (adapted)
├── docs/                               # (Future) Documentation
│   ├── SETUP.md
│   ├── MONGODB_ATLAS.md
│   └── TROUBLESHOOTING.md
├── tests/                              # (Future) Test suite
│   ├── __init__.py
│   ├── test_search.py
│   ├── test_ingestion.py
│   └── fixtures/
├── documents/                          # User's document folder
├── .env                                # Environment config (gitignored)
├── .env.example                        # Environment template
├── .gitignore
├── pyproject.toml                      # UV configuration
├── uv.lock                             # UV lock file (auto-generated)
├── README.md                           # Main documentation
└── LICENSE                             # Project license
```

### UV Commands Quick Reference

**Setup:**
```bash
# Create virtual environment
uv venv

# Activate environment
source .venv/bin/activate  # Unix
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -r requirements.txt

# Or install from pyproject.toml
uv pip install -e .
```

**Running:**
```bash
# Run ingestion
uv run python -m src.ingestion.ingest -d ./documents

# Run CLI agent
uv run python -m src.cli

# Run with specific Python version
uv run --python 3.11 python -m src.cli
```

**Development:**
```bash
# Add dependency
uv pip install pydantic-ai

# Add dev dependency
uv pip install --dev pytest

# Update dependencies
uv pip install --upgrade pydantic-ai

# Sync dependencies from lock file
uv pip sync
```

---

## Document Approval

**Version:** 1.0
**Date:** 2025-01-15
**Status:** Draft - Pending Review

**Next Steps:**
1. Review PRD with stakeholders
2. Validate technical approach with MongoDB experts
3. Confirm budget for MongoDB Atlas and LLM APIs
4. Approve implementation timeline
5. Begin Phase 1 development
