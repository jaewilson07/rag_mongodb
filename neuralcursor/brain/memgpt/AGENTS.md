# MemGPT - Working Memory Controller

## Overview

The MemGPT module provides a unified interface for managing working memory across both Neo4j and MongoDB. It implements autonomous context paging, working set management, and intelligent routing between structural (Neo4j) and episodic (MongoDB) storage.

## Core Concepts

### Working Memory State

**Core Memory**: High-priority items kept in active context
- Recently accessed nodes
- Current project focus
- Active conversation context

**Working Set**: List of recently accessed node UIDs
- LRU (Least Recently Used) eviction
- Automatic promotion on access
- Paging to long-term storage when full

**Context Window**: Token-based limit for active memory
- Monitors token usage
- Triggers paging at 80% capacity
- Prevents context overflow

## File Structure

```
memgpt/
├── __init__.py
└── agent.py        # MemGPT agent with context management
```

## Usage Guide

### Initialize Agent

```python
from neuralcursor.brain.memgpt.agent import MemGPTAgent
from neuralcursor.brain.neo4j.client import Neo4jClient
from neuralcursor.brain.mongodb.client import MongoDBClient

# Initialize clients
neo4j = Neo4jClient(neo4j_config)
await neo4j.connect()

mongodb = MongoDBClient(mongodb_config)
await mongodb.connect()

# Create MemGPT agent
memgpt = MemGPTAgent(neo4j, mongodb)
```

### Unified Memory Search

```python
# Search across both databases
results = await memgpt.retrieve_from_memory(
    query="JWT authentication implementation",
    memory_type="both",  # "episodic", "structural", or "both"
    limit=10
)

# Results include source annotation
for result in results:
    source = result['source']  # "neo4j" or "mongodb"
    data = result['data']
    
    if source == "neo4j":
        # Structural knowledge (Decisions, Requirements, CodeEntities)
        node_type = result['labels'][0]
        relevance = result['score']
        print(f"[{node_type}] {data['name']} (relevance: {relevance:.2f})")
    else:
        # Episodic knowledge (Resources, ChatMessages)
        print(f"[Resource] {data['title']}")
```

### Save to Memory

```python
# Save episodic data (routes to MongoDB)
await memgpt.save_to_memory(
    content="User prefers using TypeScript for type safety",
    memory_type="episodic",
    metadata={"session_id": "session_123", "topic": "preferences"}
)

# For structural data, use Neo4j client directly
# (MemGPT returns a message to use specific node creation methods)
from neuralcursor.brain.neo4j.models import DecisionNode

decision = DecisionNode(
    name="Use TypeScript",
    context="Team discussion on type safety",
    decision="Migrate to TypeScript for better developer experience",
    rationale="Catch errors at compile time, better IDE support"
)
uid = await memgpt.neo4j.create_node(decision)
```

### Working Set Management

```python
# Add node to working set (marks as recently accessed)
await memgpt.add_to_working_set("node_uid_123")

# Get current active context
context = await memgpt.get_active_context()

print(f"Active Project: {context['active_project']['name']}")
print(f"Working Set Size: {context['working_set_size']}")
print(f"Context Window Usage: {context['context_usage']:.1%}")

print("\nRecently Accessed:")
for node in context['recent_nodes']:
    print(f"  - {node['name']} ({node['node_type']})")
```

### Autonomous Context Paging

```python
# Automatic paging when context fills up
# This happens automatically via add_to_working_set,
# but can be triggered manually

summary = await memgpt.manage_working_set(
    context_window_size=10000  # Max tokens
)

print(f"Context Usage: {summary['context_usage']:.1%}")
print(f"Working Set Size: {summary['working_set_size']}")
print(f"Operations: {len(summary['operations'])}")

# View paged items
for op in summary['operations']:
    if op['operation_type'] == 'page':
        print(f"Paged: {op['target']}")
```

### Manual Paging

```python
# Manually page a specific node to long-term storage
operation = await memgpt.page_to_long_term("node_uid_456")

if operation.success:
    print(f"Successfully paged: {operation.target}")
else:
    print(f"Paging failed: {operation.message}")
```

## Design Patterns

### Pattern 1: Context-Aware Retrieval

