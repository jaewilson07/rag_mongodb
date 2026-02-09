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
- Single-repo application (MongoDB RAG agent + ingestion + CLI + DeepWiki frontend).

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

# Validate config (includes MongoDB connection check)
- uv run python -m mdrag.test_config

# Setup MongoDB collections (idempotent)
- uv run python setup/setup_mongodb_tables.py

# Ingest documents
- uv run python -m mdrag.ingestion.ingest -d ./documents

# Run CLI
- uv run python -m mdrag.cli

# Docker (self-hosted)
- docker-compose up -d
- docker-compose logs -f rag-agent
- python start_services.py

# Claude Code with local vLLM (GLM-4.7)
- docker compose -f docker-compose.vllm.yml -f docker-compose.vllm.48gb.yml up -d  # 48GB: quantized model
- ./run_claude_local.sh                            # Launch Claude Code
- ./scripts/test_vllm_prompt.sh "Your prompt"      # Test vLLM directly

# Frontend (DeepWiki)
- cd frontend && npm install && npm run dev   # Dev server (port 3000)
- docker-compose up -d                         # Includes wiki-frontend on 3000

## Docker Configuration
- Use host ports in the 7000–7500 range to avoid conflicts with other infrastructure.
- Current defaults:
   - MongoDB: 7017 -> container 27017
   - Mongot (Atlas Search): 7027 -> container 27027
   - SearXNG: 7080 -> container 8080
   - vLLM: 11435 -> container 8000 (Ollama 11434 + 1, from local-ai-packaged)
- Prefer `.env` with `env_file` in compose to reduce inline environment noise.

# Lint / Format
- uv run ruff check .
- uv run black .

## Architecture Overview

### Component Organization
- src/: core agent runtime, tools, providers, CLI.
- src/ingestion/: Docling conversion, chunking, embeddings, ingestion pipeline.
- src/integrations/: external service integrations (Crawl4AI, Google Drive/Docs).
- frontend/: DeepWiki Next.js app (Knowledge Wiki, Web Crawler, Save & Research, Readings).
- src/logging_config.py: shared console logging configuration.
- documents/: sample and user-provided documents.
- examples/: reference-only patterns (do not modify).
- sample/: validation and example scripts by domain.
- setup/: MongoDB collection setup (setup_mongodb_tables.py).
- tests/: pytest-style validation tests.

### Data Flow
1. Ingestion converts documents → DoclingChunks (structure-aware, inherits ExtractSource, includes MetadataPassport and frontmatter) with embeddings.
2. Chunks + documents stored in MongoDB (two-collection pattern).
3. Deduplication is handled via upsert on content_hash (hash of chunk body); minor changes to chunk text will create new entries, but this ensures no exact duplicates. Optionally, deduplication can be keyed on source identity (e.g., URL) if required.
4. Agent queries MongoDB via semantic, text, and hybrid search.

### Service Composition Pattern
- Not used; prefer small, focused classes and async functions.

### Docker Compose & Port Mapping

- **MongoDB**: Host port 7017 → container 27017
- **Mongot (Atlas Search)**: Host port 7027 → container 27027
- **SearXNG**: Host port 7080 → container 8080
- **vLLM**: Host port 11435 → container 8000 (Ollama 11434 + 1)
- **Frontend**: Host port 3000 → container 3000

These ports are set in `docker-compose.yml` and must match `.env` and app settings. See [docs/design-patterns/docker-compose.md](docs/design-patterns/docker-compose.md) for details and best practices.

- All sensitive values and connection strings are set in `.env` and referenced in compose files using `${VAR}` syntax.
- Avoid mapping multiple services to the same host port.
- If you change a port, update all references in `.env`, compose, and settings.

See also: [docs/design-patterns/](docs/design-patterns/)

---

## Repository Map (Top Level)

```mermaid
flowchart TB
   root[MongoDB-RAG-Agent/]
   root --> src[src/ - core runtime + ingestion + integrations]
   root --> frontend[frontend/ - DeepWiki Next.js app]
   root --> docs[docs/ - design docs]
   root --> sample[sample/ - reference scripts]
   root --> setup[setup/ - MongoDB collection setup]
   root --> tests[tests/ - validation tests]
   root --> server[server/ - maintenance scripts]
   root --> scripts[scripts/ - maintenance (avoid modifying)]
   root --> data[data/ - local data cache]

   root --> docker[docker + runtime]
   docker --> dockerfile[Dockerfile]
   docker --> compose[docker-compose.yml]
   docker --> start_services[start_services.py]

   root --> config[project config]
   config --> readme[README.md]
   config --> pyproject[pyproject.toml]
   config --> agents[AGENTS.md]
```


## File Organization & Root Directory Standards

Do not create new root-level files or directories beyond AGENTS.md. Use:
- .github/ for GitHub configs
- .claude/ for reference docs
- docs/ for documentation
- scripts/ for maintenance scripts (avoid modifying)
- sample/ for validation scripts
- setup/ for MongoDB setup scripts
- tests/ for pytest-style checks
- temp/ for scratch (gitignored)

