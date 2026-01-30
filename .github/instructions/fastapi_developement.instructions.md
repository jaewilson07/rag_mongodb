---
name: fastapi-development
description: Guide FastAPI development with testing, coverage, and design patterns. Use when building FastAPI endpoints, writing tests, configuring pytest, setting up coverage, creating dependency injection patterns, or when the user asks about API testing strategies.
---

reference [Microservices Design Patterns](microservices-design.md) for API design conventions.

# FastAPI Development

Best practices for building, testing, and maintaining FastAPI applications following this project's established patterns.

## Project Structure

Follow the domain-driven modular structure used in `04-lambda/src/`:

```
src/
├── capabilities/           # Domain capabilities (RAG, calendar, persona)
│   └── <domain>/
│       ├── __init__.py
│       ├── agent.py        # Pydantic AI agent definition
│       ├── config.py       # Domain-specific settings
│       ├── dependencies.py # Dependency injection class
│       ├── models.py       # Pydantic models
│       ├── router.py       # FastAPI router
│       ├── tools.py        # Agent tools
│       └── services/       # Business logic services
├── workflows/              # Multi-step workflows
├── services/               # Shared services (auth, storage, compute)
├── server/                 # FastAPI app entry point
│   ├── main.py
│   ├── dependencies.py
│   └── api/
└── shared/                 # Shared utilities
tests/
├── conftest.py             # Shared fixtures
├── test_<domain>/          # Domain-specific tests
└── test_samples/           # Sample script tests
```

## Dependency Injection Pattern

Use dataclass-based dependencies that inherit from `BaseDependencies`:

```python
from dataclasses import dataclass, field
from typing import Any
from shared.dependencies import BaseDependencies

@dataclass
class MyDependencies(BaseDependencies):
    """Dependencies injected into the service context."""

    # External clients
    mongo_client: AsyncMongoClient | None = None
    openai_client: openai.AsyncOpenAI | None = None

    # Configuration
    settings: Any | None = None

    # User context for RLS
    current_user_id: str | None = None
    current_user_email: str | None = None
    is_admin: bool = False

    @classmethod
    def from_settings(cls, **kwargs) -> "MyDependencies":
        """Factory method to create dependencies from settings."""
        return cls(**kwargs)

    async def initialize(self) -> None:
        """Initialize external connections."""
        # Initialize clients here
        pass

    async def cleanup(self) -> None:
        """Clean up external connections."""
        if self.mongo_client:
            await self.mongo_client.close()
```

### Context Manager Pattern (Recommended)

Use the `ManagedDependencies` context manager for automatic cleanup:

```python
from server.core.api_utils import ManagedDependencies

@router.get("/items")
async def list_items(
    user: User = Depends(get_current_user),
    limit: int = 10,
) -> list[ItemResponse]:
    """List items with automatic dependency cleanup."""
    async with ManagedDependencies(MyDeps, user_email=user.email) as deps:
        service = MyService(deps)
        return await service.list_items(limit=limit)
```

**Benefits**:
- Automatic cleanup on exception or normal exit
- More Pythonic and readable
- No risk of forgetting `finally` block
- Standard asyncio pattern

**Manual Pattern** (when you need fine-grained control):
```python
@router.get("/items")
async def list_items(
    user: User = Depends(get_current_user),
) -> list[ItemResponse]:
    """List items with manual dependency management."""
    deps = MyDeps.from_settings(user_email=user.email)
    await deps.initialize()
    try:
        service = MyService(deps)
        return await service.list_items()
    finally:
        await deps.cleanup()
```

## Router Pattern

Keep routers thin - delegate to services:

```python
from fastapi import APIRouter, Depends, HTTPException
from server.dependencies import get_current_user
from services.auth.models import User

router = APIRouter(prefix="/api/v1/myfeature", tags=["myfeature"])

@router.get("/items")
async def list_items(
    user: User = Depends(get_current_user),
    limit: int = 10,
) -> list[ItemResponse]:
    """List items for the current user."""
    deps = MyDependencies.from_settings(
        user_id=str(user.id),
        user_email=user.email,
    )
    await deps.initialize()
    try:
        service = MyService(deps)
        return await service.list_items(limit=limit)
    finally:
        await deps.cleanup()
```

