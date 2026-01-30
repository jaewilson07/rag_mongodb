"""FastAPI entry point for ingestion APIs."""

from fastapi import FastAPI

from src.server.api.health.router import health_router
from src.server.api.ingest.router import ingest_router, jobs_router
from src.server.api.feedback.router import feedback_router
from src.server.api.query.router import query_router

app = FastAPI(title="MongoDB RAG Agent", version="0.1.0")

app.include_router(ingest_router)
app.include_router(jobs_router)
app.include_router(health_router)
app.include_router(query_router)
app.include_router(feedback_router)
