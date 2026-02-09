#!/bin/bash

# Configuration for running Claude Code with local vLLM
# See: https://docs.vllm.ai/en/latest/serving/integrations/claude_code/

# Point to local vLLM server
export ANTHROPIC_BASE_URL=http://localhost:8000/v1

# Use the API key configured in vLLM (default: secret-token)
export ANTHROPIC_API_KEY=${VLLM_API_KEY:-secret-token}

# Dummy token required by Claude CLI
export ANTHROPIC_AUTH_TOKEN=dummy

# Map all Claude tiers to our local model
# Ensure this matches the --served-model-name in docker-compose.vllm.yml
export ANTHROPIC_DEFAULT_OPUS_MODEL=glm-4.7
export ANTHROPIC_DEFAULT_SONNET_MODEL=glm-4.7
export ANTHROPIC_DEFAULT_HAIKU_MODEL=glm-4.7

echo "Starting Claude Code with local vLLM (GLM-4.7-Flash)..."
echo "Model: $ANTHROPIC_DEFAULT_SONNET_MODEL"
echo "URL: $ANTHROPIC_BASE_URL"

# Run claude, passing all arguments
claude "$@"
