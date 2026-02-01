"""Dataclass models for Google Drive resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import Field

from mdrag.integrations.models import Source, SourceFrontmatter


@dataclass
class GoogleDriveFile:
    """Represents a file or folder in Google Drive."""

    id: str
    name: str
    mime_type: str
    created_time: datetime
    modified_time: datetime
    web_view_link: str
    parents: list[str] | None = None
    size: int | None = None
    _raw: Any = field(default=None, repr=False)

    @property
    def raw(self) -> Any:
        """Get the raw API response dict for accessing extended attributes."""
        return self._raw

    @classmethod
    def from_dict(cls, obj: dict[str, Any], **kwargs) -> GoogleDriveFile:
        """
        Create GoogleDriveFile from API response dictionary.

        Args:
            obj: Dictionary containing the API response data
            **kwargs: Additional context

        Returns:
            GoogleDriveFile instance
        """
        # Parse datetime fields
        # Handle ISO format with or without timezone
        created_str = obj["createdTime"]
        modified_str = obj["modifiedTime"]

        # Replace Z with +00:00 for ISO parsing
        if created_str.endswith("Z"):
            created_str = created_str.replace("Z", "+00:00")
        if modified_str.endswith("Z"):
            modified_str = modified_str.replace("Z", "+00:00")

        created_time = datetime.fromisoformat(created_str)
        modified_time = datetime.fromisoformat(modified_str)

        return cls(
            id=obj["id"],
            name=obj["name"],
            mime_type=obj["mimeType"],
            created_time=created_time,
            modified_time=modified_time,
            web_view_link=obj["webViewLink"],
            parents=obj.get("parents"),
            size=obj.get("size"),
            _raw=obj,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert file to dictionary (excludes raw)."""
        return {
            "id": self.id,
            "name": self.name,
            "mime_type": self.mime_type,
            "created_time": self.created_time.isoformat(),
            "modified_time": self.modified_time.isoformat(),
            "web_view_link": self.web_view_link,
            "parents": self.parents,
            "size": self.size,
        }


@dataclass
class SearchResult:
    """Result of a Google Drive search query."""

    query: str
    folder_id: str | None = None
    folder_name: str | None = None
    total_results: int = 0
    files: list[GoogleDriveFile] = field(default_factory=list)
    _raw: Any = field(default=None, repr=False)

    @property
    def raw(self) -> Any:
        """Get the raw API response for accessing extended attributes."""
        return self._raw

    @classmethod
    def from_dict(cls, obj: dict[str, Any], **kwargs) -> SearchResult:
        """
        Create SearchResult from dictionary.

        Args:
            obj: Dictionary containing search result data
            **kwargs: Additional context

        Returns:
            SearchResult instance
        """
        # Recursively deserialize files
        files = [GoogleDriveFile.from_dict(f) for f in obj.get("files", [])]

        return cls(
            query=obj["query"],
            folder_id=obj.get("folder_id"),
            folder_name=obj.get("folder_name"),
            total_results=obj.get("total_results", len(files)),
            files=files,
            _raw=obj,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert search result to dictionary (excludes raw)."""
        return {
            "query": self.query,
            "folder_id": self.folder_id,
            "folder_name": self.folder_name,
            "total_results": self.total_results,
            "files": [f.to_dict() for f in self.files],
        }


class GoogleDocumentTab(Source):
    """Represents a Google Doc tab/section split from exported HTML."""

    tab_id: str
    title: str
    index: int
    parent_tab_id: str | None = None
    tab_url: str | None = None
    raw: Any = Field(default=None, exclude=True, repr=False)

    @property
    def markdown_content(self) -> str:
        """Backward-compatible accessor for the tab markdown content."""
        return self.content

    @property
    def tab_name(self) -> str:
        """Alias for tab title (used in frontmatter metadata)."""
        return self.title

    @classmethod
    def from_dict(cls, obj: dict[str, Any], **kwargs) -> GoogleDocumentTab:
        """
        Create GoogleDocumentTab from dictionary.

        Args:
            obj: Dictionary containing tab data
            **kwargs: Additional context

        Returns:
            GoogleDocumentTab instance
        """
        frontmatter_data = obj.get("frontmatter") or {}
        frontmatter = SourceFrontmatter.model_validate(frontmatter_data)

        return cls(
            frontmatter=frontmatter,
            content=obj.get("content") or obj.get("markdown_content") or "",
            metadata=obj.get("metadata", {}),
            links=obj.get("links", []),
            html=obj.get("html"),
            tab_id=obj.get("tab_id") or obj.get("id") or "",
            title=obj.get("title") or "",
            index=obj.get("index", 0),
            parent_tab_id=obj.get("parent_tab_id"),
            tab_url=obj.get("tab_url"),
            raw=obj,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert tab to dictionary (excludes raw)."""
        data = self.model_dump(exclude={"raw"}, exclude_none=True)
        data["markdown_content"] = self.content
        return data


class Source_GoogleDocsTab(GoogleDocumentTab):
    """Source payload for Google Docs tab exports."""
    pass


__all__ = [
    "GoogleDocumentTab",
    "GoogleDriveFile",
    "SearchResult",
    "Source_GoogleDocsTab",
]
