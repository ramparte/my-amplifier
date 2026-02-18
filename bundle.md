---
bundle:
  name: my-amplifier
  version: 1.12.0
  description: Personal Amplifier with amplifier-dev + dev-memory + agent-memory + deliberate-development + made-support + user habits + amplifier-stories + attention-firewall + session-discovery + project-orchestration

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
  
  # NOTE: python-dev and lsp-python removed - already included via amplifier-dev → foundation
  
  # Deliberate development - decomposition-first workflow
  # NOTE: This bundle needs its foundation include removed (thin bundle pattern for composition)
  - bundle: git+https://github.com/ramparte/amplifier-bundle-deliberate-development@main
  
  # MADE support - file support requests from sessions
  # NOTE: This bundle needs its foundation include removed (thin bundle pattern for composition)
  - bundle: git+https://github.com/microsoft-amplifier/amplifier-bundle-made-support@main
  
  # Amplifier Stories - autonomous storytelling engine
  - bundle: git+https://github.com/ramparte/amplifier-stories@master
  
  # Projector - cross-session project management, strategy enforcement, coordination
  - bundle: git+https://github.com/ramparte/amplifier-bundle-projector@main

  # Session Discovery - index and search past sessions (distro tier 2 feature)
  - bundle: git+https://github.com/ramparte/amplifier-toolkit@main#subdirectory=bundles/session-discovery

  # Project Orchestration - natural language project management (NEW in v1.11.0)
  - behavior: git+https://github.com/ramparte/amplifier-bundle-project-orchestrator@main#subdirectory=behaviors/project-orchestration.yaml

  # Daily Flow - personal daily workflow (/brief, /dispatch, /eod)
  - bundle: file:///home/samschillace/dev/ANext/amplifier-bundle-daily-flow
---

# My Personal Amplifier

A thin bundle combining amplifier-dev with persistent dev-memory capabilities, deliberate development workflow, MADE support, user habits enforcement, M365 agent collaboration, and natural language project orchestration.

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

**Project Orchestration (NEW in v1.11.0):**
- Natural language project management: "where are we?", "do phase X", "continue"
- Fresh isolated sessions per task (automatic context isolation)
- Persistent state across sessions (.project/state.json or .longbuilder/state/project_state.json)
- Approval gates at strategic checkpoints
- Automated test verification after each task
- Phase-based execution with progress tracking

## Usage

```bash
# Run directly
amplifier run --bundle git+https://github.com/ramparte/my-amplifier@main

# Or set as default in ~/.amplifier/settings.yaml:
# bundle: git+https://github.com/ramparte/my-amplifier@main
```

## Project Orchestration Commands (NEW)

When working in a project directory with `.project/state.json` or `.longbuilder/state/project_state.json`:

```
> where are we?
[Shows current phase, progress, next tasks]

> do phase 1
[Executes all pending tasks in Phase 1 with approval gates]

> continue
[Resumes from current state]
```

Each task runs in a fresh isolated session automatically - no manual setup needed!

---

@my-amplifier:context/user-habits.md

@my-amplifier:context/attention-firewall.md

---

@foundation:context/shared/common-system-base.md
