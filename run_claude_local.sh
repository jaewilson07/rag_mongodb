#!/bin/bash

# Configuration for running Claude Code with local vLLM
# See: https://docs.vllm.ai/en/latest/serving/integrations/claude_code/

# Option A: LiteLLM proxy (recommended for 48GB) - caps max_tokens server-side
# Option B: Direct vLLM - set USE_LITELLM=false to bypass proxy
export USE_LITELLM=${USE_LITELLM:-true}
VLLM_PORT="${VLLM_PORT:-11435}"
if [ "$USE_LITELLM" = "true" ]; then
  export ANTHROPIC_BASE_URL=http://localhost:4000
else
  export ANTHROPIC_BASE_URL=http://localhost:${VLLM_PORT}
fi

export ANTHROPIC_API_KEY=dummy

# Dummy token required by Claude CLI
export ANTHROPIC_AUTH_TOKEN=dummy

# Cap output tokens so 20k input + output fits in 32k context (2x 3090 headroom)
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=12000

# Map all Claude tiers to our local model
# Ensure this matches the --served-model-name in docker-compose.vllm.yml
export ANTHROPIC_DEFAULT_OPUS_MODEL=glm-4.7
export ANTHROPIC_DEFAULT_SONNET_MODEL=glm-4.7
export ANTHROPIC_DEFAULT_HAIKU_MODEL=glm-4.7

echo "Starting Claude Code with local vLLM (GLM-4.7-Flash)..."
echo "Model: $ANTHROPIC_DEFAULT_SONNET_MODEL"
echo "URL: $ANTHROPIC_BASE_URL (LiteLLM: $USE_LITELLM)"

# Run claude, passing all arguments
claude "$@"
