# Local oMLX Fast Inference

When running on the Mac Studio (macstudio via Tailscale), a secondary LLM provider
is available via oMLX on port 8000. This provides ~30% faster inference than Ollama
and SSD-backed KV caching for long-context agent sessions.

## When to Use

Delegate to `fast-local` agent when the user says:
- "Use the fast local model for this"
- "Run this through oMLX"
- "Use the fast agent"
- Any task where long-context KV caching would help (sustained multi-turn analysis)

## How It Works

oMLX runs alongside Ollama on the same machine:
- **Ollama** (port 11434): Multi-model routing matrix, warm model groups
- **oMLX** (port 8000): Single fast model (gemma4-27b), SSD KV cache

The `fast-local` agent has `provider_preferences` wired to `provider-openai`
pointed at the oMLX endpoint. No manual configuration needed at invocation time.
