"""Shared models for integrations."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Protocol

import yaml
from pydantic import BaseModel, Field


class SourceFrontmatter(BaseModel):
    """Canonical frontmatter fields stamped by ingestion services."""

    schema_version: str = "1.0"
    source_type: Literal["gdrive", "web", "upload"]
    source_url: str
    source_title: Optional[str] = None
    source_id: Optional[str] = None
    source_mime_type: Optional[str] = None
    source_web_view_url: Optional[str] = None
    source_created_at: Optional[str] = None
    source_modified_at: Optional[str] = None
    source_fetched_at: Optional[str] = None
    source_etag: Optional[str] = None
    source_owners: List[str] = Field(default_factory=list)
    source_description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_frontmatter_dict(self) -> Dict[str, Any]:
        """Return a compact dict suitable for YAML frontmatter."""
        data = self.model_dump(exclude_none=True)
        if not data.get("source_owners"):
            data.pop("source_owners", None)
        if not data.get("metadata"):
            data.pop("metadata", None)
        return data


class Source(BaseModel):
    """Normalized export payload used across integrations."""

    frontmatter: SourceFrontmatter
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    links: List[str] = Field(default_factory=list)
    html: Optional[str] = None

    def to_markdown(self) -> str:
        """Return markdown including YAML frontmatter."""
        yaml_frontmatter = yaml.safe_dump(
            self.frontmatter.to_frontmatter_dict(),
            default_flow_style=False,
            sort_keys=False,
        )
        body = self.content or ""
        return f"---\n{yaml_frontmatter}---\n\n{body}".rstrip() + "\n"


class SourceURL(BaseModel):
    """Named URL entry for frontmatter metadata."""

    name: Optional[str] = None
    url: str
    kind: Optional[Literal["link", "image"]] = None


class ExportProtocol(Protocol):
    """Protocol for integration exports that return Source."""

    async def export_as_markdown(self, *args, **kwargs) -> Source:  # pragma: no cover - interface
        ...


__all__ = ["ExportProtocol", "Source", "SourceFrontmatter", "SourceURL"]
