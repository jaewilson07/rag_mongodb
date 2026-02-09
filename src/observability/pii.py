"""Backward compatibility: re-export from mdrag.core.telemetry."""

from mdrag.core.telemetry import redact_payload, redact_text

__all__ = ["redact_text", "redact_payload"]
