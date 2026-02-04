---
bundle:
  name: my-amplifier
  version: 1.10.0
  description: Personal Amplifier with amplifier-dev + dev-memory + agent-memory + session-discovery + deliberate-development + made-support + user habits + amplifier-stories + attention-firewall

config:
  allowed_write_dirs:
    - ~/amplifier-dev-memory
    - ~/.amplifier/memory

tools:
  - module: attention_firewall
    source: ./tools/attention-firewall

includes:
  # Amplifier-dev - stay current with Amplifier developments automatically
  # Includes: foundation → python-dev → lsp-python, shadow, recipes, all standard tools
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/amplifier-dev.yaml
  
  # Dev-memory behavior - persistent local memory (thin, no foundation)
  - bundle: git+https://github.com/ramparte/amplifier-collection-dev-memory@main#subdirectory=behaviors/dev-memory.yaml
  
  # Agent-memory - semantic memory with vector search
  - bundle: git+https://github.com/ramparte/amplifier-bundle-agent-memory@main
  
  # Session discovery - automatic session indexing and search
  - bundle: git+https://github.com/ramparte/amplifier-toolkit@main#subdirectory=bundles/session-discovery
  
  # NOTE: python-dev and lsp-python removed - already included via amplifier-dev → foundation
  
  # Deliberate development - decomposition-first workflow
  # NOTE: This bundle needs its foundation include removed (thin bundle pattern for composition)
  - bundle: git+https://github.com/ramparte/amplifier-bundle-deliberate-development@main
  
  # MADE support - file support requests from sessions
  # NOTE: This bundle needs its foundation include removed (thin bundle pattern for composition)
  - bundle: git+https://github.com/microsoft-amplifier/amplifier-bundle-made-support@main
  
  # Amplifier Stories - autonomous storytelling engine
  - bundle: git+https://github.com/ramparte/amplifier-stories@master
---

# My Personal Amplifier

A thin bundle combining amplifier-dev with persistent dev-memory capabilities, deliberate development workflow, MADE support, user habits enforcement, and M365 agent collaboration.

## What's Included

**From Amplifier-Dev:**
- All standard tools (filesystem, bash, web, search, task delegation)
- Session configuration and hooks
- Access to all foundation agents (zen-architect, modular-builder, explorer, etc.)
- Shadow environments for safe testing
- Automatic updates when foundation evolves

**From Dev-Memory:**
- Persistent memory at `~/amplifier-dev-memory/`
- Natural language: "remember this:", "what do you remember about X?"
- Work tracking: "what was I working on?"
- Token-efficient architecture (reads delegated to sub-agent)

**From Session Discovery:**
- Automatic session indexing when sessions complete
- Natural queries: "What was I working on last week?", "What are my current projects?"
- Session index at `~/.amplifier/session-index.json`
- Session-namer agent for generating descriptive session names
- Fast metadata filtering before deep session-analyst searches

**From Python-Dev:**
- Automated code quality checks (ruff format + lint, pyright types, stub detection)
- Automatic hook runs after Python file writes
- Manual invocation: `python_check(paths=["src/"])`

**From LSP-Python:**
- Semantic code intelligence via Python language server
- Tools: `hover`, `goToDefinition`, `findReferences`, `incomingCalls`, `outgoingCalls`

**From Deliberate Development:**
- Decomposition-first planning (deliberate-planner agent)
- Specification-based implementation (deliberate-implementer agent)

**From MADE Support:**
- File support requests directly from sessions
- Just say "I need help with..." or "submit a support request"

**From Amplifier Stories:**
- Autonomous storytelling engine for Amplifier ecosystem
- 10 specialist agents (story-researcher, content-strategist, technical-writer, etc.)
- 5 content formats: HTML presentations, PowerPoint, Excel, Word, PDF
- 4 automated workflows (session→case study, git tag→changelog, weekly digest, blog posts)
- Create content manually or via automated recipes

**Attention Firewall:**
- Query your notification firewall database conversationally
- Check what notifications arrived and how they were filtered
- Audit suppression rules to ensure correct filtering
- Access dashboard location and recent notification history

## Usage

```bash
# Run directly
amplifier run --bundle git+https://github.com/ramparte/my-amplifier@main

# Or set as default in ~/.amplifier/settings.yaml:
# bundle: git+https://github.com/ramparte/my-amplifier@main
```

---

@my-amplifier:context/user-habits.md

@my-amplifier:context/attention-firewall.md

---

@foundation:context/shared/common-system-base.md
