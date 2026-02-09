"""Backward compatibility: redirect to mdrag.capabilities.query."""

import sys

from mdrag.capabilities import query as _query

sys.modules["mdrag.query"] = _query
