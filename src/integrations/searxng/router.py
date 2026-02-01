"""SearXNG web search REST API."""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from server.config import settings
from shared.utils.http import create_http_client
from ...mdrag_logging.service_logging import get_logger

router = APIRouter(prefix="/api/v1/searxng", tags=["searxng"])
logger = get_logger(__name__)

# SearXNG URL from settings
SEARXNG_URL = settings.searxng_url


class SearXNGSearchRequest(BaseModel):
    """Request model for SearXNG search."""

    query: str = Field(..., description="Search query string")
    result_count: int = Field(10, ge=1, le=20, description="Number of results to return (1-20)")
    categories: str | None = Field(
        None, description="Filter by category (general, news, images, etc.)"
    )
    engines: list[str] | None = Field(None, description="Filter by specific search engines")


class SearXNGSearchResult(BaseModel):
    """Individual search result from SearXNG."""

    title: str
    url: str
    content: str
    engine: str | None = None
    score: float | None = None


class SearXNGSearchResponse(BaseModel):
    """Response model for SearXNG search."""

    query: str
    results: list[SearXNGSearchResult]
    count: int
    success: bool = True


@router.post("/search", response_model=SearXNGSearchResponse)
async def search(request: SearXNGSearchRequest):
    """
    Search the web using SearXNG metasearch engine.

    SearXNG aggregates results from multiple search engines and returns
    ranked, deduplicated results. Use this for current information, real-time
    data, or information not available in the knowledge base.

    **Use Cases:**
    - Current events and news
    - Real-time information
    - Information not in knowledge base
    - Multi-engine search aggregation

    **Request Body:**
    ```json
    {
        "query": "latest AI developments",
        "result_count": 10,
        "categories": "general"
    }
    ```

    **Response:**
    ```json
    {
        "query": "latest AI developments",
        "success": true,
        "count": 10,
        "results": [
            {
                "title": "AI News Article",
                "url": "https://example.com/article",
                "content": "Article snippet...",
                "engine": "google",
                "score": 0.95
            }
        ]
    }
    ```

    **Parameters:**
    - `query` (required): Search query string
    - `result_count` (optional, default: 10): Number of results to return (1-20)
    - `categories` (optional): Filter by category (general, news, images, etc.)
    - `engines` (optional): Filter by specific search engines

    **Returns:**
    - `SearXNGSearchResponse` with query, results array, and count
    - Results include title, URL, content snippet, engine, and score

    **Errors:**
    - `500`: If SearXNG is unavailable or request fails
    - `400`: If query is empty or invalid

    **Integration:**
    - Also available as MCP tool: `web_search`
    - Results can be automatically ingested to RAG for future reference
    """

    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        await logger.info(
            "searxng_search_start",
            action="searxng_search_start",
            query=request.query,
            result_count=request.result_count,
            categories=request.categories,
            engines=request.engines,
        )
        # Build SearXNG API request
        params = {"q": request.query.strip(), "format": "json", "pageno": 1}

        # Add category filter if specified
        if request.categories:
            params["categories"] = request.categories

        # Add engine filter if specified
        if request.engines:
            params["engines"] = ",".join(request.engines)

        # Make request to SearXNG
        async with create_http_client("searxng", timeout=30.0) as client:
            response = await client.get(f"{SEARXNG_URL}/search", params=params)
            response.raise_for_status()
            data = response.json()

        # Parse SearXNG response
        # SearXNG returns results in 'results' array
        results = []
        if "results" in data:
            # Limit to requested count
            limited_results = data["results"][: request.result_count]

            for item in limited_results:
                result = SearXNGSearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    engine=item.get("engine", None),
                    score=item.get("score", None),
                )
                results.append(result)

        response = SearXNGSearchResponse(
            query=request.query, results=results, count=len(results), success=True
        )
        await logger.info(
            "searxng_search_complete",
            action="searxng_search_complete",
            query=request.query,
            result_count=len(results),
        )
        return response

    except httpx.TimeoutException:
        await logger.error(
            "SearXNG request timed out",
            action="searxng_search_timeout",
            query=request.query,
        )
        raise HTTPException(
            status_code=504,
            detail="SearXNG request timed out. The search engine may be overloaded.",
        )
    except httpx.HTTPStatusError as e:
        await logger.error(
            "SearXNG HTTP error",
            action="searxng_search_http_error",
            query=request.query,
            status_code=e.response.status_code,
            response_text=e.response.text[:200],
        )
        raise HTTPException(
            status_code=502, detail=f"SearXNG returned error: {e.response.status_code}"
        ) from e
    except httpx.RequestError as e:
        await logger.error(
            "SearXNG connection error",
            action="searxng_search_connection_error",
            query=request.query,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to SearXNG. Ensure the service is running and accessible.",
        ) from e
    except Exception as e:
        await logger.error(
            "SearXNG unexpected error",
            action="searxng_search_unexpected_error",
            query=request.query,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail=f"Unexpected error during search: {e!s}") from e
