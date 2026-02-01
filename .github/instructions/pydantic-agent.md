# Pydantic AI Agent & Tool Patterns

Reference guide for building Pydantic AI agents and tools for the RAG system.

## Agent Definition

### Basic Agent Setup

```python
from pydantic_ai import Agent, RunContext
from pydantic_ai.ag_ui import StateDeps
from pydantic import BaseModel

class RAGState(BaseModel):
    """Minimal shared state for RAG agent."""
    pass

# Create agent with StateDeps
rag_agent = Agent(
    get_llm_model(),  # From providers.py
    deps_type=StateDeps[RAGState],
    system_prompt=MAIN_SYSTEM_PROMPT
)
```

### Agent with Dynamic Instructions

```python
from textwrap import dedent

@rag_agent.instructions
async def rag_instructions(ctx: RunContext[StateDeps[RAGState]]) -> str:
    """
    Dynamic instructions for the RAG agent.

    Args:
        ctx: The run context containing RAG state information.

    Returns:
        Instructions string for the RAG agent.
    """
    return dedent(
        """
        You are an intelligent RAG (Retrieval-Augmented Generation) assistant.

        INSTRUCTIONS:
        1. When the user asks a question, use the `search_knowledge_base` tool
        2. The tool will return relevant documents from the knowledge base
        3. Base your answer on the retrieved information
        4. Always cite which documents you're referencing
        5. If you cannot find relevant information, be honest about it
        6. Choose between:
           - "semantic" search for conceptual queries (default)
           - "hybrid" search for specific facts or keyword matching

        Be concise and helpful in your responses.
        """
    )
```

## Tool Definition

### Search Tool Pattern

**Important**: Dependencies are provided via `RunContext` - do NOT initialize them inside tools.

```python
@rag_agent.tool
async def search_knowledge_base(
    ctx: RunContext[AgentDependencies],  # Type parameter matches agent's deps_type
    query: str,
    match_count: Optional[int] = 5,
    search_type: Optional[str] = "semantic"
) -> str:
    """
    Search the knowledge base for relevant information.

    Args:
        ctx: Agent runtime context with dependencies (already initialized)
        query: Search query text
        match_count: Number of results to return (default: 5)
        search_type: Type of search - "semantic" or "hybrid" (default: semantic)

    Returns:
        String containing the retrieved information formatted for the LLM
    """
    try:
        # Access dependencies from context - they are already initialized
        # Do NOT call initialize() here - dependencies are provided by the caller
        deps = ctx.deps

        # Perform search based on type using provided dependencies
        if search_type == "hybrid":
            results = await hybrid_search(
                ctx=deps,
                query=query,
                match_count=match_count
            )
        else:
            results = await semantic_search(
                ctx=deps,
                query=query,
                match_count=match_count
            )

        # Format results
        if not results:
            return "No relevant information found in the knowledge base."

        # Build formatted response
        response_parts = [f"Found {len(results)} relevant documents:\n"]

        for i, result in enumerate(results, 1):
            title = result.get('document_title', 'Unknown')
            content = result.get('content', '')
            similarity = result.get('combined_score', result.get('similarity', 0))

            response_parts.append(
                f"\n--- Document {i}: {title} (relevance: {similarity:.2f}) ---"
            )
            response_parts.append(content)

        return "\n".join(response_parts)

    except Exception as e:
        logger.exception("search_tool_failed", query=query, error=str(e))
        return f"Error searching knowledge base: {str(e)}"
```

**Key Points:**
- Dependencies are accessed via `ctx.deps` - they are already initialized
- The `RunContext[DepsType]` type parameter must match the agent's `deps_type`
- Do NOT call `initialize()` or `cleanup()` inside tools - lifecycle is managed by the caller
- Tools should only use the provided dependencies, not create new ones

### Tool Best Practices

1. **Return strings, not objects**: LLMs consume text, not Pydantic models
2. **Include context**: Format results with source attribution
3. **Handle errors gracefully**: Return helpful error messages, don't crash
4. **Access dependencies via ctx.deps**: Dependencies are provided, not created in tools
5. **Do NOT initialize dependencies**: Dependencies should be initialized before `agent.run()` is called
6. **Do NOT cleanup in tools**: Resource cleanup is handled by the caller (FastAPI or application code)
7. **Log operations**: Log tool calls for debugging

### Alternative Tool Pattern (Direct Dependencies)

