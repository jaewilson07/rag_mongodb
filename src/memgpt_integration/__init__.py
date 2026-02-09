"""Backward compatibility: redirect to mdrag.integrations.memgpt."""

import sys

from mdrag.integrations import memgpt as _memgpt

sys.modules["mdrag.memgpt_integration"] = _memgpt
