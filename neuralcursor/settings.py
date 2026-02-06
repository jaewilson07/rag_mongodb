"""
NeuralCursor settings with environment variable support.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NeuralCursorSettings(BaseSettings):
    """Application settings for NeuralCursor."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="NEURALCURSOR_",
    )

    # === Neo4j Configuration ===
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_username: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(..., description="Neo4j password")
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")

    # === MongoDB Configuration ===
    mongodb_uri: str = Field(..., description="MongoDB connection URI")
    mongodb_database: str = Field(default="neuralcursor", description="MongoDB database name")

    # === Local LLM Configuration ===
    reasoning_llm_host: str = Field(
        default="http://localhost:8000", description="Reasoning LLM host (e.g., vLLM server)"
    )
    reasoning_llm_model: str = Field(
        default="deepseek-coder-33b", description="Reasoning LLM model name"
    )
    embedding_llm_host: str = Field(
        default="http://localhost:8001", description="Embedding LLM host"
    )
    embedding_llm_model: str = Field(
        default="bge-m3", description="Embedding model name"
    )
    embedding_dimensions: int = Field(default=1024, description="Embedding vector dimensions")

    # === GPU Configuration ===
    gpu_reasoning_device: str = Field(default="cuda:0", description="GPU device for reasoning LLM")
    gpu_embedding_device: str = Field(default="cuda:1", description="GPU device for embeddings")
    vram_limit_reasoning_gb: int = Field(
        default=20, description="VRAM limit for reasoning LLM (GB)"
    )
    vram_limit_embedding_gb: int = Field(
        default=4, description="VRAM limit for embedding model (GB)"
    )

    # === MemGPT Configuration ===
    memgpt_enabled: bool = Field(default=True, description="Enable MemGPT working memory")
    memgpt_core_memory_size: int = Field(
        default=10000, description="Core memory size in tokens"
    )
    memgpt_archival_storage: str = Field(
        default="neo4j", description="Archival storage backend (neo4j, mongodb)"
    )

    # === MCP Server Configuration ===
    mcp_host: str = Field(default="localhost", description="MCP server host")
    mcp_port: int = Field(default=8765, description="MCP server port")
    mcp_enabled: bool = Field(default=True, description="Enable MCP server")

    # === File Watcher Configuration ===
    watcher_enabled: bool = Field(default=True, description="Enable file system watcher")
    watcher_debounce_seconds: int = Field(
        default=2, description="Debounce delay for file changes"
    )
    watcher_ignore_patterns: list[str] = Field(
        default_factory=lambda: [
            "**/__pycache__/**",
            "**/.git/**",
            "**/.venv/**",
            "**/node_modules/**",
            "**/*.pyc",
            "**/.DS_Store",
        ],
        description="File patterns to ignore",
    )

    # === Project Configuration ===
    project_root: str = Field(default=".", description="Project root directory")
    active_project: str | None = Field(None, description="Currently active project name")

    # === Monitoring Configuration ===
    monitoring_enabled: bool = Field(default=True, description="Enable VRAM/health monitoring")
    monitoring_interval_seconds: int = Field(
        default=10, description="Monitoring update interval"
    )


def get_settings() -> NeuralCursorSettings:
    """Get application settings singleton."""
    return NeuralCursorSettings()
