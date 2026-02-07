"""API prefix configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class APIConfig:
    """Central API prefix constants."""

    V1_PREFIX: str = "/api/v1"
    INGEST_PREFIX: str = "/api/v1/ingest"
    JOBS_PREFIX: str = "/api/v1/jobs"
    HEALTH_PREFIX: str = "/api/v1/health"
    QUERY_PREFIX: str = "/api/v1/query"
    FEEDBACK_PREFIX: str = "/api/v1/feedback"
    WIKI_PREFIX: str = "/api/v1/wiki"


api_config = APIConfig()
