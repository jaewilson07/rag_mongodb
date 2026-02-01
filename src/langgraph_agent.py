"""LangGraph-based self-corrective RAG agent."""

from __future__ import annotations

from typing import Annotated, Any, List, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from .dependencies import AgentDependencies
from .prompts import MAIN_SYSTEM_PROMPT
from .settings import Settings, load_settings
from .self_corrective_rag import (
    SourceDocument,
    generate_answer,
    grade_relevance,
    rewrite_query,
    run_multi_search,
    verify_citations,
)


LANGGRAPH_SYSTEM_PROMPT = (
    MAIN_SYSTEM_PROMPT
    + "\n\n"
    + "If the knowledge base search returns no relevant information, "
    + "call the web_search tool and use those results to answer."
)


class LangGraphState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    question: str
    transformed_queries: List[str]
    context: List[SourceDocument]
    generation: str
    iteration_count: int
    max_iterations: int
    generation_attempts: int
    max_generation_attempts: int
    relevance_ok: bool
    citations_ok: bool
    warning_banner: str


def _latest_question(messages: List[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            content = message.content
            return str(content).strip()
    return ""


async def init_state(state: LangGraphState) -> dict:
    settings: Settings = load_settings()
    question = _latest_question(state.get("messages", []))
    return {
        "question": question,
        "transformed_queries": [question] if question else [],
        "context": [],
        "generation": "",
        "iteration_count": 0,
        "max_iterations": settings.rag_max_iterations,
        "generation_attempts": 0,
        "max_generation_attempts": settings.rag_max_generation_attempts,
        "relevance_ok": False,
        "citations_ok": False,
        "warning_banner": "",
    }


async def search_node(state: LangGraphState) -> dict:
    settings: Settings = load_settings()
    deps = AgentDependencies()
    await deps.initialize()
    try:
        query = state["transformed_queries"][-1] if state["transformed_queries"] else state["question"]
        documents = await run_multi_search(
            deps=deps,
            query=query,
            settings=settings,
        )
        return {"context": documents}
    finally:
        await deps.cleanup()


async def grade_relevance_node(state: LangGraphState) -> dict:
    settings: Settings = load_settings()
    relevance_ok = await grade_relevance(state["question"], state["context"], settings)
    update: dict[str, Any] = {"relevance_ok": relevance_ok}
    if not relevance_ok and state["iteration_count"] < state["max_iterations"]:
        update["iteration_count"] = state["iteration_count"] + 1
    return update


async def rewrite_query_node(state: LangGraphState) -> dict:
    settings: Settings = load_settings()
    rewritten = await rewrite_query(state["question"], state["transformed_queries"], settings)
    if not rewritten:
        return {}
    return {"transformed_queries": state["transformed_queries"] + [rewritten]}


async def generate_node(state: LangGraphState) -> dict:
    settings: Settings = load_settings()
    answer = await generate_answer(state["question"], state["context"], settings)
    return {"generation": answer}


async def verify_citations_node(state: LangGraphState) -> dict:
    settings: Settings = load_settings()
    citations_ok = await verify_citations(
        state["question"],
        state["generation"],
        state["context"],
        settings,
    )
    update: dict[str, Any] = {"citations_ok": citations_ok}
    if not citations_ok and state["generation_attempts"] < state["max_generation_attempts"]:
        update["generation_attempts"] = state["generation_attempts"] + 1
    return update


async def finalize_node(state: LangGraphState) -> dict:
    settings: Settings = load_settings()
    response = state["generation"]
    if not state["citations_ok"]:
        response = f"{settings.rag_citation_soft_fail_banner}\n\n{response}"
    return {"messages": [AIMessage(content=response)]}


def relevance_router(state: LangGraphState) -> str:
    if not state["relevance_ok"] and state["iteration_count"] < state["max_iterations"]:
        return "rewrite"
    return "generate"


def citation_router(state: LangGraphState) -> str:
    if not state["citations_ok"] and state["generation_attempts"] < state["max_generation_attempts"]:
        return "regenerate"
    return "finalize"


def build_langgraph_agent() -> Any:
    graph = StateGraph(LangGraphState)

    graph.add_node("init", init_state)
    graph.add_node("search", search_node)
    graph.add_node("grade", grade_relevance_node)
    graph.add_node("rewrite", rewrite_query_node)
    graph.add_node("generate", generate_node)
    graph.add_node("verify", verify_citations_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("init")
    graph.add_edge("init", "search")
    graph.add_edge("search", "grade")
    graph.add_conditional_edges(
        "grade",
        relevance_router,
        {
            "rewrite": "rewrite",
            "generate": "generate",
        },
    )
    graph.add_edge("rewrite", "search")
    graph.add_edge("generate", "verify")
    graph.add_conditional_edges(
        "verify",
        citation_router,
        {
            "regenerate": "generate",
            "finalize": "finalize",
        },
    )
    graph.add_edge("finalize", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