## Maintainability Principles

Apply these principles to keep FastAPI projects stable over time:

- **Routers are thin**: Parse input, call application logic, return responses. No business rules in routes.
- **Business logic is explicit**: Important rules live in named functions/classes (use cases), not inline.
- **Dependencies flow inward**: Frameworks depend on your code; domain logic does not depend on FastAPI.
- **Separate schemas from domain models**: Pydantic models are for I/O; domain models are for behavior.
- **Dependencies are wiring, not logic**: Use them for sessions and lifecycles only.
- **Make side effects obvious**: External calls, writes, and state changes should be easy to spot.
- **Prefer explicit use cases**: Use intentful names like `DeactivateUserAccount` over generic `UserService.update()`.
- **Version APIs intentionally**: Plan for parallel versions without hacks.
- **Design for testability**: Favor unit tests for business logic; keep HTTP tests minimal.

### Common Maintainability Failure Modes

- **Fat routers**: Routes doing validation, queries, and business logic.
- **No clear separation of responsibilities**: Tight coupling makes refactors risky.
- **Framework-centric design**: Business logic tied to FastAPI, making reuse/testing harder.

## Modern FastAPI Production Practices

### Architecture & Project Structure

- **Modular routers**: Split endpoints by domain (`/users`, `/items`) and include via `app.include_router()`.
- **Suggested layout**:
    - `app/routers/` for endpoints
    - `app/schemas/` for Pydantic I/O models
    - `app/models/` for ORM models
    - `app/dependencies.py` for shared dependencies
- **Annotated dependencies**: Prefer `Annotated` for readability and reuse.

```python
from typing import Annotated
from fastapi import Depends

db: Annotated[Session, Depends(get_db)]
```

### High-Performance Concurrency

- **Async for I/O**: Use `async def` with async-friendly libraries (e.g., `httpx`).
- **Sync for blocking**: Use `def` for CPU-bound or blocking work; FastAPI runs it in a thread pool.
- **Offload heavy tasks**:
    - Use `BackgroundTasks` for light side effects (email, webhooks).
    - Use Celery/RabbitMQ for heavy CPU/ML jobs.

### Data Validation & Pydantic v2

- **Custom base models**: Centralize shared config (e.g., casing, datetime handling).
- **Validate in models, not routes**: Use `@field_validator` to keep endpoints slim.
- **Response models**: Always set `response_model` for automatic validation and serialization.

### Lifespan & Resource Management

- **Use lifespan**: Prefer the `lifespan` async context manager over `startup`/`shutdown` decorators.
- **Connection pooling**: Initialize pools once and store on `app.state` or inside the lifespan context.

### Production & Security Essentials

- **Disable docs in production**: Set `docs_url=None` and `redoc_url=None` when deploying.
- **Secrets via settings**: Use Pydantic Settings (`BaseSettings`) for typed, centralized config.
- **Production stack**: Run Uvicorn under Gunicorn with `UvicornWorker`, behind a reverse proxy.

## Router Prefix Convention

All routers **MUST** define their own prefix using constants from `server.config.api_config`. This ensures:
- Consistent API versioning across all endpoints
- Clear endpoint ownership (each router owns its prefix)
- No prefix duplication in `main.py` router registration
- Easier discovery and documentation
- Single source of truth for API structure

### Using APIConfig

Import the singleton instance and use the appropriate prefix constant:

```python
from server.config import api_config

# For service-layer routers (services/external/immich/)
router = APIRouter(
    prefix=f"{api_config.SERVICES_PREFIX}/immich",
    tags=["services", "immich"]
)

# For capability routers (capabilities/persona/)
router = APIRouter(
    prefix=api_config.CAPABILITIES_PREFIX,
    tags=["capabilities", "persona"]
)

# For workflow routers (workflows/ingestion/crawl4ai/)
router = APIRouter(
    prefix=f"{api_config.V1_PREFIX}/crawl",
    tags=["workflows", "crawl"]
)
```

