# Sample Scripts - Agent Guide

## Purpose
Curated sample and validation scripts grouped by domain.

## Layout
- sample/rag/ - end-to-end and conversational agent checks
- sample/retrieval/ - search and pipeline validation
- sample/ingestion/ - ingestion-related validation utilities
- sample/mongodb/ - cluster and index inspection
- sample/eval/ - gold dataset evaluation

## Run Examples
- uv run python sample/rag/comprehensive_e2e_test.py
- uv run python sample/retrieval/test_search.py
- uv run python sample/ingestion/validate_source_urls.py
- uv run python sample/mongodb/check_indexes.py
- uv run python sample/eval/run_gold_eval.py

## Notes
- These scripts require a configured .env and MongoDB with indexes.
- They are not part of pytest or CI.

---

## Known Patterns & Gotchas

### MongoDB Configuration

**Multiple MongoDB Instances**
- This project's `docker-compose.yml` runs `ragagent-atlas-local-1` on port **7017** (mapped from 27017)
- The adjacent `local-ai-packaged` project runs `mongodb` on port **27017** (direct mapping)
- **Rule**: Always verify which MongoDB instance you're connecting to. Check `docker ps` and match credentials.
- **Credentials**: 
  - `ragagent-atlas-local-1`: `admin:admin123`
  - `local-ai-packaged/mongodb`: `admin:goose-night-bad-slow` (check .env in that project)

**Replica Set Configuration After Restart**
- MongoDB Atlas Local requires replica set mode for vector search
- After container restarts, replica set member hostname can become invalid (e.g., `localhost:27017` instead of `mongodb:27017`)
- **Error**: `MongoServerError: Our replica set config is invalid or we are not a member of it`
- **Fix**: Reconfigure with correct hostname:
  ```bash
  docker exec <container> mongosh -u admin -p <password> --authenticationDatabase admin \
    --eval "var cfg = rs.conf(); cfg.members[0].host = '<container-name>:27017'; rs.reconfig(cfg, {force: true})"
  ```
- **Wait**: Give replica set 5-10 seconds to stabilize after reconfig before running queries

**Vector Search Index Creation**
- Requires `mongot` (Atlas Search service) to be running inside the MongoDB container
- `mongodb/mongodb-atlas-local` image includes mongot but it must be started by entrypoint
- **Error**: `Error connecting to Search Index Management service` (code 125) means mongot isn't running
- **Check**: `docker inspect <container> | grep mongot` should show `mongotHost: localhost:27027`
- **Collections**: `documents` and `chunks` are created automatically on first insert
- **Indexes**: Must be created programmatically or via Atlas UI (cannot use `collection.create_index()` for vector search)

### Build System

**Python Cache Directories in Package**
- setuptools will try to package `__pycache__` directories if they contain unexpected subdirectories (e.g., `_ARCHIVE`)
- **Error**: `error: package directory 'src/__pycache__/_ARCHIVE' does not exist`
- **Prevention**: 
  1. Add exclusions to `pyproject.toml`: `exclude = ["*.egg-info", "__pycache__", "*/__pycache__"]`
  2. Create `MANIFEST.in` with `global-exclude __pycache__`
  3. Clean stale egg-info: `rm -rf src/*.egg-info`

### Async/Await Patterns

**Motor Collection Methods**
- Motor (async PyMongo) returns coroutines that MUST be awaited
- **Wrong**: `indexes = collection.list_indexes().to_list(length=None)` (missing await)
- **Correct**: `indexes = await collection.list_indexes().to_list(length=None)`
- **Error**: `'coroutine' object has no attribute 'to_list'` or `coroutine was never awaited`

### Pre-flight Check Implementation

**Collection vs Index Checking**
- Don't check if collections exist before running index operations
- Collections are created automatically on first document insert in MongoDB
- **Rule**: Check if index exists, not if collection exists. Index check will fail gracefully if collection doesn't exist.

### Port Mapping Confusion

**Docker Port Notation**
- Format: `<host>:<container>`
- `7017:27017` means host port 7017 maps to container port 27017
- **Rule**: Always use the LEFT port number (host port) when connecting from host machine
- MongoDB driver connects to `localhost:<HOST_PORT>`, not container port
