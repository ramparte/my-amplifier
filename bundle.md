---
bundle:
  name: my-amplifier
  version: 1.8.0
  description: Personal Amplifier with amplifier-dev + dev-memory + python-dev + lsp-python + deliberate-development + made-support + user habits + M365 collaboration

config:
  allowed_write_dirs:
    - ~/amplifier-dev-memory

includes:
  # Amplifier-dev - stay current with Amplifier developments automatically
  # Includes: foundation → python-dev → lsp-python, shadow, recipes, all standard tools
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/amplifier-dev.yaml
  
  # Dev-memory behavior - persistent local memory (thin, no foundation)
  - bundle: git+https://github.com/ramparte/amplifier-collection-dev-memory@main#subdirectory=behaviors/dev-memory.yaml
  
  # NOTE: python-dev and lsp-python removed - already included via amplifier-dev → foundation
  
  # Deliberate development - decomposition-first workflow
  # NOTE: This bundle needs its foundation include removed (thin bundle pattern for composition)
  - bundle: git+https://github.com/ramparte/amplifier-bundle-deliberate-development@main
  
  # M365 Collaboration - agent-to-agent communication via SharePoint
  # NOTE: Using bundle.yaml which has proper tool module config (bundle.md has string instead of dict)
  - bundle: git+https://github.com/ramparte/amplifier-bundle-m365-collab@main#bundle.yaml
  
  # MADE support - file support requests from sessions
  # NOTE: This bundle needs its foundation include removed (thin bundle pattern for composition)
  - bundle: git+https://github.com/microsoft-amplifier/amplifier-bundle-made-support@main
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

**From M365 Collaboration:**
- `m365_collab` tool for agent-to-agent communication
- Post tasks, status updates, and work handoffs
- Pick up tasks from other agent instances
- Persistent message board via SharePoint

## M365 Collaboration Setup

Set these environment variables before starting Amplifier:

```bash
export M365_TENANT_ID="your-tenant-id"
export M365_CLIENT_ID="your-client-id"
export M365_CLIENT_SECRET="your-client-secret"
```

Then use the `m365_collab` tool directly:

```
m365_collab(operation="get_pending_tasks")
m365_collab(operation="post_task", title="Review code", description="Check auth module")
```

## Usage

```bash
# Run directly
amplifier run --bundle git+https://github.com/ramparte/my-amplifier@main

# Or set as default in ~/.amplifier/settings.yaml:
# bundle: git+https://github.com/ramparte/my-amplifier@main
```

---

@my-amplifier:context/user-habits.md

---

@foundation:context/shared/common-system-base.md
