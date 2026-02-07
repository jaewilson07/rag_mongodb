"""FastAPI entry point for ingestion APIs."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mdrag.dependencies import AgentDependencies
from mdrag.server.api.health.router import health_router
from mdrag.server.api.ingest.router import ingest_router, jobs_router
from mdrag.server.api.feedback.router import feedback_router
from mdrag.server.api.query.router import query_router
from mdrag.server.api.wiki.router import wiki_router
from mdrag.server.api.readings.router import readings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Fail fast if core services are unavailable."""
	deps = AgentDependencies()
	await deps.initialize()
	await deps.cleanup()
	yield


app = FastAPI(title="MongoDB RAG Agent", version="0.1.0", lifespan=lifespan)

# CORS middleware for frontend
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(jobs_router)
app.include_router(health_router)
app.include_router(query_router)
app.include_router(feedback_router)
app.include_router(wiki_router)
app.include_router(readings_router)
