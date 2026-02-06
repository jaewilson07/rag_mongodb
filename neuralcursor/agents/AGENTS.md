# Autonomous Background Agents

## Overview

The agents module provides autonomous background services that handle long-running tasks without user intervention. These agents maintain graph health, distill conversations, monitor changes, and discover patterns.

## Agents Overview

```
agents/
├── __init__.py
├── librarian.py         # Conversation distillation (MongoDB → Neo4j)
├── watcher.py          # File system monitoring
├── optimizer.py        # Graph maintenance and cleanup
├── conflict_detector.py # Architectural drift detection
└── synthesizer.py      # Cross-project pattern discovery
```

## Agent Architecture

All agents follow a common pattern:
1. **Initialization** with Neo4j/MongoDB clients
2. **Background loop** with configurable intervals
3. **Graceful shutdown** on termination signals
4. **Structured logging** for observability

## Librarian Agent

### Purpose

Distills raw conversation logs (MongoDB) into structured knowledge graph nodes (Neo4j).

### Workflow

```
MongoDB Session → Summarize → Extract Decisions → Create Graph Nodes → Mark Complete
```

### Usage

```python
from neuralcursor.agents.librarian import LibrarianAgent

librarian = LibrarianAgent(neo4j_client, mongodb_client)

# Process a single session
session = await mongodb_client.get_session("session_123")
conversation_uid = await librarian.distill_session(session)

# Or run continuous background loop
await librarian.run_distillation_loop(
    interval_seconds=300,  # Check every 5 minutes
    batch_size=5          # Process up to 5 sessions at once
)
```

### Configuration

```bash
# No specific env vars, uses LLM orchestrator
# Runs automatically when orchestrator starts
```

### Output

Creates Neo4j nodes:
- **ConversationNode**: Summary and key points
- **DecisionNode(s)**: Extracted architectural decisions
- **Relationships**: Links between conversation and decisions

See [Librarian Implementation Details](./librarian.py)

## File Watcher Agent

### Purpose

Monitors file system for changes and automatically updates Neo4j graph.

### Workflow

```
File Change → Debounce → Hash Check → Update FileNode → Extract CodeEntities
```

### Usage

```python
from neuralcursor.agents.watcher import FileSystemWatcherService

watcher = FileSystemWatcherService(neo4j_client)

# Start watching
await watcher.start()

# Stop watching
await watcher.stop()
```

### Configuration

```bash
NEURALCURSOR_WATCHER_ENABLED=true
NEURALCURSOR_WATCHER_DEBOUNCE_SECONDS=2
NEURALCURSOR_WATCHER_IGNORE_PATTERNS='["**/__pycache__/**","**/.git/**"]'
NEURALCURSOR_PROJECT_ROOT=/path/to/project
```

### Events Tracked

- **File Created**: Creates FileNode
- **File Modified**: Updates content hash, timestamp
- **File Deleted**: Archives FileNode

### Supported Languages

```python
language_map = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".rs": "rust",
    # ... and more
}
```

See [File Watcher Implementation](./watcher.py)

## Graph Optimizer Agent

### Purpose

Maintains graph health through periodic maintenance routines.

### Workflow

```
Find Duplicates → Cleanup Broken Links → Archive Old Projects → Generate Stats
```

### Usage

```python
from neuralcursor.agents.optimizer import GraphOptimizer

optimizer = GraphOptimizer(neo4j_client)

# Run single optimization cycle
summary = await optimizer.run_optimization_cycle()

print(f"Health Score: {summary['health_score']}/100")
print(f"Duplicates Found: {summary['actions']['duplicates_found']}")
print(f"Projects Archived: {summary['actions']['projects_archived']}")

# Or run weekly cycle
await optimizer.run_weekly_cycle(interval_days=7)
```

### Operations

**1. Duplicate Detection**
```python
duplicates = await optimizer.find_duplicate_nodes()
# Finds nodes with same name and type
```

**2. Broken Relationship Cleanup**
```python
cleaned = await optimizer.cleanup_broken_relationships()
# Removes dangling relationships
```

**3. Project Archival**
```python
archived = await optimizer.archive_completed_projects(days_inactive=90)
# Archives completed projects not touched in 90 days
```

**4. Graph Statistics**
```python
stats = await optimizer.compute_graph_stats()
# Returns node counts, relationships, orphaned nodes, etc.
```

### Health Scoring

```python
health_score = 100
if orphaned_nodes > 10: health_score -= 10
if duplicates > 5: health_score -= 10
if total_nodes > 10000: health_score -= 5
```

See [Optimizer Implementation](./optimizer.py)

## Conflict Detector Agent

### Purpose

Identifies architectural drifts and contradictions using LLM semantic analysis.

### Workflow

