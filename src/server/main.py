"""FastAPI entry point for ingestion APIs."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from mdrag.dependencies import AgentDependencies
from mdrag.server.api.health.router import health_router
from mdrag.server.api.ingest.router import ingest_router, jobs_router
from mdrag.server.api.feedback.router import feedback_router
from mdrag.server.api.query.router import query_router


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Fail fast if core services are unavailable."""
	deps = AgentDependencies()
	await deps.initialize()
	await deps.cleanup()
	yield


app = FastAPI(title="MongoDB RAG Agent", version="0.1.0", lifespan=lifespan)

app.include_router(ingest_router)
app.include_router(jobs_router)
app.include_router(health_router)
app.include_router(query_router)
app.include_router(feedback_router)
