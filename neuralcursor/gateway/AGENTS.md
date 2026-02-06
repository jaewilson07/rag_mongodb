# FastAPI Gateway - Unified Memory API

## Overview

The gateway module provides a FastAPI server that serves as the unified entry point for all memory operations. It exposes REST APIs for creating nodes, querying the graph, managing sessions, and monitoring system health.

## Architecture

```
gateway/
├── __init__.py
├── server.py           # FastAPI application with endpoints
├── models.py           # Request/Response Pydantic models
└── dependencies.py     # Dependency injection for clients
```

## Purpose

- **Single Entry Point**: All memory operations go through one API
- **Unified State**: Ensures MemGPT and MCP share data state
- **Health Monitoring**: Centralized health checks
- **REST Interface**: Standard HTTP/JSON API

## Server Configuration

```bash
NEURALCURSOR_NEO4J_URI=bolt://localhost:7687
NEURALCURSOR_MONGODB_URI=mongodb://localhost:27017
```

### Startup

```python
from neuralcursor.gateway.server import app

# Using uvicorn
import uvicorn

uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000,
    log_level="info"
)
```

See [server.py](./server.py) for full implementation.

## Available Endpoints

### Health Check

**GET `/health`**

Returns system health status.

**Response:**
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "mongodb_connected": true,
  "timestamp": "2024-02-06T10:30:00Z",
  "details": {
    "neo4j_uri": "bolt://localhost:7687",
    "mongodb_database": "neuralcursor"
  }
}
```

### Node Operations

**POST `/graph/nodes`**

Create a new node in Neo4j.

**Request:**
```json
{
  "node_type": "Decision",
  "name": "Use JWT Authentication",
  "description": "Decision to implement JWT-based auth",
  "properties": {
    "context": "Need secure API authentication",
    "decision": "Implement JWT with refresh tokens",
    "rationale": "Industry standard, scalable",
    "alternatives": ["Session-based", "OAuth2"]
  }
}
```

**Response:**
```json
{
  "uid": "abc123def456",
  "node_type": "Decision",
  "name": "Use JWT Authentication",
  "description": "Decision to implement JWT-based auth",
  "properties": {...}
}
```

**GET `/graph/nodes/{uid}`**

Retrieve a node by UID.

**Response:**
```json
{
  "uid": "abc123def456",
  "node_type": "Decision",
  "name": "Use JWT Authentication",
  "properties": {...}
}
```

### Relationship Operations

**POST `/graph/relationships`**

Create a relationship between nodes.

**Request:**
```json
{
  "from_uid": "decision_uid",
  "to_uid": "requirement_uid",
  "relation_type": "IMPLEMENTS",
  "weight": 1.0,
  "properties": {}
}
```

**Response:**
```json
{
  "success": true,
  "from_uid": "decision_uid",
  "to_uid": "requirement_uid",
  "relation_type": "IMPLEMENTS"
}
```

### Query Operations

**POST `/graph/query`**

Execute a Cypher query.

**Request:**
```json
{
  "cypher": "MATCH (d:Decision) WHERE d.status = $status RETURN d LIMIT 10",
  "parameters": {
    "status": "active"
  }
}
```

**Response:**
```json
{
  "results": [...],
  "count": 10,
  "query_time_ms": 125.5
}
```

**POST `/graph/path`**

Find path between two nodes.

**Request:**
```json
{
  "from_uid": "code_entity_uid",
  "to_uid": "requirement_uid",
  "max_depth": 5,
  "relation_types": ["IMPLEMENTS", "DEPENDS_ON"]
}
```

**Response:**
```json
{
  "paths": [
    {
      "nodes": [...],
      "relationships": [...]
    }
  ],
  "count": 1,
  "mermaid_diagram": "graph TD\n..."
}
```

### Schema Information

**GET `/graph/schema`**

Get schema validation info.

**Response:**
```json
{
  "constraints": 9,
  "indexes": 10,
  "node_counts": {
    "Project": 5,
    "Decision": 23,
    "CodeEntity": 150
  },
  "total_nodes": 178,
  "total_relationships": 245,
  "schema_valid": true
}
```

### Memory Operations

**POST `/memory/chat`**

Save a chat message.

**Request:**
```json
{
  "session_id": "session_123",
  "role": "user",
  "content": "How do we implement JWT?",
  "metadata": {
    "topic": "authentication"
  }
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "session_123",
  "message_role": "user"
}
```

**GET `/memory/sessions/{session_id}`**

Get a conversation session.

**Response:**
```json
{
  "session_id": "session_123",
  "project_context": "auth_service",
  "messages": [...],
  "started_at": "2024-02-06T10:00:00Z",
  "last_activity": "2024-02-06T10:30:00Z",
  "metadata": {}
}
```

**GET `/memory/sessions`**

Get recent sessions.

**Query Parameters:**
- `limit`: Max sessions (default: 10)
- `project_context`: Filter by project

**Response:**
```json
{
  "sessions": [...],
  "count": 5
}
```

## Dependency Injection

The gateway uses FastAPI's dependency injection:

```python
from fastapi import Depends
from neuralcursor.gateway.dependencies import get_gateway_deps, GatewayDependencies

@app.get("/some-endpoint")
async def endpoint(deps: GatewayDependencies = Depends(get_gateway_deps)):
    # Use deps.neo4j and deps.mongodb
    result = await deps.neo4j.query(cypher)
    return result
