# Project Reorganization Specification

## 1. Executive Summary
This document outlines a plan to reorganize the `MongoDB-RAG-Agent` repository. The goal is to transition from a flat, sprawling `src/` directory to a structured, layered architecture that clearly separates **Infrastructure**, **Core Domain Logic**, **Integrations**, and **User Interfaces**. This structure is designed to support containerization (Docker) and multiple frontend consumers (FastAPI, MCP, Web, CLI).

## 2. Architectural Principles

We will adopt a **Layered Architecture** (similar to Clean Architecture or Hexagonal Architecture) to enforce boundaries.

1.  **Core / Domain Layer**: Contains the business logic (RAG orchestration, Document processing, "The Brain"). Agnostic of the interface (CLI vs API).
2.  **Infrastructure Layer**: Handles low-level operations (Database connections, Vector Store drivers, Logging, Telemetry).
3.  **Integrations Layer**: Adapters for external services (Google Drive, Confluence, Jira, Neo4j).
4.  **Interface / Application Layer**: The entry points for the user. These act as "Hosts" that wire up the lower layers.
    *   **API**: FastAPI server.
    *   **MCP**: Model Context Protocol server.
    *   **CLI**: Command-line tools.
    *   **Frontend**: Next.js web application.

## 3. Proposed Directory Structure

```text
/
├── docker/                     # Docker infrastructure
│   ├── compose/                # Compose files (split by environment/purpose)
│   │   ├── base.yml
│   │   ├── dev.yml
│   │   └── prod.yml
│   ├── Dockerfile.api          # Backend API
│   ├── Dockerfile.mcp          # MCP Server
│   ├── Dockerfile.worker       # Async workers (if needed)
│   └── services/               # Service-specific configs (e.g., searxng config)
│
├── docs/                       # Project documentation
│
├── frontend/                   # Existing Next.js application (User Interface)
│   ├── ...
│   └── Dockerfile
│
├── scripts/                    # Devops / Utility scripts (non-production code)
│
├── src/                        # The Monorepo "Backend" Python Package
│   ├── core/                   # Shared low-level building blocks
│   │   ├── config.py           # Settings management (Pydantic)
│   │   ├── database.py         # MongoDB connection factories
│   │   ├── logging.py
│   │   ├── exceptions.py
│   │   └── telemetry.py
│   │
│   ├── domain/                 # Core Business Logic (The "Services")
│   │   ├── ingestion/          # Document processing pipelines
│   │   ├── retrieval/          # Vector search logic, RAG strategies
│   │   ├── orchestration/      # LangGraph agents, "Librarian", "Brain"
│   │   └── validation/         # Data validation logic
│   │
│   ├── integrations/           # Adapters for External Systems (was _services)
│   │   ├── confluence/
│   │   ├── google_drive/
│   │   ├── jira/
│   │   ├── neo4j/
│   │   └── llm/                # LLM Provider wrappers (OpenAI, Anthropic)
│   │
│   └── interfaces/             # Application Entry Points
│       ├── api/                # FastAPI Application
│       │   ├── main.py
│       │   ├── routers/
│       │   └── dependencies.py
│       │
│       ├── mcp/                # MCP Server Implementation
│       │   ├── server.py
│       │   └── tools.py
│       │
│       └── cli/                # CLI Commands
│           └── main.py
│
├── tests/                      # Mirror of src structure
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── .env.example
├── pyproject.toml              # Single source of truth for python dependencies
└── README.md
```

## 4. Layered Service Orchestration & Docker

### Docker Strategy
Instead of cluttering the root with `docker-compose.yml` files, we move them to `docker/compose/`.
*   **Core Infrastructure**: MongoDB, Neo4j, Redis/Qdrant (if used), vLLM.
*   **Application Services**: The Python code will be built into images targeted for specific interfaces (API, MCP).

### Service orchestration
The `src/domain/orchestration` layer is where the "Agent" lives.
*   **API Container**: Mounts `src`, runs `uvicorn src.interfaces.api.main:app`. Exposes REST endpoints that call `domain` services.
*   **MCP Container**: Mounts `src`, runs the MCP STDIO or SSE server. Reuses the exact same `domain` logic as the API.
*   **Worker Container** (Optional): If ingestion is heavy, a Celery/Dramatiq worker can run here, importing from `domain.ingestion`.

## 5. Migration Steps

1.  **Consolidate configuration**: Ensure `settings.py` (to be moved to `src/core/config.py`) can load environment variables consistently for all interfaces.
2.  **Move "Core" utilities**: Identify logging, DB connections, and base types. Move to `src/core`.
3.  **Migrate Integrations**: Move `_services/*` and `src/integrations/*` to `src/integrations/`. Standardize their interfaces.
4.  **Refactor Domain**: Identify the "Business Logic" in `src/agent.py`, `src/librarian_agent`, etc., and organize into `src/domain/`.
5.  **Setup Interfaces**:
    *   Refactor `src/server` -> `src/interfaces/api`.
    *   Refactor `src/mcp_server` -> `src/interfaces/mcp`.
    *   Refactor `src/cli.py` -> `src/interfaces/cli`.
6.  **Update Docker**: Create the new Docker structure and update paths.

## 6. Key Benefits

*   **DRY (Don't Repeat Yourself)**: The API, CLI, and MCP server all import the exact same logic from `src/domain`.
*   **Testability**: `domain` logic can be unit tested without spinning up an HTTP server.
*   **Scalability**: We can deploy just the API, or just the Worker, or just the MCP server depending on needs.
*   **Clarity**: New developers know exactly where "DB stuff" goes vs "Business Logic" vs "HTTP Handling".