```python
async def smart_search(
    memgpt: MemGPTAgent,
    query: str,
    prefer_recent: bool = True
) -> list[dict]:
    """
    Search with awareness of working set.
    
    Prioritizes recently accessed items for relevance.
    """
    # Get active context
    context = await memgpt.get_active_context()
    recent_uids = [n['uid'] for n in context['recent_nodes']]
    
    # Search both databases
    all_results = await memgpt.retrieve_from_memory(
        query=query,
        memory_type="both",
        limit=20
    )
    
    if prefer_recent:
        # Boost scores for items in working set
        for result in all_results:
            if result.get('data', {}).get('uid') in recent_uids:
                result['boosted'] = True
                result['score'] = result.get('score', 0) * 1.5
        
        # Re-sort by boosted scores
        all_results.sort(key=lambda r: r.get('score', 0), reverse=True)
    
    return all_results[:10]
```

### Pattern 2: Working Set Warming

```python
async def warm_working_set_for_project(
    memgpt: MemGPTAgent,
    project_uid: str
) -> None:
    """
    Pre-load working set with project context.
    
    Useful when switching to a new project.
    """
    # Find project and related entities
    cypher = """
    MATCH (project:Project {uid: $uid})
    OPTIONAL MATCH (project)-[:CONTAINS]->(code:CodeEntity)
    OPTIONAL MATCH (code)-[:DERIVED_FROM]->(decision:Decision)
    OPTIONAL MATCH (decision)-[:IMPLEMENTS]->(req:Requirement)
    RETURN 
        project.uid as project_uid,
        collect(DISTINCT code.uid) as code_uids,
        collect(DISTINCT decision.uid) as decision_uids,
        collect(DISTINCT req.uid) as req_uids
    """
    
    results = await memgpt.neo4j.query(cypher, {"uid": project_uid})
    
    if results:
        data = results[0]
        
        # Add to working set
        await memgpt.add_to_working_set(data['project_uid'])
        
        for uid in data['code_uids'][:10]:  # Limit to top 10
            if uid:
                await memgpt.add_to_working_set(uid)
        
        for uid in data['decision_uids'][:5]:
            if uid:
                await memgpt.add_to_working_set(uid)
        
        # Update active project
        memgpt.state.active_project = project_uid
```

### Pattern 3: Session Context Capture

```python
async def capture_session_context(
    memgpt: MemGPTAgent,
    session_id: str,
    messages: list[dict],
    project: str | None = None
) -> None:
    """
    Capture conversation context with automatic routing.
    
    Saves to MongoDB and adds referenced nodes to working set.
    """
    # Save messages to MongoDB
    for msg in messages:
        await memgpt.save_to_memory(
            content=msg['content'],
            memory_type="episodic",
            metadata={
                "session_id": session_id,
                "role": msg['role'],
                "project": project
            }
        )
    
    # Extract mentioned node UIDs (if any in metadata)
    mentioned_uids = []
    for msg in messages:
        if 'mentioned_nodes' in msg.get('metadata', {}):
            mentioned_uids.extend(msg['metadata']['mentioned_nodes'])
    
    # Add to working set
    for uid in set(mentioned_uids):
        await memgpt.add_to_working_set(uid)
```

### Pattern 4: Context Window Monitoring

```python
async def monitor_context_health(
    memgpt: MemGPTAgent
) -> dict:
    """
    Monitor context window health and trigger maintenance.
    
    Returns health metrics and performs cleanup if needed.
    """
    context = await memgpt.get_active_context()
    
    health = {
        "working_set_size": context['working_set_size'],
        "context_usage": context['context_usage'],
        "status": "healthy"
    }
    
    # Check thresholds
    if context['context_usage'] > 0.9:
        health['status'] = "critical"
        health['action'] = "emergency_paging"
        
        # Emergency paging
        summary = await memgpt.manage_working_set(
            context_window_size=8000  # Aggressive limit
        )
        health['paged_items'] = len(summary['operations'])
        
    elif context['context_usage'] > 0.7:
        health['status'] = "warning"
        health['action'] = "scheduled_paging"
    
    return health
```

## Working Memory State

### State Structure

```python
from neuralcursor.brain.memgpt.agent import WorkingMemoryState

state = WorkingMemoryState(
    core_memory={
        "active_project": "project_uid_123",
        "recent_decisions": ["dec_uid_1", "dec_uid_2"],
        "preferences": {"language": "typescript"}
    },
    working_set=[
        "node_uid_1",
        "node_uid_2",
        "node_uid_3",
        # ... up to context limit
    ],
    active_project="project_uid_123",
    context_window_usage=0.65  # 65% full
)
```

### State Persistence

Working memory state is kept in memory but backed by databases:
- **Working Set UIDs**: Stored as list in agent
- **Core Memory**: Can be serialized to MongoDB
- **Archived Status**: Marked in Neo4j nodes

## Memory Operations

### Operation Types

