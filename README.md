# Agentic RAG - Knowledge Base Search

THIS README IS A PLACEHOLDER FROM ANOTHER PROJECT - NOTHING HAS BEEN DOCUMENTED FOR THIS MONGODB RAG AGENT YET.

An intelligent RAG (Retrieval-Augmented Generation) agent demonstrating semantic and hybrid search capabilities using PostgreSQL with PGVector.

## Features

- Semantic search using vector embeddings
- Hybrid search combining semantic and keyword matching
- Automatic search strategy selection by the agent
- Knowledge base with 21 sample documents about AI/tech companies
- Result synthesis and source attribution
- Optional LangFuse observability
- Multiple LLM and embedding provider support

## Prerequisites

- Python 3.10+
- PostgreSQL with PGVector extension
- LLM provider API key (OpenAI, OpenRouter, Ollama, or compatible)
- Embedding provider API key (OpenAI or Ollama)

## Setup

1. Create and activate virtual environment:
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
```

4. Edit `.env` and add your credentials:
```
DATABASE_URL=postgresql://user:password@localhost:5432/agentic_rag

LLM_PROVIDER=openrouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your-api-key
LLM_CHOICE=anthropic/claude-haiku-4.5

EMBEDDING_PROVIDER=openai
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=your-api-key
EMBEDDING_MODEL=text-embedding-3-small
```

5. Set up database with PGVector extension and run schema:
```bash
# In your PostgreSQL database, enable PGVector
CREATE EXTENSION IF NOT EXISTS vector;

# Run the schema (create tables and functions)
# Use your SQL client or psql command
```

6. Ingest the sample documents:
```bash
python ingestion/ingest.py
```

This will process 21 documents from the `documents/` folder and store them with embeddings in the database.

## Usage

Run the agent:
```bash
python cli.py
```

Ask questions about the knowledge base. The agent will automatically choose between semantic and hybrid search. Type `exit` to quit.

Available commands:
- `info` - Display system configuration
- `clear` - Clear the screen
- `exit/quit` - Exit the application

## Project Structure

- `cli.py` - Interactive CLI interface
- `agent.py` - Main RAG agent implementation
- `tools.py` - Semantic and hybrid search tools
- `prompts.py` - System prompts for the agent
- `dependencies.py` - Agent dependencies and database connection
- `providers.py` - LLM and embedding provider setup
- `settings.py` - Configuration management
- `ingestion/` - Document processing and embedding generation
  - `ingest.py` - Main ingestion script
  - `chunker.py` - Text chunking logic
  - `embedder.py` - Embedding generation
- `documents/` - Sample knowledge base (21 markdown files)
- `sql/schema.sql` - PostgreSQL schema with PGVector functions
- `.env.example` - Environment variable template
- `requirements.txt` - Python dependencies

## How It Works

The agent uses:
- **Pydantic AI** for the agent framework
- **PostgreSQL + PGVector** for vector storage and similarity search
- **Semantic search** for conceptual queries (pure vector similarity)
- **Hybrid search** for specific facts (combines vector + keyword matching)
- **Intelligent routing** to automatically select the best search strategy
- **LangFuse** (optional) for observability and tracing

## Search Strategies

**Semantic Search**: Best for conceptual/thematic queries
- "What companies are investing in AI?"
- "Tell me about AI alignment approaches"

**Hybrid Search**: Best for specific facts or keywords
- "What is OpenAI's valuation?"
- "Sam Altman background"
- Combines vector similarity with PostgreSQL full-text search

## Database Schema

The database includes:
- `documents` - Full documents with metadata
- `chunks` - Text chunks with vector embeddings
- `match_chunks()` - Function for pure semantic search
- `hybrid_search()` - Function for combined semantic + keyword search
