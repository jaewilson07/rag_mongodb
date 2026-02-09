"""FastAPI entry point for ingestion APIs."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mdrag.dependencies import AgentDependencies
from mdrag.interfaces.api.api.feedback.router import feedback_router
from mdrag.interfaces.api.api.health.router import health_router
from mdrag.interfaces.api.api.ingest.router import ingest_router, jobs_router
from mdrag.interfaces.api.api.query.router import query_router
from mdrag.interfaces.api.api.readings.router import readings_router
from mdrag.interfaces.api.api.wiki.router import wiki_router
from mdrag.settings import load_settings
from mdrag.validation import ValidationError, validate_rq_workers, validate_vllm

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Fail fast if core services are unavailable."""
	deps = AgentDependencies()
	await deps.initialize()
	
	# Validate RQ workers for queue-based endpoints (ingestion, readings)
	settings = load_settings()
	redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
	validate_rq_workers(redis_url, queue_name="default")
	
	# Validate vLLM services if enabled
	if settings.vllm_enabled:
		try:
			validate_vllm(
				settings.vllm_reasoning_url,
				settings.vllm_embedding_url,
			)
			logger.info("✓ vLLM services validation passed")
		except ValidationError as e:
			logger.error(f"vLLM validation failed:\n{e}")
			# Fail fast - if vLLM is explicitly enabled but unavailable, don't start
			raise RuntimeError("vLLM services unavailable but vllm_enabled=True") from e
	
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
