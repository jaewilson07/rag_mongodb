# Microservices API Design

Best practices for designing microservices endpoints in FastAPI, aligned with this project's patterns.

## REST API Endpoint Design

### Resource Naming

- **Use plural nouns**: `/api/v1/users`, `/api/v1/events`, `/api/v1/documents`
- **Lowercase with hyphens**: `/api/v1/knowledge-base`, `/api/v1/calendar-events`
- **Nest for relationships**: `/api/v1/users/{user_id}/orders` (max 2-3 levels)
- **Use path parameters for identifiers**: `/api/v1/documents/{document_id}`
- **Use query parameters for filtering**: `/api/v1/documents?status=published&limit=10`

### HTTP Method Semantics

| Method | Purpose | Idempotent | Request Body | Response |
|--------|---------|------------|--------------|----------|
| GET | Retrieve resource(s) | Yes | No | Resource data |
| POST | Create resource | No | Yes | Created resource |
| PUT | Replace resource | Yes | Yes | Updated resource |
| PATCH | Partial update | Yes | Yes | Updated resource |
| DELETE | Remove resource | Yes | No | 204 or confirmation |

### Endpoint Pattern (Project Standard)

From your existing routers:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search documents",
    operation_id="search_documents",
)
async def search_documents(
    request: SearchRequest,
    user: User = Depends(get_current_user),
    deps: AgentDeps = Depends(get_agent_deps),
) -> SearchResponse:
    """
    Search the document collection with semantic and text matching.

    **Use Cases:**
    - Find relevant documents by topic
    - Retrieve specific content by keywords
    - Discover related materials

    **Request Example:**
    ```json
    {
        "query": "authentication best practices",
        "limit": 10,
        "search_type": "hybrid"
    }
    ```

    **Performance Notes:**
    - Hybrid search combines semantic + text matching
    - Results are ranked by relevance score
    """
    try:
        results = await deps.service.search(
            query=request.query,
            user_id=user.id,  # Data isolation
            limit=request.limit,
        )
        return SearchResponse(results=results)
    finally:
        await deps.cleanup()
```

## API Versioning Strategy

### URL Path Versioning (Project Standard)

```python
# Recommended - matches your current pattern
router = APIRouter(prefix="/api/v1/documents")

# Version in URL makes it explicit
# /api/v1/documents  -> Current stable
# /api/v2/documents  -> Breaking changes
```

### When to Increment Version

- **Major version (v1 → v2)**: Breaking changes to request/response schema
- **No version change needed**: Additive changes, new optional fields, new endpoints

### Deprecation Headers

```python
from fastapi import Response

@router.get("/legacy-endpoint", deprecated=True)
async def legacy_endpoint(response: Response):
    """
    **Deprecated**: Use `/api/v2/new-endpoint` instead.

    This endpoint will be removed on 2024-12-01.
    """
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Sat, 01 Dec 2024 00:00:00 GMT"
    response.headers["Link"] = '</api/v2/new-endpoint>; rel="successor-version"'
    return {"message": "Use new endpoint"}
```

## Pagination Patterns

### Offset-Based Pagination

Best for: Small datasets, simple UI requirements

```python
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""
    items: list[T]
    total: int = Field(..., description="Total items matching query")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    has_next: bool = Field(..., description="More pages available")
    has_prev: bool = Field(..., description="Previous pages available")

class PaginationParams(BaseModel):
    """Standard pagination query parameters."""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")

@router.get("/documents", response_model=PaginatedResponse[Document])
async def list_documents(
    pagination: PaginationParams = Depends(),
    user: User = Depends(get_current_user),
):
    skip = (pagination.page - 1) * pagination.page_size

    items, total = await service.list_documents(
        user_id=user.id,
        skip=skip,
        limit=pagination.page_size,
    )

    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        has_next=(pagination.page * pagination.page_size) < total,
        has_prev=pagination.page > 1,
    )
```

### Cursor-Based Pagination

Best for: Large datasets, real-time data, infinite scroll

```python
from datetime import datetime
from typing import Optional