```
Monitor Changes → Detect Conflicts → Analyze with LLM → Alert User
```

### Usage

```python
from neuralcursor.agents.conflict_detector import ConflictDetector

detector = ConflictDetector(neo4j_client)

# Check a specific requirement
conflicts = await detector.check_requirement_conflicts("req_uid_123")

for conflict in conflicts:
    print(f"Conflict: {conflict['type']}")
    print(f"Severity: {conflict['severity']}")
    print(f"Explanation: {conflict['explanation']}")
    print(f"Recommendation: {conflict['recommendation']}")

# Check a new decision
conflicts = await detector.check_decision_conflicts("decision_uid_456")

# Full graph scan
scan_results = await detector.scan_for_conflicts()
print(f"Total conflicts: {scan_results['total_conflicts']}")
```

### Conflict Types

**1. Requirement vs Decision**
- New decision contradicts existing requirement
- Severity: medium to high

**2. Decision vs Decision**
- New decision contradicts previous decision
- Severity: high (potential regression)

**3. Code vs Requirement**
- Implementation deviates from documented requirement
- Severity: medium

### LLM Analysis

Uses reasoning LLM to detect semantic conflicts:

```python
prompt = """
Analyze these two statements for conflicts:

Statement 1: {text1}
Statement 2: {text2}

CONFLICT: [YES or NO]
SEVERITY: [low, medium, high]
EXPLANATION: [brief explanation]
RECOMMENDATION: [what to do]
"""
```

See [Conflict Detector Implementation](./conflict_detector.py)

## Cross-Project Synthesizer Agent

### Purpose

Discovers patterns and reusable components across different projects.

### Workflow

```
Scan Projects → Find Similar Patterns → Check Reusability → Generate Report
```

### Usage

```python
from neuralcursor.agents.synthesizer import CrossProjectSynthesizer

synthesizer = CrossProjectSynthesizer(neo4j_client)

# Find similar patterns in a project
patterns = await synthesizer.find_similar_patterns("project_uid_123")

for pattern in patterns:
    print(f"Found: {pattern['source_entity']} in {pattern['source_project']}")
    print(f"Similar to: {pattern['similar_entity']} in {pattern['target_project']}")

# Discover reusable utilities
utilities = await synthesizer.discover_reusable_utilities()

for util in utilities:
    print(f"Utility: {util['name']}")
    print(f"Used {util['usage_count']} times in {util['project']}")
    print(f"Suggestion: {util['suggestion']}")

# Find common decisions across projects
common = await synthesizer.find_common_decisions()

for decision in common:
    print(f"Pattern: {decision['pattern']}")
    print(f"Projects: {decision['project1']} & {decision['project2']}")
    print(f"Similarity: {decision['similarity_score']}%")

# Full synthesis cycle
summary = await synthesizer.run_synthesis_cycle()
print(f"Total discoveries: {summary['total_discoveries']}")
```

### Discovery Types

**1. Reusable Utilities**
- Functions used multiple times
- High internal connectivity
- Potential for shared library

**2. Common Decisions**
- Similar decisions across projects
- Potential design patterns
- Knowledge transfer opportunities

**3. Similar Patterns**
- Code patterns appearing in multiple places
- Naming conventions
- Architectural similarities

See [Synthesizer Implementation](./synthesizer.py)

## Agent Orchestration

All agents are managed by the main orchestrator:

```python
from neuralcursor.orchestrator import NeuralCursorOrchestrator

orchestrator = NeuralCursorOrchestrator()
await orchestrator.run()
```

This starts:
- **Librarian**: Background distillation loop
- **Watcher**: File system monitoring
- **Optimizer**: Weekly maintenance cycle
- **GPU Monitor**: VRAM tracking

Conflict Detector and Synthesizer run on-demand or via scheduler.

## Design Patterns

### Pattern 1: Agent Initialization

```python
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig
from neuralcursor.brain.mongodb.client import MongoDBClient, MongoDBConfig
from neuralcursor.agents.librarian import LibrarianAgent

async def init_agent():
    # Setup clients
    neo4j = Neo4jClient(Neo4jConfig(...))
    await neo4j.connect()
    
    mongodb = MongoDBClient(MongoDBConfig(...))
    await mongodb.connect()
    
    # Create agent
    agent = LibrarianAgent(neo4j, mongodb)
    
    return agent, neo4j, mongodb

agent, neo4j, mongodb = await init_agent()
```

### Pattern 2: Background Loop with Graceful Shutdown

