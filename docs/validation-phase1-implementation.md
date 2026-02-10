# Phase 1 Validation Implementation

**Date:** February 9, 2026  
**Status:** ✅ Complete

## Overview

Implemented critical pre-flight validation checks to improve application consistency and fail-fast behavior when core services are unavailable.

## What Was Added

### 1. Neo4j Validation ✅

**Critical Gap:** Background services (file watcher, librarian, MCP server) crashed on first Neo4j operation if database unavailable.

**Implementation:**
- **Core:** `validate_neo4j(uri, username, password, database)` in [src/validation.py](../src/validation.py)
- **Sample:** `check_neo4j(uri, username, password, database)` in [sample/utils/__init__.py](../sample/utils/__init__.py)

**Validates:**
- Neo4j package installed
- Connection reachable
- Database accessible
- Authentication successful

**Usage:**
```python
from mdrag.validation import validate_neo4j, ValidationError

try:
    validate_neo4j(
        neo4j_uri="bolt://localhost:7687",
        username="neo4j",
        password="password",
        database="neuralcursor",
    )
except ValidationError as e:
    logger.error(f"Neo4j unavailable: {e}")
    sys.exit(1)
```

**Updated Services:**
- [scripts/start_file_watcher.py](../scripts/start_file_watcher.py) - Validates before watching files
- [scripts/start_librarian.py](../scripts/start_librarian.py) - Validates MongoDB + Neo4j
- [scripts/start_mcp_server.py](../scripts/start_mcp_server.py) - Validates before starting MCP
- [neuralcursor/gateway/server.py](../neuralcursor/gateway/server.py) - Validates in lifespan

### 2. vLLM Validation ✅

**Gap:** NeuralCursor gateway started but failed on first request when vLLM services unavailable.

**Implementation:**
- **Core:** `validate_vllm(reasoning_url, embedding_url, api_key)` in [src/validation.py](../src/validation.py)
- **Sample:** `check_vllm(reasoning_url, embedding_url, api_key)` in [sample/utils/__init__.py](../sample/utils/__init__.py)

**Validates:**
- Reasoning endpoint (`/health`) reachable
- Embedding endpoint (`/health`) reachable
- Optional API key authentication

**Usage:**
```python
from mdrag.validation import validate_vllm, ValidationError

if settings.vllm_enabled:
    try:
        validate_vllm(
            reasoning_url="http://localhost:8000",
            embedding_url="http://localhost:8001",
        )
    except ValidationError as e:
        logger.error(f"vLLM services unavailable: {e}")
        sys.exit(1)
```

**Conditional:** Only runs when `settings.vllm_enabled=True`

**Updated Services:**
- [src/server/main.py](../src/server/main.py) - Validates vLLM when `vllm_enabled=True`
- [neuralcursor/gateway/server.py](../neuralcursor/gateway/server.py) - Validates vLLM endpoints (soft-fail, logs warning)

**Implementation:**
- **Core:** `validate_vllm(reasoning_url, embedding_url, api_key)` in [src/validation.py](../src/validation.py)
- **Sample:** `check_vllm(reasoning_url, embedding_url, api_key)` in [sample/utils/__init__.py](../sample/utils/__init__.py)

**Validates:**
- Reasoning endpoint (`/health`) reachable
- Embedding endpoint (`/health`) reachable
- Optional API key authentication

**Usage:**
```python
from mdrag.validation import validate_vllm, ValidationError

if settings.vllm_enabled:
    try:
        validate_vllm(
            reasoning_url="http://localhost:8000",
            embedding_url="http://localhost:8001",
        )
    except ValidationError as e:
        logger.error(f"vLLM services unavailable: {e}")
        sys.exit(1)
```

**Conditional:** Only runs when `settings.vllm_enabled=True`

### 3. RQ Workers at FastAPI Startup ✅

**Gap:** FastAPI accepted queue-based ingestion/readings requests even when no workers running.

**Implementation:**
- Added `validate_rq_workers()` call to [src/server/main.py](../src/server/main.py) lifespan
- Validates that at least one RQ worker is listening to `default` queue before accepting requests

**Before:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    deps = AgentDependencies()
    await deps.initialize()
    await deps.cleanup()
    yield
```

**After:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    deps = AgentDependencies()
    await deps.initialize()
    
    # Validate RQ workers for queue-based endpoints
    settings = load_settings()
    redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
    validate_rq_workers(redis_url, queue_name="default")
    
    await deps.cleanup()
    yield
```

**Impact:**
- FastAPI won't start if no workers available
- Prevents jobs queuing indefinitely
- Clear error message with setup instructions

