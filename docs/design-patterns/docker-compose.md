# Docker Compose Design Patterns for MongoDB RAG Agent

## Overview
This document describes the Docker Compose configuration patterns used in the MongoDB RAG Agent project, including port mapping, service dependencies, and environment variable management. It also highlights best practices for avoiding conflicts between compose files and the .env file.

## Service Ports and Host Mapping
- **MongoDB**: Exposed on host port 7017 → container 27017
- **Mongot (Atlas Search)**: Exposed on host port 7027 → container 27027
- **SearXNG**: Exposed on host port 7080 → container 8080
- **Frontend (DeepWiki)**: Exposed on host port 3000 → container 3000

These ports are chosen to avoid conflicts with other local infrastructure and are referenced in `docker-compose.yml` and `.env` as needed.

The frontend (`wiki-frontend`) proxies all API requests to the `rag-agent` backend on port 8000. Ensure `rag-agent` is running when using the frontend.

## Environment Variables
- All sensitive and environment-specific values (e.g., database credentials, API keys) are set in the `.env` file and referenced in compose files using `${VAR}` syntax.
- The `.env` file should be the single source of truth for credentials and connection strings.
- Example: `MONGODB_URI=mongodb://admin:admin123@localhost:7017/rag_db?authSource=admin`

## Compose File Patterns
- Use `depends_on` and `healthcheck` to ensure service startup order and readiness.
- Use named volumes for persistent data.
- Use a dedicated Docker network (`rag_network`) for service isolation.
- Avoid hardcoding secrets in compose files; always use environment variables.

## Conflict Avoidance
- Ensure that the ports in the compose files (7017, 7027, 7080) match those referenced in `.env` and application settings.
- Do not map multiple services to the same host port.
- If you change a port in one place (e.g., SearXNG to 7080), update all references in `.env`, compose files, and settings.

## Example Compose Snippet
```yaml
services:
  atlas-local:
    ports:
      - "7017:27017"
  mongot:
    ports:
      - "7027:27027"
  searxng:
    ports:
      - "7080:8080"
  wiki-frontend:
    ports:
      - "3000:3000"
```

## Best Practices
- Use `.env` for all secrets and connection details.
- Document any port or service changes in [AGENTS.md](../../AGENTS.md) and this file.
- Validate with `docker-compose up -d` and check for port conflicts.
- Use `docker ps` to verify port mappings.

## See Also
- [Ingestion Pipeline Validation](ingestion-validation.md) - Validation patterns for ingestion services
- [Document Ingestion](document_ingestion.md) - Docker configuration conventions

---

_Last updated: 2026-02-09_
