## Service Ports and Host Mapping
- **MongoDB**: Exposed on host port 7017 → container 27017
- **Mongot (Atlas Search)**: Exposed on host port 7027 → container 27027
- **SearXNG**: Exposed on host port 7080 → container 8080
- **vLLM**: Exposed on host port 11435 → container 8000
- **LiteLLM**: Exposed on host port 4000 → container 4000 (standard LiteLLM port)
- **Frontend (DeepWiki)**: Exposed on host port 3000 → container 3000
- **RAG Agent API**: Exposed on host port 8000 → container 8000

These ports are chosen to avoid conflicts with other local infrastructure and are referenced in `docker-compose.yml` and `.env` as needed. Most services use the 7000-7500 range; exceptions are documented above (LiteLLM uses standard port 4000).

The frontend (`wiki-frontend`) proxies all API requests to the `rag-agent` backend on port 8000. Ensure `rag-agent` is running when using the frontend.

## Environment Variables
- All sensitive and environment-specific values (e.g., database credentials, API keys) are set in the `.env` file and referenced in compose files using `${VAR}` syntax.
- All services use `env_file: [.env]` to source environment variables consistently.
- The `.env` file should be the single source of truth for credentials and connection strings.
- Example: `MONGODB_URI=mongodb://admin:admin123@localhost:7017/rag_db?authSource=admin`

## Compose File Patterns
- Use `depends_on` and `healthcheck` to ensure service startup order and readiness.
- All HTTP services should have healthchecks for reliability.
- Use named volumes for persistent data.
- Use a dedicated Docker network (`rag_network`) for service isolation.
- All services use explicit `container_name:` (format: `{project}-{service}`) for consistent CLI experience.
- Avoid hardcoding secrets in compose files; always use environment variables.
- Use `env_file: [.env]` for all services to ensure consistent environment variable sourcing.

### Network Configuration Pattern
- Main `docker-compose.yml` defines `rag_network` as a local bridge network.
- Included compose files (e.g., `docker-compose.vllm.yml`) reference the same `rag_network` without `external: true`.
- When running vLLM compose standalone, it creates its own `rag_network`.
- When included via main compose, services share the parent's network.
- **Never use `external: true` with explicit network name** in compose files that may be included—this causes network conflicts.

### Healthcheck Patterns
All HTTP services should have appropriate healthchecks:

```yaml
# MongoDB (using mongosh)
healthcheck:
  test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s

# HTTP services (using wget)
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:PORT"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s

# API services (using curl)
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:PORT/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

## Conflict Avoidance
- Ensure that the ports in the compose files (7017, 7027, 7080, etc.) match those referenced in `.env` and application settings.
- Do not map multiple services to the same host port.
- If you change a port in one place (e.g., SearXNG to 7080), update all references in `.env`, compose files, and settings.
- Use explicit `container_name:` to avoid auto-generated names that change.

## Example Compose Snippet
```yaml
services:
  mongodb:
    container_name: ragagent-mongodb
    ports:
      - "7017:27017"
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - rag_network
    restart: unless-stopped

networks:
  rag_network:
    driver: bridge
```

## Best Practices
- Use `.env` for all secrets and connection details.
- All services should use `env_file: [.env]` for consistency.
- All services should have explicit `container_name:` in format `{project}-{service}`.
- All HTTP services should have healthchecks.
- Document any port or service changes in AGENTS.md and this file.
- Validate with `docker compose up -d` and check for port conflicts.
- Use `docker ps` to verify port mappings and health status.
