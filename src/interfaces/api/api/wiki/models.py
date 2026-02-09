"""Pydantic models for wiki API endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WikiStructureRequest(BaseModel):
    """Request to generate a wiki structure from ingested data."""

    title: str = Field(
        default="Knowledge Base Wiki",
        description="Title for the wiki",
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filters for document selection (source_type, source_group, etc.)",
    )
    match_count: int = Field(
        default=20,
        description="Number of document groups to consider for structure",
    )


class WikiPageGenerateRequest(BaseModel):
    """Request to generate content for a single wiki page."""

    page_id: str = Field(..., description="ID of the page to generate")
    page_title: str = Field(..., description="Title of the page")
    source_documents: List[str] = Field(
        default_factory=list,
        description="Source document IDs or titles relevant to this page",
    )
    wiki_title: str = Field(
        default="Knowledge Base",
        description="Title of the parent wiki",
    )


class WikiChatRequest(BaseModel):
    """Request for chat interaction within wiki context."""

    messages: List[Dict[str, str]] = Field(
        ..., description="Chat message history"
    )
    wiki_context: str = Field(
        default="",
        description="Wiki context to scope the query",
    )
    search_type: str = Field(default="hybrid", description="Search type")
    match_count: int = Field(default=5, description="Number of results")


class WikiPage(BaseModel):
    """A single wiki page in the structure."""

    id: str
    title: str
    content: str = ""
    importance: str = "medium"
    relatedPages: List[str] = Field(default_factory=list)
    sourceDocuments: List[str] = Field(default_factory=list)
    parentId: Optional[str] = None
    isSection: bool = False
    children: List[str] = Field(default_factory=list)


class WikiSection(BaseModel):
    """A section grouping wiki pages."""

    id: str
    title: str
    pages: List[str] = Field(default_factory=list)
    subsections: List[str] = Field(default_factory=list)


class WikiStructureResponse(BaseModel):
    """Response containing the wiki structure."""

    id: str
    title: str
    description: str
    pages: List[WikiPage]
    sections: List[WikiSection]
    rootSections: List[str]


class WikiProjectResponse(BaseModel):
    """A wiki project summary."""

    id: str
    title: str
    description: str
    createdAt: str
    updatedAt: str
    pageCount: int
    sourceCount: int


class WikiProjectsListResponse(BaseModel):
    """Response listing all wiki projects."""

    projects: List[WikiProjectResponse]