This pattern assumes dependencies are already initialized and provided via `RunContext`:

```python
@rag_agent.tool
async def search_knowledge_base(
    ctx: RunContext[AgentDependencies],  # Dependencies type matches agent's deps_type
    query: str,
    match_count: Optional[int] = 5,
    search_type: Optional[str] = "semantic"
) -> str:
    """Search knowledge base with direct dependency access.

    Note: Dependencies are already initialized by the caller before agent.run() is called.
    """

    # Access dependencies from context - they are already initialized
    deps = ctx.deps
    mongo_client = deps.mongo_client
    db = deps.db

    # Generate query embedding using provided dependencies
    embedding = await deps.get_embedding(query)

    # Build and execute search pipeline
    if search_type == "hybrid":
        pipeline = build_hybrid_search_pipeline(query, embedding, match_count)
    else:
        pipeline = build_semantic_search_pipeline(embedding, match_count)

    results = await db.chunks.aggregate(pipeline).to_list(length=match_count)

    # Format and return
    return format_search_results(results)
```

**Important**: This pattern correctly accesses dependencies via `ctx.deps` without initializing them. The dependencies must be initialized before calling `agent.run(deps=deps)`.

## Streaming Implementation

### CLI Streaming Pattern

```python
async def stream_agent_interaction(
    user_input: str,
    message_history: List,
    deps: StateDeps[RAGState]
) -> tuple[str, List]:
    """
    Stream agent interaction with real-time tool call display.

    Args:
        user_input: The user's input text
        message_history: Conversation history
        deps: StateDeps with RAG state

    Returns:
        Tuple of (streamed_text, updated_message_history)
    """
    response_text = ""

    # Stream the agent execution
    async with rag_agent.iter(
        user_input,
        deps=deps,
        message_history=message_history
    ) as run:

        async for node in run:

            # User prompt node
            if Agent.is_user_prompt_node(node):
                pass  # Clean start

            # Model request node - stream thinking
            elif Agent.is_model_request_node(node):
                console.print("[bold blue]Assistant:[/bold blue] ", end="")

                async with node.stream(run.ctx) as request_stream:
                    async for event in request_stream:
                        # Text part start
                        if isinstance(event, PartStartEvent) and event.part.part_kind == 'text':
                            initial_text = event.part.content
                            if initial_text:
                                console.print(initial_text, end="")
                                response_text += initial_text

                        # Text delta (streaming)
                        elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                            delta_text = event.delta.content_delta
                            if delta_text:
                                console.print(delta_text, end="")
                                response_text += delta_text

                console.print()  # New line

            # Tool calls
            elif Agent.is_call_tools_node(node):
                async with node.stream(run.ctx) as tool_stream:
                    async for event in tool_stream:
                        event_type = type(event).__name__

                        if event_type == "FunctionToolCallEvent":
                            # Extract tool information
                            tool_name = "Unknown Tool"
                            args = None

                            if hasattr(event, 'part'):
                                part = event.part

                                if hasattr(part, 'tool_name'):
                                    tool_name = part.tool_name
                                elif hasattr(part, 'function_name'):
                                    tool_name = part.function_name

                                if hasattr(part, 'args'):
                                    args = part.args
                                elif hasattr(part, 'arguments'):
                                    args = part.arguments

                            console.print(f"  [cyan]Calling tool:[/cyan] [bold]{tool_name}[/bold]")

                            # Show search parameters
                            if args and isinstance(args, dict):
                                if 'query' in args:
                                    console.print(f"    [dim]Query:[/dim] {args['query']}")
                                if 'search_type' in args:
                                    console.print(f"    [dim]Type:[/dim] {args['search_type']}")
                                if 'match_count' in args:
                                    console.print(f"    [dim]Results:[/dim] {args['match_count']}")

                        elif event_type == "FunctionToolResultEvent":
                            console.print(f"  [green]✓ Search completed[/green]")

            # End node
            elif Agent.is_end_node(node):
                pass

    # Get new messages from run
    new_messages = run.result.new_messages()

    return (response_text.strip(), new_messages)
```

### Streaming Event Types

**PartStartEvent**: Initial text content
```python
if isinstance(event, PartStartEvent) and event.part.part_kind == 'text':
    initial_text = event.part.content
```

**PartDeltaEvent**: Streaming text updates
```python
if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
    delta_text = event.delta.content_delta
```