```python
import asyncio
import signal

class CustomAgent:
    def __init__(self):
        self._running = False
    
    async def run_loop(self, interval_seconds: int = 300):
        self._running = True
        
        while self._running:
            try:
                # Do work
                await self.process_batch()
                
            except Exception as e:
                logger.exception("agent_error", extra={"error": str(e)})
            
            await asyncio.sleep(interval_seconds)
    
    def stop(self):
        self._running = False

# Setup signal handlers
agent = CustomAgent()

def handle_shutdown(sig):
    logger.info("shutdown_signal_received", extra={"signal": sig})
    agent.stop()

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

# Run
await agent.run_loop()
```

### Pattern 3: Agent Health Monitoring

```python
async def monitor_agent_health(agents: dict) -> dict:
    """
    Monitor health of all agents.
    
    Returns:
        Health status for each agent
    """
    health = {}
    
    for name, agent in agents.items():
        if hasattr(agent, 'get_health'):
            health[name] = await agent.get_health()
        else:
            health[name] = {
                "status": "unknown",
                "running": getattr(agent, '_running', False)
            }
    
    return health
```

## Performance Considerations

### Librarian Agent

- **Batch Size**: Process 5-10 sessions per cycle
- **Interval**: 5-10 minutes between cycles
- **LLM Latency**: ~2-5 seconds per session

### File Watcher

- **Debounce**: 2 seconds to avoid duplicate events
- **Ignored Patterns**: Exclude node_modules, .git, etc.
- **Update Latency**: < 500ms from save to graph update

### Optimizer

- **Run Frequency**: Weekly (7 days)
- **Processing Time**: 10-60 seconds per cycle
- **Resource Usage**: Low (Cypher queries)

### Conflict Detector

- **LLM Calls**: 1 per conflict check
- **Scan Time**: 30-120 seconds for full graph
- **Recommended**: Run on-demand or nightly

### Synthesizer

- **LLM Calls**: Multiple per similarity check
- **Scan Time**: 60-300 seconds for full analysis
- **Recommended**: Run weekly or on-demand

## Error Handling

All agents use consistent error handling:

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = await agent_operation()
except SpecificError as e:
    logger.exception("agent_operation_failed", extra={
        "agent": "librarian",
        "operation": "distill_session",
        "error": str(e)
    })
    # Continue processing other items
except Exception as e:
    logger.exception("agent_unexpected_error", extra={"error": str(e)})
    raise
```

## Testing

```python
import pytest
from neuralcursor.agents.librarian import LibrarianAgent

@pytest.mark.asyncio
async def test_librarian_distillation(neo4j_client, mongodb_client):
    """Test conversation distillation."""
    librarian = LibrarianAgent(neo4j_client, mongodb_client)
    
    # Create test session
    from neuralcursor.brain.mongodb.client import ChatMessage, ConversationSession
    
    session = ConversationSession(
        session_id="test_123",
        messages=[
            ChatMessage(role="user", content="Should we use Redux or Zustand?"),
            ChatMessage(role="assistant", content="Let's use Zustand because..."),
        ]
    )
    
    # Insert session
    await mongodb_client.db.sessions.insert_one(session.model_dump())
    
    # Distill
    conversation_uid = await librarian.distill_session(session)
    
    assert conversation_uid is not None
    
    # Verify Neo4j node created
    node = await neo4j_client.get_node(conversation_uid)
    assert node is not None
    assert 'Zustand' in node['summary']
```

## Troubleshooting

### Librarian Not Processing Sessions

**Check:**
```python
# Verify sessions exist
sessions = await mongodb_client.get_sessions_for_distillation(min_messages=5)
print(f"Sessions ready: {len(sessions)}")

# Check distillation status
session = await mongodb_client.get_session("session_123")
print(f"Distilled: {session.metadata.get('distilled', False)}")
```

### File Watcher Not Detecting Changes

**Check:**
```bash
# Verify watcher is enabled
echo $NEURALCURSOR_WATCHER_ENABLED

# Check ignore patterns
echo $NEURALCURSOR_WATCHER_IGNORE_PATTERNS

# Test file detection
touch test_file.py
# Should appear in logs within 2 seconds
```

### Optimizer Health Score Low

**Check:**
```python
# Get detailed stats
stats = await optimizer.compute_graph_stats()
print(f"Orphaned nodes: {stats['orphaned_nodes']}")
print(f"Duplicates: ...")

# Run manual cleanup
await optimizer.cleanup_broken_relationships()
duplicates = await optimizer.find_duplicate_nodes()
```

## Related Documentation

- [librarian.py](./librarian.py) - Conversation distillation implementation
- [watcher.py](./watcher.py) - File system monitoring implementation
- [optimizer.py](./optimizer.py) - Graph maintenance implementation
- [conflict_detector.py](./conflict_detector.py) - Conflict detection implementation
- [synthesizer.py](./synthesizer.py) - Pattern discovery implementation
- [../AGENTS.md](../AGENTS.md) - Root documentation
- [../orchestrator.py](../orchestrator.py) - Main orchestration
