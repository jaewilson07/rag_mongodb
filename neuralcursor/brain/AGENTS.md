# NeuralCursor Brain Module

## Overview

The `brain/` module implements the dual-database memory layer that forms the core of NeuralCursor's persistent memory system.

## Architecture

```
brain/
├── neo4j/          # Graph database (Logical Brain)
├── mongodb/        # Document store (Episodic Brain)
└── memgpt/         # Working memory controller
```

## Dual-Database Strategy

### Neo4j: The Logical Brain

**Purpose**: Stores structural relationships and architectural logic

**Use Cases**:
- Multi-hop relationship traversal
- Architectural decision tracking
- Code dependency graphs
- PARA methodology implementation

**When to Use**:
```python
# Use Neo4j when you need to:
# 1. Find relationships between entities
# 2. Traverse dependency chains
# 3. Query structural patterns
# 4. Store architectural decisions

from neuralcursor.brain.neo4j.client import Neo4jClient
```

See: [neo4j/AGENTS.md](./neo4j/AGENTS.md)

### MongoDB: The Episodic Brain

**Purpose**: Stores temporal, episodic data

**Use Cases**:
- Chat conversation logs
- Document chunks with embeddings
- External resources (URLs, summaries)
- Session tracking for distillation

**When to Use**:
```python
# Use MongoDB when you need to:
# 1. Store conversation history
# 2. Perform semantic search on documents
# 3. Track temporal sessions
# 4. Store resource metadata

from neuralcursor.brain.mongodb.client import MongoDBClient
```

See: [mongodb/AGENTS.md](./mongodb/AGENTS.md)

### MemGPT: Working Memory Controller

**Purpose**: Manages active context and paging between hot/cold storage

**Use Cases**:
- Working set management (recently accessed nodes)
- Autonomous context paging when window fills
- Core memory vs cold storage management
- Unified retrieval across both databases

**When to Use**:
```python
# Use MemGPT when you need to:
# 1. Manage active context window
# 2. Search across both databases
# 3. Automatically page old data to long-term storage
# 4. Track recently accessed items

from neuralcursor.brain.memgpt.agent import MemGPTAgent
```

See: [memgpt/AGENTS.md](./memgpt/AGENTS.md)

## Usage Patterns

### Pattern 1: Initialize Both Databases

```python
import asyncio
from neuralcursor.settings import get_settings
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig
from neuralcursor.brain.mongodb.client import MongoDBClient, MongoDBConfig
from neuralcursor.brain.memgpt.agent import MemGPTAgent

async def initialize_brain():
    settings = get_settings()
    
    # Initialize Neo4j
    neo4j_config = Neo4jConfig(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    neo4j = Neo4jClient(neo4j_config)
    await neo4j.connect()
    
    # Initialize MongoDB
    mongodb_config = MongoDBConfig(
        uri=settings.mongodb_uri,
        database=settings.mongodb_database,
    )
    mongodb = MongoDBClient(mongodb_config)
    await mongodb.connect()
    
    # Initialize MemGPT (unified interface)
    memgpt = MemGPTAgent(neo4j, mongodb)
    
    return neo4j, mongodb, memgpt

# Usage
neo4j, mongodb, memgpt = asyncio.run(initialize_brain())
```

### Pattern 2: Unified Memory Search

```python
# Search across both databases simultaneously
results = await memgpt.retrieve_from_memory(
    query="authentication implementation",
    memory_type="both",  # "episodic", "structural", or "both"
    limit=10
)

# Results include source annotation
for result in results:
    source = result['source']  # "neo4j" or "mongodb"
    data = result['data']
    
    if source == "neo4j":
        # Structural data (Decision, CodeEntity, etc.)
        node_type = result['labels'][0]
        print(f"[Graph] {node_type}: {data['name']}")
    else:
        # Episodic data (Resource, ChatMessage, etc.)
        print(f"[Docs] {data['title']}")
```

### Pattern 3: Save to Appropriate Database

