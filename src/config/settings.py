"""Application settings with environment variable support."""

from __future__ import annotations

import functools
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # MongoDB - Individual components for composition
    mongodb_host: Optional[str] = Field(
        default=None, description="MongoDB host (when composing URI from components)"
    )
    mongodb_port: Optional[int] = Field(
        default=27017, description="MongoDB port (when composing URI from components)"
    )
    mongodb_username: Optional[str] = Field(
        default=None, description="MongoDB username (when composing URI from components)"
    )
    mongodb_password: Optional[str] = Field(
        default=None, description="MongoDB password (when composing URI from components)"
    )
    mongodb_connection_string: str = Field(
        default="", description="MongoDB connection string", validation_alias="MONGODB_URI"
    )

    @field_validator("mongodb_connection_string", mode="before")
    @classmethod
    def compose_mongodb_uri(cls, v: str, info) -> str:
        """Compose MongoDB URI from components if not provided directly."""
        if v:  # If MONGODB_URI is explicitly provided, use it
            return v

        # Try to compose from components
        data = info.data
        host = data.get("mongodb_host")

        if host:
            # Build URI from components
            port = data.get("mongodb_port", 27017)
            username = data.get("mongodb_username")
            password = data.get("mongodb_password")

            if username and password:
                return f"mongodb://{username}:{password}@{host}:{port}/?directConnection=true&authSource=admin"
            else:
                return f"mongodb://{host}:{port}/"

        raise ValueError("Either MONGODB_URI or MONGODB_HOST must be provided")
    mongodb_database: str = Field(default="rag_db", description="MongoDB database name")
    mongodb_collection_documents: str = Field(
        default="documents", description="MongoDB collection for documents"
    )
    mongodb_collection_chunks: str = Field(
        default="chunks", description="MongoDB collection for chunks"
    )
    mongodb_vector_index: str = Field(
        default="vector_index", description="MongoDB vector search index name"
    )
    mongodb_text_index: str = Field(
        default="text_index", description="MongoDB text search index name"
    )
    mongodb_collection_traces: str = Field(
        default="traces", description="MongoDB collection for query traces"
    )
    mongodb_collection_feedback: str = Field(
        default="feedback", description="MongoDB collection for feedback"
    )
    mongodb_docker_port: int = Field(
        default=7017, description="MongoDB Docker port for local development"
    )

    # LLM Provider
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_api_key: str = Field(default="", description="LLM API key")
    llm_model: str = Field(default="gpt-4o-mini", description="LLM model name")
    llm_base_url: Optional[str] = Field(
        default=None, description="LLM base URL (optional)"
    )
    llm_temperature: float = Field(
        default=0.0, description="LLM temperature for sampling"
    )

    # Embedding Provider
    embedding_provider: str = Field(default="openai", description="Embedding provider")
    embedding_api_key: str = Field(default="", description="Embedding API key")
    embedding_model: str = Field(
        default="text-embedding-3-small", description="Embedding model name"
    )
    embedding_base_url: Optional[str] = Field(
        default=None, description="Embedding base URL (optional)"
    )
    embedding_dimension: int = Field(default=1536, description="Embedding dimension")

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379", description="Redis connection URL"
    )

    # vLLM (optional)
    vllm_enabled: bool = Field(default=False, description="Enable vLLM")
    vllm_reasoning_url: Optional[str] = Field(
        default=None, description="vLLM reasoning URL"
    )
    vllm_embedding_url: Optional[str] = Field(
        default=None, description="vLLM embedding URL"
    )
    vllm_reasoning_model: Optional[str] = Field(
        default=None, description="vLLM reasoning model"
    )
    vllm_embedding_model: Optional[str] = Field(
        default=None, description="vLLM embedding model"
    )

    # Crawl4AI
    crawl4ai_max_depth: int = Field(
        default=3, description="Crawl4AI maximum crawl depth"
    )
    crawl4ai_word_count_threshold: int = Field(
        default=100, description="Crawl4AI word count threshold"
    )
    crawl4ai_remove_overlay_elements: bool = Field(
        default=True, description="Crawl4AI remove overlay elements"
    )
    crawl4ai_remove_base64_images: bool = Field(
        default=True, description="Crawl4AI remove base64 images"
    )


@functools.lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Load settings from environment. Cached for performance."""
    return Settings()