## Testing

Run the test script to verify all validations:

```bash
uv run python temp/test_new_validations.py
```

**Expected Output:**
```
============================================================
CORE VALIDATION TESTS (src/validation.py)
============================================================

1. Neo4j Validation
----------------------------------------------------------------------
✓ Neo4j validation PASSED

2. vLLM Validation
----------------------------------------------------------------------
⊘ vLLM disabled (vllm_enabled=False), skipping validation

3. RQ Workers Validation
----------------------------------------------------------------------
❌ RQ workers validation FAILED:
RQ worker validation failed
  Workers listening to 'default': 0
  Setup: Start an ingestion worker in a separate terminal:
    uv run rq worker default --url redis://localhost:6379/0
  Jobs will queue but never process until a worker is running.


============================================================
SAMPLE PRE-FLIGHT CHECKS (sample/utils/__init__.py)
============================================================
✓ Neo4j: Neo4j connection successful (database: neuralcursor)
❌ RQ Workers: No RQ workers listening to 'default' queue
   Hint: Start a worker: uv run rq worker default --url redis://localhost:6379/0
```

## Service Startup Examples

### File Watcher (with Neo4j validation)

```bash
$ python scripts/start_file_watcher.py

============================================================
NeuralCursor File Watcher
============================================================
✓ Settings loaded
✓ Neo4j validation passed
✓ Memory gateway initialized
============================================================
Watching for file changes...
Press Ctrl+C to stop
============================================================
```

**On failure:**
```bash
$ python scripts/start_file_watcher.py

Neo4j validation failed:
  Connection: FAILED
  Error: Failed to establish connection ...
  Setup: Ensure Neo4j is running at bolt://localhost:7687
  Docker: docker compose up -d neo4j
```

### FastAPI Server (with RQ worker validation)

```bash
$ uv run uvicorn mdrag.interfaces.api.main:app

# Without workers running:
ERROR: RQ worker validation failed
  Workers listening to 'default': 0
  Setup: Start an ingestion worker in a separate terminal:
    uv run rq worker default --url redis://localhost:6379/0
  Jobs will queue but never process until a worker is running.
```

**Fix:**
```bash
# Terminal 1: Start RQ worker
uv run rq worker default --url redis://localhost:6379/0

# Terminal 2: Start FastAPI (now succeeds)
uv run uvicorn mdrag.interfaces.api.main:app
INFO: ✓ MongoDB validation passed
INFO: ✓ RQ workers validation passed (1 worker on 'default' queue)
INFO: Application startup complete
```

## Updated Files

### Core Validation
- [src/validation.py](../src/validation.py)
  - Added `validate_neo4j()`
  - Added `validate_vllm()`

### Sample Utilities
- [sample/utils/__init__.py](../sample/utils/__init__.py)
  - Added `check_neo4j()`
  - Added `check_vllm()`
  - Already had `check_rq_workers()` (added earlier)

### FastAPI
- [src/server/main.py](../src/server/main.py)
  - Added RQ worker validation in lifespan
  - Added conditional vLLM validation when `vllm_enabled=True`

### Background Services
- [scripts/start_file_watcher.py](../scripts/start_file_watcher.py)
- [scripts/start_librarian.py](../scripts/start_librarian.py)
- [scripts/start_mcp_server.py](../scripts/start_mcp_server.py)
- [neuralcursor/gateway/server.py](../neuralcursor/gateway/server.py)
  - Added vLLM validation with soft-fail (logs warning, continues startup)

## Next Steps (Phase 2)

From the original analysis, remaining gaps include:

1. **Enhanced MongoDB Validation** - Verify index structure (dimension, field mapping)
2. **Endpoint-Specific Dependency Injection** - Per-route validation (e.g., `/ingest/web` → Playwright)
3. **MemGPT/Letta Validation** - Check package installed before use
4. **Background Service Health Monitoring** - Health check endpoints
5. **Docker Healthchecks** - Add healthchecks for Neo4j, Redis, SearXNG

## Summary

**Before:**
- Background services crashed with cryptic errors when Neo4j unavailable
- FastAPI accepted jobs even when no workers to process them
- vLLM failures discovered only at request time

**After:**
- ✅ All services validate dependencies at startup
- ✅ Clear error messages with setup instructions
- ✅ Fail-fast behavior prevents silent failures
- ✅ Consistent validation pattern across services

**Impact:**
- Faster debugging (errors at startup, not runtime)
- Better developer experience (clear setup instructions)
- Production readiness (services won't start in broken state)
