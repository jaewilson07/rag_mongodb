# NeuralCursor: Second Brain for Cursor IDE

A persistent, context-aware "Second Brain" system that gives Cursor IDE architectural intuition through a dual-database memory layer.

## Architecture Overview

### Dual-Database Memory Layer

1. **Neo4j (The Logical Brain)**: Structural logic using PARA methodology
   - Projects, Areas, Resources, Archives
   - Decisions, Requirements, CodeEntities
   - Multi-hop relationship traversal

2. **MongoDB Atlas (The Episodic Brain)**: Contextual memory
   - Chat logs and conversations
   - Document chunks with embeddings
   - External resources (web clips, specs)

3. **MemGPT (The Working Memory)**: Stateful context management
   - Autonomous context paging
   - Working set management
   - Long-term memory coordination

### Component Structure

```
neuralcursor/
├── brain/                 # Core memory systems
│   ├── neo4j/            # Graph database (logical brain)
│   ├── mongodb/          # Document store (episodic brain)
│   └── memgpt/           # Working memory controller
├── mcp/                  # Model Context Protocol server
│   ├── tools/           # MCP tools for Cursor
│   └── server.py        # MCP server implementation
├── agents/              # Autonomous background agents
│   ├── librarian.py    # Note distillation agent
│   ├── watcher.py      # File system monitor
│   └── synthesizer.py  # Cross-project discovery
├── llm/                 # Local LLM infrastructure
│   ├── orchestrator.py # Dual 3090 load balancing
│   └── providers.py    # vLLM/TensorRT-LLM configs
├── gateway/            # FastAPI memory gateway
└── monitoring/         # Health checks & VRAM monitoring
```

## Current Implementation Status

- [x] Phase 0: Project structure and planning
- [ ] Phase 1: Bio-Digital Substrate (Infrastructure)
- [ ] Phase 2: Cognitive Controller (MemGPT)
- [ ] Phase 3: Neural Interface (MCP Server)
- [ ] Phase 4: Self-Evolution & Maintenance

## Quick Start

See [QUICKSTART.md](./QUICKSTART.md) for setup instructions.
