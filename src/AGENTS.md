# Core Runtime (src) - Agent Guide

## Technical Stack
- Framework: Pydantic AI 0.1.x
- Language: Python 3.10+
- Key Dependencies:
  - PyMongo 4.10+ - async MongoDB client
  - OpenAI SDK - embeddings
  - Rich 13.9+ - CLI rendering

## Architecture & Patterns

### File Organization
- agent.py - Pydantic AI agent + search tool
- tools.py - semantic/text/hybrid search pipelines
- dependencies.py - MongoDB + embedding clients
- settings.py - Pydantic Settings config
- providers.py - LLM/embedding model provider setup
- prompts.py - system prompts
- cli.py - streaming CLI

### Code Examples

✅ DO: Initialize and ping MongoDB in AgentDependencies
- Example in src/dependencies.py (initialize): await self.mongo_client.admin.command("ping")

❌ DON'T: Skip document metadata join in search pipelines
- Anti-pattern: returning chunks without $lookup to documents
❌ DON'T: Recreate AgentDependencies per tool call
- Anti-pattern: building new clients instead of reusing `StateDeps` in src/agent.py

### Domain Dictionary
- Document: source record stored in documents collection
- Chunk: searchable unit in chunks collection with embedding
- Hybrid search: RRF merge of vector + text searches

## Service Composition
- Not used in this component.

## Key Files & JIT Search

### Touch Points
- Agent tool: src/agent.py
- Search pipelines: src/tools.py
- Configuration: src/settings.py

### Search Commands
- /bin/grep -R "def search_knowledge_base" -n src
- /bin/grep -R "class SearchResult" -n src

## Testing & Validation

### Test Command
- uv run python -m src.test_config

### Test Strategy
- Unit: Validate settings, tool outputs formatting
- Integration: Run CLI with live MongoDB + embeddings

### Test Locations
- test_scripts/ (integration and E2E checks)

## Component Gotchas

1. Use async I/O for MongoDB and OpenAI calls.
2. Tool functions should return strings for LLM consumption.
3. Match count must respect settings.max_match_count.
4. Manual RRF is in src/tools.py; do not assume $rankFusion.
5. Reuse `AgentDependencies` via `StateDeps`; avoid per-call client creation.
