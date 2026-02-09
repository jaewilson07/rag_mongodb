"""Wiki workflow exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class WikiError(MDRAGException):
    """Raised when wiki workflow fails (structure, streaming, page generation)."""

    pass


__all__ = ["WikiError"]
