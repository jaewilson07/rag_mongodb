"""Self-corrective RAG workflow utilities shared across agents."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from .dependencies import AgentDependencies
from .mdrag_logging.service_logging import get_logger, log_async
from .prompts import (
    CITATION_VERIFIER_PROMPT,
    GENERATION_PROMPT,
    QUERY_REWRITE_PROMPT,
    RELEVANCE_GRADER_PROMPT,
)
from .settings import Settings, load_settings
from .tools import (
    SearchResult,
    WebSearchResult,
    hybrid_search,
    searxng_search,
)

logger = get_logger(__name__)


class SourceDocument(BaseModel):
    """Represents retrieved context with provenance."""

    content: str
    url: str
    source_type: str = Field(description="Either 'atlas' or 'searxng'")
    title: Optional[str] = None
    relevance_score: Optional[float] = None


class GraphState(BaseModel):
    """Shared graph state for self-corrective RAG."""

    question: str
    transformed_queries: List[str] = Field(default_factory=list)
    context: List[SourceDocument] = Field(default_factory=list)
    generation: str = ""
    iteration_count: int = 0
    max_iterations: int = 2
    generation_attempts: int = 0
    max_generation_attempts: int = 2
    relevance_ok: bool = False
    citations_ok: bool = False
    warning_banner: str = ""


def build_chat_model(settings: Settings, temperature: float | None = None) -> ChatOpenAI:
    """Build ChatOpenAI. Use temperature param for explicit override (e.g. 0.0 for verification).
    Otherwise provider decides (OpenRouter omits, vLLM/Ollama include when set)."""
    from mdrag.llm.completion_client import get_llm_init_kwargs
    kwargs: dict = {
        "model": settings.llm_model,
        "api_key": SecretStr(settings.llm_api_key),
        "base_url": settings.llm_base_url,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    else:
        kwargs.update(get_llm_init_kwargs(settings))
    return ChatOpenAI(**kwargs)


def atlas_results_to_documents(results: List[SearchResult]) -> List[SourceDocument]:
    docs: List[SourceDocument] = []
    for result in results:
        url = (
            result.metadata.get("source_url")
            if isinstance(result.metadata, dict)
            else None
        ) or result.document_source
        docs.append(
            SourceDocument(
                content=result.content,
                url=url or "",
                source_type="atlas",
                title=result.document_title,
                relevance_score=result.similarity,
            )
        )
    return docs


def web_results_to_documents(results: List[WebSearchResult]) -> List[SourceDocument]:
    docs: List[SourceDocument] = []
    for result in results:
        docs.append(
            SourceDocument(
                content=result.content,
                url=result.url,
                source_type="searxng",
                title=result.title,
                relevance_score=result.score,
            )
        )
    return docs


def dedupe_documents(documents: List[SourceDocument]) -> List[SourceDocument]:
    seen: set[str] = set()
    deduped: List[SourceDocument] = []
    for doc in documents:
        key = f"{doc.url}::" + re.sub(r"\s+", " ", doc.content.strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(doc)
    return deduped


def format_context(documents: List[SourceDocument]) -> str:
    if not documents:
        return "No sources available."

    lines: List[str] = []
    for idx, doc in enumerate(documents, start=1):
        title = doc.title or doc.url or f"Source {idx}"
        content = doc.content.strip() or "(no snippet)"
        lines.append(
            f"[{idx}] {title}\nURL: {doc.url}\nContent: {content}"
        )
    return "\n\n".join(lines)


def _extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
        return "".join(parts)
    return ""


async def rewrite_query(question: str, prior_queries: List[str], settings: Settings) -> str:
    model = build_chat_model(settings=settings)
    prompt = QUERY_REWRITE_PROMPT.format(
        question=question,
        prior_queries="; ".join(prior_queries) if prior_queries else "(none)",
    )
    response = await model.ainvoke([SystemMessage(content=prompt), HumanMessage(content=question)])
    return _content_to_text(response.content).strip()


async def grade_relevance(
    question: str,
    documents: List[SourceDocument],
    settings: Settings,
) -> bool:
    if not documents:
        return False

    model = build_chat_model(settings=settings, temperature=0.0)  # Deterministic for verification
    prompt = RELEVANCE_GRADER_PROMPT.format(
        question=question,
        context=format_context(documents),
    )
    response = await model.ainvoke([SystemMessage(content=prompt)])
    payload = _extract_json(_content_to_text(response.content))
    return bool(payload.get("relevant"))


async def generate_answer(
    question: str,
    documents: List[SourceDocument],
    settings: Settings,
) -> str:
    model = build_chat_model(settings=settings)
    prompt = GENERATION_PROMPT.format(
        question=question,
        context=format_context(documents),
    )
    response = await model.ainvoke([SystemMessage(content=prompt)])
    return _content_to_text(response.content).strip()


def _has_valid_citations(answer: str, documents: List[SourceDocument]) -> bool:
    if not answer:
        return False
    citation_matches = re.findall(r"\[(\d+)\]", answer)
    if not citation_matches:
        return False
    max_index = len(documents)
    return all(1 <= int(idx) <= max_index for idx in citation_matches)


async def verify_citations(
    question: str,
    answer: str,
    documents: List[SourceDocument],
    settings: Settings,
) -> bool:
    if not _has_valid_citations(answer, documents):
        return False

    model = build_chat_model(settings=settings, temperature=0.0)  # Deterministic for verification
    prompt = CITATION_VERIFIER_PROMPT.format(
        question=question,
        answer=answer,
        context=format_context(documents),
    )
    response = await model.ainvoke([SystemMessage(content=prompt)])
    payload = _extract_json(_content_to_text(response.content))
    return bool(payload.get("verified"))


async def run_multi_search(
    deps: AgentDependencies,
    query: str,
    settings: Settings,
) -> List[SourceDocument]:
    class DepsWrapper:
        def __init__(self, deps: AgentDependencies):
            self.deps = deps

    deps_ctx = DepsWrapper(deps)
    atlas_results = await hybrid_search(
        ctx=deps_ctx,
        query=query,
        match_count=settings.default_match_count,
    )
    web_results = await searxng_search(
        ctx=deps_ctx,
        query=query,
        result_count=settings.rag_web_result_count,
    )

    documents = atlas_results_to_documents(atlas_results) + web_results_to_documents(web_results)
    return dedupe_documents(documents)


async def run_self_corrective_rag(
    question: str,
    deps: AgentDependencies,
) -> GraphState:
    settings = load_settings()
    log_async(
        logger,
        "info",
        "self_corrective_rag_started",
        action="self_corrective_rag_started",
        question=question,
    )
    state = GraphState(
        question=question,
        transformed_queries=[question],
        max_iterations=settings.rag_max_iterations,
        max_generation_attempts=settings.rag_max_generation_attempts,
    )

    while state.iteration_count <= state.max_iterations:
        query = state.transformed_queries[-1]
        state.context = await run_multi_search(deps=deps, query=query, settings=settings)

        state.relevance_ok = await grade_relevance(state.question, state.context, settings)
        if state.relevance_ok:
            break

        if state.iteration_count >= state.max_iterations:
            break

        state.iteration_count += 1
        rewritten = await rewrite_query(state.question, state.transformed_queries, settings)
        if rewritten:
            state.transformed_queries.append(rewritten)

    while state.generation_attempts <= state.max_generation_attempts:
        state.generation = await generate_answer(state.question, state.context, settings)
        state.citations_ok = await verify_citations(
            state.question,
            state.generation,
            state.context,
            settings,
        )
        if state.citations_ok:
            break
        if state.generation_attempts >= state.max_generation_attempts:
            break
        state.generation_attempts += 1

    if not state.citations_ok:
        state.warning_banner = settings.rag_citation_soft_fail_banner

    log_async(
        logger,
        "info",
        "self_corrective_rag_completed",
        action="self_corrective_rag_completed",
        relevance_ok=state.relevance_ok,
        citations_ok=state.citations_ok,
        iterations=state.iteration_count,
        generation_attempts=state.generation_attempts,
    )

    return state