### Standard Prefix Patterns

| Layer | Constant | Pattern | Example |
|-------|----------|---------|---------|
| Auth | `api_config.AUTH_PREFIX` | `/api/v1/auth` | `/api/v1/auth/me` |
| Data Services | `api_config.DATA_PREFIX` | `/api/v1/data/{service}` | `/api/v1/data/mongodb` |
| Capabilities | `api_config.CAPABILITIES_PREFIX` | `/api/v1/capabilities` | `/api/v1/capabilities/persona/chat` |
| RAG | `api_config.RAG_PREFIX` | `/api/v1/rag` | `/api/v1/rag/search` |
| Workflows | `api_config.WORKFLOWS_PREFIX` or custom | `/api/v1/{workflow}` | `/api/v1/crawl/single` |
| Services | `api_config.SERVICES_PREFIX` | `/api/v1/services/{name}` | `/api/v1/services/immich` |
| Admin | `api_config.ADMIN_PREFIX` | `/api/v1/admin` | `/api/v1/admin/discord/config` |
| MCP | `api_config.MCP_PREFIX` | `/api/v1/mcp` | `/api/v1/mcp/tools/list` |
| Preferences | `api_config.PREFERENCES_PREFIX` | `/api/v1/preferences` | `/api/v1/preferences/{key}` |

### Router Definition Example

```python
# In your router.py - ALWAYS use api_config constants
from fastapi import APIRouter
from server.config import api_config

router = APIRouter(
    prefix=f"{api_config.SERVICES_PREFIX}/myservice",
    tags=["services", "myservice"]
)

# Routes are relative to the prefix
@router.get("/items")  # Full path: /api/v1/services/myservice/items
async def list_items(): ...

@router.post("/items")  # Full path: /api/v1/services/myservice/items
async def create_item(): ...
```

### Router Registration in main.py

Since routers define their own prefixes, registration in `main.py` is simple:

```python
# In server/main.py - NO additional prefix needed
from myfeature.router import router as myfeature_router

# Router already has prefix="/api/v1/myfeature"
app.include_router(myfeature_router)  # No prefix argument!
```

### Common Mistakes to Avoid

1. **Don't hardcode prefixes - use api_config:**
   ```python
   # BAD - hardcoded prefix
   router = APIRouter(prefix="/api/v1/feature")

   # GOOD - using api_config constant
   from server.config import api_config
   router = APIRouter(prefix=f"{api_config.V1_PREFIX}/feature")
   ```

2. **Don't duplicate prefixes:**
   ```python
   # BAD - prefix defined twice
   router = APIRouter(prefix=f"{api_config.SERVICES_PREFIX}/feature")
   app.include_router(router, prefix=f"{api_config.SERVICES_PREFIX}/feature")
   # Results in: /api/v1/services/feature/api/v1/services/feature

   # GOOD - prefix defined once in router
   router = APIRouter(prefix=f"{api_config.SERVICES_PREFIX}/feature")
   app.include_router(router)  # Results in: /api/v1/services/feature
   ```

3. **Don't omit the prefix in router definition:**
   ```python
   # BAD - no prefix in router, relies on main.py
   router = APIRouter()
   app.include_router(router, prefix="/api/v1/feature")

   # GOOD - prefix self-documented in router using api_config
   from server.config import api_config
   router = APIRouter(prefix=f"{api_config.V1_PREFIX}/feature")
   app.include_router(router)
   ```

4. **Always include tags for OpenAPI grouping:**
   ```python
   # GOOD - tags help organize API docs
   from server.config import api_config
   router = APIRouter(
       prefix=api_config.CAPABILITIES_PREFIX,
       tags=["capabilities", "calendar"]
   )
   ```

## Testing Strategy

### Test Types