**FunctionToolCallEvent**: Tool execution started
```python
if type(event).__name__ == "FunctionToolCallEvent":
    tool_name = event.part.tool_name
    args = event.part.args
```

**FunctionToolResultEvent**: Tool execution completed
```python
if type(event).__name__ == "FunctionToolResultEvent":
    result = event.result
```

## Message History Management

### Maintaining Context

```python
class ConversationManager:
    """Manages conversation history for the agent."""

    def __init__(self):
        self.message_history: List = []

    async def send_message(
        self,
        user_input: str,
        deps: StateDeps[RAGState]
    ) -> str:
        """Send message and update history."""

        # Stream response
        response_text, new_messages = await stream_agent_interaction(
            user_input,
            self.message_history,
            deps
        )

        # Add new messages to history
        self.message_history.extend(new_messages)

        return response_text

    def clear_history(self):
        """Clear conversation history."""
        self.message_history = []

    def get_history_length(self) -> int:
        """Get number of messages in history."""
        return len(self.message_history)
```

### History Truncation

```python
def truncate_history(
    message_history: List,
    max_messages: int = 20
) -> List:
    """Keep only recent messages to avoid context limits."""
    if len(message_history) <= max_messages:
        return message_history

    # Keep most recent messages
    return message_history[-max_messages:]
```

## Dependencies Pattern

### Pydantic AI Dependency System

Pydantic AI uses a type-safe dependency injection system where dependencies are:
1. **Declared** via `deps_type` parameter in `Agent()` constructor
2. **Passed** explicitly when calling `agent.run(deps=deps)` or `agent.iter(deps=deps)`
3. **Accessed** via `RunContext[DepsType]` and `ctx.deps` attribute in tools, instructions, and system prompts

### Dependency Types

Dependencies can be:
- **Dataclasses**: Using `@dataclass` decorator
- **Pydantic BaseModel**: Using `BaseModel` class
- **Simple Types**: `str`, `int`, `bool`, etc.
- **StateDeps**: For stateful agents (`StateDeps[StateType]` where `StateType` is a Pydantic BaseModel)

### Dataclass Dependencies Example

```python
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext

@dataclass
class AgentDependencies:
    """Dependencies injected into the agent context."""
    mongo_client: AsyncMongoClient
    db: Any
    openai_client: openai.AsyncOpenAI
    settings: Any

    async def initialize(self):
        """Initialize external connections."""
        # Initialize MongoDB connection
        await self.mongo_client.admin.command('ping')
        # OpenAI client is already initialized

    async def cleanup(self):
        """Clean up connections."""
        await self.mongo_client.close()

    async def get_embedding(self, text: str) -> list[float]:
        """Generate embedding for text."""
        response = await self.openai_client.embeddings.create(
            model=self.settings.embedding_model,
            input=text
        )
        return response.data[0].embedding

# Create agent with dataclass dependencies
agent = Agent(
    'openai:gpt-4o',
    deps_type=AgentDependencies
)

# Use in tools
@agent.tool
async def search(ctx: RunContext[AgentDependencies], query: str) -> str:
    embedding = await ctx.deps.get_embedding(query)
    # Use ctx.deps.mongo_client, ctx.deps.db, etc.
    return "Search results..."
```

### Pydantic BaseModel Dependencies Example

```python
from pydantic import BaseModel
from typing import Optional
from pydantic_ai import Agent, RunContext

class AgentDependencies(BaseModel):
    """Dependencies as Pydantic model."""
    mongo_client: Optional[AsyncMongoClient] = None
    db: Optional[Any] = None
    openai_client: Optional[openai.AsyncOpenAI] = None
    settings: Optional[Any] = None

    @classmethod
    def from_settings(cls, **kwargs) -> "AgentDependencies":
        """Factory method to create dependencies from settings."""
        return cls(**kwargs)

    async def initialize(self):
        """Initialize external connections."""
        if not self.mongo_client:
            self.mongo_client = AsyncMongoClient(self.settings.mongodb_uri)
            self.db = self.mongo_client[self.settings.mongodb_database]
        # ... rest of initialization

    async def cleanup(self):
        """Clean up connections."""
        if self.mongo_client:
            await self.mongo_client.close()

# Create agent
agent = Agent('openai:gpt-4o', deps_type=AgentDependencies)

# Initialize and use
deps = AgentDependencies.from_settings()
await deps.initialize()
try:
    result = await agent.run("Query", deps=deps)
finally:
    await deps.cleanup()
```

