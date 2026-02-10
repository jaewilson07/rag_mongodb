# MongoDB RAG Agent Changelog

> Session updates. Newest entries at the top.

---

## Recent Updates

### 2026-02-09 - Removed Backward-Compat Stubs and Shims

- **observability**: Deleted `src/observability/` (re-exports); imports updated to `mdrag.core.telemetry` in `interfaces/api/services/feedback.py` and `capabilities/query/service.py`.
- **capabilities/ingestion/storage**: Deleted stub; test and code use `mdrag.integrations.mongodb.adapters.storage`.
- **llm**: Deleted `src/llm/` (stubs and duplicate implementations); all imports updated to `mdrag.integrations.llm.*` (scripts, workflows/neuralcursor, workflows/rag, self_corrective_rag).
- **server**: Deleted entire `src/server/` (duplicate of `interfaces/api`); sample scripts and docs now use `mdrag.interfaces.api.services.wiki`, `mdrag.interfaces.api.services.readings`, and `uv run uvicorn mdrag.interfaces.api.main:app`.

### 2026-02-09 - Outstanding Plan Tasks (Workflows, CLI, MCP, Docker)

- **Workflow exceptions**: Added `workflows/rag/exceptions.py` (RAGError), `workflows/wiki/exceptions.py` (WikiError), `workflows/readings/exceptions.py` (ReadingsError). Created `workflows/wiki/` and `workflows/readings/` package structure.
- **RAG agent and tools in workflows**: Moved implementation to `workflows/rag/agent.py` and `workflows/rag/tools.py`; root `agent.py` and `tools.py` are backward-compat stubs re-exporting from `mdrag.workflows.rag`. Updated `workflows/rag/__init__.py` to export agent, tools, and exceptions.
- **CLI under interfaces**: Added `interfaces/cli/cli.py` and `interfaces/cli/cli_langgraph.py` (canonical CLI); root `cli.py` and `cli_langgraph.py` now delegate to `mdrag.interfaces.cli.cli` and `mdrag.interfaces.cli.cli_langgraph`.
- **MCP interface**: Added `interfaces/mcp/__init__.py` re-exporting `NeuralCursorMCPServer` and `MCPTools` from `mdrag.mcp_server`.
- **Docker and docs**: `docker-compose.yml` and `Dockerfile` now use `python -m mdrag.cli`; `docs/deepwiki-frontend.md` recommends `uv run uvicorn mdrag.interfaces.api.main:app`.
- **NeuralCursor move completed**: Moved `mcp_server`, `file_watcher`, `librarian_agent`, `maintenance` into `workflows/neuralcursor/`. Canonical code lives in `mdrag.workflows.neuralcursor.*`; root `mcp_server`, `file_watcher`, `librarian_agent`, `maintenance` are backward-compat stubs. Scripts (`start_mcp_server.py`, `start_librarian.py`, `start_file_watcher.py`, `init_neuralcursor.py`, `run_brain_care.py`) now use `mdrag.*` imports. Added `workflows/neuralcursor/exceptions.py` (NeuralCursorError). Fixed `integrations/neo4j/client.py` to use `mdrag.settings`.

### 2026-02-09 - Phase 5 Cleanup (src/ Reorganization)

