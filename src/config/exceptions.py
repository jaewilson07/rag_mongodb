"""Config-specific exceptions."""

from __future__ import annotations

from mdrag.core.exceptions import MDRAGException


class ConfigError(MDRAGException):
    """Raised when configuration load, parsing, or validation fails."""

    pass


__all__ = ["ConfigError"]