| Type | Location | Purpose |
|------|----------|---------|
| Unit | `tests/test_<domain>/test_*.py` | Test individual functions/classes in isolation |
| Integration | `tests/test_<domain>/test_*_integration.py` | Test component interactions |
| Endpoint | `tests/test_<domain>/test_*_endpoint.py` | Test FastAPI routes |
| Sample | `tests/test_samples/` | Validate sample scripts work |

### Pytest Configuration

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

### Mock Fixtures Pattern

Create reusable fixtures in `conftest.py`:

```python
import pytest
from unittest.mock import AsyncMock, Mock

@pytest.fixture
def mock_mongo_client():
    """Mock MongoDB client."""
    client = AsyncMock()
    client.__getitem__ = Mock(return_value=AsyncMock())
    return client

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client with proper structure."""
    client = AsyncMock()
    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message = Mock()
    mock_choice.message.content = "Test response"
    mock_response.choices = [mock_choice]

    mock_create = AsyncMock(return_value=mock_response)
    mock_completions = Mock()
    mock_completions.create = mock_create
    mock_chat = Mock()
    mock_chat.completions = mock_completions
    client.chat = mock_chat
    return client

@pytest.fixture
def mock_dependencies(mock_mongo_client, mock_openai_client):
    """Mock dependencies for testing."""
    deps = AsyncMock()
    deps.mongo_client = mock_mongo_client
    deps.openai_client = mock_openai_client
    deps.initialize = AsyncMock()
    deps.cleanup = AsyncMock()
    return deps
```

### Testing Async Functions

```python
import pytest

@pytest.mark.asyncio
async def test_async_service(mock_dependencies):
    """Test async service method."""
    service = MyService(mock_dependencies)
    result = await service.process_data("input")
    assert result.status == "success"
```

### Testing FastAPI Endpoints

```python
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Sync test client
def test_endpoint_sync(test_app):
    client = TestClient(test_app)
    response = client.get("/api/v1/items")
    assert response.status_code == 200

# Async test client (preferred for async routes)
@pytest.mark.asyncio
async def test_endpoint_async(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/items")
        assert response.status_code == 200
```

### Dependency Override for Testing

```python
from fastapi import FastAPI
from server.dependencies import get_current_user

@pytest.fixture
def test_app(mock_user):
    """Create test app with overridden dependencies."""
    from server.main import app

    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield app
    app.dependency_overrides.clear()
```

## Coverage Configuration

See [coverage-config.md](coverage-config.md) for detailed `.coveragerc` and pytest-cov setup.

### Quick Coverage Command

```bash
# Run tests with coverage
pytest --cov=src --cov-report=term-missing --cov-report=html

# Fail if coverage drops below threshold
pytest --cov=src --cov-fail-under=80
```

## Logging Best Practices

