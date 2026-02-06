# Model Context Protocol (MCP) Server

## Overview

The MCP module implements a WebSocket server that exposes NeuralCursor's memory tools to Cursor IDE via the Model Context Protocol. This enables seamless integration where Cursor can query the Second Brain as part of its normal operation.

## Architecture

```
mcp/
├── __init__.py
├── server.py       # WebSocket MCP server
└── tools.py        # Tool implementations
```

## MCP Server

### Purpose

Provides a WebSocket endpoint that Cursor connects to for accessing Second Brain functionality.

### Initialization

```python
from neuralcursor.mcp.server import MCPServer

server = MCPServer()
await server.start()  # Runs on ws://localhost:8765
```

### Configuration

```bash
NEURALCURSOR_MCP_ENABLED=true
NEURALCURSOR_MCP_HOST=localhost
NEURALCURSOR_MCP_PORT=8765
```

### Message Format

**Request:**
```json
{
  "tool": "query_architectural_graph",
  "params": {
    "query": "JWT authentication",
    "node_types": ["Decision", "Requirement"],
    "max_results": 10
  }
}
```

**Response:**
```json
{
  "tool": "query_architectural_graph",
  "result": {
    "nodes": [...],
    "count": 5,
    "mermaid_diagram": "graph TD\n..."
  },
  "success": true
}
```

See [server.py](./server.py) for full implementation.

## Available Tools

### 1. query_architectural_graph

**Purpose**: Query the knowledge graph for architectural insights

**Parameters:**
- `query` (string): Search query
- `node_types` (optional list): Filter by node types
- `max_results` (int, default 10): Maximum results

**Returns:**
- `nodes`: List of matching nodes with relevance scores
- `count`: Number of results
- `mermaid_diagram`: Visual graph representation

**Example:**
```python
from neuralcursor.mcp.tools import MCPTools, QueryGraphRequest

request = QueryGraphRequest(
    query="authentication JWT decisions",
    node_types=["Decision", "Requirement"],
    max_results=10
)

result = await mcp_tools.query_architectural_graph(request)

for node in result['nodes']:
    print(f"[{node['type']}] {node['name']} (score: {node['relevance_score']:.2f})")
```

### 2. retrieve_past_decisions

**Purpose**: Get architectural decisions with full context

**Parameters:**
- `context` (string): Context or code area to search
- `limit` (int, default 5): Maximum decisions to return

**Returns:**
- `decisions`: List of decision nodes
- `count`: Number of decisions found

**Example:**
```python
from neuralcursor.mcp.tools import RetrieveDecisionsRequest

request = RetrieveDecisionsRequest(
    context="authentication library choice",
    limit=5
)

result = await mcp_tools.retrieve_past_decisions(request)

for decision in result['decisions']:
    print(f"Decision: {decision['decision']}")
    print(f"Context: {decision['context']}")
    print(f"Rationale: {decision['rationale']}")
    print(f"Consequences: {', '.join(decision['consequences'])}")
```

### 3. search_resources

**Purpose**: Search external resources (YouTube, articles, docs)

**Parameters:**
- `query` (string): Search query
- `resource_types` (optional list): Filter by type
- `limit` (int, default 10): Maximum resources

**Returns:**
- `resources`: List of external resources
- `count`: Number of resources found

**Example:**
```python
from neuralcursor.mcp.tools import SearchResourcesRequest

request = SearchResourcesRequest(
    query="React state management patterns",
    resource_types=["youtube", "article"],
    limit=10
)

result = await mcp_tools.search_resources(request)

for resource in result['resources']:
    print(f"[{resource['type']}] {resource['title']}")
    print(f"  URL: {resource['url']}")
    print(f"  Summary: {resource['summary']}")
```

### 4. find_relationships

**Purpose**: Find relationships for a code entity or file

**Parameters:**
- `file_path` (string): File path or entity name
- `relationship_types` (optional list): Filter relationship types
- `max_depth` (int, default 3): Maximum traversal depth

**Returns:**
- `relationships`: Graph of relationships
- `count`: Number of paths found
- `mermaid_diagram`: Visual relationship graph
- `source_uid`: Starting node UID

**Example:**
```python
from neuralcursor.mcp.tools import FindRelationshipsRequest

request = FindRelationshipsRequest(
    file_path="src/auth/AuthProvider.tsx",
    relationship_types=["DEPENDS_ON", "IMPLEMENTS"],
    max_depth=3
)

result = await mcp_tools.find_relationships(request)

print(result['mermaid_diagram'])
# Shows: AuthProvider -> useAuth -> LoginPage
#        AuthProvider -> Decision -> Requirement
```

