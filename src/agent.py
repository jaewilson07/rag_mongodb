"""Main MongoDB RAG agent implementation with shared state."""

from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, ConfigDict
from typing import Optional
from textwrap import dedent

from pydantic_ai.ag_ui import StateDeps

from .providers import get_llm_model
from .dependencies import AgentDependencies
from .prompts import MAIN_SYSTEM_PROMPT
from .tools import (
    format_web_search_results,
    hybrid_search,
    searxng_search,
    semantic_search,
    text_search,
)
from .retrieval.formatting import format_search_results
from .self_corrective_rag import run_self_corrective_rag


class RAGState(BaseModel):
    """Minimal shared state for the RAG agent."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    agent_deps: Optional[AgentDependencies] = None


# Create the RAG agent with AGUI support
rag_agent = Agent(
    get_llm_model(),
    deps_type=StateDeps[RAGState],
    instructions=MAIN_SYSTEM_PROMPT
)


@rag_agent.instructions
async def rag_instructions(ctx: RunContext[StateDeps[RAGState]]) -> str:
    """Dynamic instructions for the RAG agent.

    Uses runtime context to reinforce tool usage and citation expectations.
    """
    _ = ctx
    return dedent(
        """
        INSTRUCTIONS:
        1. Use `self_corrective_rag` for knowledge questions requiring citations.
        2. Prefer "hybrid" for specific facts; use "semantic" for conceptual queries.
        3. Base answers on retrieved content and cite sources when possible.
        4. If RAG results are empty, use `web_search` as a fallback.
        5. If web results are empty, say so and ask a clarifying question.
        """
    ).strip()


@rag_agent.tool
async def self_corrective_rag(
    ctx: RunContext[StateDeps[RAGState]],
    question: str,
) -> str:
    """Run the self-corrective RAG workflow with feedback loops."""
    state = ctx.deps.state
    if state.agent_deps is None:
        state.agent_deps = AgentDependencies()

    agent_deps = state.agent_deps
    if agent_deps is None:
        return "Search unavailable: dependencies not initialized."
    if not agent_deps.mongo_client:
        await agent_deps.initialize()

    workflow_state = await run_self_corrective_rag(question, agent_deps)
    response = workflow_state.generation
    if workflow_state.warning_banner:
        response = f"{workflow_state.warning_banner}\n\n{response}"
    return response


@rag_agent.tool
async def web_search(
    ctx: RunContext[StateDeps[RAGState]],
    query: str,
    result_count: Optional[int] = 5,
    categories: Optional[str] = None,
    engines: Optional[list[str]] = None,
) -> str:
    """Search the web via SearXNG and return formatted results."""
    state = ctx.deps.state
    if state.agent_deps is None:
        state.agent_deps = AgentDependencies()

    agent_deps = state.agent_deps
    if agent_deps is None:
        return "Web search unavailable: dependencies not initialized."

    class DepsWrapper:
        def __init__(self, deps):
            self.deps = deps

    deps_ctx = DepsWrapper(agent_deps)
    results = await searxng_search(
        ctx=deps_ctx,
        query=query,
        result_count=result_count or 5,
        categories=categories,
        engines=engines,
    )
    return format_web_search_results(results)


@rag_agent.tool
async def search_knowledge_base(
    ctx: RunContext[StateDeps[RAGState]],
    query: str,
    match_count: Optional[int] = 5,
    search_type: Optional[str] = "hybrid"
) -> str:
    """
    Search the knowledge base for relevant information.

    Args:
        ctx: Agent runtime context with state dependencies
        query: Search query text
        match_count: Number of results to return (default: 5)
        search_type: Type of search - "semantic" or "text" or "hybrid" (default: hybrid)

    Returns:
        String containing the retrieved information formatted for the LLM
    """
    try:
        # Initialize or reuse dependencies for the session
        state = ctx.deps.state
        if state.agent_deps is None:
            state.agent_deps = AgentDependencies()

        agent_deps = state.agent_deps
        if agent_deps is None:
            return "Search unavailable: dependencies not initialized."
        if not agent_deps.mongo_client:
            await agent_deps.initialize()

        # Create a context wrapper for the search tools
        class DepsWrapper:
            def __init__(self, deps):
                self.deps = deps

        deps_ctx = DepsWrapper(agent_deps)

        # Perform the search based on type
        if search_type == "hybrid":
            results = await hybrid_search(
                ctx=deps_ctx,
                query=query,
                match_count=match_count
            )
        elif search_type == "semantic":
            results = await semantic_search(
                ctx=deps_ctx,
                query=query,
                match_count=match_count
            )
        else:
            results = await text_search(
                ctx=deps_ctx,
                query=query,
                match_count=match_count
            )

        # Format results as a simple string with citations
        if not results:
            web_results = await searxng_search(
                ctx=deps_ctx,
                query=query,
                result_count=match_count or 5,
            )
            if web_results:
                return "RAG returned no results. Falling back to web search.\n\n" + format_web_search_results(web_results)
            if agent_deps.last_search_error:
                return f"Search unavailable: {agent_deps.last_search_error}"
            return "No relevant information found in the knowledge base."

        agent_deps.last_search_error = None
        agent_deps.last_search_error_code = None

        return format_search_results(results)

    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"
