"""Server-level dependency helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mdrag.dependencies import AgentDependencies


class ManagedDependencies:
    """Async context manager for AgentDependencies lifecycle."""

    def __init__(self, deps: AgentDependencies | None = None) -> None:
        self.deps = deps or AgentDependencies()

    async def __aenter__(self) -> AgentDependencies:
        await self.deps.initialize()
        return self.deps

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.deps.cleanup()


@asynccontextmanager
async def get_agent_dependencies() -> AsyncIterator[AgentDependencies]:
    """Yield initialized AgentDependencies for FastAPI dependencies."""
    deps = AgentDependencies()
    await deps.initialize()
    try:
        yield deps
    finally:
        await deps.cleanup()
