---
bundle:
  name: my-amplifier
  version: 2.0.0
  description: Optimized personal Amplifier. Uses exp-lean base (~18K tokens) instead of full amplifier-dev (~55K). Adds back superpowers, recipes, MADE support, team-knowledge, dev-memory, attention-firewall. Rollback available via my-amplifier-safe.

config:
  allowed_write_dirs:
    - ~/amplifier-dev-memory
    - ~/.amplifier/memory

tools:
  - module: attention_firewall
    source: ./tools/attention-firewall

includes:
  # ===== BASE: exp-lean-amplifier-dev (~18K tokens) =====
  # Provides: core tools (fs, bash, web, search, todo, delegate, apply_patch),
  # python-dev (ruff, pyright, LSP), 7 dev agents (explorer, bug-hunter, git-ops,
  # zen-architect, modular-builder, file-ops, post-task-cleanup), UX hooks
  # (streaming, status, redaction, logging, session-naming, todo), skills (visibility off).
  # Compact system-base.md instead of 40K+ foundation context.
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=experiments/exp-lean/exp-lean-amplifier-dev.md

  # ===== ACTIVELY USED ADDITIONS =====

  # Superpowers - modes, skills, brainstormer/implementer/plan-writer agents
  # Usage: 2,353 delegations to superpowers agents in 14 days
  - bundle: git+https://github.com/microsoft/amplifier-bundle-superpowers@main

  # Recipes - multi-step workflow orchestration
  # Usage: 1,056 recipe invocations in 14 days
  - bundle: git+https://github.com/microsoft/amplifier-bundle-recipes@main

  # MADE support - file support requests + amplifier stories agents
  # Usage: regular use for support filing and story creation
  - bundle: git+https://github.com/microsoft-amplifier/amplifier-bundle-made-support@main

  # Team Knowledge - shared team knowledge base
  # Usage: 549 calls in 14 days
  - bundle: git+https://github.com/microsoft/amplifier-bundle-team-knowledge-base@main

  # Dev-memory - persistent local memory across sessions
  # Usage: 78 delegations to memory-retrieval in 14 days
  # NOTE: Context-heavy (~7K tokens) - future optimization target
  - bundle: git+https://github.com/ramparte/amplifier-collection-dev-memory@main#subdirectory=behaviors/dev-memory.yaml

  # Agent-memory - semantic memory with vector search
  - bundle: git+https://github.com/ramparte/amplifier-bundle-agent-memory@main

  # ===== DROPPED (available via delegation when needed) =====
  # Projector:           0 direct tool calls, hook injected every turn for nothing
  # Session-discovery:   0 direct delegations (naming handled by hooks in base)
  # Project-orchestrator: 0 usage
  # Daily-flow:          0 usage
  # Dev-machine:         delegate to dev-machine:* agents directly when needed
  # Dot-graph:           delegate to dot-graph:* agents directly when needed
  # Browser-tester:      delegate to browser-tester:* agents directly when needed
  # Design-intelligence: delegate to design-intelligence:* agents directly when needed
  # Shadow environments: not included in exp-lean base; delegate when needed
  #
  # These agents still work via delegate(agent="dev-machine:admissions-advisor", ...)
  # etc. -- they resolve from their git source without being in the root bundle.

agents:
  include:
    # Fast local inference agent (oMLX on Mac Studio)
    - my-amplifier:agents/fast-local
---

# My Personal Amplifier

Optimized personal bundle. Uses exp-lean base for a compact system prompt (~18K tokens), with selective additions for actively-used capabilities.

## What's Included

**Base (exp-lean-amplifier-dev):**
- Core tools: filesystem, bash, web, search, todo, delegate, apply_patch
- Python dev: ruff + pyright quality checks, LSP via pyright
- Dev agents: explorer, bug-hunter, git-ops, zen-architect, modular-builder, file-ops, post-task-cleanup
- UX hooks: streaming UI, status context, redaction, logging, session naming, todo display
- Skills: available on-demand (visibility disabled to save ~1.2K tokens/turn)

**Additions:**
- Superpowers: brainstorm/debug/verify modes, implementer/plan-writer agents
- Recipes: multi-step workflow orchestration
- MADE Support: file support requests, amplifier stories agents
- Team Knowledge: shared team knowledge base
- Dev-Memory: persistent local memory ("remember this:", "what do you remember about X?")
- Attention Firewall: query notification database ("check my WhatsApp groups")
- Fast-local agent: oMLX inference on Mac Studio

## Available via Delegation (not in root context)

These aren't loaded at startup but work when you ask for them:
- `delegate(agent="dev-machine:admissions-advisor", ...)` -- dev machine builder
- `delegate(agent="dot-graph:dot-author", ...)` -- DOT graph authoring
- `delegate(agent="browser-tester:browser-operator", ...)` -- browser automation
- `delegate(agent="design-intelligence:component-designer", ...)` -- design system
- `delegate(agent="foundation:session-analyst", ...)` -- session analysis/repair

## Rollback

If something breaks:
```bash
amplifier bundle use my-amplifier-safe   # full v1.14.0 bundle
```

## Usage

```bash
amplifier run --bundle git+https://github.com/ramparte/my-amplifier@main
```

---

@my-amplifier:context/user-habits.md

@my-amplifier:context/fleet-awareness.md

@my-amplifier:context/omlx-awareness.md
