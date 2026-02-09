"""Backward compatibility: redirect to mdrag.capabilities.memory."""

import sys

from mdrag.capabilities import memory as _memory

sys.modules["mdrag.memory_gateway"] = _memory
