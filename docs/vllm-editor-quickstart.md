# vLLM Editor Integration - Quick Reference

## 🎯 What's Configured

Your local vLLM instance (Qwen2.5-Coder-14B) is now integrated with:
- ✅ **VS Code** via Continue extension
- ✅ **Cursor** editor
- ✅ **Tab autocomplete** for both editors

## 📍 Configuration Files

| File | Purpose | Status |
|------|---------|--------|
| `.vscode/settings.json` | Workspace settings | ✅ Updated |
| `~/.continue/config.json` | Continue global config | ✅ Created |
| `~/.cursor/models.json` | Cursor model config | ✅ Created |

## 🚀 Usage

### Continue Extension (VS Code/Cursor)
```
Ctrl+L (Cmd+L Mac)  - Open chat panel
/edit               - Edit selected code
/comment            - Add documentation  
/test               - Generate pytest tests
/cmd                - Generate shell commands
```

### Tab Autocomplete
Just start typing! Suggestions appear inline. Press `Tab` to accept.

### Model Selection
In Continue panel:
1. Click model dropdown at top
2. Select "Qwen2.5 Coder 14B (vLLM - Local)"

## 🔧 Configuration Details

```json
{
  "endpoint": "http://localhost:11435/v1",
  "model": "qwen-coder",
  "apiKey": "secret-token",
  "contextLength": 32768,
  "temperature": 0.2
}
```

## 🧪 Test Commands

**Test vLLM is responding:**
```bash
curl http://localhost:11435/health
```

**Test chat completion:**
```bash
curl http://localhost:11435/v1/chat/completions \
  -H "Authorization: Bearer secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-coder",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

**Check GPU usage:**
```bash
nvidia-smi
# Should show both GPUs at ~23GB usage
```

## 📊 Performance Expectations

| Metric | Value |
|--------|-------|
| First token latency | 2-3 seconds |
| Tokens/second | 30-40 |
| Context window | 32,768 tokens |
| GPU 0 memory | ~23.9 GB |
| GPU 1 memory | ~23.2 GB |

## 🐛 Troubleshooting

### Issue: Extension can't connect
```bash
# Check vLLM is running
docker ps | grep vllm-qwen-coder

# Check logs
docker logs vllm-qwen-coder --tail 50

# Restart if needed
docker compose -f docker-compose.vllm.yml restart
```

### Issue: Slow responses
- First request is always slower (cold start)
- Check GPU usage: `nvidia-smi`
- Both GPUs should be 50-80% utilized

### Issue: "Unauthorized" error
- Verify `apiKey` is `secret-token` in config
- Check `.env` has `VLLM_API_KEY=secret-token`

### Issue: Model not in dropdown
1. Restart VS Code / Cursor
2. Check `~/.continue/config.json` exists
3. Verify JSON syntax is valid: `jq . ~/.continue/config.json`

## 📚 Related Documentation

- [vLLM Setup Guide](./vllm-setup.md)
- [Editor Configuration Details](./vllm-editor-config.md)
- [Continue Extension Docs](https://continue.dev/docs)

## 🔄 Switching Back to Remote APIs

To switch back to OpenAI/OpenRouter:

**In `.vscode/settings.json`:**
```json
{
  "continue.models": [
    {
      "title": "GPT-4",
      "provider": "openai",
      "model": "gpt-4",
      "apiKey": "your-openai-key"
    }
  ]
}
```

**Or keep both:**
```json
{
  "continue.models": [
    {
      "title": "Qwen2.5 Coder (Local vLLM)",
      "provider": "openai",
      "model": "qwen-coder",
      "apiKey": "secret-token",
      "apiBase": "http://localhost:11435/v1"
    },
    {
      "title": "GPT-4 (Fallback)",
      "provider": "openai",
      "model": "gpt-4",
      "apiKey": "your-openai-key"
    }
  ]
}
```

Then select from dropdown in Continue panel!

## ⚡ Pro Tips

1. **Use lower temperature (0.1-0.2) for autocomplete** - More predictable code
2. **Use higher temperature (0.3-0.5) for chat** - More creative solutions
3. **Enable context providers** - Code, docs, diff, terminal
4. **Create custom commands** - Add project-specific prompts
5. **Use `/cmd` for shell commands** - Faster than typing

## 🎉 You're All Set!

Your editors are now using local Qwen2.5-Coder-14B via vLLM with tensor parallelism across both RTX 3090s!

Press `Ctrl+L` in VS Code or `Ctrl+K` in Cursor to start coding with AI assistance. 🚀
