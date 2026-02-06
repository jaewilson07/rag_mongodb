# Neo4j Graph Database - Logical Brain

## Overview

The Neo4j module implements the "Logical Brain" using the PARA methodology (Projects, Areas, Resources, Archives) to store structural relationships and architectural knowledge.

## Core Concepts

### PARA Ontology

**Projects**: Goal-oriented work with deadlines
- Active development efforts
- Time-bound objectives
- Status tracking (active, completed, archived)

**Areas**: Standards maintained over time
- Ongoing responsibilities
- No end date
- Focus level tracking

**Resources**: Reference material
- External content (YouTube, articles, docs)
- Learning resources
- Inspiration sources

**Archives**: Inactive items from other categories
- Completed projects
- Deprecated code
- Historical reference

### Additional Node Types

**Decision**: Architectural choices with rationale
- Why was this choice made?
- What alternatives were considered?
- What are the consequences?

**Requirement**: Functional/non-functional requirements
- What needs to be built?
- Acceptance criteria
- Implementation status

**CodeEntity**: Actual code structures
- Classes, functions, modules
- File location and line numbers
- Language and signature

**File**: Tracked files in codebase
- Automatic updates from file watcher
- Content hash for change detection
- Size and modification time

**Conversation**: Distilled chat logs
- Summary of key points
- Extracted decisions
- Links to MongoDB conversation IDs

## File Structure

```
neo4j/
├── __init__.py
├── models.py       # Pydantic models for nodes and relationships
├── schema.py       # Schema initialization and validation
└── client.py       # Async Neo4j client with CRUD operations
```

## Usage Guide

### Initialize Client

```python
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig

config = Neo4jConfig(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="your-password",
    database="neo4j"
)

client = Neo4jClient(config)
await client.connect()  # Automatically initializes schema
```

### Create Nodes

```python
from neuralcursor.brain.neo4j.models import (
    ProjectNode,
    DecisionNode,
    RequirementNode,
    CodeEntityNode
)

# Create a project
project = ProjectNode(
    name="Authentication System",
    description="Build JWT-based authentication",
    status="active",
    goals=["Implement JWT", "Add refresh tokens", "Security audit"],
    technologies=["Node.js", "jsonwebtoken", "Redis"]
)
project_uid = await client.create_node(project)

# Create a requirement
requirement = RequirementNode(
    name="JWT Token Management",
    description="Securely manage JWT tokens with refresh mechanism",
    requirement_type="functional",
    priority="high",
    status="pending",
    acceptance_criteria=[
        "Tokens expire after 15 minutes",
        "Refresh tokens valid for 7 days",
        "Secure storage in httpOnly cookies"
    ]
)
req_uid = await client.create_node(requirement)

# Create a decision
decision = DecisionNode(
    name="Use jsonwebtoken library",
    description="Selected jsonwebtoken npm package",
    context="Need a robust JWT library for Node.js",
    decision="Use jsonwebtoken package for JWT operations",
    rationale="Most popular library (25M+ weekly downloads), actively maintained, good TypeScript support",
    alternatives=["jose", "jwt-simple", "node-jsonwebtoken"],
    consequences=[
        "Need to handle async operations",
        "Must configure algorithm carefully",
        "Regular security updates required"
    ]
)
dec_uid = await client.create_node(decision)

# Create a code entity
code_entity = CodeEntityNode(
    name="AuthService",
    description="Core authentication service handling JWT operations",
    entity_type="class",
    file_path="src/services/AuthService.ts",
    line_start=15,
    line_end=150,
    language="typescript",
    signature="class AuthService { constructor(config: AuthConfig) }"
)
code_uid = await client.create_node(code_entity)
```

### Create Relationships

```python
from neuralcursor.brain.neo4j.models import Relationship, RelationType

# Link decision to requirement (implements)
rel1 = Relationship(
    from_uid=dec_uid,
    to_uid=req_uid,
    relation_type=RelationType.IMPLEMENTS,
    weight=1.0
)
await client.create_relationship(rel1)

# Link code entity to decision (inspired by)
rel2 = Relationship(
    from_uid=code_uid,
    to_uid=dec_uid,
    relation_type=RelationType.DERIVED_FROM,
    weight=1.0
)
await client.create_relationship(rel2)

# Link project contains code
rel3 = Relationship(
    from_uid=project_uid,
    to_uid=code_uid,
    relation_type=RelationType.CONTAINS,
    weight=1.0
)
await client.create_relationship(rel3)
```

### Query Nodes

```python
# Get a specific node
node = await client.get_node(project_uid)
print(f"Project: {node['name']}")
print(f"Status: {node['status']}")

# Search with full-text
cypher = """
CALL db.index.fulltext.queryNodes('node_search', $query)
YIELD node, score
RETURN properties(node) as props, labels(node) as labels, score
ORDER BY score DESC
LIMIT 10
"""

results = await client.query(
    cypher,
    {"query": "authentication JWT"}
)

for record in results:
    print(f"[{record['labels'][0]}] {record['props']['name']} (score: {record['score']:.2f})")
```

