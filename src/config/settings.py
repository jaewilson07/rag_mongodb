"""Settings configuration for MongoDB RAG Agent."""

from typing import Optional

from dotenv import load_dotenv
from pydantic import ConfigDict, Field, computed_field
from pydantic_settings import BaseSettings

from mdrag.config.exceptions import ConfigError

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # MongoDB Configuration
    mongodb_uri: Optional[str] = Field(
        default=None,
        description="MongoDB connection string (if provided, overrides composed URI)",
    )

    mongodb_host: str = Field(
        default="localhost", description="MongoDB host (use 'atlas-local' for Docker)"
    )

    mongodb_port: int = Field(default=27017, description="MongoDB port")

    mongodb_username: str = Field(default="admin", description="MongoDB username")

    mongodb_password: str = Field(default="admin123", description="MongoDB password")

    mongodb_docker_port: int = Field(
        default=7017,
        description="Host port for this project's Docker MongoDB (atlas-local). Used by sample pre-flight for auto-start.",
    )

    mongodb_database: str = Field(default="rag_db", description="MongoDB database name")

    mongodb_collection_documents: str = Field(
        default="documents", description="Collection for source documents"
    )

    mongodb_collection_chunks: str = Field(
        default="chunks", description="Collection for document chunks with embeddings"
    )

    mongodb_collection_traces: str = Field(
        default="traces", description="Collection for query traces"
    )

    mongodb_collection_feedback: str = Field(
        default="feedback", description="Collection for user feedback"
    )

    mongodb_vector_index: str = Field(
        default="vector_index",
        description="Vector search index name (must be created in Atlas UI)",
    )

    mongodb_text_index: str = Field(
        default="text_index",
        description="Full-text search index name (must be created in Atlas UI)",
    )

    @computed_field
    @property
    def mongodb_connection_string(self) -> str:
        """Compose MongoDB URI from components or return provided URI."""
        if self.mongodb_uri and self.mongodb_uri.strip():
            return self.mongodb_uri

        # Construct URI from components
        return (
            f"mongodb://{self.mongodb_username}:{self.mongodb_password}"
            f"@{self.mongodb_host}:{self.mongodb_port}"
            f"/{self.mongodb_database}?authSource=admin"
        )

    # LLM Configuration (OpenAI-compatible)
    llm_provider: str = Field(
        default="openrouter",
        description="LLM provider (openai, anthropic, gemini, ollama, etc.)",
    )

    llm_api_key: str = Field(..., description="API key for the LLM provider")

    llm_model: str = Field(
        default="anthropic/claude-haiku-4.5",
        description="Model to use for search and summarization",
    )

    llm_base_url: Optional[str] = Field(
        default="https://openrouter.ai/api/v1",
        description="Base URL for the LLM API (for OpenAI-compatible providers)",
    )

    llm_temperature: Optional[float] = Field(
        default=None,
        description="LLM sampling temperature. When None, omit from API (models that reject it: OpenRouter, some vLLM). When set (e.g. 0.3), pass to API (Ollama supports it).",
    )

    # Embedding Configuration
    embedding_provider: str = Field(default="openai", description="Embedding provider")

    embedding_api_key: str = Field(..., description="API key for embedding provider")

    embedding_model: str = Field(
        default="text-embedding-3-small", description="Embedding model to use"
    )

    embedding_base_url: Optional[str] = Field(
        default="https://api.openai.com/v1", description="Base URL for embedding API"
    )

    embedding_dimension: int = Field(
        default=1536,
        description="Embedding vector dimension (1536 for text-embedding-3-small)",
    )

    # Search Configuration
    default_match_count: int = Field(
        default=10, description="Default number of search results to return"
    )

    max_match_count: int = Field(
        default=50, description="Maximum number of search results allowed"
    )

    default_text_weight: float = Field(
        default=0.3, description="Default text weight for hybrid search (0-1)"
    )

    # Self-Corrective RAG Configuration
    rag_max_iterations: int = Field(
        default=2,
        description="Maximum query rewrite iterations for self-corrective RAG",
    )

    rag_max_generation_attempts: int = Field(
        default=2,
        description="Maximum generation attempts for citation verification",
    )

    rag_web_result_count: int = Field(
        default=5,
        description="Number of SearXNG results to include per query",
    )

    rag_citation_soft_fail_banner: str = Field(
        default="Warning: Some statements may be insufficiently sourced.",
        description="Banner shown when citations fail verification",
    )

    # SearXNG Configuration
    searxng_url: str = Field(
        default="http://localhost:7080", description="SearXNG base URL"
    )

    # Crawl4AI Configuration
    crawl4ai_word_count_threshold: int = Field(
        default=10, description="Minimum word count for Crawl4AI blocks"
    )
    crawl4ai_remove_overlay_elements: bool = Field(
        default=True, description="Remove overlay elements during Crawl4AI"
    )
    crawl4ai_remove_base64_images: bool = Field(
        default=True, description="Remove base64 images during Crawl4AI"
    )
    crawl4ai_cache_mode: str = Field(
        default="BYPASS", description="Crawl4AI cache mode"
    )
    crawl4ai_browser_type: str = Field(
        default="chromium", description="Crawl4AI browser type"
    )
    crawl4ai_timeout: int = Field(
        default=30, description="Crawl4AI request timeout in seconds"
    )
    crawl4ai_max_depth: int = Field(
        default=2, description="Crawl4AI deep crawl max depth"
    )
    crawl4ai_max_concurrent: int = Field(
        default=10, description="Crawl4AI deep crawl max concurrency"
    )
    crawl4ai_user_agent: Optional[str] = Field(
        default=None, description="Custom user agent for Crawl4AI"
    )
    crawl4ai_cookies: Optional[str] = Field(
        default=None, description="Cookies for Crawl4AI (string format)"
    )

    # Google Drive / Docs Configuration
    google_service_account_file: Optional[str] = Field(
        default=None, description="Path to Google service account JSON"
    )
    google_impersonate_subject: Optional[str] = Field(
        default=None, description="Optional user to impersonate"
    )
    google_drive_folder_ids: Optional[str] = Field(
        default=None, description="Comma-separated Google Drive folder IDs"
    )
    google_drive_file_ids: Optional[str] = Field(
        default=None, description="Comma-separated Google Drive file IDs"
    )
    google_docs_ids: Optional[str] = Field(
        default=None, description="Comma-separated Google Docs IDs"
    )

    # Ingestion Job Queue
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for ingestion job queue and status tracking",
    )

    # Neo4j Configuration (NeuralCursor Second Brain)
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI for knowledge graph",
    )
    neo4j_username: str = Field(
        default="neo4j",
        description="Neo4j database username",
    )
    neo4j_password: str = Field(
        default="password",
        description="Neo4j database password",
    )
    neo4j_database: str = Field(
        default="neuralcursor",
        description="Neo4j database name for Second Brain",
    )

    # Local LLM Configuration (vLLM)
    vllm_enabled: bool = Field(
        default=False,
        description="Enable local vLLM serving on dual GPUs",
    )
    vllm_reasoning_url: str = Field(
        default="http://localhost:8000",
        description="vLLM reasoning LLM endpoint (GPU 0)",
    )
    vllm_embedding_url: str = Field(
        default="http://localhost:8001",
        description="vLLM embedding/RAG endpoint (GPU 1)",
    )
    vllm_reasoning_model: str = Field(
        default="deepseek-ai/deepseek-coder-33b-instruct",
        description="Reasoning model for graph extraction",
    )
    vllm_embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="Embedding model for local RAG",
    )


def load_settings() -> Settings:
    """Load settings with proper error handling."""
    try:
        return Settings()
    except Exception as e:
        error_msg = f"Failed to load settings: {e}"
        if "mongodb_uri" in str(e).lower():
            error_msg += "\nMake sure to set MONGODB_URI in your .env file"
        if "llm_api_key" in str(e).lower():
            error_msg += "\nMake sure to set LLM_API_KEY in your .env file"
        if "embedding_api_key" in str(e).lower():
            error_msg += "\nMake sure to set EMBEDDING_API_KEY in your .env file"
        raise ConfigError(error_msg, original_error=e) from e
