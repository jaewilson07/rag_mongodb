# MongoDB RAG Agent - AGENTS.md

## Agent Behavioral Protocols

### Thinking Process
1. Explore existing patterns in src/ before adding new ones.
2. Verify DRY: reuse providers, dependencies, and tool patterns.
3. Plan before execution when touching multiple files.
4. Drift check: if docs conflict with code, follow code and flag the mismatch.

### Safety Constraints
- Never run destructive commands without explicit confirmation:
  - rm -rf, docker system prune -a, database drops.
- Do not attempt to create Atlas Vector/Search indexes programmatically.
- No blind retries; inspect logs and adjust strategy.
- Treat environments separately (local Docker vs Atlas).
- Never log or commit secrets (.env contents).

### Development Workflow
- Use feature branches for new work; avoid committing directly to main.
- Open a PR for any new feature or multi-file change.

## Token Economy & Output
- Keep responses concise; reference file paths instead of dumping full files.
- Prefer small, targeted edits; avoid reformatting.
- Surface only the minimum code or config necessary to resolve tasks.

## Universal Tech Stack

### Repository Type
- Single-repo application (MongoDB RAG agent + ingestion + CLI).

### Languages & Frameworks
- Python 3.10+
- Pydantic 2.x, Pydantic AI 0.1.x
- PyMongo 4.10+ (async client), OpenAI SDK
- Docling 2.14+, Transformers
- Rich 13.9+ for CLI

### Core Commands

# Setup
- uv venv
- uv sync

# Validate config
- uv run python -m src.test_config

# Ingest documents
- uv run python -m src.ingestion.ingest -d ./documents

# Run CLI
- uv run python -m src.cli

# Docker (self-hosted)
- docker-compose up -d
- docker-compose logs -f rag-agent

# Lint / Format
- uv run ruff check .
- uv run black .

## Architecture Overview

### Component Organization
- src/: core agent runtime, tools, providers, CLI.
- src/ingestion/: Docling conversion, chunking, embeddings, ingestion pipeline.
- src/integrations/: external service integrations (Crawl4AI, Google Drive/Docs).
- src/logging_config.py: shared console logging configuration.
- documents/: sample and user-provided documents.
- examples/: reference-only patterns (do not modify).
- test_scripts/: ad-hoc validation scripts.

### Data Flow
1. Ingestion converts documents → chunks with embeddings.
2. Chunks + documents stored in MongoDB (two-collection pattern).
3. Agent queries MongoDB via semantic, text, and hybrid search.

### Service Composition Pattern
- Not used; prefer small, focused classes and async functions.

### Network/Communication
- MongoDB Atlas Vector Search + Atlas Search via aggregation pipelines.
- OpenAI-compatible LLM/embedding providers.

## File Organization & Root Directory Standards

Do not create new root-level files or directories beyond AGENTS.md. Use:
- .github/ for GitHub configs
- .claude/ for reference docs
- docs/ for documentation
- scripts/ for maintenance scripts (avoid modifying)
- test_scripts/ for validation scripts
- temp/ for scratch (gitignored)

## Common Patterns

### Settings via Pydantic Settings
When: reading .env config consistently.
Example: src/settings.py
Anti-pattern: accessing os.environ directly in multiple modules.

### Dependencies Initialization
When: MongoDB or embedding client access.
Example: src/dependencies.py
Anti-pattern: creating ad-hoc clients per call without cleanup (reuse `AgentDependencies` via `StateDeps`).

### Search Pipelines with Lookup
When: returning search results.
Example: src/tools.py
Anti-pattern: missing $lookup for document metadata.

### Docling Hybrid Chunking
When: chunking multi-format documents.
Example: src/ingestion/chunker.py
Anti-pattern: passing raw markdown string to HybridChunker.

### External Ingestion Sources
When: pulling content from Crawl4AI or Google Drive/Docs.
Example: src/ingestion/ingest.py and src/ingestion/google_drive.py
Anti-pattern: bypassing metadata extraction or skipping Docling conversion for file formats.

### Logging Configuration
When: initializing CLI or batch scripts.
Example: src/logging_config.py
Anti-pattern: per-module logging.basicConfig calls with inconsistent formats.

## JIT Index (Component Map)

### Stack-Level Documentation
- src/AGENTS.md - core runtime, tools, CLI patterns
- src/ingestion/AGENTS.md - ingestion and chunking pipeline

### Component-Level Documentation
- examples/AGENTS.md - reference-only patterns
- test_scripts/AGENTS.md - validation and smoke tests

## Search Hints

# Find hybrid search
- /bin/grep -R "def hybrid_search" -n src

# Find ingestion pipeline
- /bin/grep -R "class DocumentIngestionPipeline" -n src/ingestion

# Find Crawl4AI integration
- /bin/grep -R "class Crawl4AIClient" -n src

# Find Google Drive integration
- /bin/grep -R "class GoogleDriveClient" -n src

# Find dependencies
- /bin/grep -R "class AgentDependencies" -n src

## Error Handling Protocol

1. MongoDB connection failures:
   - Verify MONGODB_URI, then ping in AgentDependencies.
2. Missing index errors (code 291):
   - Create vector/search indexes in Atlas UI.
3. Embedding failures:
   - Check EMBEDDING_API_KEY and EMBEDDING_MODEL.
4. Docling conversion errors:
   - Log and continue; do not crash ingestion.
5. Google Drive access errors:
   - Verify GOOGLE_SERVICE_ACCOUNT_FILE and optional impersonation subject.

## Agent Gotchas

1. Hybrid search uses manual RRF in src/tools.py (not $rankFusion).
2. Embeddings must be stored as Python lists, not strings.
3. HybridChunker needs DoclingDocument; fallback chunking is last resort.
4. Examples folder is reference-only and should not be modified.
5. Ingestion is non-destructive by default; use `--clean` to wipe collections.
6. Crawl4AI requires the crawl4ai package (and Playwright runtime when crawling).
