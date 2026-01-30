"""Query API routes with citation mapping."""

from __future__ import annotations

from fastapi import APIRouter

from src.query import QueryService
from src.server.api.query.models import QueryRequest, QueryResponse
from src.server.config import api_config

query_router = APIRouter(
    prefix=api_config.QUERY_PREFIX,
    tags=["query"],
)


@query_router.post("", response_model=QueryResponse)
async def query_knowledge_base(request: QueryRequest) -> QueryResponse:
    """Run grounded query with citations."""
    service = QueryService()
    try:
        result = await service.answer_query(
            query=request.query,
            search_type=request.search_type,
            match_count=request.match_count,
            filters=request.filters,
            parent_trace_id=request.parent_trace_id,
        )
        return QueryResponse(**result)
    finally:
        await service.close()
