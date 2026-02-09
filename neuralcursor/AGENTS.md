# NeuralCursor - Root Module Documentation

## Overview

NeuralCursor is a persistent, context-aware "Second Brain" system for Cursor IDE that provides architectural intuition through a dual-database memory layer (Neo4j + MongoDB Atlas) with intelligent context management.

## Architecture Overview

```
neuralcursor/
├── brain/          # Memory layer (Neo4j, MongoDB, MemGPT)
├── agents/         # Autonomous background agents
├── mcp/            # Model Context Protocol server for Cursor
├── gateway/        # FastAPI unified memory API
├── llm/            # Local LLM orchestration (dual GPU)
├── monitoring/     # Health monitoring and VRAM tracking
├── orchestrator.py # Main service coordinator
├── cli.py          # Interactive CLI
└── settings.py     # Global configuration
```

## Core Principles

### 1. Dual-Database Architecture

**Neo4j (The Logical Brain):**
- Stores structural relationships using PARA ontology
- Nodes: Project, Area, Resource, Archive, Decision, Requirement, CodeEntity, File, Conversation
- Enables multi-hop reasoning and architectural queries
- See: [brain/neo4j/AGENTS.md](./brain/neo4j/AGENTS.md)

**MongoDB (The Episodic Brain):**
- Stores temporal data: chat logs, sessions, resources
- Document chunks with embeddings for semantic search
- Distillation queue for Librarian agent
- See: [brain/mongodb/AGENTS.md](./brain/mongodb/AGENTS.md)

### 2. Agent-Based Processing

All long-running tasks are handled by autonomous agents:
- **Librarian**: Distills conversations into graph nodes
- **Watcher**: Monitors file changes and updates graph
- **Optimizer**: Weekly graph maintenance
- **Conflict Detector**: Identifies architectural drifts
- **Synthesizer**: Cross-project pattern discovery

See: [agents/AGENTS.md](./agents/AGENTS.md)

### 3. Local-First Philosophy

- All LLM inference runs on local hardware (dual 3090s)
- Zero cloud API calls for reasoning or embeddings
- Complete data privacy
- See: [llm/AGENTS.md](./llm/AGENTS.md)

### 4. MCP Integration

Model Context Protocol provides seamless Cursor integration:
- WebSocket server exposes memory tools
- Tools: query_graph, retrieve_decisions, search_resources, find_relationships
- Automatic tool discovery by Cursor
- See: [mcp/AGENTS.md](./mcp/AGENTS.md)

## Quick Start

### Initialize a Client

```python
import asyncio
from neuralcursor.settings import get_settings
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig

async def init():
    settings = get_settings()
    
    config = Neo4jConfig(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    
    client = Neo4jClient(config)
    await client.connect()
    
    return client

client = asyncio.run(init())
```

### Create a Project Node

```python
from neuralcursor.brain.neo4j.models import ProjectNode

project = ProjectNode(
    name="My New Project",
    description="Building something awesome",
    status="active",
    goals=["Learn", "Build", "Deploy"],
    technologies=["Python", "Neo4j", "FastAPI"]
)

uid = await client.create_node(project)
print(f"Project created: {uid}")
```

### Query the Graph

```python
# Find all active projects
cypher = """
MATCH (p:Project)
WHERE p.status = 'active' AND NOT p.archived = true
RETURN p.name as name, p.goals as goals
ORDER BY p.created_at DESC
"""

results = await client.query(cypher)
for record in results:
    print(f"Project: {record['name']}")
    print(f"Goals: {', '.join(record['goals'])}")
```

### Search Episodic Memory

```python
from neuralcursor.brain.mongodb.client import MongoDBClient, MongoDBConfig
from neuralcursor.brain.memgpt.agent import MemGPTAgent

mongodb = MongoDBClient(MongoDBConfig(uri=settings.mongodb_uri))
await mongodb.connect()

memgpt = MemGPTAgent(client, mongodb)

# Search across both databases
results = await memgpt.retrieve_from_memory(
    query="authentication decisions",
    memory_type="both",
    limit=10
)

for result in results:
    print(f"[{result['source']}] {result['data']['name']}")
```

