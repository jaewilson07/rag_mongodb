"""Tracing helpers with OpenTelemetry fallback."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

try:
    from opentelemetry import trace
    from opentelemetry.trace import Span
except Exception:  # pragma: no cover - optional dependency
    trace = None
    Span = None  # type: ignore


def new_trace_id() -> str:
    return str(uuid.uuid4())


@contextmanager
def start_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> Generator[Optional[Span], None, None]:
    """Start an OTEL span when available; otherwise no-op."""
    if trace is None:
        yield None
        return

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span
