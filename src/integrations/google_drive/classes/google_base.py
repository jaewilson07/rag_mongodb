"""Base classes and protocols for Google API services following SOLID principles."""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from mdrag.integrations.models import Source

from .google_auth import GoogleAuth


@runtime_checkable
class GoogleAPIProtocol(Protocol):
    """Protocol for Google API services with authentication and core operations."""

    authenticator: GoogleAuth

    async def execute_query(self, query: str, **kwargs) -> dict[str, Any]:
        """Execute a raw API query."""
        ...

    async def get_file_metadata(self, file_id: str, **kwargs) -> dict[str, Any]:
        """Get metadata for a specific file."""
        ...

    async def export_as_media(self, file_id: str, mime_type: str) -> Any:
        """Export a file as media in the requested MIME type."""
        ...

    async def get_file_media(self, file_id: str) -> Any:
        """Download file media from the API."""
        ...


class GoogleBaseAPI(ABC):
    """Base class for Google API services with shared authentication pattern.

    Provides common initialization and authentication management for all Google
    API services (Drive, Docs, Sheets, etc).
    """

    def __init__(self, authenticator: GoogleAuth):
        """Initialize with authenticated credentials.

        Args:
            authenticator: GoogleAuth instance for handling OAuth credentials
        """
        self.authenticator = authenticator
        self._service = None

    @property
    @abstractmethod
    def service(self):
        """Lazy-loaded Google API service client."""

    async def refresh_credentials_if_needed(self) -> None:
        """Refresh OAuth credentials if they are expired."""
        await self.authenticator.refresh_if_needed_async()


class GoogleBaseSearch(ABC):
    """Abstract base class for Google API search operations.

    Defines the interface for search functionality that can be implemented
    by different Google services (Drive files, Docs content, etc).
    """

    def __init__(self, parent: GoogleAPIProtocol):
        """Initialize with parent API service.

        Args:
            parent: Parent Google API service instance
        """
        self._parent = parent

    @abstractmethod
    async def _execute_search(self, query: str, **kwargs) -> dict[str, Any]:
        """Execute service-specific search query.

        Args:
            query: Search query string
            **kwargs: Service-specific search parameters

        Returns:
            Raw API response
        """

    async def search(self, query: str, top_n: int = 10, **kwargs) -> Any:
        """Public search interface with common parameters.

        Args:
            query: Search query string
            top_n: Maximum number of results
            **kwargs: Service-specific parameters

        Returns:
            Formatted search results
        """
        # Common search logic here
        results = await self._execute_search(query, page_size=top_n, **kwargs)
        return self._format_results(results, query, **kwargs)

    @abstractmethod
    def _format_results(self, raw_results: dict[str, Any], query: str, **kwargs) -> Any:
        """Format raw API results into service-specific result objects.

        Args:
            raw_results: Raw API response
            query: Original search query
            **kwargs: Additional context for formatting

        Returns:
            Formatted result object
        """


class GoogleBaseExport(ABC):
    """Abstract base class for Google API export/download operations.

    Defines the interface for content export functionality that can be
    implemented by different Google services.
    """

    def __init__(self, parent: GoogleAPIProtocol):
        """Initialize with parent API service.

        Args:
            parent: Parent Google API service instance
        """
        self._parent = parent

    def _clean_name(self, value: str) -> str:
        """Clean a string for use as a filename.

        Keeps alphanumeric characters and specific special characters
        (space, underscore, hyphen, period), replacing all others with underscore.

        Args:
            value: String to clean

        Returns:
            Cleaned filename-safe string
        """
        return "".join(c if c.isalnum() or c in (" ", "_", "-", ".") else "_" for c in value)

    @abstractmethod
    async def _download_content(self, file_id: str, mime_type: str) -> str:
        """Download content from service-specific API.

        Args:
            file_id: File identifier
            mime_type: MIME type of the file

        Returns:
            File content as string
        """

    async def export_as_markdown(
        self,
        file_id: str,
        include_metadata: bool = True,
        **kwargs,
    ) -> "Source":
        """Export content as markdown with required metadata.

        Args:
            file_id: File identifier
            include_metadata: Whether to include YAML frontmatter
            **kwargs: Service-specific export parameters

        Returns:
            Source payload including frontmatter and markdown content
        """
        # Get file metadata
        metadata = await self._parent.get_file_metadata(file_id)
        mime_type = metadata["mimeType"]

        # Download content
        content = await self._download_content(file_id, mime_type)

        _ = (include_metadata, kwargs)
        return self._build_with_frontmatter(metadata, content)

    @abstractmethod
    def _build_with_frontmatter(self, metadata: dict[str, Any], content: str) -> "Source":
        """Build Source content with YAML frontmatter.

        Args:
            metadata: File metadata from API
            content: File content

        Returns:
            Source payload including YAML frontmatter
        """


__all__ = ["GoogleAPIProtocol", "GoogleBaseAPI", "GoogleBaseExport", "GoogleBaseSearch"]
