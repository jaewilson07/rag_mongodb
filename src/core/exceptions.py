"""Project-wide base exception hierarchy."""

from __future__ import annotations


class MDRAGException(Exception):
    """Base exception for all MDRAG errors.

    All project-specific exceptions should inherit from this class
    to enable consistent error handling patterns.
    """

    def __init__(self, message: str, original_error: Exception | None = None):
        """Initialize with message and optional original error.

        Args:
            message: Human-readable error description
            original_error: Optional original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error


__all__ = ["MDRAGException"]
