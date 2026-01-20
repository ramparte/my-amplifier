---
bundle:
  name: my-amplifier
  version: 1.3.0
  description: Personal Amplifier with amplifier-dev + dev-memory + python-dev + lsp-python + deliberate-development + user habits enforcement

config:
  allowed_write_dirs:
    - ~/amplifier-dev-memory

includes:
  # Amplifier-dev - stay current with Amplifier developments automatically
  # Includes: standard tools, foundation agents, recipes, shadow environments
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/amplifier-dev.yaml
  
  # Dev-memory behavior - persistent local memory
  - bundle: git+https://github.com/ramparte/amplifier-collection-dev-memory@main#subdirectory=behaviors/dev-memory.yaml
  
  # Python development - code quality checks (ruff, pyright, stub detection)
  - bundle: git+https://github.com/microsoft/amplifier-bundle-python-dev@main
  
  # Python LSP - semantic code intelligence via Python language server
  - bundle: git+https://github.com/microsoft/amplifier-bundle-lsp-python@main
  
  # Deliberate development - decomposition-first workflow
  - bundle: git+https://github.com/ramparte/amplifier-toolkit@main#subdirectory=bundles/deliberate-development
---

# My Personal Amplifier

A thin bundle combining amplifier-dev with persistent dev-memory capabilities, deliberate development workflow, and user habits enforcement.

## What's Included

**From Amplifier-Dev:**
- All standard tools (filesystem, bash, web, search, task delegation)
- Session configuration and hooks
- Access to all foundation agents (zen-architect, modular-builder, explorer, etc.)
- Shadow environments for safe testing (already included)
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
- Catches issues before commit

**From LSP-Python:**
- Semantic code intelligence via Python language server
- Tools: `hover`, `goToDefinition`, `findReferences`, `incomingCalls`, `outgoingCalls`
- Better than grep for "what calls this?" questions
- Understands actual code structure, not just text

**From Deliberate Development (NEW in 1.3.0):**
- Decomposition-first planning (deliberate-planner agent)
- Specification-based implementation (deliberate-implementer agent)
- Recipes: deliberate-design, feature-development
- "4-5 planning turns, then one go-do-it turn" philosophy

**User Habits Enforcement:**
- Proactive prompting for exit criteria and reference materials
- Rejection of "blocked" as acceptable task closure
- Evidence requirements before accepting completion claims
- Dev-memory integration for tracking commitments
- Active pushback when setting up for failure

## Usage

```bash
# Add to your local bundle list
amplifier bundle add git+https://github.com/ramparte/my-amplifier@main

# Or run directly
amplifier run --bundle git+https://github.com/ramparte/my-amplifier@main

# Or set as default in ~/.amplifier/settings.yaml:
# bundle: git+https://github.com/ramparte/my-amplifier@main
```

---

@my-amplifier:context/user-habits.md

---

@foundation:context/shared/common-system-base.md