### StateDeps for Stateful Agents

```python
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.ag_ui import StateDeps

class RAGState(BaseModel):
    """State for the RAG agent."""
    conversation_history: list[str] = []
    user_preferences: dict[str, Any] = {}

# Create agent with StateDeps
agent = Agent(
    'openai:gpt-4o',
    deps_type=StateDeps[RAGState]
)

# Access state in tools
@agent.tool
async def update_history(ctx: RunContext[StateDeps[RAGState]], message: str) -> str:
    ctx.deps.state.conversation_history.append(message)
    return "History updated"

# Use with state
state = RAGState()
deps = StateDeps(state=state)
result = await agent.run("Hello", deps=deps)
```

### Key Principles

1. **Dependencies are provided, not created**: Tools access `ctx.deps` - dependencies are initialized before `agent.run()` is called
2. **Type safety**: `RunContext[DepsType]` ensures type checking matches the agent's `deps_type`
3. **Lifecycle management**: Dependencies with resources (DB connections, HTTP clients) should have `initialize()` and `cleanup()` methods, but these are called by application code, not by Pydantic AI
4. **No initialization in tools**: Tools should never call `initialize()` or create new dependency instances
5. **For Pydantic BaseModel dependencies**: Use `@classmethod from_settings()` pattern for factory creation

### Common Mistakes to Avoid

**❌ WRONG - Initializing dependencies inside tools:**
```python
@agent.tool
async def search(ctx: RunContext[AgentDependencies], query: str) -> str:
    # ❌ DON'T DO THIS - dependencies are already provided!
    deps = AgentDependencies.from_settings()
    await deps.initialize()
    try:
        # ... use deps
    finally:
        await deps.cleanup()
```

**✅ CORRECT - Access dependencies from RunContext:**
```python
@agent.tool
async def search(ctx: RunContext[AgentDependencies], query: str) -> str:
    # ✅ Dependencies are already initialized and provided
    deps = ctx.deps
    # Use deps directly - no initialization needed
    results = await deps.search(query)
    return format_results(results)
```

**❌ WRONG - Mixing FastAPI Depends() with Pydantic AI RunContext:**
```python
@agent.tool
async def search(
    ctx: RunContext[AgentDependencies],
    db: Annotated[Session, Depends(get_db)]  # ❌ DON'T DO THIS
) -> str:
    # FastAPI Depends() doesn't work in Pydantic AI tools
```

**✅ CORRECT - Use RunContext for all dependencies:**
```python
@agent.tool
async def search(ctx: RunContext[AgentDependencies], query: str) -> str:
    # ✅ All dependencies come from ctx.deps
    db = ctx.deps.db
    # Use db directly
```

**❌ WRONG - Creating new dependency instances in tools:**
```python
@agent.tool
async def search(ctx: RunContext[AgentDependencies], query: str) -> str:
    # ❌ DON'T create new instances
    new_deps = AgentDependencies(...)
    await new_deps.initialize()
```

**✅ CORRECT - Use provided dependencies:**
```python
@agent.tool
async def search(ctx: RunContext[AgentDependencies], query: str) -> str:
    # ✅ Use the provided dependencies
    deps = ctx.deps
    # Dependencies are already initialized by the caller
```

## FastAPI Integration Patterns

### FastAPI Dependency Injection System

FastAPI uses a different dependency injection system than Pydantic AI:
- **Declaration**: Dependencies are declared in function signatures using `Depends()`
- **Injection**: FastAPI automatically resolves and injects dependencies before endpoint execution
- **Type Safety**: Use `Annotated[Type, Depends(function)]` pattern (Python 3.10+)
- **Resource Cleanup**: Use `yield` in dependency functions for proper cleanup

### Basic FastAPI Dependency Pattern

```python
from typing import Annotated
from fastapi import Depends, FastAPI, APIRouter

router = APIRouter()

# Simple dependency function
async def get_common_params(
    q: str | None = None,
    skip: int = 0,
    limit: int = 100
) -> dict:
    return {"q": q, "skip": skip, "limit": limit}

# Use in endpoint
@router.get("/items/")
async def read_items(
    commons: Annotated[dict, Depends(get_common_params)]
):
    return commons
```

### FastAPI Dependency with Resource Cleanup (yield pattern)

