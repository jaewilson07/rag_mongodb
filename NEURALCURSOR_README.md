# NeuralCursor: Persistent Second Brain for Cursor IDE

A complete implementation of the architectural "Second Brain" system that gives Cursor IDE **Architectural Intuition**—understanding not just what code is, but **why it exists** and how it connects across your entire local ecosystem.

## Overview

NeuralCursor is a **persistent, context-aware memory system** that transforms Cursor from a transient chat assistant into an architectural knowledge partner. It combines:

- **Neo4j Knowledge Graph**: Structural logic following PARA methodology
- **MongoDB Atlas**: Episodic context and document storage  
- **MemGPT**: Stateful context management with working memory
- **MCP Server**: Model Context Protocol integration for Cursor
- **Dual GPU Orchestration**: Local vLLM serving on 3090s (optional)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Cursor IDE + MCP                        │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────▼────────────┐
         │   Memory Gateway        │
         │ (Unified Data Bridge)   │
         └───────┬─────────┬───────┘
                 │         │
    ┌────────────▼──┐   ┌─▼────────────────┐
    │   Neo4j       │   │   MongoDB Atlas   │
    │ (Structural)  │   │   (Episodic)      │
    │               │   │                   │
    │ • Projects    │   │ • Chat Logs       │
    │ • Decisions   │   │ • Raw Notes       │
    │ • Requirements│   │ • Documents       │
    │ • CodeEntity  │   │ • Resources       │
    │ • Resources   │   │                   │
    └───────────────┘   └───────────────────┘
           │                      │
           │    ┌─────────────────▼──────┐
           │    │  Librarian Agent        │
           │    │ (MongoDB→Neo4j)         │
           │    └─────────────────────────┘
           │
    ┌──────▼─────────────────┐
    │  File Watcher           │
    │ (AST → Neo4j Updates)   │
    └─────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- MongoDB Atlas (free M0 tier) OR local MongoDB
- Neo4j (local or Aura)
- Optional: Dual NVIDIA GPUs for local LLM serving

### Installation

```bash
# Clone repository
git clone https://github.com/jaewilson07/rag_mongodb
cd rag_mongodb

# Install dependencies
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

Edit `.env`:

```bash
# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=neuralcursor

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neuralcursor

# LLM Provider
LLM_PROVIDER=openrouter
LLM_API_KEY=your-api-key
LLM_MODEL=anthropic/claude-haiku-4.5

# Embedding Provider
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your-api-key
EMBEDDING_MODEL=text-embedding-3-small

# Optional: Local vLLM
VLLM_ENABLED=false
VLLM_REASONING_URL=http://localhost:8000
VLLM_EMBEDDING_URL=http://localhost:8001
```

### Initialize System

```bash
# Initialize Neo4j schema and check connections
python scripts/init_neuralcursor.py
```

## Components

### 1. Memory Gateway

**Location**: `src/memory_gateway/`

Unified interface for Neo4j (structural) and MongoDB (episodic) operations.

```python
from src.memory_gateway.gateway import MemoryGateway

async with MemoryGateway(settings) as gateway:
    # Query architectural context
    context = await gateway.get_architectural_context(query)
    
    # Get working set
    working_set = await gateway.get_working_set()
