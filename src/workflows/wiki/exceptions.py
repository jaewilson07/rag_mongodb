"""Wiki workflow exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class WikiError(MDRAGException):
    """Raised when wiki structure, streaming, or page generation fails."""

    pass


__all__ = ["WikiError"]
