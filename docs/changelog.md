# MongoDB RAG Agent Changelog

> Session updates. Newest entries at the top.

---

## Recent Updates

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
