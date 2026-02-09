"""Integration-level exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class IntegrationError(MDRAGException):
    """Raised when an integration (MongoDB, Neo4j, Crawl4AI, etc.) fails."""

    pass


__all__ = ["IntegrationError"]