### 5. get_active_context

**Purpose**: Get current active context from MemGPT

**Parameters:** None

**Returns:**
- `active_project`: Current project details
- `recent_nodes`: Recently accessed nodes
- `working_set_size`: Number of items in working set
- `context_usage`: Context window usage (0-1)

**Example:**
```python
# No parameters needed
result = await mcp_tools.tools.memgpt.get_active_context()

print(f"Active Project: {result['active_project']['name']}")
print(f"Working Set: {result['working_set_size']} items")
print(f"Context Usage: {result['context_usage']:.1%}")
```

## Cursor Integration

### Setup in Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "servers": {
    "neuralcursor": {
      "type": "websocket",
      "url": "ws://localhost:8765",
      "description": "NeuralCursor Second Brain"
    }
  }
}
```

### Usage in Cursor

Once configured, Cursor automatically discovers and uses the tools:

```
User: Why did we choose JWT for authentication?

Cursor: [Calls retrieve_past_decisions]

Based on the Second Brain, here's what I found:

The decision to use JWT was made on January 15, 2024 because:
1. Stateless authentication (no server-side sessions)
2. Scalable across multiple servers
3. Standard format with good library support

The jsonwebtoken npm package was selected for implementation.
```

See [../.cursorrules](../../.cursorrules) for full integration guide.

## Tool Implementation

### MCPTools Class

```python
from neuralcursor.mcp.tools import MCPTools
from neuralcursor.brain.neo4j.client import Neo4jClient
from neuralcursor.brain.mongodb.client import MongoDBClient
from neuralcursor.brain.memgpt.agent import MemGPTAgent

# Initialize
mcp_tools = MCPTools(
    neo4j_client=neo4j,
    mongodb_client=mongodb,
    memgpt_agent=memgpt
)

# Use tools
result = await mcp_tools.query_architectural_graph(request)
```

### Mermaid Diagram Generation

Tools automatically generate Mermaid diagrams:

```python
def _generate_mermaid(self, nodes: list[dict]) -> str:
    """Generate Mermaid diagram from nodes."""
    mermaid_lines = ["graph TD"]
    
    for node in nodes:
        uid = node['uid'][:8]
        name = node['name'][:30]
        node_type = node['type']
        
        # Style by type
        if node_type == "Decision":
            style = ":::decisionStyle"
        # ... etc
        
        mermaid_lines.append(f'    {uid}["{name}"] {style}')
    
    return "\n".join(mermaid_lines)
```

## Design Patterns

### Pattern 1: Tool Error Handling

```python
async def query_architectural_graph(self, request):
    """Query with graceful error handling."""
    try:
        results = await self.neo4j.query(cypher, params)
        return {
            "nodes": results,
            "count": len(results),
            "mermaid_diagram": self._generate_mermaid(results)
        }
    except Exception as e:
        logger.exception("mcp_query_failed", extra={"error": str(e)})
        return {
            "error": str(e),
            "nodes": [],
            "count": 0
        }
```

### Pattern 2: WebSocket Connection Management

```python
async def handle_connection(self, websocket):
    """Handle WebSocket connection lifecycle."""
    client_address = websocket.remote_address
    logger.info("mcp_client_connected", extra={"address": client_address})
    
    try:
        async for message in websocket:
            response = await self.handle_message(websocket, message)
            await websocket.send(json.dumps(response))
    
    except websockets.exceptions.ConnectionClosed:
        logger.info("mcp_client_disconnected", extra={"address": client_address})
    
    except Exception as e:
        logger.exception("mcp_connection_error", extra={"error": str(e)})
```

### Pattern 3: Request Validation

```python
async def handle_message(self, websocket, message):
    """Validate and route requests."""
    try:
        data = json.loads(message)
        tool_name = data.get("tool")
        params = data.get("params", {})
        
        # Validate tool exists
        if tool_name not in self.available_tools:
            return {"error": f"Unknown tool: {tool_name}", "success": False}
        
        # Validate params with Pydantic
        if tool_name == "query_architectural_graph":
            request = QueryGraphRequest(**params)
            result = await self.tools.query_architectural_graph(request)
        
        return {"tool": tool_name, "result": result, "success": True}
        
    except ValidationError as e:
        return {"error": f"Invalid parameters: {e}", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}