class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based pagination response."""
    items: list[T]
    next_cursor: str | None = Field(None, description="Cursor for next page")
    has_more: bool = Field(..., description="More items available")

@router.get("/events", response_model=CursorPaginatedResponse[Event])
async def list_events(
    cursor: str | None = None,
    limit: int = Field(20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    # Decode cursor (typically base64-encoded timestamp or ID)
    after_timestamp = decode_cursor(cursor) if cursor else None

    items = await service.list_events(
        user_id=user.id,
        after=after_timestamp,
        limit=limit + 1,  # Fetch one extra to check has_more
    )

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = encode_cursor(items[-1].created_at) if has_more else None

    return CursorPaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    )
```

## Standard Response Models

### Success Response Wrapper (Optional)

```python
class APIResponse(BaseModel, Generic[T]):
    """Standard success response wrapper."""
    success: bool = True
    data: T
    message: str | None = None

# Usage
@router.post("/documents", response_model=APIResponse[Document])
async def create_document(...) -> APIResponse[Document]:
    doc = await service.create(...)
    return APIResponse(data=doc, message="Document created successfully")
```

### Error Response Structure

```python
class ErrorDetail(BaseModel):
    """Individual error detail."""
    field: str | None = None
    message: str
    code: str | None = None

class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error_code: str
    message: str
    details: list[ErrorDetail] | None = None

# Example error responses for OpenAPI docs
ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Bad Request"},
    401: {"model": ErrorResponse, "description": "Unauthorized"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
    404: {"model": ErrorResponse, "description": "Not Found"},
    422: {"model": ErrorResponse, "description": "Validation Error"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"},
}

@router.get(
    "/documents/{document_id}",
    response_model=Document,
    responses=ERROR_RESPONSES,
)
async def get_document(document_id: str, ...):
    ...
```

## Error Handling Standards

### HTTP Status Code Mapping

| Status | Meaning | When to Use |
|--------|---------|-------------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST creating resource |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid request syntax |
| 401 | Unauthorized | Missing/invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource state conflict |
| 422 | Unprocessable | Validation errors |
| 500 | Server Error | Unexpected server issues |

### Custom Exception Classes

```python
from fastapi import HTTPException, status

class DomainException(Exception):
    """Base exception for domain errors."""
    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class ResourceNotFoundError(DomainException):
    """Resource not found."""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            error_code="RESOURCE_NOT_FOUND",
        )

class ResourceConflictError(DomainException):
    """Resource state conflict."""
    def __init__(self, message: str):
        super().__init__(message=message, error_code="RESOURCE_CONFLICT")
```

### Global Exception Handler

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    status_map = {
        "RESOURCE_NOT_FOUND": 404,
        "RESOURCE_CONFLICT": 409,
        "VALIDATION_ERROR": 422,
    }
    return JSONResponse(
        status_code=status_map.get(exc.error_code, 400),
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
        ).model_dump(),
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the full exception for debugging
    logger.exception("Unhandled exception", exc_info=exc)

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        ).model_dump(),
    )
```

## Inter-Service Communication

### Synchronous (REST)

Best for: Client-facing APIs, request-response patterns

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class ExternalServiceClient:
    """Client for external service with retry logic."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get_resource(self, resource_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/resources/{resource_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
```

### Idempotency Keys

For non-idempotent operations (POST), use idempotency keys:

```python
from fastapi import Header

@router.post("/payments")
async def create_payment(
    request: PaymentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    # Check if request already processed
    existing = await cache.get(f"idempotency:{idempotency_key}")
    if existing:
        return existing

    # Process payment
    result = await service.process_payment(request)

    # Cache result for 24 hours
    await cache.set(
        f"idempotency:{idempotency_key}",
        result,
        ttl=86400,
    )

    return result
```

### Asynchronous (Event-Driven)

Best for: Background processing, notifications, audit logs

```python
# Producer
async def publish_event(event_type: str, payload: dict):
    """Publish event for async processing."""
    await message_queue.publish(
        topic=event_type,
        message={
            "event_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        },
    )

# In endpoint
@router.post("/documents")
async def create_document(request: CreateDocumentRequest, ...):
    document = await service.create_document(request)

    # Fire and forget - processed asynchronously
    await publish_event("document.created", {"document_id": document.id})

    return document
```

## OpenAPI Documentation

### Rich Endpoint Documentation

Follow the pattern from your existing routers:

```python
@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search knowledge base",
    description="Perform semantic and text search across documents.",
    operation_id="search_knowledge_base",
    tags=["search", "rag"],
    responses={
        200: {
            "description": "Search results",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "id": "doc_123",
                                "content": "Example content...",
                                "score": 0.95,
                            }
                        ],
                        "total": 42,
                    }
                }
            },
        },
        **ERROR_RESPONSES,
    },
)
async def search_knowledge_base(
    request: SearchRequest = Body(
        ...,
        examples=[
            {
                "summary": "Basic search",
                "value": {"query": "authentication", "limit": 10},
            },
            {
                "summary": "Filtered search",
                "value": {
                    "query": "API design",
                    "limit": 20,
                    "filters": {"source": "documentation"},
                },
            },
        ],
    ),
    user: User = Depends(get_current_user),
) -> SearchResponse:
    """
    Search the knowledge base for relevant information.

    **Use Cases:**
    - Find answers to questions
    - Discover related documentation
    - Research specific topics

    **Search Types:**
    - `semantic`: Vector similarity search
    - `text`: Full-text keyword search
    - `hybrid`: Combined approach (recommended)

    **Performance Notes:**
    - Results cached for 5 minutes
    - Max 100 results per request
    """
    ...
```

### Model Documentation

```python
from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    """Search request parameters."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language search query",
        examples=["How do I authenticate?"],
    )
    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum results to return",
    )
    search_type: str = Field(
        "hybrid",
        pattern="^(semantic|text|hybrid)$",
        description="Search algorithm to use",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "authentication best practices",
                    "limit": 10,
                    "search_type": "hybrid",
                }
            ]
        }
    }
```

## Data Isolation Pattern

Always scope queries to the authenticated user:

```python
@router.get("/documents")
async def list_documents(
    user: User = Depends(get_current_user),
    deps: AgentDeps = Depends(get_agent_deps),
):
    # Regular users see only their data
    if not user.is_admin:
        return await deps.service.list_by_user(user_id=user.id)

    # Admins can see all data
    return await deps.service.list_all()
```

## Additional Resources

- [FastAPI Official Documentation](https://fastapi.tiangolo.com/)
- [RESTful API Design Guidelines](https://restfulapi.net/)
- [HTTP Status Codes](https://httpstatuses.com/)
