# NeuralCursor: Second Brain for Cursor IDE

## Product Requirements Document

### Vision

Transform the Cursor IDE into a context-aware system with **Architectural Intuition** - understanding not just what code is, but why it exists and how it connects across your entire local ecosystem.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Cursor IDE                              │
│                   (User Interface)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │ MCP Protocol
┌──────────────────────┴──────────────────────────────────────┐
│                  NeuralCursor MCP Server                     │
│              (Model Context Protocol Bridge)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                  FastAPI Gateway                             │
│            (Unified Memory Entry Point)                      │
└─────────┬────────────────────────────────┬──────────────────┘
          │                                │
┌─────────┴────────┐              ┌────────┴──────────┐
│   MemGPT Agent   │              │  Dual 3090 GPUs    │
│ (Working Memory) │              │   vLLM/TensorRT    │
└─────────┬────────┘              └────────┬───────────┘
          │                                │
┌─────────┴────────────────────────────────┴──────────────────┐
│                  Dual Database Layer                         │
├──────────────────────────────┬───────────────────────────────┤
│  Neo4j (Logical Brain)       │  MongoDB (Episodic Brain)     │
│  - PARA Ontology             │  - Chat Logs                  │
│  - Graph Relationships       │  - Document Chunks            │
│  - Architectural Logic       │  - External Resources         │
└──────────────────────────────┴───────────────────────────────┘
```

### Phase 1: Bio-Digital Substrate (Infrastructure)

#### Components

1. **Neo4j PARA Schema**
   - Nodes: Project, Area, Resource, Archive, Decision, Requirement, CodeEntity
   - Relationships: DEPENDS_ON, IMPLEMENTS, SUPERSEDES, RELATES_TO

2. **Dual GPU Orchestration**
   - GPU 0: Reasoning LLM (DeepSeek-Coder-33B)
   - GPU 1: Embedding & RAG (BGE-M3)

3. **FastAPI Gateway**
   - Unified memory operations API
   - Health monitoring endpoints
   - VRAM usage tracking

4. **MongoDB Atlas Extension**
   - Existing vector search
   - Add: Chat history collection
   - Add: Resource metadata collection

#### Definition of Done

- [ ] Local LLM responds with < 2.0s TTFT
- [ ] Neo4j accessible via bolt connection
- [ ] MongoDB Atlas Vector Search operational
- [ ] Health dashboard shows VRAM usage

### Phase 2: Cognitive Controller (MemGPT)

#### Components

1. **MemGPT Custom Wrapper**
   - System tools for Neo4j read/write
   - System tools for MongoDB read/write
   - Custom memory management logic

2. **Context Paging System**
   - Automatic detection of context window limits
   - Intelligent paging to long-term memory
   - Priority-based memory retention

3. **Librarian Agent (LangGraph)**
   - Monitor MongoDB "Capture" bucket
   - Distill raw notes into Neo4j nodes
   - Deduplication and consolidation

4. **Working Set Management**
   - Core Memory: Active projects and files
   - Cold Storage: Archived projects
   - Vector similarity search across both

#### Definition of Done

- [ ] MemGPT saves to both databases
- [ ] Librarian condenses 5 logs → 1 Decision node (90% accuracy)
- [ ] Memory paging visible in logs
- [ ] System resumes discussions after reboot

### Phase 3: Neural Interface (MCP Server)

#### Components

1. **MCP Tool Suite**
   - `query_architectural_graph`: Returns dependency maps
   - `retrieve_past_decisions`: Fetches reasoning for code
   - `search_resources`: Hybrid search across all sources
   - `update_context`: Manual context injection
   - `get_project_state`: Current project understanding

2. **`.cursorrules` Integration**
   - System prompt: Always check brain before answering
   - Tool usage guidelines
   - Context formatting rules

3. **File System Watcher**
   - Monitor file saves in Cursor
   - Parse AST changes
   - Update Neo4j relationships in real-time
   - < 500ms update latency

4. **Visual Feedback UI**
   - Markdown "Living Doc" generation
   - Active project context visualization
   - Mermaid graph generation

#### Definition of Done

- [ ] Cursor displays "NeuralCursor MCP"
- [ ] File save triggers Neo4j update in < 500ms
- [ ] Cursor answers "Why did we stop using X?" correctly

### Phase 4: Self-Evolution (Maintenance)

#### Components

1. **Graph Pruning System**
   - Weekly "Brain Care" routine
   - Detect broken links
   - Merge duplicate nodes
   - Archive completed projects

2. **Conflict Detection Engine**
   - Monitor code changes vs. Requirements
   - Alert on architectural drift
   - Suggest reconciliation strategies

3. **Cross-Project Synthesis**
   - Pattern detection across projects
   - Reusable component discovery
   - Knowledge transfer suggestions

4. **Hardware Optimization**
   - GPU load balancing
   - Quantization (4-bit/8-bit)
   - Context window maximization

#### Definition of Done

- [ ] De-duplication runs without data loss
- [ ] Conflict detection identifies test errors
- [ ] VRAM stable with 10,000+ nodes
- [ ] 50% faster project onboarding vs. standard RAG

### Success Metrics

#### Final Vision Test

> "Jae opens a 2-year-old project. Within 5 seconds, Cursor explains:
> - Why a specific function was written that way
> - Which YouTube video inspired the design
> - How it relates to current home server hardware
> ...all without Jae typing a single context prompt."

#### Phase-Specific Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| 1 | LLM TTFT | < 2.0s |
| 1 | 3-hop query time | < 1.0s |
| 2 | Context resume accuracy | 90%+ |
| 2 | Note distillation accuracy | 90%+ |
| 3 | Graph update latency | < 500ms |
| 3 | Context relevancy | 80%+ |
| 4 | Project onboarding speedup | 50%+ |
| 4 | Architectural regressions | 0 |

### Technology Stack

#### Core Infrastructure
- **Neo4j**: 5.x (Graph database)
- **MongoDB Atlas**: Existing vector search + new collections
- **FastAPI**: Gateway service
- **Redis**: MemGPT state management

#### LLM & Embeddings
- **vLLM**: GPU 0 - Reasoning LLM hosting
- **TensorRT-LLM**: GPU 1 - Embedding models
- **MemGPT**: Working memory controller
- **LangGraph**: Agent orchestration

#### Integration
- **MCP SDK**: Cursor protocol integration
- **Watchdog**: File system monitoring
- **Rich**: Terminal UI components
- **Mermaid**: Graph visualization

#### Development
- **UV**: Package management
- **Pydantic**: Data validation
- **PyTest**: Testing framework

### Development Phases Timeline

Each phase is independent and can be validated separately:

1. **Phase 1** (Infrastructure): Foundation setup
2. **Phase 2** (MemGPT): Cognitive layer
3. **Phase 3** (MCP): Cursor integration
4. **Phase 4** (Evolution): Self-improvement

### Next Steps

1. Setup Neo4j Docker container with PARA schema
2. Add Neo4j dependencies to `pyproject.toml`
3. Create FastAPI gateway service
4. Configure dual GPU orchestration
5. Build health monitoring dashboard