### Multi-Hop Traversal

```python
# Find the path from CodeEntity to original Requirement
paths = await client.find_path(
    from_uid=code_uid,
    to_uid=req_uid,
    max_depth=5,
    relation_types=[RelationType.IMPLEMENTS, RelationType.DERIVED_FROM]
)

for path in paths:
    nodes = path['nodes']
    relationships = path['relationships']
    
    # Print the path
    path_str = " -> ".join([f"{n['name']} ({n['type']})" for n in nodes])
    print(f"Path: {path_str}")
    
    # Print relationship types
    rel_str = " -> ".join([r['type'] for r in relationships])
    print(f"Relations: {rel_str}")
```

### Update Nodes

```python
# Update project status
await client.update_node(
    project_uid,
    {
        "status": "completed",
        "completed_at": "2024-02-06T10:30:00Z"
    }
)

# Mark as archived
await client.update_node(
    project_uid,
    {
        "archived": True,
        "archived_at": "2024-02-06T10:30:00Z",
        "archive_reason": "Project completed successfully"
    }
)
```

### Delete Nodes

```python
# Delete node and all relationships
deleted = await client.delete_node(node_uid)
if deleted:
    print("Node deleted successfully")
```

## Schema Design

### Constraints

All node types have unique UID constraints:

```cypher
CREATE CONSTRAINT project_uid IF NOT EXISTS 
FOR (p:Project) REQUIRE p.uid IS UNIQUE

CREATE CONSTRAINT decision_uid IF NOT EXISTS 
FOR (d:Decision) REQUIRE d.uid IS UNIQUE

-- ... etc for all node types
```

### Indexes

Indexes for common queries:

```cypher
-- Status queries
CREATE INDEX project_status IF NOT EXISTS 
FOR (p:Project) ON (p.status)

-- File path queries
CREATE INDEX file_path IF NOT EXISTS 
FOR (f:File) ON (f.file_path)

-- Full-text search across all node types
CREATE FULLTEXT INDEX node_search IF NOT EXISTS
FOR (n:Project|Area|Resource|Archive|Decision|Requirement|CodeEntity|Conversation)
ON EACH [n.name, n.description]
```

### Relationships

All relationship types are defined in `RelationType` enum:

```python
class RelationType(str, Enum):
    DEPENDS_ON = "DEPENDS_ON"       # Dependency between entities
    IMPLEMENTS = "IMPLEMENTS"        # Implementation of requirement
    SUPERSEDES = "SUPERSEDES"        # Replaces older decision
    BELONGS_TO = "BELONGS_TO"        # Project belongs to area
    REFERENCES = "REFERENCES"        # References external resource
    RELATES_TO = "RELATES_TO"        # General relationship
    CONTAINS = "CONTAINS"            # Container relationship
    DERIVED_FROM = "DERIVED_FROM"    # Code derived from decision
    INSPIRED_BY = "INSPIRED_BY"      # Inspired by resource
```

## Design Patterns

### Pattern 1: Architectural Decision Record (ADR)

```python
async def record_architecture_decision(
    client: Neo4jClient,
    decision_text: str,
    context: str,
    rationale: str,
    alternatives: list[str],
    implements_requirement: str | None = None
) -> str:
    """
    Record an architectural decision with full context.
    
    Returns:
        UID of created decision node
    """
    decision = DecisionNode(
        name=decision_text[:100],  # Truncate for name
        description=decision_text,
        context=context,
        decision=decision_text,
        rationale=rationale,
        alternatives=alternatives
    )
    
    decision_uid = await client.create_node(decision)
    
    # Link to requirement if specified
    if implements_requirement:
        relationship = Relationship(
            from_uid=decision_uid,
            to_uid=implements_requirement,
            relation_type=RelationType.IMPLEMENTS
        )
        await client.create_relationship(relationship)
    
    return decision_uid
```

### Pattern 2: Find Related Decisions

```python
async def find_related_decisions(
    client: Neo4jClient,
    context_keyword: str,
    limit: int = 10
) -> list[dict]:
    """
    Find decisions related to a specific context.
    
    Useful for checking if similar decisions were made before.
    """
    cypher = """
    MATCH (d:Decision)
    WHERE d.context CONTAINS $keyword OR d.decision CONTAINS $keyword
      AND NOT d.archived = true
    RETURN properties(d) as decision
    ORDER BY d.created_at DESC
    LIMIT $limit
    """
    
    results = await client.query(
        cypher,
        {"keyword": context_keyword, "limit": limit}
    )
    
    return [r['decision'] for r in results]
```

### Pattern 3: Track Code Evolution

