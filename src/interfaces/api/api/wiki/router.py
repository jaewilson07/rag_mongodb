"""Wiki API routes for generating and querying knowledge wikis."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from mdrag.interfaces.api.api.wiki.models import (
    WikiChatRequest,
    WikiPageGenerateRequest,
    WikiProjectsListResponse,
    WikiStructureRequest,
    WikiStructureResponse,
)
from mdrag.interfaces.api.config import api_config
from mdrag.interfaces.api.services.wiki import WikiService

logger = logging.getLogger(__name__)

wiki_router = APIRouter(
    prefix=api_config.WIKI_PREFIX,
    tags=["wiki"],
)


@wiki_router.post("/structure", response_model=WikiStructureResponse)
async def generate_wiki_structure(
    request: WikiStructureRequest,
) -> WikiStructureResponse:
    """Generate a wiki structure from ingested documents.

    Analyzes the ingested documents and creates a structured wiki
    with pages and sections organized by topic.
    """
    service = WikiService()
    try:
        result = await service.generate_structure(
            title=request.title,
            filters=request.filters,
            match_count=request.match_count,
        )
        return WikiStructureResponse(**result)
    except Exception as e:
        logger.exception("Error generating wiki structure: %s", str(e))
        raise


@wiki_router.post("/generate")
async def generate_wiki_page(
    request: WikiPageGenerateRequest,
) -> StreamingResponse:
    """Generate content for a single wiki page.

    Uses RAG to search relevant chunks and generate comprehensive
    wiki page content with citations and diagrams.
    """
    service = WikiService()

    async def content_stream():
        try:
            async for chunk in service.stream_page_content(
                page_id=request.page_id,
                page_title=request.page_title,
                source_documents=request.source_documents,
                wiki_title=request.wiki_title,
            ):
                yield chunk
        except Exception as e:
            logger.exception("Error streaming page content: %s", str(e))
            yield f"\n\nError generating content: {str(e)}"

    return StreamingResponse(
        content_stream(),
        media_type="text/plain; charset=utf-8",
    )


@wiki_router.post("/chat")
async def wiki_chat(request: WikiChatRequest) -> StreamingResponse:
    """Chat with the knowledge base within wiki context.

    Provides a conversational interface to query the ingested
    data with streaming responses.
    """
    service = WikiService()

    async def chat_stream():
        try:
            async for chunk in service.stream_chat_response(
                messages=request.messages,
                wiki_context=request.wiki_context,
                match_count=request.match_count,
            ):
                yield chunk
        except Exception as e:
            logger.exception("Error streaming chat: %s", str(e))
            yield f"\n\nError: {str(e)}"

    return StreamingResponse(
        chat_stream(),
        media_type="text/plain; charset=utf-8",
    )


@wiki_router.get("/projects", response_model=WikiProjectsListResponse)
async def list_wiki_projects() -> WikiProjectsListResponse:
    """List available wiki projects based on ingested data.

    Returns summaries of document groups that can be used
    to generate wikis.
    """
    service = WikiService()
    try:
        projects = await service.list_projects()
        return WikiProjectsListResponse(projects=projects)
    except Exception as e:
        logger.exception("Error listing projects: %s", str(e))
        return WikiProjectsListResponse(projects=[])
