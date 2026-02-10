"""NeuralCursor workflow exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class NeuralCursorError(MDRAGException):
    """Raised when MCP server, file watcher, librarian, or maintenance fails."""

    pass


__all__ = ["NeuralCursorError"]