```python
# MemGPT automatically routes to correct database
await memgpt.save_to_memory(
    content="User decided to use JWT authentication",
    memory_type="episodic",  # Saves to MongoDB
    metadata={"session_id": "session_123", "topic": "auth"}
)

# For structural data, use Neo4j client directly
from neuralcursor.brain.neo4j.models import DecisionNode

decision = DecisionNode(
    name="Use JWT Authentication",
    context="Need stateless auth for API",
    decision="Implement JWT with refresh tokens",
    rationale="Scalable, stateless, industry standard"
)
uid = await neo4j.create_node(decision)
```

### Pattern 4: Working Set Management

```python
# Add to working set (marks as recently accessed)
await memgpt.add_to_working_set(node_uid)

# Get active context
context = await memgpt.get_active_context()

print(f"Active project: {context['active_project']['name']}")
print(f"Working set size: {context['working_set_size']}")
print(f"Context window usage: {context['context_usage']:.1%}")

# Recently accessed nodes
for node in context['recent_nodes']:
    print(f"  - {node['name']} ({node['node_type']})")

# Automatic paging when context fills
# This happens automatically but can be triggered manually
summary = await memgpt.manage_working_set(context_window_size=10000)
print(f"Paged {len(summary['operations'])} items to long-term storage")
```

### Pattern 5: Conversation to Graph

```python
# Save chat to MongoDB
from neuralcursor.brain.mongodb.client import ChatMessage
from datetime import datetime

message = ChatMessage(
    role="user",
    content="We should migrate to TypeScript for better type safety",
    metadata={"topic": "technical_decision"}
)

await mongodb.save_chat_message("session_456", message)

# Later, Librarian agent will distill this into Neo4j nodes
# See: neuralcursor/agents/librarian.py
```

## Data Flow

```
┌─────────────────────────────────────────────────────┐
│                  User Interaction                    │
│               (via Cursor or CLI)                    │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              MemGPT Agent (Unified Interface)       │
│                                                      │
│  • Decides where to save data                       │
│  • Manages working set                              │
│  • Searches across both databases                   │
│  • Pages old data to long-term storage              │
└───────────┬─────────────────────────┬───────────────┘
            │                         │
            ▼                         ▼
┌───────────────────┐     ┌──────────────────────────┐
│   Neo4j Graph     │     │    MongoDB Atlas         │
│  (Structural)     │     │    (Episodic)            │
│                   │     │                          │
│ • Decisions       │     │ • Chat logs              │
│ • Requirements    │     │ • Sessions               │
│ • CodeEntities    │     │ • Resources              │
│ • Files           │     │ • Document chunks        │
└───────────────────┘     └──────────────────────────┘
            │                         │
            └────────┬────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  Background Agents    │
         │                       │
         │ • Librarian: MongoDB → Neo4j
         │ • Optimizer: Graph cleanup
         │ • Synthesizer: Pattern discovery
         └───────────────────────┘
```

## Design Principles

### 1. Separation of Concerns

- **Neo4j**: Long-term structural knowledge
- **MongoDB**: Short-term episodic data
- **MemGPT**: Coordination layer

### 2. Automatic Routing

MemGPT decides where data belongs:
- Conversations → MongoDB
- Decisions/Requirements → Neo4j
- Recent context → Working set
- Old context → Archived in Neo4j

### 3. Unified Retrieval

Applications don't need to know which database to query:

```python
# Single interface for all searches
results = await memgpt.retrieve_from_memory("auth patterns", memory_type="both")
```

### 4. Lazy Loading

- Working set keeps frequently accessed nodes hot
- Cold data remains searchable but isn't loaded
- Automatic promotion when accessed

## Connection Management

### Connection Pooling

Both databases use connection pooling:

```python
# Neo4j
Neo4jConfig(
    max_connection_pool_size=50,
    connection_acquisition_timeout=60
)

# MongoDB (Motor handles pooling automatically)
MongoDBConfig(uri="mongodb://...")
```

### Cleanup

```python
async def cleanup():
    await neo4j.close()
    await mongodb.close()

# Or use context managers (recommended)
async with neo4j_client:
    # Do work
    pass  # Automatically closes
```

## Schema Management