```python
from typing import Annotated, AsyncGenerator
from fastapi import Depends, APIRouter

router = APIRouter()

# Dependency with yield for cleanup
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSessionLocal()
    try:
        yield session  # Injected into endpoint
        await session.commit()  # Commit if no exceptions
    except Exception:
        await session.rollback()  # Rollback on error
        raise
    finally:
        await session.close()  # Always close

# Use in endpoint
@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db_session)]
):
    user = await db.get(User, user_id)
    return user
```

### Integrating Pydantic AI Agents with FastAPI

When using Pydantic AI agents in FastAPI endpoints, combine both dependency systems:

```python
from typing import Annotated, AsyncGenerator
from fastapi import Depends, APIRouter
from pydantic_ai import Agent, RunContext

router = APIRouter()

# FastAPI dependency that creates and manages AgentDependencies
async def get_agent_deps() -> AsyncGenerator[AgentDependencies, None]:
    """FastAPI dependency that yields AgentDependencies for Pydantic AI agent."""
    deps = AgentDependencies.from_settings()
    await deps.initialize()
    try:
        yield deps  # Injected into endpoint, passed to agent.run()
    finally:
        await deps.cleanup()  # Cleanup after response

# Endpoint using both FastAPI and Pydantic AI dependencies
@router.post("/agent/query")
async def query_agent(
    request: AgentRequest,
    deps: Annotated[AgentDependencies, Depends(get_agent_deps)]
):
    """Query the RAG agent using dependencies from FastAPI."""
    # FastAPI provides deps via Depends(), we pass it to Pydantic AI
    result = await rag_agent.run(request.query, deps=deps)
    return AgentResponse(query=request.query, response=result.data)
```

### Key Differences: Pydantic AI vs FastAPI Dependencies

| Aspect | Pydantic AI | FastAPI |
|--------|-------------|---------|
| **Declaration** | `deps_type` in `Agent()` | `Depends()` in function signature |
| **Injection** | Explicit: `agent.run(deps=deps)` | Automatic: FastAPI injects before endpoint |
| **Access** | `RunContext[DepsType]` and `ctx.deps` | Direct parameter in function |
| **Type Safety** | `RunContext[DepsType]` | `Annotated[Type, Depends(...)]` |
| **Use Case** | Agent tools, instructions, agent resources | REST endpoints, DB sessions, auth |
| **Lifecycle** | Managed by application code | Managed by FastAPI (with yield) |

### Common Patterns

**Pattern 1: FastAPI manages lifecycle, Pydantic AI uses dependencies**
```python
# FastAPI dependency with yield
async def get_agent_deps() -> AsyncGenerator[AgentDependencies, None]:
    deps = AgentDependencies.from_settings()
    await deps.initialize()
    try:
        yield deps
    finally:
        await deps.cleanup()

# Endpoint
@router.post("/query")
async def query(deps: Annotated[AgentDependencies, Depends(get_agent_deps)]):
    result = await agent.run("Query", deps=deps)
    return result.data
```

**Pattern 2: Shared dependencies across multiple endpoints**
```python
# Create type alias for reuse
AgentDepsDep = Annotated[AgentDependencies, Depends(get_agent_deps)]

@router.post("/query")
async def query(deps: AgentDepsDep):
    result = await agent.run("Query", deps=deps)
    return result.data

@router.post("/search")
async def search(deps: AgentDepsDep):
    result = await agent.run("Search", deps=deps)
    return result.data
```

**Pattern 3: Dependency scope control**
```python
# Cleanup before response is sent
async def get_deps_early_cleanup() -> AsyncGenerator[AgentDependencies, None]:
    deps = AgentDependencies.from_settings()
    await deps.initialize()
    try:
        yield deps
    finally:
        await deps.cleanup()

# Use scope="function" to cleanup before response
@router.post("/query")
async def query(
    deps: Annotated[
        AgentDependencies,
        Depends(get_deps_early_cleanup, scope="function")
    ]
):
    result = await agent.run("Query", deps=deps)
    return result.data
```

### Important Notes

1. **Do NOT mix patterns**: Don't use `Depends()` inside Pydantic AI tools - use `RunContext` instead
2. **Lifecycle management**: FastAPI handles dependency lifecycle with `yield`, Pydantic AI just uses the dependencies
3. **Initialization timing**: Dependencies should be initialized in FastAPI dependency functions, not in Pydantic AI tools
4. **Type consistency**: The type in `Annotated[Type, Depends(...)]` should match the agent's `deps_type`

