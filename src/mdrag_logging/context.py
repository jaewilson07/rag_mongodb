"""Context helpers for correlation IDs."""

from __future__ import annotations

import contextvars


_correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


def set_correlation_id(value: str | None) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id_var.set(value)


def get_correlation_id() -> str | None:
    """Get the correlation ID for the current context."""
    return _correlation_id_var.get()


__all__ = ["get_correlation_id", "set_correlation_id"]