### DoclingChunks Model Refactor
When: chunking and storing document segments for RAG.
Pattern: Use `DoclingChunks` (renamed from `DocumentChunk`), which inherits from `ExtractSource` and includes the full `MetadataPassport` and frontmatter. See `src/ingestion/docling/chunker.py` for implementation.
Anti-pattern: Using ad-hoc chunk models or omitting metadata/frontmatter.

### Intelligent Chunking Sample
When: chunking large documents with structure-aware subsetting.
Pattern: See `sample/docling/chunk_pydantic_sample.py` for an example that subsets markdown by headings before chunking into `DoclingChunks`.
Anti-pattern: Blindly chunking large documents without subsetting or structure awareness.

### Dependencies Initialization
When: MongoDB or embedding client access.
Example: src/dependencies.py
Anti-pattern: creating ad-hoc clients per call without cleanup (reuse `AgentDependencies` via `StateDeps`).

### MongoDB Startup Validation
When: validating MongoDB before workflows (CLI, server, ingestion, samples).
Pattern: Use `mdrag.validation.validate_mongodb(settings, strict=True|False)`. `strict=True` for query/CLI/server (connection + collections + indexes); `strict=False` for ingestion/test_config (connection only). When `strict=False`, return immediately after ping—do not run `list_collection_names`, which can fail with "node is not in primary or recovering state" on replica sets.
Anti-pattern: skipping validation, or running schema checks (list_collection_names, index checks) when strict=False.

### Neo4j Startup Validation
When: validating Neo4j before NeuralCursor services (file watcher, librarian, MCP server, gateway).
Pattern: Use `mdrag.validation.validate_neo4j(uri, username, password, database)` at startup. Validates connection, authentication, and database accessibility before service initialization.
Example: [scripts/start_file_watcher.py](scripts/start_file_watcher.py), [scripts/start_librarian.py](scripts/start_librarian.py), [neuralcursor/gateway/server.py](neuralcursor/gateway/server.py)
Anti-pattern: connecting to Neo4j without validation; services crash with cryptic errors on first operation.

### vLLM Service Validation
When: validating vLLM endpoints before NeuralCursor workflows (when `vllm_enabled=True`).
Pattern: Use `mdrag.validation.validate_vllm(reasoning_url, embedding_url, api_key)` conditionally. Only runs when vLLM is enabled; checks both reasoning and embedding health endpoints.
Anti-pattern: starting services without checking vLLM availability when enabled; requests fail at runtime instead of startup.

### RQ Worker Validation at Startup
When: validating RQ workers before accepting queue-based requests (FastAPI ingestion/readings endpoints).
Pattern: Call `mdrag.validation.validate_rq_workers(redis_url, queue_name)` in FastAPI lifespan after MongoDB validation. Ensures at least one worker is listening before accepting requests.
Example: [src/server/main.py](src/server/main.py) lifespan
Anti-pattern: accepting ingestion/readings requests when no workers available; jobs queue indefinitely without processing.

### Sample Pre-Flight Auto-Setup
When: running sample scripts (chat_wiki, query_rag, etc.) that use `check_mongodb` from sample/utils.
Pattern: `check_mongodb(settings, auto_start=True, auto_schema=True)` will attempt to: auto-start atlas-local (URI 7017) on connection failure; create collections and run init_indexes when missing; run `rs.initiate()` on NotPrimaryOrSecondary. Skip `readPreference=primaryPreferred` when URI has `directConnection=true` to avoid blocking on RSGhost.
Rule: For this project's Docker MongoDB, use MONGODB_URI with localhost and `mongodb_docker_port` (default 7017). Other MongoDB from different compose may need manual rs.initiate().

