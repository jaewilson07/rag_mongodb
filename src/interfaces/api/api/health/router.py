"""Health check routes for vector database."""

from __future__ import annotations

from fastapi import APIRouter

from mdrag.dependencies import AgentDependencies
from mdrag.mdrag_logging.service_logging import log_call
from mdrag.interfaces.api.config import api_config

health_router = APIRouter(
    prefix=api_config.HEALTH_PREFIX,
    tags=["health"],
)


@health_router.get("/vector-db")
@log_call(action_name="vector_db_health")
async def vector_db_health() -> dict:
    """Return vector database status and document counts."""
    deps = AgentDependencies()
    await deps.initialize()
    try:
        chunks_collection = deps.db[deps.settings.mongodb_collection_chunks]
        documents_collection = deps.db[deps.settings.mongodb_collection_documents]

        chunk_count = await chunks_collection.count_documents({})
        document_count = await documents_collection.count_documents({})

        return {
            "status": "ok",
            "chunks": chunk_count,
            "documents": document_count,
            "vector_index": deps.settings.mongodb_vector_index,
            "text_index": deps.settings.mongodb_text_index,
        }
    finally:
        await deps.cleanup()
