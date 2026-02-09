"""Backward compatibility: re-export from mdrag.core.telemetry."""

from mdrag.core.telemetry import new_trace_id, start_span

__all__ = ["new_trace_id", "start_span"]