```

## Performance Considerations

### Response Time Targets

| Tool | Target | Typical |
|------|--------|---------|
| query_architectural_graph | < 500ms | ~300ms |
| retrieve_past_decisions | < 400ms | ~250ms |
| search_resources | < 600ms | ~400ms |
| find_relationships | < 1000ms | ~800ms |
| get_active_context | < 100ms | ~50ms |

### Concurrent Connections

Server supports multiple simultaneous Cursor connections:

```python
# WebSocket server handles multiple connections
await websockets.serve(
    self.handle_connection,
    host="localhost",
    port=8765,
    max_size=10_000_000,  # 10MB max message size
    max_queue=32          # Max queued messages
)
```

### Result Caching

Consider caching for frequently accessed data:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedMCPTools(MCPTools):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)
    
    async def query_architectural_graph(self, request):
        cache_key = f"query:{request.query}:{','.join(request.node_types or [])}"
        
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_data
        
        result = await super().query_architectural_graph(request)
        self._cache[cache_key] = (result, datetime.now())
        
        return result
```

## Testing

### Unit Tests

```python
import pytest
from neuralcursor.mcp.tools import MCPTools, QueryGraphRequest

@pytest.mark.asyncio
async def test_query_architectural_graph(neo4j_client, mongodb_client, memgpt_agent):
    """Test graph querying."""
    tools = MCPTools(neo4j_client, mongodb_client, memgpt_agent)
    
    request = QueryGraphRequest(
        query="authentication",
        max_results=5
    )
    
    result = await tools.query_architectural_graph(request)
    
    assert 'nodes' in result
    assert 'count' in result
    assert 'mermaid_diagram' in result
    assert result['count'] <= 5
```

### Integration Tests

```python
import pytest
import websockets
import json

@pytest.mark.asyncio
async def test_mcp_server_connection():
    """Test WebSocket server connection and tool call."""
    async with websockets.connect("ws://localhost:8765") as websocket:
        # Send tool request
        request = {
            "tool": "get_active_context",
            "params": {}
        }
        
        await websocket.send(json.dumps(request))
        
        # Receive response
        response_str = await websocket.recv()
        response = json.loads(response_str)
        
        assert response['success'] is True
        assert 'result' in response
        assert 'working_set_size' in response['result']
```

## Troubleshooting

### MCP Server Won't Start

**Check:**
```bash
# Port already in use?
lsof -i :8765

# Firewall blocking?
sudo ufw status

# Check logs
tail -f logs/mcp_server.log
```

### Cursor Not Connecting

**Check:**
```bash
# Verify ~/.cursor/mcp.json exists
cat ~/.cursor/mcp.json

# Test WebSocket manually
websocat ws://localhost:8765
{"tool": "get_active_context", "params": {}}

# Check Cursor logs
cat ~/Library/Logs/Cursor/main.log | grep mcp
```

### Tool Calls Timing Out

**Check:**
```python
# Verify database connections
await neo4j.driver.verify_connectivity()
await mongodb.db.command("ping")

# Check query performance
import time
start = time.time()
result = await tools.query_architectural_graph(request)
print(f"Query took: {time.time() - start:.2f}s")
```

## Security Considerations

### Local-Only Access

By default, MCP server binds to localhost:

```python
# Secure: Only localhost
await websockets.serve(handler, "localhost", 8765)

# Insecure: Exposed to network
await websockets.serve(handler, "0.0.0.0", 8765)  # DON'T DO THIS
```

### Message Size Limits

```python
# Prevent large message attacks
max_size=10_000_000  # 10MB limit
```

### Rate Limiting

Consider adding rate limiting for production:

```python
from collections import defaultdict
from time import time

class RateLimiter:
    def __init__(self, requests_per_minute=60):
        self.requests = defaultdict(list)
        self.limit = requests_per_minute
    
    def check(self, client_id):
        now = time()
        # Remove old requests
        self.requests[client_id] = [
            t for t in self.requests[client_id]
            if now - t < 60
        ]
        
        if len(self.requests[client_id]) >= self.limit:
            return False
        
        self.requests[client_id].append(now)
        return True
```

## Related Documentation

- [server.py](./server.py) - Full MCP server implementation
- [tools.py](./tools.py) - Tool implementations and Mermaid generation
- [../.cursorrules](../../.cursorrules) - Cursor integration guide
- [../brain/AGENTS.md](../brain/AGENTS.md) - Memory layer details
- [../AGENTS.md](../AGENTS.md) - Root documentation