```python
async def track_code_entity_history(
    client: Neo4jClient,
    file_path: str
) -> list[dict]:
    """
    Get the history of a code entity through decision nodes.
    
    Shows why the code was written and how it evolved.
    """
    cypher = """
    MATCH (code:CodeEntity {file_path: $file_path})
    OPTIONAL MATCH (code)-[:DERIVED_FROM]->(decision:Decision)
    OPTIONAL MATCH (decision)-[:IMPLEMENTS]->(requirement:Requirement)
    OPTIONAL MATCH (decision)-[:SUPERSEDES]->(prev_decision:Decision)
    RETURN 
        properties(code) as code,
        collect(DISTINCT properties(decision)) as decisions,
        collect(DISTINCT properties(requirement)) as requirements,
        collect(DISTINCT properties(prev_decision)) as previous_decisions
    """
    
    results = await client.query(cypher, {"file_path": file_path})
    return results
```

### Pattern 4: Project Dependency Graph

```python
async def get_project_dependencies(
    client: Neo4jClient,
    project_uid: str,
    max_depth: int = 3
) -> dict:
    """
    Get all dependencies for a project.
    
    Returns code entities, requirements, and decisions.
    """
    cypher = """
    MATCH (project:Project {uid: $uid})
    OPTIONAL MATCH (project)-[:CONTAINS]->(code:CodeEntity)
    OPTIONAL MATCH (code)-[:DEPENDS_ON*1..$max_depth]->(dep:CodeEntity)
    OPTIONAL MATCH (code)-[:DERIVED_FROM]->(decision:Decision)
    OPTIONAL MATCH (decision)-[:IMPLEMENTS]->(req:Requirement)
    RETURN 
        properties(project) as project,
        collect(DISTINCT properties(code)) as code_entities,
        collect(DISTINCT properties(dep)) as dependencies,
        collect(DISTINCT properties(decision)) as decisions,
        collect(DISTINCT properties(req)) as requirements
    """
    
    results = await client.query(
        cypher,
        {"uid": project_uid, "max_depth": max_depth}
    )
    
    return results[0] if results else {}
```

## Performance Optimization

### Use Parameterized Queries

```python
# ✅ GOOD - Uses query cache
cypher = "MATCH (n:Decision {uid: $uid}) RETURN n"
result = await client.query(cypher, {"uid": uid})

# ❌ BAD - No cache benefit
cypher = f"MATCH (n:Decision {{uid: '{uid}'}}) RETURN n"
result = await client.query(cypher)
```

### Batch Operations

```python
# Create multiple nodes in a transaction
async with client.driver.session(database=client.config.database) as session:
    async with session.begin_transaction() as tx:
        for node_data in nodes:
            await tx.run(
                "CREATE (n:Node) SET n = $props",
                props=node_data
            )
        await tx.commit()
```

### Limit Result Sets

```python
# Always use LIMIT for large result sets
cypher = """
MATCH (n:Decision)
WHERE NOT n.archived = true
RETURN n
ORDER BY n.created_at DESC
LIMIT 100
"""
```

## Error Handling

```python
import logging
from neo4j.exceptions import ServiceUnavailable, TransientError

logger = logging.getLogger(__name__)

try:
    result = await client.query(cypher, params)
except ServiceUnavailable as e:
    logger.exception("neo4j_unavailable", extra={"error": str(e)})
    # Retry logic or graceful degradation
except TransientError as e:
    logger.exception("neo4j_transient_error", extra={"error": str(e)})
    # Retry the operation
except Exception as e:
    logger.exception("neo4j_query_failed", extra={"cypher": cypher, "error": str(e)})
    raise
```

## Testing

```python
import pytest
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig
from neuralcursor.brain.neo4j.models import ProjectNode, RelationType

@pytest.fixture
async def neo4j_client():
    """Test fixture for Neo4j client."""
    config = Neo4jConfig(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test-password",
        database="test"
    )
    
    client = Neo4jClient(config)
    await client.connect()
    
    yield client
    
    # Cleanup
    await client.query("MATCH (n) DETACH DELETE n")  # Clear test data
    await client.close()

@pytest.mark.asyncio
async def test_create_and_retrieve_node(neo4j_client):
    """Test node creation and retrieval."""
    project = ProjectNode(
        name="Test Project",
        description="A test project",
        status="active"
    )
    
    uid = await neo4j_client.create_node(project)
    assert uid is not None
    
    retrieved = await neo4j_client.get_node(uid)
    assert retrieved['name'] == "Test Project"
    assert retrieved['status'] == "active"
```

## Related Documentation

- [models.py](./models.py) - Complete node and relationship models
- [schema.py](./schema.py) - Schema initialization details
- [client.py](./client.py) - Full client API reference
- [../AGENTS.md](../AGENTS.md) - Brain module overview
- [../../AGENTS.md](../../AGENTS.md) - Root documentation