```

### 2. MCP Server

**Location**: `src/mcp_server/`

Exposes 6 tools to Cursor IDE via Model Context Protocol:

1. **query_architectural_graph**: Trace Requirements → Decisions → Code
2. **retrieve_past_decisions**: Show decision history and evolution
3. **search_resources**: Find videos/articles that inspired decisions
4. **get_active_project_context**: Show active projects and files
5. **find_cross_project_patterns**: Discover reusable code
6. **get_graph_statistics**: Graph health metrics

**Start MCP Server:**
```bash
python scripts/start_mcp_server.py
```

### 3. MemGPT Integration

**Location**: `src/memgpt_integration/`

Stateful context management with:
- Custom system tools for Second Brain operations
- Autonomous context paging (hot/cold storage)
- Working Set management
- Conversation checkpointing

### 4. Librarian Agent

**Location**: `src/librarian_agent/`

LangGraph-based agent that:
- Monitors MongoDB for unprocessed episodic memories
- Extracts structured entities (Decisions, Requirements, etc.)
- Creates Neo4j nodes and relationships
- Runs on configurable schedule (default: every 30 minutes)

**Start Librarian:**
```bash
python scripts/start_librarian.py
```

### 5. File Watcher

**Location**: `src/file_watcher/`

Monitors filesystem and automatically:
- Parses Python files via AST
- Extracts functions, classes, methods
- Updates Neo4j graph on file save
- Handles dependencies and relationships

**Start File Watcher:**
```bash
python scripts/start_file_watcher.py
```

### 6. Maintenance Tools

**Location**: `src/maintenance/`

Brain Care routine for graph health:

- **GraphOptimizer**: Deduplication, pruning, archiving
- **ConflictDetector**: Detects contextual drift and architectural conflicts
- **DiscoveryAgent**: Finds cross-project patterns

**Run Brain Care:**
```bash
python scripts/run_brain_care.py
```

### 7. VRAM Monitor (Optional)

**Location**: `src/llm/vram_monitor.py`

Real-time GPU monitoring dashboard for dual 3090 setup.

**Start vLLM Servers:**
```bash
python scripts/start_vllm.py
```

## Usage

### In Cursor IDE

1. **Configure MCP**: Add NeuralCursor MCP server to Cursor settings
2. **Open `.cursorrules`**: System prompt is automatically loaded
3. **Start coding**: Cursor will proactively query the Second Brain

**Example interactions:**

```
You: Why do we use Redis for caching?
Cursor: *Calls query_architectural_graph*
"Redis was chosen for the 'Improve Query Performance' requirement. 
The rationale was database queries exceeded 2s, and Redis provides 
sub-millisecond latency. This was inspired by [YouTube: Redis Crash Course]."

You: Opens src/auth/jwt.py
Cursor: *Automatically calls query_architectural_graph*
"This file implements JWT authentication for the 'Secure API Access' 
requirement. JWT was chosen over sessions for stateless architecture..."
```

### Saving Decisions

Decisions are automatically captured by:
1. **MemGPT**: Listens to conversations
2. **Librarian Agent**: Processes chat logs every 30 minutes
3. **Manual**: Via MCP tools in Cursor

### Viewing Context

```bash
# Visual dashboard
open src/context_dashboard/dashboard.html

# VRAM monitor (if using local LLMs)
open data/vram_dashboard.html

# Graph statistics
python -c "
from src.memory_gateway.gateway import MemoryGateway
from src.settings import load_settings
import asyncio

async def main():
    settings = load_settings()
    async with MemoryGateway(settings) as gw:
        stats = await gw.get_graph_stats()
        print(stats)

