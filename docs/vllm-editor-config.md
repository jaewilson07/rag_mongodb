# vLLM Configuration for VS Code Extensions

## Overview

This configuration enables VS Code and Cursor to use your local vLLM instance (Qwen2.5-Coder-14B) running on `localhost:8000`.

## Files Updated

### 1. `.vscode/settings.json` (Workspace Settings)
```json
{
  "continue.models": [
    {
      "title": "Qwen2.5 Coder 14B (vLLM - Local)",
      "provider": "openai",
      "model": "qwen-coder",
      "apiKey": "secret-token",
      "apiBase": "http://localhost:8000/v1"
    }
  ],
  "continue.tabAutocompleteModel": {
    "title": "Qwen2.5 Coder 14B",
    "provider": "openai",
    "model": "qwen-coder",
    "apiKey": "secret-token",
    "apiBase": "http://localhost:8000/v1"
  }
}
```

### 2. `~/.continue/config.json` (Continue Extension Global Config)
Full configuration with:
- **Chat model**: Qwen2.5-Coder-14B via vLLM
- **Tab autocomplete**: Same model (optimized for speed)
- **Context length**: 32,768 tokens
- **Temperature**: 0.2 for chat, 0.1 for autocomplete

### 3. `~/.cursor/models.json` (Cursor Editor Config)
Cursor-specific model configuration pointing to vLLM.

## Usage

### Continue Extension (VS Code / Cursor)

1. **Open Continue Panel**: 
   - Press `Cmd+L` (Mac) or `Ctrl+L` (Linux/Windows)
   - Or click the Continue icon in the sidebar

2. **Select Model**:
   - Click the model dropdown
   - Choose "Qwen2.5 Coder 14B (vLLM)"

3. **Chat Commands**:
   ```
   /edit - Modify selected code
   /comment - Add comments
   /test - Generate pytest tests
   /cmd - Generate shell commands
   ```

4. **Tab Autocomplete**:
   - Start typing code
   - Autocomplete suggestions will appear inline
   - Press `Tab` to accept

### Cursor Editor

1. **Open Cursor Chat**:
   - Press `Cmd+K` (Mac) or `Ctrl+K` (Linux/Windows)

2. **Model Selection**:
   - Should automatically use vLLM endpoint
   - Check status bar for active model

## Testing the Configuration

### Test Continue Extension
```bash
# Open VS Code
code .

# In Continue panel, ask:
"Write a Python function to validate email addresses using regex"
```

### Test vLLM Endpoint Directly
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-coder",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

## Performance Tips

### For Faster Autocomplete
- Reduce `maxTokens` to 128-256
- Use lower temperature (0.05-0.1)
- Enable caching in vLLM (prefix caching is already enabled)

### For Better Chat Responses
- Increase temperature to 0.3-0.5 for creative tasks
- Use full 32K context for large codebases
- Enable context providers (code, docs, diff, terminal)

## Troubleshooting

### Issue: Extension can't connect to vLLM
```bash
# Check vLLM is running
curl http://localhost:8000/health

# Check vLLM logs
docker logs vllm-qwen-coder --tail 50

# Restart vLLM if needed
docker compose -f docker-compose.vllm.yml restart
```

### Issue: Slow responses
- **Check GPU usage**: `nvidia-smi`
- **Expected**: Both GPUs at ~50-80% utilization
- **If idle**: Model may be warming up (first request is slower)

### Issue: Out of memory errors
```bash
# Reduce context window in docker-compose.vllm.yml
# Change: --max-model-len 32768
# To:     --max-model-len 16384

docker compose -f docker-compose.vllm.yml restart
```

### Issue: Wrong model responses
- Verify `apiBase` ends with `/v1`
- Check `apiKey` matches `VLLM_API_KEY` in .env
- Confirm model name is exactly `qwen-coder`

## Switching Models

### Use Ollama Instead
```json
{
  "continue.models": [
    {
      "title": "Qwen3 Coder (Ollama)",
      "provider": "ollama",
      "model": "qwen3-coder:32k",
      "apiBase": "http://localhost:11434"
    }
  ]
}
```

### Use OpenAI/OpenRouter as Fallback
```json
{
  "continue.models": [
    {
      "title": "GPT-4o (Fallback)",
      "provider": "openai",
      "model": "gpt-4o",
      "apiKey": "your-openai-key"
    }
  ]
}
```

## Configuration Reference

### Available Context Providers
- **code**: Currently open files
- **docs**: Project documentation
- **diff**: Git changes
- **terminal**: Terminal output
- **problems**: Linter/compiler errors
- **folder**: File tree
- **codebase**: Full codebase search

### Completion Options
```json
{
  "temperature": 0.2,        // Randomness (0.0-1.0)
  "topP": 0.95,              // Nucleus sampling
  "presencePenalty": 0.0,    // Avoid repetition
  "frequencyPenalty": 0.0,   // Avoid common phrases
  "maxTokens": 4096          // Max response length
}
```

## See Also

- [Continue Documentation](https://continue.dev/docs)
- [vLLM Setup Guide](./vllm-setup.md)
- [Cursor Documentation](https://cursor.sh/docs)
