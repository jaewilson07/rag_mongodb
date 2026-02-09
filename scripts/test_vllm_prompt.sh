#!/bin/bash
# Test vLLM with a simple prompt via OpenAI-compatible API.
# Run after: docker compose -f docker-compose.vllm.yml up -d
# Wait for model to load (~2-5 min), then: ./scripts/test_vllm_prompt.sh

set -e
VLLM_PORT="${VLLM_PORT:-11435}"
VLLM_URL="${VLLM_URL:-http://localhost:${VLLM_PORT}}"
API_KEY="${VLLM_API_KEY:-secret-token}"
PROMPT="${1:-What is 2 + 2? Reply in one sentence.}"

echo "Testing vLLM at $VLLM_URL"
echo "Prompt: $PROMPT"
echo "---"

# Escape prompt for JSON
PROMPT_ESC=$(printf '%s' "$PROMPT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')
curl -s -X POST "$VLLM_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{\"model\": \"glm-4.7\", \"messages\": [{\"role\": \"user\", \"content\": $PROMPT_ESC}], \"max_tokens\": 256}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'choices' in d and d['choices']:
    print('Response:', d['choices'][0]['message']['content'])
else:
    print('Error:', json.dumps(d, indent=2))
"
