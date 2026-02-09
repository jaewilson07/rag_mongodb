# vLLM + Claude CLI Setup (GLM-4.7 on 2x RTX 3090)

## Overview

This guide covers running Claude Code with a local vLLM backend (GLM-4.7-Flash) on 2x RTX 3090 GPUs, and delegating tasks from Cursor to Claude CLI. Uses vLLM nightly + transformers from git for GLM-4.7 support ([HF](https://huggingface.co/zai-org/GLM-4.7-Flash), [Medium guide](https://medium.com/@zh.milo/glm-4-7-flash-the-ultimate-2026-guide-to-local-ai-coding-assistant-93a43c3f8db3)).

## 1. vLLM Docker Configuration

### Package versions (Dockerfile.vllm)

- **vLLM**: Nightly build (`pip install -U vllm --pre --index-url ... --extra-index-url https://wheels.vllm.ai/nightly`)
- **Transformers**: Latest from git (`pip install git+https://github.com/huggingface/transformers.git`)

### Model choice

| VRAM | Model | Override |
|------|-------|----------|
| 80GB+ or 4 GPUs | `zai-org/GLM-4.7-Flash` (base, ~60GB) | default |
| **48GB (2x 3090)** | `cyankiwi/GLM-4.7-Flash-AWQ-4bit` | use `-f docker-compose.vllm.48gb.yml` |

### Settings for 2x 3090 GPUs

| Setting | Value | Rationale |
|---------|-------|------------|
| `--tensor-parallel-size` | 2 | Matches GPU count |
| `--gpu-memory-utilization` | 0.90 | Safe for quantized model; KV cache headroom |
| `--max-model-len` | 32768 | Balance context vs memory |
| `--tool-call-parser` | glm47 | GLM-4.7 tool calling format |
| `--reasoning-parser` | glm45 | Claude Code reasoning compatibility |
| `ipc: host` | (docker-compose) | **Required** for tensor parallel (PyTorch shared memory) |

### Start vLLM

**48GB (2x 3090) – quantized model (recommended):**

```bash
docker compose -f docker-compose.vllm.yml -f docker-compose.vllm.48gb.yml up -d --build
```

**80GB+ or 4 GPUs – base model:**

```bash
docker compose -f docker-compose.vllm.yml up -d --build
```

Model load takes ~2–5 minutes. Verify:

```bash
curl -s http://localhost:11435/health
# Expect: {"status":"ok"} or similar
```

### Test with a Prompt

```bash
./scripts/test_vllm_prompt.sh "What is 2 + 2?"
```

## 2. Claude Code CLI

### Prerequisites

- [Claude Code](https://code.claude.com) installed (`claude` in PATH)

### Run Claude Code with vLLM

```bash
./run_claude_local.sh
```

This sets `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, and model names so Claude Code uses your local vLLM instead of Anthropic's API.

### Send a Prompt

Once Claude Code starts, type your prompt in the interactive session. For non-interactive use, check `claude --help` for available flags.

## 3. Cursor Agent Delegation

The project includes a Cursor rule (`.cursor/rules/claude-cli-delegate.mdc`) that instructs the agent to:

- Suggest delegating multi-file refactors, exploratory coding, or tool-calling tasks to Claude Code
- Provide the correct commands: `./run_claude_local.sh` and task description

**When to delegate:** Multi-step coding tasks, shell-heavy workflows, or when the user explicitly asks for Claude CLI.

## 48GB VRAM (2x 3090) Token Limit

Claude Code sends ~20k tokens of system prompt + tools before your message. It also requests up to 32k output tokens. With vLLM at 32k max context, that overflows.

**Solution: LiteLLM proxy** (default). Routes Claude Code → LiteLLM (4000) → vLLM (internal 8000). LiteLLM caps `max_tokens: 12000` before forwarding, so 20k input + 12k output fits in 32k. vLLM is exposed on host port 11435 (Ollama 11434 + 1).

```bash
# Default: use LiteLLM (port 4000)
./run_claude_local.sh --dangerously-skip-permissions -p "Say hello"

# Bypass LiteLLM, talk to vLLM directly on port 11435 (needs CLAUDE_CODE_MAX_OUTPUT_TOKENS=12000)
USE_LITELLM=false ./run_claude_local.sh -p "Say hello"
```

## Troubleshooting

### vLLM won't start

- **OOM / CUDA out of memory (48GB)**: Use the 48GB override: `docker compose -f docker-compose.vllm.yml -f docker-compose.vllm.48gb.yml up -d`. Or reduce `--gpu-memory-utilization` to 0.80 or `--max-model-len` to 16384.
- **Quantization error** (cyankiwi model): Ensure `--quantization compressed-tensors` in the 48GB override
- **Tool call errors**: Use `--tool-call-parser glm47` (not `openai`)

### Claude Code can't connect

- Verify vLLM is healthy: `curl http://localhost:11435/health`
- Check `ANTHROPIC_BASE_URL=http://localhost:11435` when using direct vLLM (no LiteLLM; no `/v1`)
- Ensure `ANTHROPIC_API_KEY` matches `VLLM_API_KEY` in `.env`

### Logs & debugging hangs

**Tail both vLLM and LiteLLM:**
```bash
./scripts/debug_vllm_request.sh
```

**Isolate where it hangs:** If Claude Code hangs, run in another terminal:
```bash
./scripts/debug_vllm_request.sh direct
```
- If `direct` hangs → problem is vLLM (inference slow or stuck)
- If `direct` returns quickly → problem is LiteLLM or Claude Code ↔ LiteLLM

**Verbose LiteLLM logs:**
```bash
LITELLM_LOG=DEBUG docker compose -f docker-compose.vllm.yml -f docker-compose.vllm.48gb.yml up -d litellm
docker logs litellm-proxy -f
```

**Individual logs:**
```bash
docker logs vllm-glm -f
docker logs litellm-proxy -f
```