### Common Mistakes to Avoid

**❌ WRONG - Using FastAPI Depends() in Pydantic AI tools:**
```python
@agent.tool
async def search(
    ctx: RunContext[AgentDependencies],
    db: Annotated[Session, Depends(get_db)]  # ❌ FastAPI Depends() doesn't work here
) -> str:
    pass
```

**✅ CORRECT - All dependencies come from RunContext:**
```python
@agent.tool
async def search(ctx: RunContext[AgentDependencies], query: str) -> str:
    # ✅ Access all dependencies via ctx.deps
    db = ctx.deps.db
    # Use db directly
```

**❌ WRONG - Initializing dependencies in FastAPI endpoints:**
```python
@router.post("/query")
async def query(request: AgentRequest):
    # ❌ DON'T initialize here - use FastAPI dependency
    deps = AgentDependencies.from_settings()
    await deps.initialize()
    try:
        result = await agent.run(request.query, deps=deps)
    finally:
        await deps.cleanup()
```

**✅ CORRECT - Use FastAPI dependency with yield:**
```python
async def get_agent_deps() -> AsyncGenerator[AgentDependencies, None]:
    deps = AgentDependencies.from_settings()
    await deps.initialize()
    try:
        yield deps
    finally:
        await deps.cleanup()

@router.post("/query")
async def query(
    request: AgentRequest,
    deps: Annotated[AgentDependencies, Depends(get_agent_deps)]  # ✅ FastAPI manages lifecycle
):
    result = await agent.run(request.query, deps=deps)
    return result.data
```

## Provider Configuration

### LLM Provider Setup

```python
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel

def get_llm_model(model_choice: Optional[str] = None) -> OpenAIModel:
    """
    Get LLM model configuration.
    Supports any OpenAI-compatible API provider.
    """
    settings = load_settings()

    llm_choice = model_choice or settings.llm_model
    base_url = settings.llm_base_url
    api_key = settings.llm_api_key

    # Create provider
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)

    return OpenAIModel(llm_choice, provider=provider)
```

### Multiple Provider Support

```python
def get_llm_model_by_provider(provider_name: str) -> OpenAIModel:
    """Get model based on provider name."""
    settings = load_settings()

    providers = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini"
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "model": "anthropic/claude-haiku-4.5"
        },
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "model": "qwen2.5:14b-instruct"
        }
    }

    config = providers.get(provider_name, providers["openai"])

    provider = OpenAIProvider(
        base_url=config["base_url"],
        api_key=settings.llm_api_key
    )

    return OpenAIModel(config["model"], provider=provider)
```

## Error Handling in Tools

### Graceful Degradation

**Important**: Dependencies are provided via `RunContext` - do NOT initialize them inside tools.

```python
@rag_agent.tool
async def search_knowledge_base(
    ctx: RunContext[AgentDependencies],  # Dependencies already provided
    query: str,
    match_count: Optional[int] = 5,
    search_type: Optional[str] = "semantic"
) -> str:
    """Search with comprehensive error handling.

    Note: Dependencies are already initialized by the caller.
    """

    # Access dependencies from context - they are already initialized
    deps = ctx.deps

    # Perform search with error handling
    try:
        if search_type == "hybrid":
            results = await hybrid_search(deps, query, match_count)
        else:
            results = await semantic_search(deps, query, match_count)

    except OperationFailure as e:
        if e.code == 291:
            return (
                "Vector search index is not configured. "
                "Please set up indexes in MongoDB Atlas before searching."
            )
        raise

    except ConnectionFailure:
        return (
            "Could not connect to MongoDB. "
            "Please check your connection and try again."
        )

    except Exception as e:
        logger.exception("search_tool_error", query=query)
        return f"An error occurred while searching: {str(e)}"

    # Format results
    if not results:
        return "No relevant information found in the knowledge base."

    return format_results(results)
```

**Key Points:**
- Dependencies are accessed via `ctx.deps` - no initialization needed
- Error handling focuses on the search operation, not dependency lifecycle
- Cleanup is handled by the caller (FastAPI dependency or application code)

## Testing Agents and Tools