asyncio.run(main())
"
```

## Neo4j Schema (PARA)

**Nodes:**
- `Project`: Goal-oriented work with deadlines
- `Area`: Ongoing responsibilities
- `Decision`: Architectural or design choices
- `Requirement`: Functional/non-functional needs
- `CodeEntity`: Functions, classes, modules, files
- `Resource`: Videos, articles, papers, tutorials

**Relationships:**
- `DEPENDS_ON`: Dependency between entities
- `IMPLEMENTS`: Decision → CodeEntity
- `SUPERSEDES`: New decision replaces old
- `INSPIRED_BY`: Resource → Decision
- `HAS_DECISION`: Project → Decision
- `HAS_REQUIREMENT`: Project → Requirement
- `CONTAINS`: Project → CodeEntity

## Key Queries

### Why does this code exist?
```cypher
MATCH path = (req:Requirement)-[:IMPLEMENTS]->(dec:Decision)-[:IMPLEMENTS]->(code:CodeEntity)
WHERE code.file_path = $file_path
OPTIONAL MATCH (dec)-[:SUPERSEDES]->(old_dec:Decision)
OPTIONAL MATCH (dec)<-[:INSPIRED_BY]-(res:Resource)
RETURN path, old_dec, res
```

### Find cross-project patterns
```cypher
MATCH (code:CodeEntity {entity_type: 'function'})
MATCH (p:Project)-[:CONTAINS]->(code)
WITH code, collect(DISTINCT p) as projects
WHERE size(projects) >= 2
RETURN code.name, projects, size(projects) as usage_count
```

### Decision history
```cypher
MATCH (code:CodeEntity {uuid: $uuid})<-[:IMPLEMENTS]-(dec:Decision)
OPTIONAL MATCH (dec)-[:SUPERSEDES*]->(old_dec:Decision)
RETURN dec, collect(old_dec) as history
ORDER BY dec.decided_at DESC
```

## Performance

- **Query latency**: <100ms for architectural queries
- **Graph updates**: <500ms on file save
- **Librarian cycle**: ~30 seconds for 50 documents
- **Brain Care**: ~2-5 minutes for 10,000 nodes
- **Local LLM** (optional): <2s time-to-first-token on 3090

## Maintenance

### Weekly Brain Care

Run automated maintenance:
```bash
python scripts/run_brain_care.py
```

This will:
- ✅ Merge duplicate nodes
- ✅ Archive completed projects
- ✅ Fix broken relationships
- ✅ Detect conflicts
- ✅ Discover patterns
- ✅ Provide recommendations

### Monitor Health

```bash
# Graph statistics
python -m src.mcp_server.tools get_graph_statistics

# Active context
python -m src.mcp_server.tools get_active_project_context
```

## Troubleshooting

### Neo4j Connection Failed
```bash
# Check Neo4j is running
neo4j status

# Verify credentials in .env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

### MongoDB Connection Failed
```bash
# Test connection
python -c "
from pymongo import MongoClient
client = MongoClient('your-mongodb-uri')
print(client.admin.command('ping'))
"
```

### MCP Server Not Responding
```bash
# Check if server is running
ps aux | grep start_mcp_server

# Restart server
python scripts/start_mcp_server.py
```

## Project Structure

```
neuralcursor/
├── src/
│   ├── integrations/
│   │   └── neo4j/          # Neo4j client, schema, models, queries
│   ├── memory_gateway/     # Unified Neo4j + MongoDB interface
│   ├── mcp_server/         # MCP server and tools
│   ├── memgpt_integration/ # MemGPT wrapper and context manager
│   ├── librarian_agent/    # Knowledge distillation agent
│   ├── file_watcher/       # AST parser and file monitor
│   ├── llm/                # vLLM config and VRAM monitor
│   ├── maintenance/        # Graph optimizer, conflict detector, discovery
│   └── context_dashboard/  # Visual context dashboard
├── scripts/
│   ├── init_neuralcursor.py      # Initialize system
│   ├── start_mcp_server.py       # Start MCP server
│   ├── start_librarian.py        # Start Librarian agent
│   ├── start_file_watcher.py     # Start file watcher
│   ├── start_vllm.py             # Start local LLMs (optional)
│   └── run_brain_care.py         # Run maintenance
├── .cursorrules            # Cursor system prompt
├── .env.example            # Environment template
└── NEURALCURSOR_README.md  # This file
```

## Success Metrics

The system is successful when:

> You can open a 2-year-old project, and Cursor—within 5 seconds—can explain 
> exactly why a specific function was written the way it was, which YouTube video 
> inspired the design, and how it relates to the current architecture.

**Achieved when:**
- ✅ Zero "I don't know why this code exists"
- ✅ Every architectural question has a graph-backed answer
- ✅ Context persists across reboots and sessions
- ✅ Cross-project patterns are discoverable
- ✅ Time to onboard to old projects reduced by 50%+

## Contributing

See the main repository README for contribution guidelines.

## License

MIT License - see LICENSE file

## Acknowledgments

Built on top of the MongoDB RAG Agent foundation, with inspiration from:
- Tiago Forte's PARA method
- MemGPT for stateful memory management
- Model Context Protocol (MCP) for IDE integration
- Neo4j for knowledge graphs

---

**Created by**: NeuralCursor Development Team  
**Version**: 1.0.0  
**Last Updated**: 2026-02-06