```python
from neuralcursor.brain.memgpt.agent import MemoryOperation

# Save operation
op = MemoryOperation(
    operation_type="save",
    target="mongodb/episodic",
    data={"session_id": "session_123"},
    success=True,
    message="Saved to episodic memory"
)

# Retrieve operation
op = MemoryOperation(
    operation_type="retrieve",
    target="both",
    success=True,
    message=f"Found {len(results)} results"
)

# Page operation
op = MemoryOperation(
    operation_type="page",
    target="node_uid_456",
    success=True,
    message="Paged to long-term memory"
)
```

## Context Paging Strategy

### LRU Eviction

When context window reaches 80% capacity:

1. Calculate how many items to page (typically 30%)
2. Select oldest items from working set
3. Mark as archived in Neo4j (but remain searchable)
4. Remove from working set
5. Log paging operation

```python
# Automatic paging logic
if context_window_usage > 0.8:
    items_to_page = int(len(working_set) * 0.3)
    
    for uid in working_set[:items_to_page]:  # Oldest first
        await page_to_long_term(uid)
        working_set.remove(uid)
```

### Promotion on Access

When accessing a paged node:

1. Check if node is archived
2. If archived, un-archive it
3. Add back to working set
4. Update `updated_at` timestamp

```python
async def access_node(uid: str):
    node = await neo4j.get_node(uid)
    
    if node.get('archived'):
        # Un-archive and promote
        await neo4j.update_node(uid, {"archived": False})
    
    # Add to working set
    await memgpt.add_to_working_set(uid)
```

## Performance Considerations

### Working Set Size

Optimal working set size depends on:
- Context window limit (typically 8,000-15,000 tokens)
- Average node size (varies by type)
- Query performance requirements

**Recommendation**: Keep working set under 100 items for optimal performance.

### Search Performance

```python
# Fast: Search only structural (Neo4j)
results = await memgpt.retrieve_from_memory(
    query="auth decision",
    memory_type="structural",
    limit=10
)

# Slower: Search both databases
results = await memgpt.retrieve_from_memory(
    query="auth decision",
    memory_type="both",
    limit=10
)
```

### Memory Usage

MemGPT state is kept in Python memory:
- Working set: ~100 UIDs × 36 bytes = ~3.6KB
- Core memory: Varies by content
- Total: Typically < 1MB

## Error Handling

```python
import logging

logger = logging.getLogger(__name__)

try:
    results = await memgpt.retrieve_from_memory(query)
except Exception as e:
    logger.exception("memgpt_retrieve_failed", extra={"error": str(e)})
    # Graceful degradation: return empty results
    results = []
```

## Testing

```python
import pytest
from neuralcursor.brain.memgpt.agent import MemGPTAgent, WorkingMemoryState

@pytest.mark.asyncio
async def test_working_set_management(neo4j_client, mongodb_client):
    """Test working set addition and paging."""
    memgpt = MemGPTAgent(neo4j_client, mongodb_client)
    
    # Add items to working set
    for i in range(15):
        await memgpt.add_to_working_set(f"node_uid_{i}")
    
    assert len(memgpt.state.working_set) == 15
    
    # Trigger paging (with small context window)
    summary = await memgpt.manage_working_set(context_window_size=1000)
    
    # Should have paged some items
    assert len(summary['operations']) > 0
    assert memgpt.state.context_window_usage < 0.8
```

## Integration Examples

### With MCP Server

```python
# MCP tool calls MemGPT for unified search
from neuralcursor.mcp.tools import MCPTools

mcp_tools = MCPTools(neo4j, mongodb, memgpt)

# Tool uses MemGPT for context-aware search
result = await mcp_tools.query_architectural_graph(request)
```

See: [../../mcp/AGENTS.md](../../mcp/AGENTS.md)

### With Librarian Agent

```python
# Librarian adds distilled nodes to working set
from neuralcursor.agents.librarian import LibrarianAgent

librarian = LibrarianAgent(neo4j, mongodb)

# After distillation, add to working set
conversation_uid = await librarian.distill_session(session)
if conversation_uid:
    await memgpt.add_to_working_set(conversation_uid)
```

See: [../../agents/AGENTS.md](../../agents/AGENTS.md)

## Related Documentation

- [agent.py](./agent.py) - Full MemGPT agent implementation
- [../AGENTS.md](../AGENTS.md) - Brain module overview
- [../neo4j/AGENTS.md](../neo4j/AGENTS.md) - Neo4j integration
- [../mongodb/AGENTS.md](../mongodb/AGENTS.md) - MongoDB integration
- [../../AGENTS.md](../../AGENTS.md) - Root documentation
