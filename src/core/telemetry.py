"""Telemetry: tracing and PII redaction utilities."""

from __future__ import annotations

import re
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

try:
    from opentelemetry import trace
    from opentelemetry.trace import Span
except Exception:  # pragma: no cover - optional dependency
    trace = None
    Span = None  # type: ignore

# PII patterns
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"\b(\+?\d{1,2}[\s.-]?)?(\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}\b"
)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def new_trace_id() -> str:
    """Generate a new trace ID (UUID string)."""
    return str(uuid.uuid4())


@contextmanager
def start_span(
    name: str, attributes: Optional[Dict[str, Any]] = None
) -> Generator[Optional["Span"], None, None]:
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


def redact_text(text: str) -> str:
    """Redact basic PII patterns from text."""
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = SSN_RE.sub("[REDACTED_SSN]", text)
    return text


def redact_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redact PII from a payload dict."""
    redacted: Dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            redacted[key] = redact_text(value)
        elif isinstance(value, dict):
            redacted[key] = redact_payload(value)
        elif isinstance(value, list):
            redacted[key] = [
                redact_text(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            redacted[key] = value
    return redacted


__all__ = [
    "new_trace_id",
    "start_span",
    "redact_text",
    "redact_payload",
]
