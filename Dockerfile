# Multi-stage build for MongoDB RAG Agent
FROM python:3.11.7-slim AS builder

# Install UV package manager
COPY --from=ghcr.io/astral-sh/uv:0.5.24 /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    uv pip compile pyproject.toml -o /tmp/requirements.txt && \
    uv pip install --python /app/.venv/bin/python -r /tmp/requirements.txt

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
COPY --chown=app:app examples/ ./examples/
COPY --chown=app:app documents/ ./documents/

# Set Python path to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

# Drop privileges
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import src.cli"

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "src.cli"]
