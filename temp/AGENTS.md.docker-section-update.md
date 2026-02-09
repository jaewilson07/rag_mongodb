## Docker Configuration
- Use host ports in the 7000–7500 range to avoid conflicts with other infrastructure.
- Current defaults:
   - MongoDB: 7017 -> container 27017
   - Mongot (Atlas Search): 7027 -> container 27027
   - SearXNG: 7080 -> container 8080
   - vLLM: 11435 -> container 8000 (Ollama 11434 + 1, from local-ai-packaged)
   - LiteLLM: 4000 -> container 4000 (standard LiteLLM port, external tool)
   - Frontend: 3000 -> container 3000
   - RAG Agent API: 8000 -> container 8000
- Prefer `.env` with `env_file` in compose to reduce inline environment noise.
- All services use explicit `container_name:` for consistent log/exec commands.
- Network: All services share `rag_network` (bridge driver). vLLM compose can run standalone or via include.

## Container Names
Standardized naming pattern: `{project}-{service}`
- `ragagent-mongodb` - MongoDB Atlas Local
- `ragagent-searxng` - SearXNG metasearch
- `ragagent-rag-agent` - Main RAG application
- `ragagent-wiki-frontend` - DeepWiki Next.js frontend
- `vllm-glm` - vLLM inference server
- `litellm-proxy` - LiteLLM OpenAI-compatible proxy

Usage: `docker logs ragagent-mongodb`, `docker exec -it ragagent-rag-agent bash`
