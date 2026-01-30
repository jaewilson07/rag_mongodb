"""PII redaction utilities for logs and traces."""

from __future__ import annotations

import re
from typing import Any, Dict

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b(\+?\d{1,2}[\s.-]?)?(\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


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