### Unit Testing Tools

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.unit
async def test_search_tool_success():
    """Test search tool with successful results."""

    # Mock context
    ctx = MagicMock()
    ctx.deps = MagicMock()

    # Mock dependencies
    mock_deps = AsyncMock()
    mock_deps.initialize = AsyncMock()
    mock_deps.cleanup = AsyncMock()

    # Mock search results
    mock_results = [
        {
            "document_title": "Test Doc",
            "content": "Test content",
            "similarity": 0.9
        }
    ]

    # Patch dependencies
    with patch('examples.tools.AgentDependencies', return_value=mock_deps):
        with patch('examples.tools.semantic_search', return_value=mock_results):
            result = await search_knowledge_base(
                ctx=ctx,
                query="test query",
                match_count=5,
                search_type="semantic"
            )

    assert "Found 1 relevant documents" in result
    assert "Test Doc" in result
    mock_deps.initialize.assert_called_once()
    mock_deps.cleanup.assert_called_once()
```

### Integration Testing Agent

```python
@pytest.mark.integration
async def test_agent_with_real_search():
    """Test agent with real MongoDB search."""

    # Setup
    state = RAGState()
    deps = StateDeps[RAGState](state=state)

    # Initialize real connections
    agent_deps = AgentDependencies()
    await agent_deps.initialize()

    try:
        # Run agent
        result = await rag_agent.run(
            "What is the technical architecture?",
            deps=deps
        )

        # Verify
        assert result.output
        assert len(result.output) > 0

    finally:
        await agent_deps.cleanup()
```

### Testing Tools Directly with RunContext

When testing tools directly (outside of agent.run()), use the `create_run_context()` helper to create a proper `RunContext`:

```python
import pytest
from server.projects.shared.context_helpers import create_run_context
from server.projects.mongo_rag.dependencies import AgentDependencies
from server.projects.mongo_rag.tools import semantic_search

@pytest.mark.asyncio
async def test_semantic_search_directly():
    """Test semantic search tool directly with RunContext."""
    deps = AgentDependencies()
    await deps.initialize()

    try:
        # Create run context using helper
        ctx = create_run_context(deps)

        # Call tool directly
        results = await semantic_search(ctx, query="test", match_count=5)

        assert len(results) >= 0  # May be empty if no documents
        if results:
            assert results[0].similarity > 0
    finally:
        await deps.cleanup()
```

### Using create_run_context Helper

The `create_run_context()` helper standardizes RunContext creation in samples and tests:

```python
from server.projects.shared.context_helpers import create_run_context

# Simple usage - just pass dependencies
ctx = create_run_context(deps)

# With optional state
ctx = create_run_context(deps, state={"key": "value"})

# With agent instance (for advanced use cases)
ctx = create_run_context(deps, agent=my_agent)

# With custom run_id
ctx = create_run_context(deps, run_id="custom-run-id")
```

**Benefits:**
- Type-safe: Returns `RunContext[DepsType]` matching tool signatures
- Consistent: Single pattern across all samples and tests
- Maintainable: Centralized logic for RunContext creation
- Simple: No need to manually construct RunContext with all parameters

### Testing Agents with Override Pattern

According to Pydantic AI best practices, use `agent.override()` to inject test dependencies:

```python
import pytest
from pydantic_ai.models.test import TestModel
from server.projects.mongo_rag.agent import rag_agent
from server.projects.mongo_rag.dependencies import AgentDependencies

@pytest.fixture
def override_rag_agent():
    """Override agent with TestModel for testing."""
    test_deps = AgentDependencies()  # Mock or test dependencies
    with rag_agent.override(model=TestModel(), deps=test_deps):
        yield

@pytest.mark.asyncio
async def test_rag_agent(override_rag_agent: None):
    """Test RAG agent with overridden model and dependencies."""
    result = await rag_agent.run("What is authentication?")
    assert result.data is not None
    assert len(result.data) > 0
```

### When to Use Each Pattern

**Use `agent.run(deps=deps)` when:**
- Testing the full agent workflow
- You want to test agent behavior end-to-end
- You need to verify agent tool selection and orchestration

**Use `create_run_context()` + direct tool calls when:**
- Testing individual tools in isolation
- You want to test tool logic without agent overhead
- You need fine-grained control over tool inputs
- Writing sample scripts that demonstrate tool usage

**Use `agent.override()` when:**
- Testing agent behavior with mocked models (TestModel)
- Injecting test dependencies without modifying agent definition
- Running tests that should not make real LLM calls