```

See [dependencies.py](./dependencies.py) for implementation.

## Design Patterns

### Pattern 1: Lifespan Management

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    await init_clients()
    logger.info("gateway_started")
    
    yield
    
    # Shutdown
    await close_clients()
    logger.info("gateway_stopped")

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: Error Handling

```python
from fastapi import HTTPException

@app.post("/graph/nodes")
async def create_node(request: CreateNodeRequest, neo4j = Depends(get_neo4j_client)):
    try:
        node = create_node_from_request(request)
        uid = await neo4j.create_node(node)
        return NodeResponse(uid=uid, ...)
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("node_creation_failed")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Pattern 3: Response Models

```python
from pydantic import BaseModel
from datetime import datetime

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    neo4j_connected: bool
    mongodb_connected: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: dict[str, Any] = Field(default_factory=dict)

@app.get("/health", response_model=HealthResponse)
async def health_check(deps = Depends(get_gateway_deps)) -> HealthResponse:
    # FastAPI automatically validates and serializes
    return HealthResponse(
        status="healthy",
        neo4j_connected=True,
        mongodb_connected=True
    )
```

## CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## API Documentation

FastAPI automatically generates interactive docs:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Testing

### Unit Tests

```python
import pytest
from fastapi.testclient import TestClient
from neuralcursor.gateway.server import app

client = TestClient(app)

def test_health_endpoint():
    """Test health check."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "neo4j_connected" in data

def test_create_node():
    """Test node creation."""
    response = client.post("/graph/nodes", json={
        "node_type": "Project",
        "name": "Test Project",
        "description": "A test project",
        "properties": {"status": "active"}
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "uid" in data
    assert data["name"] == "Test Project"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_workflow(test_client):
    """Test complete workflow."""
    # Create project
    project_response = test_client.post("/graph/nodes", json={
        "node_type": "Project",
        "name": "Auth System",
        "properties": {"status": "active"}
    })
    project_uid = project_response.json()["uid"]
    
    # Create decision
    decision_response = test_client.post("/graph/nodes", json={
        "node_type": "Decision",
        "name": "Use JWT",
        "properties": {
            "context": "Need auth",
            "decision": "Use JWT"
        }
    })
    decision_uid = decision_response.json()["uid"]
    
    # Create relationship
    rel_response = test_client.post("/graph/relationships", json={
        "from_uid": project_uid,
        "to_uid": decision_uid,
        "relation_type": "CONTAINS"
    })
    
    assert rel_response.status_code == 200
    
    # Query to verify
    query_response = test_client.post("/graph/query", json={
        "cypher": "MATCH (p:Project {uid: $uid})-[:CONTAINS]->(d:Decision) RETURN d",
        "parameters": {"uid": project_uid}
    })
    
    assert query_response.json()["count"] == 1
```

## Performance Considerations

### Connection Pooling

Both clients maintain connection pools:

```python
# Neo4j
Neo4jConfig(max_connection_pool_size=50)

# MongoDB (Motor)
AsyncIOMotorClient(maxPoolSize=50)
```

### Response Streaming

For large result sets:

```python
from fastapi.responses import StreamingResponse

@app.get("/graph/nodes/stream")
async def stream_nodes():
    async def generate():
        async for node in neo4j.stream_query("MATCH (n) RETURN n"):
            yield json.dumps(node) + "\n"
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")
```

### Caching

Consider adding response caching:

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="neuralcursor:")

@app.get("/graph/schema")
@cache(expire=300)  # Cache for 5 minutes
async def get_schema():
    return await neo4j.get_schema_info()
```

## Security

### Authentication

Add authentication for production:

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security

security = HTTPBearer()

@app.get("/graph/nodes/{uid}")
async def get_node(
    uid: str,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    # Verify token
    token = credentials.credentials
    # ... authentication logic ...
    
    return await get_node_internal(uid)
```

### Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@app.get("/graph/nodes")
@limiter.limit("100/minute")
async def list_nodes(request: Request):
    # ... endpoint logic ...
    pass
```

## Monitoring

### Prometheus Metrics

```python
from prometheus_fastapi_instrumentator import Instrumentator

# Add metrics endpoint
Instrumentator().instrument(app).expose(app)

# Access metrics at /metrics
```

### Logging

```python
import logging
from neuralcursor.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

@app.post("/graph/nodes")
async def create_node(request):
    logger.info("node_creation_requested", extra={
        "node_type": request.node_type,
        "name": request.name
    })
    
    # ... create node ...
    
    logger.info("node_created", extra={"uid": uid})
```

## Troubleshooting

### Server Won't Start

```bash
# Check port availability
lsof -i :8000

# Check database connections
curl http://localhost:8000/health

# View logs
tail -f logs/gateway.log
```

### Slow Responses

```python
# Add query timing
import time

@app.post("/graph/query")
async def query_graph(request):
    start = time.time()
    result = await neo4j.query(request.cypher, request.parameters)
    query_time = (time.time() - start) * 1000
    
    logger.info("query_executed", extra={
        "query_time_ms": query_time,
        "result_count": len(result)
    })
    
    return {"results": result, "query_time_ms": query_time}
```

## Related Documentation

- [server.py](./server.py) - Full FastAPI server implementation
- [models.py](./models.py) - Request/Response models
- [dependencies.py](./dependencies.py) - Dependency injection
- [../brain/AGENTS.md](../brain/AGENTS.md) - Memory layer details
- [../AGENTS.md](../AGENTS.md) - Root documentation
