#!/bin/bash
# Debug vLLM/LiteLLM requests - isolate where hangs occur.
#
# Usage:
#   ./scripts/debug_vllm_request.sh              # Tail both logs
#   ./scripts/debug_vllm_request.sh --verbose   # Restart LiteLLM with DEBUG, then tail
#   ./scripts/debug_vllm_request.sh direct     # Test vLLM directly (bypass LiteLLM)

set -e
cd "$(dirname "$0")/.."

VLLM_PORT="${VLLM_PORT:-11435}"

case "${1:-}" in
  direct)
    echo "=== Direct vLLM test (bypass LiteLLM) ==="
    echo "If this hangs, the problem is vLLM. If it returns quickly, the problem is LiteLLM."
    echo "Port: $VLLM_PORT"
    echo ""
    tmp=$(mktemp)
    trap "rm -f $tmp" EXIT
    code=$(curl -s -o "$tmp" -w "%{http_code}" -m 120 -X POST "http://localhost:${VLLM_PORT}/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -d '{"model":"glm-4.7","messages":[{"role":"user","content":"Hi"}],"max_tokens":32}' 2>/dev/null || echo "000")
    if [ "$code" = "000" ]; then
      echo "Connection failed (refused/timeout). Is vLLM up? docker ps"
    elif [ ! -s "$tmp" ]; then
      echo "Empty response (code $code)"
    else
      python3 -c "
import json,sys
p=sys.argv[1]
code=sys.argv[2]
try:
  d=json.load(open(p))
  if d.get('choices'):
    c=d['choices'][0].get('message',{}).get('content') or d['choices'][0].get('message',{}).get('reasoning_content') or '?'
    print('OK (code', code + '):', str(c)[:120])
  else:
    print('Error:', d.get('error',d))
except Exception as e: print('Parse error:', e, '- Raw:', open(p).read()[:200])
" "$tmp" "$code"
    fi
    ;;
  --verbose)
    echo "=== Restarting LiteLLM with DEBUG logging ==="
    LITELLM_LOG=DEBUG docker compose -f docker-compose.vllm.yml -f docker-compose.vllm.48gb.yml up -d litellm
    echo "LiteLLM restarted. Now tailing logs..."
    echo "Run Claude Code in another terminal; watch for request flow."
    echo ""
    docker compose -f docker-compose.vllm.yml -f docker-compose.vllm.48gb.yml logs -f vllm-glm litellm-proxy
    ;;
  *)
    echo "=== vLLM + LiteLLM log tail (Ctrl+C to stop) ==="
    echo "Run Claude Code in another terminal; watch for incoming requests."
    echo ""
    echo "Options:"
    echo "  direct   - Test vLLM directly (bypass LiteLLM) to isolate hang"
    echo "  --verbose - Restart LiteLLM with DEBUG, then tail logs"
    echo ""
    docker compose -f docker-compose.vllm.yml -f docker-compose.vllm.48gb.yml logs -f vllm-glm litellm-proxy
    ;;
esac
