---
bundle:
  name: my-amplifier-local
  version: 1.1.0
  description: Lightweight bundle for local models. Declares modules directly to avoid context accumulation from foundation behaviors.

session:
  raw: true
  orchestrator:
    module: loop-streaming
    source: git+https://github.com/microsoft/amplifier-module-loop-streaming@main
    config:
      extended_thinking: false
  context:
    module: context-simple
    source: git+https://github.com/microsoft/amplifier-module-context-simple@main
    config:
      max_tokens: 28000
      compact_threshold: 0.65
      auto_compact: true

tools:
  - module: tool-filesystem
    source: git+https://github.com/microsoft/amplifier-module-tool-filesystem@main
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@main
  - module: tool-web
    source: git+https://github.com/microsoft/amplifier-module-tool-web@main
  - module: tool-search
    source: git+https://github.com/microsoft/amplifier-module-tool-search@main
  - module: tool-delegate
    source: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=modules/tool-delegate
    config:
      features:
        self_delegation:
          enabled: true
        session_resume:
          enabled: true
        context_inheritance:
          enabled: true
          max_turns: 5
        provider_selection:
          enabled: false
      settings:
        exclude_tools: [tool-delegate]
        exclude_hooks: []

# NO includes -- every module declared directly to avoid context accumulation
---

# Local Amplifier

You are Amplifier, an AI assistant running on a local model. Be direct and helpful.

**Tools:**
- `read_file`, `write_file`, `edit_file`, `glob` -- filesystem operations
- `bash` -- shell commands (git, make, npm, pip, etc.)
- `web_search`, `web_fetch` -- web search and URL fetching
- `grep` -- fast code search with regex
- `delegate` -- spawn a sub-agent for token-heavy work

**Rules:**
- Execute tasks directly. Don't ask clarifying questions unless truly ambiguous.
- Use tools to accomplish what the user asks.
- Keep responses concise.
- The user's GitHub username is **ramparte**.
- When committing, include the Amplifier co-author trailer.
