# NeuralCursor Quick Start Guide

Get your Second Brain running in under 10 minutes.

## Prerequisites

- Python 3.11+
- Neo4j database (Docker or hosted)
- MongoDB instance (or MongoDB Atlas)
- Dual NVIDIA 3090 GPUs (or modify config for your setup)
- UV package manager

## Installation

### 1. Install Dependencies

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
cd /path/to/your/repo
uv sync
```

### 2. Start Database Services

#### Option A: Docker Compose (Recommended)

```bash
# Create docker-compose.yml
cat > docker-compose-neuralcursor.yml << 'EOF'
version: '3.8'

services:
  neo4j:
    image: neo4j:5.14-enterprise
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/your-password-here
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
    volumes:
      - neo4j_data:/data

  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

volumes:
  neo4j_data:
  mongo_data:
EOF

# Start services
docker-compose -f docker-compose-neuralcursor.yml up -d
```

#### Option B: Cloud Services

- **Neo4j**: Use Neo4j Aura Free tier
- **MongoDB**: Use MongoDB Atlas Free tier

### 3. Configure Environment

```bash
# Copy example config
cp .env.neuralcursor.example .env

# Edit with your settings
nano .env
```

**Minimum required config:**

```bash
# Neo4j
NEURALCURSOR_NEO4J_URI=bolt://localhost:7687
NEURALCURSOR_NEO4J_PASSWORD=your-password-here

# MongoDB
NEURALCURSOR_MONGODB_URI=mongodb://localhost:27017

# LLM Endpoints (assumes you have vLLM servers running)
NEURALCURSOR_REASONING_LLM_HOST=http://localhost:8000
NEURALCURSOR_EMBEDDING_LLM_HOST=http://localhost:8001
```

### 4. Start Local LLM Servers (Dual 3090 Setup)

**Terminal 1: Reasoning LLM (GPU 0)**

```bash
# Using vLLM
uv pip install vllm

python -m vllm.entrypoints.openai.api_server \
  --model deepseek-ai/deepseek-coder-33b-instruct \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9 \
  --device cuda:0 \
  --port 8000
```

**Terminal 2: Embedding Model (GPU 1)**

```bash
# Using sentence-transformers with vLLM
python -m vllm.entrypoints.openai.api_server \
  --model BAAI/bge-m3 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.5 \
  --device cuda:1 \
  --port 8001
```

### 5. Start NeuralCursor Services

**Terminal 3: FastAPI Gateway**

```bash
source .venv/bin/activate
python -m neuralcursor.gateway.server
```

**Terminal 4: MCP Server (for Cursor)**

```bash
source .venv/bin/activate
python -m neuralcursor.mcp.server
```

**Terminal 5: Librarian Agent (optional, for background distillation)**

```bash
source .venv/bin/activate
python -m neuralcursor.agents.librarian
```

**Terminal 6: Health Monitoring Dashboard**

```bash
source .venv/bin/activate
python -m neuralcursor.monitoring.dashboard
```

## Verify Installation

### Check Gateway Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "mongodb_connected": true
}
```

### Check Neo4j Schema

Open Neo4j Browser at `http://localhost:7474` and run:

```cypher
CALL db.schema.visualization()
```

You should see the PARA ontology nodes.

### Test MCP Server

```bash
# Install websocat for WebSocket testing
brew install websocat  # macOS

# Connect to MCP server
websocat ws://localhost:8765
```

Send a test message:
```json
{
  "tool": "get_active_context",
  "params": {}
}
```

## Configure Cursor IDE

### 1. Add MCP Configuration

Create or edit `~/.cursor/mcp.json`:

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

### 2. Verify in Cursor

1. Open Cursor IDE
2. Open Command Palette (Cmd/Ctrl + Shift + P)
3. Search for "MCP: Show Active Servers"
4. Verify "neuralcursor" is listed and connected

### 3. Test Integration

In Cursor, ask:
```
What architectural decisions have we made recently?
```

Cursor should call `retrieve_past_decisions` via MCP.

## First Use

### Create Your First Project Node

```python
import asyncio
from neuralcursor.brain.neo4j.client import Neo4jClient, Neo4jConfig
from neuralcursor.brain.neo4j.models import ProjectNode
from neuralcursor.settings import get_settings

async def create_first_project():
    settings = get_settings()
    
    config = Neo4jConfig(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    
    client = Neo4jClient(config)
    await client.connect()
    
    project = ProjectNode(
        name="NeuralCursor Development",
        description="Building a second brain for Cursor IDE",
        status="active",
        goals=[
            "Implement dual-database architecture",
            "Integrate with Cursor via MCP",
            "Enable persistent memory across sessions"
        ],
        technologies=["Neo4j", "MongoDB", "FastAPI", "MCP", "vLLM"]
    )
    
    uid = await client.create_node(project)
    print(f"Created project node: {uid}")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(create_first_project())
```

### Start Using in Cursor

Now when you work in Cursor:

1. **Make a decision** - The brain will capture it
2. **Edit files** - File watcher updates the graph automatically
3. **Ask "why"** - Cursor queries the Second Brain
4. **Switch projects** - Context persists across sessions

## Monitoring

### VRAM Dashboard

```bash
python -m neuralcursor.monitoring.dashboard
```

Shows real-time GPU usage, system resources, and connection status.

### Neo4j Browser

Navigate to `http://localhost:7474` to visualize the knowledge graph.

### Gateway API Docs

Navigate to `http://localhost:8000/docs` to see FastAPI interactive documentation.

## Troubleshooting

### MCP Server Won't Start

Check ports:
```bash
lsof -i :8765
```

### Neo4j Connection Failed

Verify Neo4j is running:
```bash
docker ps | grep neo4j
```

Check logs:
```bash
docker logs <neo4j-container-id>
```

### GPU Out of Memory

Reduce model size or adjust `--gpu-memory-utilization`:
```bash
# For smaller VRAM
--gpu-memory-utilization 0.7
```

Or use quantized models:
```bash
--quantization awq
```

### File Watcher Not Detecting Changes

Check ignore patterns in `.env`:
```bash
NEURALCURSOR_WATCHER_IGNORE_PATTERNS='["**/__pycache__/**","**/.git/**"]'
```

## Next Steps

- [Architecture Deep Dive](./docs/architecture.md)
- [MCP Tool Reference](./docs/mcp-tools.md)
- [Graph Query Examples](./docs/cypher-examples.md)
- [MemGPT Configuration](./docs/memgpt-config.md)

## Support

- GitHub Issues: Report bugs and feature requests
- Documentation: Full docs in `/docs`
- Community: Join discussions

---

**🎉 Congratulations!** Your Second Brain is now running. Cursor now has persistent architectural memory.
