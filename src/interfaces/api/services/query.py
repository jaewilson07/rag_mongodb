"""Service layer for query routes."""

from __future__ import annotations

from mdrag.query.service import QueryService
from mdrag.interfaces.api.api.query.models import QueryRequest, QueryResponse


class QueryAPIService:
    """Handle query API requests."""

    async def handle_query(self, request: QueryRequest) -> QueryResponse:
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