- **UI artifacts moved out of src**: `ChatWindow.jsx` → `frontend/components/`, `dashboard.html` (NeuralCursor context dashboard) → `frontend/public/context-dashboard.html`. Removed `src/components/` and `src/context_dashboard/`.
- **Removed src/mdrag/**: Documentation-only folder deleted; content duplicated in `src/AGENTS.md` and sub-AGENTS.md.
- **Deleted duplicate legacy code**: Under redirect packages, removed duplicate files; kept only `__init__.py` stubs. Removed: `src/ingestion/` (docling, jobs, sources, embedder, ingest, models, protocols, storage, validation), `src/query/service.py`, `src/retrieval/` (embeddings, formatting, vector_store), `src/memory_gateway/` (gateway, models), `src/memgpt_integration/` (context_manager, tools, wrapper). Canonical code remains in `capabilities/` and `integrations/`.
- **Canonical import fix**: `capabilities/ingestion/embedder.py` now imports from `mdrag.capabilities.ingestion.docling.chunker` instead of `mdrag.ingestion.docling.chunker` for internal use.
- **workflows/rag restored**: Added `workflows/__init__.py`, `workflows/rag/__init__.py`, `workflows/rag/dependencies.py` (AgentDependencies) so `mdrag.dependencies` re-export works.
- **Docs**: `NEURALCURSOR_README.md` updated to reference `frontend/public/context-dashboard.html`; root `AGENTS.md` reference to `src/mdrag/integrations/models.py` → `src/integrations/models.py`.

### 2026-02-09 - Sample Script Fixes

- **Namespace validation**: Fixed `ValidationError` in `chunk_pydantic_sample`, `docling_ingest`, and upload flow. `UploadCollector` and `DoclingProcessor` now convert namespace via `model_dump()` / `_to_namespace()` to avoid cross-module Pydantic type mismatch.
- **darwinxml_demo**: Fixed `ColoredLogger.info()` duplicate `message` kwarg; added required `document_uid` to `MetadataPassport`; changed `document_id` → `document_uid` for `wrap_chunk()`; fixed `GraphTriple` access (use `.subject` / `.predicate` / `.object` instead of dict subscript).
- **Samples verified**: `chunk_pydantic_sample`, `darwinxml_demo`, `youtube/extract_video`, `searxng/query_searxng` run successfully. MongoDB samples require running MongoDB; RAG/wiki/readings require MongoDB + Redis + API keys.

### 2026-02-09 - src/ Folder Reorganization (Layered Architecture)

- **Phase 1 (Core)**: `core/` (exceptions, logging, telemetry, validation), `config/` (settings, validate_config). `MDRAGException` base; `ValidationError` subclasses it; `ConfigError` in config.
- **Phase 2 (Protocols)**: `integrations/mongodb/adapters/storage.py` with `MongoStorageAdapter`; `ingestion/storage.py` re-exports for backward compat.
- **Phase 3 (Capabilities)**: `capabilities/ingestion`, `capabilities/retrieval`, `capabilities/query`, `capabilities/memory`; `integrations/llm`, `integrations/memgpt`. Exception modules in each capability.
- **Phase 4 (Workflows)**: `workflows/rag/dependencies.py` (`AgentDependencies`); `interfaces/api/` (server moved); `workflows/rag/wiki/readings` exception modules.
- **Backward compat**: `mdrag.settings`, `mdrag.validation`, `mdrag.ingestion`, `mdrag.retrieval`, `mdrag.query`, `mdrag.dependencies`, `mdrag.server` re-export from new paths.
- **Entry point**: `uv run python -m mdrag.validate_config` for config validation.

### 2026-02-09 - vLLM Auto-Start with Docker Compose

- **Default integration**: Modified `docker-compose.yml` to include vLLM services via `include` directive
- **Services included**: `vllm-glm` (GLM-4.7-Flash-AWQ-4bit quantized model) and `litellm` proxy
- **Network integration**: Connected vLLM services to `rag_network` for communication with RAG agent
- **Command**: `docker compose up -d` now starts all services including vLLM on dual GPUs (2x RTX 3090)
- **Ports**: vLLM on `11435`, LiteLLM proxy on `4000`
- **Configuration**: Uses `docker-compose.vllm.yml` + `docker-compose.vllm.48gb.yml` for 48GB VRAM setup with compressed-tensors quantization
- **GPU support**: Verified NVIDIA Container Toolkit v1.18.1 with Docker GPU access

### 2026-02-08 - RQ Worker Validation in Ingestion Pipeline

- Added `validate_rq_workers(redis_url, queue_name="default")` to `mdrag.validation` — ensures at least one RQ worker is listening to the ingestion queue
- `validate_ingestion()` and `validate_readings()` now require workers when `require_redis=True` (crawl_and_save, ReadingsService, API ingest endpoints)
- Jobs enqueued without workers would never process; validation fails fast with setup instructions: `uv run rq worker default --url redis://localhost:6379/0`
- Updated [docs/design-patterns/ingestion-validation.md](design-patterns/ingestion-validation.md), `src/server/AGENTS.md`, `src/ingestion/AGENTS.md`

### 2026-02-08 - Ingestion Pipeline Validation

- **Core validation**: Added `validate_embedding_api`, `validate_playwright`, `validate_google_credentials`, `validate_youtube_deps`, `validate_searxng`, `validate_llm_api` to `mdrag.validation`
- **Pipeline-attached validation**: New `src/ingestion/validation.py` with `validate_ingestion()` and `validate_readings()`; collector-specific checks (Crawl4AI: Playwright; gdrive: credentials; upload: none)
- **Entry points**: Validation runs in `IngestionWorkflow.ingest_collector()`, ingest CLI `main()`, `IngestionService.run_job()`, `ReadingsService.save_reading()`
- **ReadingsService**: Validates MongoDB, Redis, LLM API, plus Playwright/SearXNG (web) or yt-dlp/youtube-transcript-api (YouTube) per URL type
- **Design docs**: Captured in [docs/design-patterns/ingestion-validation.md](design-patterns/ingestion-validation.md); `src/ingestion/AGENTS.md` (Pre-Ingest Validation)

**Retrospective**:
- Validation should be attached to pipeline entry points; core checks run for all, collector-specific checks run only when that collector is used.
- Use Settings for all config (redis_url, searxng_url); never hardcode connection strings in validation.

### 2026-02-08 - Redis Validation in test_config

- Added `validate_redis(redis_url)` to `mdrag.validation` for Redis connection checks
- `uv run python -m mdrag.test_config` now validates Redis (step 4/6) alongside MongoDB
- Required for ingestion job queue (crawl_and_save, API ingest endpoints)
- crawl_and_save and save_url already had Redis in pre-flight; test_config now catches Redis issues before running samples

### 2026-02-08 - LLM Temperature: Provider-Based Design (No Workflow Testing)

- **Design**: Temperature is a provider capability, not a workflow concern. Workflow code no longer tests or branches on temperature.
- **LLMCompletionClient**: Injected via `AgentDependencies.llm_client`; builds completion kwargs internally. OpenRouter → omit temperature; Ollama/vLLM → include when `llm_temperature` is set.
- **get_llm_init_kwargs**: New helper in `mdrag.llm.completion_client` for LangChain ChatOpenAI and vLLM. Use `provider_supports_temperature=True` for vLLM (always supports it).
- **Migrated**: wiki, readings, query services → `deps.llm_client.create()`; librarian agent, distiller, self_corrective_rag, vllm_client → `get_llm_init_kwargs()`.
- **Removed**: `llm_temperature_kwargs` from `src/settings.py`; all workflow branching on temperature.

### 2026-02-08 - setup/setup_mongodb_tables.py

- Added `setup/setup_mongodb_tables.py` for idempotent MongoDB collection creation
- Creates documents, chunks, traces, feedback only if missing; uses Settings
- Invokes `server/maintenance/init_indexes.py` for vector/text indexes
- Usage: `uv run python setup/setup_mongodb_tables.py`

### 2026-02-08 - chat_wiki & Sample Pre-Flight Fixes

- **urlparse**: Fixed `AttributeError: module 'urllib' has no attribute 'urlparse'`—use `from urllib.parse import urlparse`; `__import__("urllib.parse")` returns top-level `urllib`, not `urllib.parse`
- **Async subprocess**: `subprocess.run` blocks event loop; wrapped `_try_initiate_replica_set` and `_try_start_mongodb` in `asyncio.to_thread()` to avoid blocking
- **directConnection**: Skip `readPreference=primaryPreferred` when URI has `directConnection=true`; RSGhost nodes block with that
- **Sample pre-flight**: Now correctly calls rs.initiate on first NotPrimaryOrSecondary (was missing in inner except)

**Retrospective**:
- In async code, never call blocking sync functions (subprocess.run, etc.) directly; use `asyncio.to_thread()`.
- `__import__("urllib.parse")` returns the top-level package, not the submodule—use explicit imports.

### 2026-02-08 - Retrospective: Config Over Hardcoding

- **Lesson**: Pull connection details (URI, ports, hosts) from Settings or a config class. Avoid hardcoding; parse URIs when needed.
- **Lesson**: When logic depends on project-specific values (e.g. Docker port), add config fields (e.g. `mongodb_docker_port`) instead of hardcoding.

### 2026-02-08 - Sample Pre-Flight: Auto-Start MongoDB, Auto-Schema, Replica Set Init

- **sample/utils/check_mongodb** now triggers corrective actions when validation fails:
  - **Auto-start**: If connection fails and URI uses localhost:7017, runs `docker compose up -d atlas-local` and retries after 30s
  - **Auto-schema**: If connected but collections/indexes missing, creates documents/chunks collections and runs `init_indexes.py`
  - **Replica set init**: On NotPrimaryOrSecondary (13436), runs `rs.initiate()` on the MongoDB container and retries
- Added `readPreference=primaryPreferred` to connection URI for replica set compatibility
- Retry (3 attempts, 2–5s backoff) for ConnectionFailure, ServerSelectionTimeoutError, NotPrimaryOrSecondary
- Error hint for NotPrimaryOrSecondary: "For this project's Docker MongoDB, use MONGODB_URI with localhost:7017"
- **Note**: If using a different MongoDB (e.g. localhost:27017 from another compose), ensure replica set is initialized and healthy
- **Config**: Added `mongodb_docker_port` (default 7017) to Settings; sample pre-flight uses it instead of hardcoded ports. URI host/port parsed from `settings.mongodb_uri`.

### 2026-02-08 - Retrospective: Dependency Fix Validation

- **Lesson**: Before applying error-message suggestions (e.g. env bypasses), check official docs. Prefer fixing root cause (version alignment) when possible.
- **Lesson**: Before version pinning to fix mismatch, verify pip dependency tree allows it—run `pip install <pkg>==X.X` or `pip check`; upstream strict deps may block downgrade.

### 2026-02-09 - vLLM FlashInfer Version Mismatch

- Fixed vLLM startup failure: `flashinfer-cubin (0.6.1) does not match flashinfer (0.6.3)`
- **Approach**: `FLASHINFER_DISABLE_VERSION_CHECK=1` in `docker-compose.vllm.yml` (env var suggested by error message)
- **Deprecated**: Version pinning (`flashinfer-python==0.6.2 flashinfer-cubin==0.6.2`)—vLLM nightly strictly requires flashinfer 0.6.3, and flashinfer-cubin 0.6.3 is not on PyPI yet; pin causes dependency conflict

**Retrospective**:
- When upstream (vLLM) pins a newer version than a sub-package (flashinfer-cubin) has released, env bypass may be the only viable fix until the ecosystem catches up.

### 2026-02-08 - DeepWiki Frontend Documentation

- Documented DeepWiki frontend (Knowledge Wiki, Web Crawler, Save & Research, Readings) in docs/deepwiki-frontend.md
- Updated root AGENTS.md with frontend in Component Organization, Repository Map, Core Commands, Docker ports, and JIT Index
- Updated frontend/AGENTS.md with cross-reference to docs and package name note
- Updated [docs/design-patterns/docker-compose.md](design-patterns/docker-compose.md) with frontend port 3000

### 2026-02-08 - MongoDB Startup Validation

- Added `mdrag.validation` module with `validate_mongodb(settings, strict=True|False)` and `ValidationError`
- `strict=True`: requires connection + collections + indexes (CLI, server, samples)
- `strict=False`: requires connection only (ingestion, test_config)
- Extended `AgentDependencies.initialize()` to call `validate_mongodb(strict=True)` before client creation
- Added pre-flight validation to ingestion CLI (`validate_mongodb(strict=False)`)
- Enhanced `test_config` with async MongoDB connection validation (step 3/5)
- Sample scripts now exit with code 1 (not 0) when pre-flight checks fail
- Error messages include setup instructions for connection and schema issues

**Retrospective**:
- When `strict=False`, return immediately after ping—`list_collection_names` can fail with "node is not in primary or recovering state" on replica sets, even when ping succeeds.
- Pre-flight failures must use `sys.exit(1)`; returning without exit code masks failures in CI and scripts.

### 2026-02-09 - vLLM Port Change (Ollama + 1)

- Changed vLLM host port from 8000 to **11435** (Ollama 11434 + 1, from local-ai-packaged)
- Resolves port conflict with rag-agent and other services on 8000
- Updated: `docker-compose.vllm.yml`, `run_claude_local.sh`, `scripts/test_vllm_prompt.sh`
- Added `VLLM_PORT=11435` to `.env` and `.env.example`
- Updated AGENTS.md, docs (vllm-claude-cli-setup, vllm-editor-config, vllm-editor-quickstart)
- Updated `.cursor/rules/claude-cli-delegate.mdc`

<!-- Add new entries here -->