## Service Orchestration

The main orchestrator manages all services:

```python
from neuralcursor.orchestrator import NeuralCursorOrchestrator

async def main():
    orchestrator = NeuralCursorOrchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

This starts:
- Neo4j and MongoDB connections
- All background agents (Librarian, Watcher, Optimizer, etc.)
- GPU monitoring dashboard
- Health checks

## Configuration

All configuration via environment variables with `NEURALCURSOR_` prefix:

```bash
# Neo4j
NEURALCURSOR_NEO4J_URI=bolt://localhost:7687
NEURALCURSOR_NEO4J_PASSWORD=your-password

# MongoDB
NEURALCURSOR_MONGODB_URI=mongodb://localhost:27017

# LLM Endpoints
NEURALCURSOR_REASONING_LLM_HOST=http://localhost:8000
NEURALCURSOR_EMBEDDING_LLM_HOST=http://localhost:8001

# Services
NEURALCURSOR_MCP_ENABLED=true
NEURALCURSOR_WATCHER_ENABLED=true
NEURALCURSOR_MONITORING_ENABLED=true
```

See: `settings.py` for complete configuration options.

## Common Patterns

### Pattern 1: Create and Link Nodes

```python
from neuralcursor.brain.neo4j.models import DecisionNode, RequirementNode, Relationship, RelationType

# Create a requirement
requirement = RequirementNode(
    name="JWT Authentication",
    description="Implement JWT-based auth",
    requirement_type="functional",
    priority="high",
    status="pending"
)
req_uid = await client.create_node(requirement)

# Create a decision
decision = DecisionNode(
    name="Use jsonwebtoken library",
    description="Selected jsonwebtoken for JWT implementation",
    context="Need secure, well-maintained JWT library",
    decision="Use jsonwebtoken package",
    rationale="Most popular, actively maintained, good TypeScript support",
    alternatives=["jose", "jwt-simple"]
)
dec_uid = await client.create_node(decision)

# Link them
relationship = Relationship(
    from_uid=dec_uid,
    to_uid=req_uid,
    relation_type=RelationType.IMPLEMENTS
)
await client.create_relationship(relationship)
```

### Pattern 2: Multi-Hop Reasoning

```python
# Find the path from a CodeEntity back to its original Requirement
path_results = await client.find_path(
    from_uid=code_entity_uid,
    to_uid=requirement_uid,
    max_depth=5,
    relation_types=[RelationType.IMPLEMENTS, RelationType.DEPENDS_ON]
)

# Returns: CodeEntity -> Decision -> Requirement
for path in path_results:
    nodes = path['nodes']
    print(f"Path found: {' -> '.join([n['name'] for n in nodes])}")
```

### Pattern 3: Working Memory Management

```python
from neuralcursor.brain.memgpt.agent import MemGPTAgent

memgpt = MemGPTAgent(neo4j_client, mongodb_client)

# Add to working set (marks as recently accessed)
await memgpt.add_to_working_set(node_uid)

# Get active context
context = await memgpt.get_active_context()
print(f"Working set size: {context['working_set_size']}")
print(f"Context usage: {context['context_usage']:.1%}")

# Automatic paging when context fills up
await memgpt.manage_working_set(context_window_size=10000)
```

### Pattern 4: Agent Background Processing

```python
from neuralcursor.agents.librarian import LibrarianAgent

librarian = LibrarianAgent(neo4j_client, mongodb_client)

# Process a single session
session = await mongodb_client.get_session("session_123")
conversation_uid = await librarian.distill_session(session)