This project uses an enhanced logging architecture adapted from [dl-remuxed](https://github.com/jaewilson07/dl-remuxed), featuring automatic entity extraction, result processing, and HTTP sanitization.

### Logging Components

Located in `04-lambda/src/server/core/logging/`:
- **ColoredLogger**: Logger wrapper with level filtering and color coding
- **Entity Extractors**: Automatic extraction of structured data from function parameters
- **Result Processors**: Automatic formatting and sanitization of results
- **Enhanced Decorators**: Config-driven logging with minimal boilerplate

### Basic Logger Usage

```python
from server.core.logging import get_logger

logger = get_logger(__name__)

# In async functions - use await
await logger.info("Operation completed",
    action="create_workflow",
    workflow_id="wf_123",
    duration_ms=245
)

# In sync functions - no await
logger.info("Sync operation completed")
```

### Enhanced Route Decorator Pattern

Use `@log_call` for automatic logging with entity extraction and result processing:

```python
from fastapi import APIRouter, Depends
from server.core.logging_utils import log_call, LogDecoratorConfig
from server.core.logging_utils import LambdaEntityExtractor, ComfyUIResultProcessor
from server.dependencies import get_current_user
from services.auth.models import User

router = APIRouter(prefix="/api/v1/comfyui", tags=["comfyui"])

@router.post("/generate")
@log_call(
    level_name="route",
    config=LogDecoratorConfig(
        entity_extractor=LambdaEntityExtractor(),
        result_processor=ComfyUIResultProcessor(),
    ),
)
async def generate_image(
    prompt_id: str,
    workflow_json: dict,
    user: User = Depends(get_current_user),
):
    """Generate image using ComfyUI workflow.

    Automatic logging includes:
    - Function entry/exit with duration
    - Entity extraction (prompt_id, user_email, node_count)
    - Result processing (image_count, image_paths)
    - Error details with full context
    """
    # Just business logic - logging is automatic
    result = await comfyui_client.submit_workflow(workflow_json)
    return result
```

**Automatic Log Output**:
```json
{
  "level": "INFO",
  "message": "generate_image started",
  "action": "generate_image",
  "entity": {
    "type": "image",
    "id": "abc-123",
    "additional_info": {
      "user_email": "user@example.com",
      "node_count": 15
    }
  },
  "result": {
    "prompt_id": "abc-123",
    "image_count": 1,
    "image_paths": ["output.png"]
  },
  "duration_ms": 3245
}
```

### Available Result Processors

#### ComfyUIResultProcessor
Extracts prompt_id, image counts/paths (not base64), node errors:
```python
from server.core.logging_utils import ComfyUIResultProcessor

@log_call(config=LogDecoratorConfig(result_processor=ComfyUIResultProcessor()))
async def submit_workflow(...):
    return await comfyui_client.submit(workflow)
```

#### MongoDBResultProcessor
Sanitizes PII fields (email, password, api_key, token):
```python
from server.core.logging_utils import MongoDBResultProcessor

@log_call(config=LogDecoratorConfig(result_processor=MongoDBResultProcessor()))
async def get_documents(...):
    return await mongo_client.find(query)
```

#### Neo4jResultProcessor
Extracts record/node/relationship counts:
```python
from server.core.logging_utils import Neo4jResultProcessor

@log_call(config=LogDecoratorConfig(result_processor=Neo4jResultProcessor()))
async def run_query(...):
    return await neo4j_client.execute(query)
```

#### HTTPResponseProcessor
Sanitizes headers (Authorization, X-API-Key), truncates large bodies:
```python
from server.core.logging_utils import HTTPResponseProcessor

@log_call(config=LogDecoratorConfig(result_processor=HTTPResponseProcessor()))
async def call_external_api(...):
    return await httpx_client.post(url, headers=headers)
```

### Entity Extractor Patterns

The `LambdaEntityExtractor` automatically detects entity types from function names and parameters:

**Supported Entity Types**:
- **workflow**: N8n workflows (`workflow_id`), ComfyUI prompts (`prompt_id`)
- **image**: ComfyUI generations, storage paths
- **document**: MongoDB documents, Neo4j nodes
- **conversation**: Chat messages, Discord interactions
- **calendar_event**: Google Calendar events

**Example - Workflow Entity**:
```python
@log_call(config=LogDecoratorConfig(entity_extractor=LambdaEntityExtractor()))
async def create_workflow(workflow_id: str, user: User, ...):
    # Automatically extracts:
    # - type: "workflow"
    # - id: workflow_id
    # - additional_info: {"user_email": "user@example.com", "workflow_type": "n8n"}
    pass
```

### Service-Level Logging Pattern

For service methods without FastAPI decorators:

```python
from server.core.logging import get_logger
import asyncio

logger = get_logger(__name__)

class MyService:
    async def process_data(self, data: dict) -> dict:
        """Process data with structured logging."""
        # Log start (non-blocking)
        asyncio.create_task(logger.info(
            "process_data_started",
            action="process_data",
            data_size=len(data)
        ))

        try:
            result = await self._do_processing(data)

            # Log success (non-blocking)
            asyncio.create_task(logger.info(
                "process_data_completed",
                action="process_data",
                result_size=len(result)
            ))

            return result
        except Exception as e:
            # Log error (non-blocking)
            asyncio.create_task(logger.error(
                "process_data_failed",
                action="process_data",
                error=str(e)
            ))
            raise
```

### Dynamic Log Level Control

Use ColoredLogger for runtime log level changes:

```python
from server.core.logging import get_logger

logger = get_logger(__name__)

# Enable debug logging temporarily
logger.set_level("DEBUG")
await logger.debug("Detailed debug info now visible")

# Restore to INFO level
logger.set_level("INFO")
```

### Creating Custom Extractors

For domain-specific entities:

```python
from dc_logger.client.extractors import EntityExtractor
from dc_logger.client.models import Entity as LogEntity

class MyEntityExtractor(EntityExtractor):
    def extract(self, func, args, kwargs) -> LogEntity | None:
        # Extract custom entity from kwargs
        entity_id = kwargs.get("my_entity_id")
        if not entity_id:
            return None

        return LogEntity(
            type="my_entity",
            id=str(entity_id),
            name=f"MyEntity {entity_id}",
            additional_info={
                "user_email": kwargs.get("user").email if kwargs.get("user") else None,
            }
        )

# Use in decorator
@log_call(config=LogDecoratorConfig(entity_extractor=MyEntityExtractor()))
async def my_route(...):
    pass
```

### Creating Custom Processors

For domain-specific result formatting:

```python
from dc_logger.client.extractors import ResultProcessor
from dc_logger.client.models import HTTPDetails

class MyResultProcessor(ResultProcessor):
    def process(self, result, http_details):
        result_context = {}

        # Extract domain-specific data
        if isinstance(result, dict):
            result_context["my_metric"] = result.get("metric")

        return result_context, http_details

# Use in decorator
@log_call(config=LogDecoratorConfig(result_processor=MyResultProcessor()))
async def my_route(...):
    pass
```

### Security: Header Sanitization

All processors automatically sanitize sensitive headers:
- `Authorization`, `X-API-Key`, `Cookie`
- `Cf-Access-Token`, `Cf-Access-Jwt-Assertion`
- Custom tokens: `immich_api_key`, `neo4j_password`

Headers are replaced with `"***"` in logs to prevent credential exposure.

### Migration from Old Pattern

**Before** (Manual logging):
```python
@router.post("/generate")
@log_route_execution(action="comfyui_generate")
async def generate_image(request: ImageRequest, user: User):
    try:
        logger.info("Starting image generation")
        result = await comfyui_client.submit_workflow(workflow_json)

        # Manual result logging
        if result:
            logger.info("completed", prompt_id=result.get("prompt_id"))
        return result
    except Exception as e:
        logger.exception("Image generation failed")
        raise HTTPException(status_code=500, detail=str(e))
```

**After** (Enhanced decorator):
```python
@router.post("/generate")
@log_call(
    level_name="route",
    config=LogDecoratorConfig(
        entity_extractor=LambdaEntityExtractor(),
        result_processor=ComfyUIResultProcessor(),
    ),
)
async def generate_image(request: ImageRequest, user: User):
    # Just business logic - logging is automatic
    result = await comfyui_client.submit_workflow(workflow_json)
    return result
```

**Benefits of New Pattern**:
- 60-70% less boilerplate code
- Automatic entity extraction from parameters
- Automatic result formatting and sanitization
- Consistent logging across all routes
- Built-in security (header/PII sanitization)

## Error Handling

Use HTTPException with appropriate status codes:

```python
from fastapi import HTTPException, status

@router.get("/items/{item_id}")
async def get_item(item_id: str, user: User = Depends(get_current_user)):
    item = await service.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found"
        )
    if item.owner_id != str(user.id) and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this item"
        )
    return item
```

## Pydantic Models

Use Pydantic v2 patterns:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class ItemCreate(BaseModel):
    """Request model for creating an item."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None

class ItemResponse(BaseModel):
    """Response model for an item."""
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    owner_id: UUID

    model_config = {"from_attributes": True}
```

## Additional Resources

- [testing-patterns.md](testing-patterns.md) - Detailed fixture patterns and examples
- [coverage-config.md](coverage-config.md) - Coverage configuration templates
- [microservices-design.md](microservices-design.md) - API endpoint design conventions
