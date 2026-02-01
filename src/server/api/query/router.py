"""Query API routes with citation mapping."""

from __future__ import annotations

from fastapi import APIRouter

from mdrag.mdrag_logging.service_logging import log_call
from mdrag.server.api.query.models import QueryRequest, QueryResponse
from mdrag.server.config import api_config
from mdrag.server.services.query import QueryAPIService

query_router = APIRouter(
    prefix=api_config.QUERY_PREFIX,
    tags=["query"],
)


@query_router.post("", response_model=QueryResponse)
@log_call(action_name="query_knowledge_base")
async def query_knowledge_base(request: QueryRequest) -> QueryResponse:
    """Run grounded query with citations."""
    service = QueryAPIService()
    return await service.handle_query(request)