# Or run continuous loop
await librarian.run_distillation_loop(
    interval_seconds=300,  # Every 5 minutes
    batch_size=5
)
```

## Module Documentation

| Module | Purpose | Documentation |
|--------|---------|---------------|
| `brain/neo4j` | Graph database with PARA ontology | [AGENTS.md](./brain/neo4j/AGENTS.md) |
| `brain/mongodb` | Episodic memory and chat logs | [AGENTS.md](./brain/mongodb/AGENTS.md) |
| `brain/memgpt` | Working memory management | [AGENTS.md](./brain/memgpt/AGENTS.md) |
| `agents/` | Autonomous background agents | [AGENTS.md](./agents/AGENTS.md) |
| `mcp/` | Cursor integration via MCP | [AGENTS.md](./mcp/AGENTS.md) |
| `gateway/` | FastAPI unified memory API | [AGENTS.md](./gateway/AGENTS.md) |
| `llm/` | Dual GPU LLM orchestration | [AGENTS.md](./llm/AGENTS.md) |
| `monitoring/` | Health checks and VRAM tracking | [AGENTS.md](./monitoring/AGENTS.md) |

## Error Handling

All modules follow consistent error handling:

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = await some_operation()
except SpecificError as e:
    logger.exception("operation_failed", extra={"context": value, "error": str(e)})
    raise
```

Errors are logged with structured context for debugging.

## Testing Strategy

```python
import pytest
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig

@pytest.mark.asyncio
async def test_node_creation():
    """Test creating a node in Neo4j."""
    config = Neo4jConfig(uri="bolt://localhost:7687", ...)
    client = Neo4jClient(config)
    await client.connect()
    
    from neuralcursor.brain.neo4j.models import ProjectNode
    
    project = ProjectNode(name="Test Project", status="active")
    uid = await client.create_node(project)
    
    assert uid is not None
    
    # Verify
    node = await client.get_node(uid)
    assert node['name'] == "Test Project"
    
    await client.close()
```

## Performance Considerations

- **Graph Queries**: Use parameterized queries to leverage Neo4j query cache
- **Batch Operations**: Insert multiple nodes/relationships in transactions
- **Working Set**: Keep working set size < 8000 tokens for optimal performance
- **GPU Memory**: Monitor VRAM usage via monitoring dashboard
- **Connection Pooling**: FastAPI gateway maintains connection pools

## Troubleshooting

### Neo4j Connection Issues

```python
# Test connection
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig

config = Neo4jConfig(uri="bolt://localhost:7687", username="neo4j", password="password")
client = Neo4jClient(config)

try:
    await client.connect()
    print("✓ Connected to Neo4j")
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### MongoDB Connection Issues

```python
# Verify MongoDB connectivity
from neuralcursor.brain.mongodb.client import MongoDBClient, MongoDBConfig

config = MongoDBConfig(uri="mongodb://localhost:27017")
client = MongoDBClient(config)

try:
    await client.connect()
    print("✓ Connected to MongoDB")
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### MCP Server Not Responding

```bash
# Check if MCP server is running
lsof -i :8765

# Test WebSocket connection
websocat ws://localhost:8765
{"tool": "get_active_context", "params": {}}
```

## Related Documentation

- [NEURALCURSOR_PRD.md](../NEURALCURSOR_PRD.md) - Product requirements
- [QUICKSTART.md](./QUICKSTART.md) - Setup guide
- [IMPLEMENTATION_COMPLETE.md](../IMPLEMENTATION_COMPLETE.md) - Implementation summary
- [.cursorrules](../.cursorrules) - Cursor integration prompt

## Contributing

When adding new features:

1. Follow existing patterns (async-first, type-safe)
2. Add comprehensive docstrings (Google style)
3. Update relevant AGENTS.md files
4. Add tests for new functionality
5. Update this documentation with crosslinks

## Support

For questions or issues:
- Check module-specific AGENTS.md files
- Review Quick Start guide
- Examine example code in this file