### Neo4j Schema Initialization

Schema is automatically created on first connection:

```python
await neo4j.connect()  # Creates constraints and indexes
```

To verify:

```python
schema_info = await neo4j.get_schema_info()
print(f"Constraints: {schema_info['constraints']}")
print(f"Indexes: {schema_info['indexes']}")
print(f"Schema valid: {schema_info['schema_valid']}")
```

### MongoDB Index Creation

Indexes are created automatically:

```python
await mongodb.connect()  # Creates necessary indexes
```

Collections:
- `sessions`: Chat sessions with distillation status
- `resources`: External resources (YouTube, articles)
- `chunks`: Document chunks (from existing RAG system)
- `documents`: Document metadata (from existing RAG system)

## Performance Tuning

### Neo4j Optimization

```python
# Use parameterized queries
cypher = "MATCH (n:Decision {uid: $uid}) RETURN n"
result = await neo4j.query(cypher, {"uid": uid})

# Batch operations in transactions
async with neo4j.driver.session() as session:
    async with session.begin_transaction() as tx:
        for node in nodes:
            await tx.run("CREATE (n:Node) SET n = $props", props=node)
        await tx.commit()
```

### MongoDB Optimization

```python
# Use projections to limit data transfer
cursor = mongodb.db.sessions.find(
    {"session_id": session_id},
    {"messages": 1, "project_context": 1}  # Only these fields
)

# Create indexes for common queries
await mongodb.db.sessions.create_index("last_activity")
```

### MemGPT Working Set Tuning

```python
# Adjust working set size based on available memory
await memgpt.manage_working_set(
    context_window_size=15000  # Increase for more hot storage
)

# Monitor context usage
context = await memgpt.get_active_context()
if context['context_usage'] > 0.9:
    logger.warning("Context window nearly full")
```

## Testing

```python
import pytest
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig
from neuralcursor.brain.mongodb.client import MongoDBClient, MongoDBConfig
from neuralcursor.brain.memgpt.agent import MemGPTAgent

@pytest.fixture
async def brain_clients():
    """Fixture providing all brain components."""
    neo4j = Neo4jClient(Neo4jConfig(...))
    await neo4j.connect()
    
    mongodb = MongoDBClient(MongoDBConfig(...))
    await mongodb.connect()
    
    memgpt = MemGPTAgent(neo4j, mongodb)
    
    yield neo4j, mongodb, memgpt
    
    await neo4j.close()
    await mongodb.close()

@pytest.mark.asyncio
async def test_unified_search(brain_clients):
    """Test searching across both databases."""
    neo4j, mongodb, memgpt = brain_clients
    
    # Create test data in both databases
    # ... setup ...
    
    results = await memgpt.retrieve_from_memory("test query", memory_type="both")
    
    assert len(results) > 0
    assert any(r['source'] == 'neo4j' for r in results)
    assert any(r['source'] == 'mongodb' for r in results)
```

## Troubleshooting

### Connection Issues

```python
# Test Neo4j
try:
    await neo4j.driver.verify_connectivity()
    print("✓ Neo4j connected")
except Exception as e:
    print(f"✗ Neo4j error: {e}")

# Test MongoDB
try:
    await mongodb.db.command("ping")
    print("✓ MongoDB connected")
except Exception as e:
    print(f"✗ MongoDB error: {e}")
```

### Schema Validation

```python
# Verify Neo4j schema
schema_info = await neo4j.get_schema_info()
if not schema_info['schema_valid']:
    print("Warning: Schema not fully initialized")
    # Reinitialize
    from neuralcursor.brain.neo4j.schema import initialize_schema
    await initialize_schema(neo4j.driver)
```

## Related Documentation

- [neo4j/AGENTS.md](./neo4j/AGENTS.md) - Neo4j graph database details
- [mongodb/AGENTS.md](./mongodb/AGENTS.md) - MongoDB episodic memory details
- [memgpt/AGENTS.md](./memgpt/AGENTS.md) - MemGPT working memory details
- [../../AGENTS.md](../AGENTS.md) - Root NeuralCursor documentation
