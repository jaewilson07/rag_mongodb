"""Backward compatibility: redirect to mdrag.capabilities.ingestion."""

import sys

import mdrag.capabilities.ingestion as _ingestion
import mdrag.capabilities.ingestion.docling  # noqa: F401
import mdrag.capabilities.ingestion.jobs  # noqa: F401
import mdrag.capabilities.ingestion.sources  # noqa: F401

sys.modules["mdrag.ingestion"] = _ingestion
sys.modules["mdrag.ingestion.docling"] = _ingestion.docling
sys.modules["mdrag.ingestion.jobs"] = _ingestion.jobs
sys.modules["mdrag.ingestion.sources"] = _ingestion.sources
