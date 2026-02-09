"""Backward compatibility: redirect to mdrag.capabilities.retrieval."""

import sys

from mdrag.capabilities import retrieval as _retrieval

sys.modules["mdrag.retrieval"] = _retrieval