### MongoDB Setup Script
When: creating MongoDB collections before ingestion or sample workflows.
Pattern: Run `uv run python setup/setup_mongodb_tables.py`. Idempotent—creates documents, chunks, traces, feedback only if missing; uses Settings; invokes init_indexes for vector/text indexes.
Anti-pattern: Hardcoding collection names; creating collections without existence check (MongoDB won't duplicate, but checking is clearer).

### Search Pipelines with Lookup
When: returning search results.
Example: src/tools.py
Anti-pattern: missing $lookup for document metadata.

### Docling Hybrid Chunking
When: chunking multi-format documents.
Example: src/ingestion/chunker.py
Anti-pattern: passing raw markdown string to HybridChunker.

### Ingestion Pipeline Validation
When: running any ingest flow (CLI, worker, samples, ReadingsService).
Pattern: Validation is attached to pipeline entry points. Use `validate_ingestion(settings, collectors=[...], require_redis=...)` for ingestion; `validate_readings(settings, url_type, searxng_url=...)` for ReadingsService. Core: MongoDB, embedding API, Redis (when queue used). Collector-specific: crawl4ai→Playwright, gdrive→credentials, upload→none. See [docs/design-patterns/ingestion-validation.md](docs/design-patterns/ingestion-validation.md).
Anti-pattern: Skipping validation; hardcoding redis_url or searxng_url instead of Settings.

### External Ingestion Sources
When: pulling content from Crawl4AI or Google Drive/Docs.
Example: src/ingestion/ingest.py and src/ingestion/google_drive.py
Anti-pattern: bypassing metadata extraction or skipping Docling conversion for file formats.

### Integration Exports (Frontmatter)
When: exporting markdown from integrations (Crawl4AI, Google Drive).
Example: src/mdrag/integrations/models.py
Anti-pattern: returning raw markdown without `ExtractFrontmatter`.

### Logging Configuration
When: initializing CLI or batch scripts.
Example: src/logging_config.py
Anti-pattern: per-module logging.basicConfig calls with inconsistent formats.

### DeepWiki Frontend
When: working on the web UI (Knowledge Wiki, Web Crawler, Save & Research, Readings).
Pattern: See frontend/AGENTS.md and docs/deepwiki-frontend.md. API routes proxy to FastAPI backend at localhost:8000.
Anti-pattern: Calling backend directly from browser (CORS); use Next.js API routes.

## Agent Gotchas

1. **Config over hardcoding**: Pull connection details (URI, ports, hosts) from Settings or a config class. Avoid hardcoding; parse URIs when needed (e.g. `from urllib.parse import urlparse`). Add config fields like `mongodb_docker_port` when logic depends on project-specific values.
2. **urlparse import**: Use `from urllib.parse import urlparse`; `__import__("urllib.parse")` returns the top-level `urllib` module, not `urllib.parse`—causes `AttributeError: module 'urllib' has no attribute 'urlparse'`.
3. **Async subprocess**: Don't call `subprocess.run` from async code—it blocks the event loop. Use `asyncio.to_thread(sync_fn, *args)` to run blocking sync code.
4. **LLM temperature**: Temperature is a provider capability. Use `LLMCompletionClient` (injected via `AgentDependencies.llm_client`) for chat completions—it omits temperature when the provider rejects it (e.g. OpenRouter). For LangChain/vLLM, use `get_llm_init_kwargs(settings)` from `mdrag.llm.completion_client`; for vLLM pass `provider_supports_temperature=True`. Never test temperature in workflow code.
5. Hybrid search uses manual RRF in src/tools.py (not $rankFusion).
6. Embeddings must be stored as Python lists, not strings.
7. HybridChunker needs DoclingDocument; fallback chunking is last resort.
8. Examples folder is reference-only and should not be modified.
9. Ingestion is non-destructive by default; use `--clean` to wipe collections.
10. Crawl4AI requires the crawl4ai package (and Playwright runtime when crawling).
11. Pre-flight checks must exit with `sys.exit(1)` on failure. Samples using `print_pre_flight_results` should call `sys.exit(1)` when it returns False—never return without setting exit code, as that masks failures in CI and scripts.
12. **Ingestion validation**: Validation is attached to pipeline entry points; core checks run for all, collector-specific checks run only when that collector is used. Never hardcode redis_url or searxng_url in validation—use Settings.

## Local Inference & vLLM Patterns

### FlashInfer Version Mismatch (vLLM Nightly)
- **Pattern**: vLLM nightly requires `flashinfer-python==0.6.3` but `flashinfer-cubin` 0.6.3 is not on PyPI yet; base image has cubin 0.6.1, causing `RuntimeError: flashinfer-cubin version does not match flashinfer version`.
- **Rule**: Set `FLASHINFER_DISABLE_VERSION_CHECK=1` in `docker-compose.vllm.yml` until flashinfer-cubin 0.6.3 is released. Version pinning fails because vLLM strictly requires flashinfer 0.6.3.

### Dependency Fix Validation (Retro)
- **Rule**: Before applying error-message suggestions (e.g. env bypasses), check official docs. Prefer fixing root cause (version alignment) when possible.
- **Rule**: Before version pinning to fix mismatch, verify pip allows the downgrade—upstream strict deps may block it (`pip install <pkg>==X.X` or `pip check`).

### vLLM Quantization (Compressed Tensors)
- **Pattern**: For newer quantized models (AWQ/GPTQ) that use the `llm-compressor` format, the model config often specifies `quantization_method: "compressed-tensors"`.
- **Rule**: You **must** explicitly set `--quantization compressed-tensors` in the launch command for these models. vLLM's `auto` detection frequently fails to map this correctly, resulting in configuration mismatch errors.

### GLM-4.7 Memory Thresholds
- **Pattern**: GLM-4.7 (and similar MoE models) have significant activation overhead beyond their static weight size.
- **Rule**: On a 48GB VRAM setup (e.g., 2x RTX 3090), the 31GB BF16 `GLM-4.7-Flash` is unstable. Always use a 4-bit quantized version (~6-10GB) to provide sufficient headroom for the KV cache and MoE-specific buffers.

### Multi-GPU Coordination
- **Rule**: Ensure the `--tensor-parallel-size` in the vLLM command matches the exact number of GPUs reserved in the `docker-compose.yml` `deploy` section.
- **Rule**: Use `--gpu-memory-utilization 0.90` as a safe default for quantized models; only push to `0.95` for full-precision models where every MB counts, as it increases the risk of OOM during peak activation.

## JIT Index (Component Map)
