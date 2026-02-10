# Multi-stage build for MongoDB RAG Agent
FROM python:3.11.7-slim AS builder

# Install UV package manager
COPY --from=ghcr.io/astral-sh/uv:0.5.24 /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files and source for install
COPY pyproject.toml ./
COPY src/ ./src/

# Create virtual environment and install dependencies
RUN uv venv /app/.venv
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    uv pip install --python /app/.venv/bin/python -e .

# Final stage
FROM python:3.11.7-slim

# Install runtime dependencies for document processing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Copy application code
COPY --chown=app:app src/ ./src/
COPY --chown=app:app server/ ./server/
COPY --chown=app:app data/ ./data/

# Set Python path to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Drop privileges
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import mdrag.cli"

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "mdrag.cli"]
