---
bundle:
  name: my-amplifier
  version: 3.0.0
  description: Personal dev+writing bundle on the lean base. Composes BEHAVIORS (not root bundles) so added capabilities do NOT re-pull the full amplifier-foundation. See context/REDESIGN-NOTES.md for the full rationale, findings, and revert path.

config:
  allowed_write_dirs:
    - ~/amplifier-dev-memory      # dev-memory YAML store
    - ~/.amplifier/memory         # agent-memory Qdrant store

tools:
  - module: attention_firewall
    source: ./tools/attention-firewall
  # Skills: re-declare tool-skills at the ROOT (highest merge precedence) to (a) add
  # extra skill sources and (b) force visibility OFF. The composed skills/superpowers/
  # made-support behaviors set visibility:true and win over the lean base's false; this
  # root declaration is intended to win over them. Skill SOURCES accumulate across
  # declarations (verified: restless-old-brian/superpowers/etc. still appear), so
  # personas survive regardless. load_skill() still works on demand.
  # NOTE: a bundle-level `overrides:` key is NOT supported — overrides only work in
  # ~/.amplifier/settings.yaml. If this root re-declaration does not win, the fallback
  # is a settings.yaml override (see context/REDESIGN-NOTES.md).
  - module: tool-skills
    source: git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=modules/tool-skills
    config:
      skills:
        - "git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=skills"
        - "git+https://github.com/ramparte/cranky-old-sam@main#subdirectory=skills"
      visibility:
        enabled: false

includes:
  # ===== BASE: exp-lean-amplifier-dev (~18K tokens) =====
  # Core tools (fs, bash, web, search, todo, delegate, apply_patch), python-dev
  # (ruff, pyright, LSP), 7 dev agents (explorer, bug-hunter, git-ops,
  # zen-architect, modular-builder, file-ops, post-task-cleanup), UX hooks,
  # tool-skills (visibility off), compact system-base.md. NO full foundation.
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=experiments/exp-lean/exp-lean-amplifier-dev.md

  # ===== ADDITIONS — BEHAVIORS ONLY (critical: behaviors do NOT re-pull foundation) =====
  # The root superpowers/made-support bundles each `include: amplifier-foundation@main`,
  # which drags in design-intelligence, browser-tester, amplifier-tester, DTU, gitea,
  # llm-wiki, evaluation, routing-matrix + ~22K of heavy delegation context — negating
  # the lean base. Their *behavior* subdirectories provide the same capabilities WITHOUT
  # that pull-through. This is THE fix for the 200K+ sub-agent prompt bloat.

  # Superpowers methodology: brainstorm/write-plan/execute-plan/debug/verify/finish
  # modes + implementer/spec-reviewer/code-quality-reviewer/code-reviewer/
  # brainstormer/plan-writer agents. (Heavily used: ~2.3K delegations/14d.)
  - bundle: git+https://github.com/microsoft/amplifier-bundle-superpowers@main#subdirectory=behaviors/superpowers-methodology.yaml

  # MADE support behavior: support-ticket filing + amplifier-story submission +
  # team-knowledge + made team skills. This ALSO provides:
  #   - recipes  (via support-tickets + story-submissions sub-behaviors)
  #   - team-knowledge  (via team-knowledge-base sub-behavior)
  #   - stories (all 12 agents)  (via story-submissions -> stories behavior)
  # Per redesign decision, recipes + team-knowledge are provided here rather than
  # included directly (avoids the different-identity double-load). Stories agents
  # MUST be registered: story recipes reference them by BARE name, so they cannot
  # be delegate-only. amplifier-stories is the primary use case (52% of sessions).
  - bundle: git+https://github.com/microsoft-amplifier/amplifier-bundle-made-support@main#subdirectory=behaviors/made-support.yaml

  # Curated skills collection (REQUIRED for persona reviewer skills: cranky-old-sam,
  # crusty-old-engineer, personafy — the dominant load_skill usage on this machine).
  # These live in amplifier-bundle-skills and previously arrived via the full
  # foundation; now included explicitly. Visibility forced off by the root tool-skills declaration above.
  - bundle: git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=behaviors/skills.yaml

  # ===== MEMORY (both kept — mechanically distinct, both actively used) =====
  # dev-memory: offline YAML flat-file (~/amplifier-dev-memory), text scan, zero deps.
  - bundle: git+https://github.com/ramparte/amplifier-collection-dev-memory@main#subdirectory=behaviors/dev-memory.yaml
  # agent-memory: Qdrant vector store (~/.amplifier/memory), semantic search.
  - bundle: git+https://github.com/ramparte/amplifier-bundle-agent-memory@main

  # ===== DELEGATE-ONLY (NOT in root context; resolve from git source on demand) =====
  # dot-graph:*, browser-tester:*, design-intelligence:*, dev-machine:*,
  # foundation:session-analyst, digital-twin-universe:*, amplifier-tester:* all work
  # via delegate(agent="<ns>:<agent>", ...) without being registered here.
  # NOTE: dot-graph was also being force-injected into EVERY session via the global
  # `bundle.app` list in ~/.amplifier/settings.yaml. That entry has been removed so
  # dot-graph is genuinely delegate-only. (Kept under `bundle.added` so it resolves.)

agents:
  include:
    # Fast local inference agent (oMLX on Mac Studio)
    - my-amplifier:agents/fast-local
---

# My Personal Amplifier

Optimized personal bundle on the **lean base** (`exp-lean-amplifier-dev`, ~18K), composing
only the capabilities this machine actually uses — added as **behaviors, not root bundles**,
so they never re-pull the full `amplifier-foundation`.

> **Why this matters:** including the *root* superpowers/made-support bundles silently dragged
> in the entire foundation (design-intelligence, browser-tester, amplifier-tester, DTU, gitea,
> llm-wiki, evaluation, routing-matrix + ~22K of delegation context), which is what pushed
> spawned sub-agent prompts past 200K tokens. Composing their **behaviors** avoids this.
> Full analysis, evidence, and revert instructions: `context/REDESIGN-NOTES.md`.

## What's Included

**Base (exp-lean-amplifier-dev):**
- Core tools: filesystem, bash, web, search, todo, delegate, apply_patch
- Python dev: ruff + pyright quality checks, LSP via pyright
- Dev agents: explorer, bug-hunter, git-ops, zen-architect, modular-builder, file-ops, post-task-cleanup
- UX hooks: streaming UI, status context, redaction, logging, session naming, todo display
- Skills: tool present, **visibility off** (forced via override) — `load_skill()` on demand

**Additions (behaviors only — no foundation pull-through):**
- **Superpowers methodology**: brainstorm/debug/verify/etc. modes + implementer/plan-writer/reviewer agents
- **MADE Support**: support-ticket filing + amplifier-story submission — and it provides **recipes**, **team-knowledge**, and the **12 stories agents** transitively
- **Curated skills collection**: persona reviewers (cranky-old-sam, crusty-old-engineer, personafy) + the standard skill library
- **Dev-Memory**: offline YAML memory ("remember this:", "what do you remember about X?")
- **Agent-Memory**: semantic vector memory (Qdrant)
- **Attention Firewall**: query notification database
- **Fast-local agent**: oMLX inference on Mac Studio

## Available via Delegation (not in root context)

Work without being registered — resolve from their git source on demand:
- `delegate(agent="dot-graph:dot-author", ...)` -- DOT graph authoring
- `delegate(agent="browser-tester:browser-operator", ...)` -- browser automation
- `delegate(agent="design-intelligence:component-designer", ...)` -- design system
- `delegate(agent="dev-machine:admissions-advisor", ...)` -- dev machine builder
- `delegate(agent="foundation:session-analyst", ...)` -- session analysis/repair

## Rollback

If something breaks:
```bash
amplifier bundle use my-amplifier-safe   # full v1.14.0 bundle
```
Or revert to the previous v2.0.0 composition — see `context/REDESIGN-NOTES.md`.

## Usage

```bash
amplifier run --bundle git+https://github.com/ramparte/my-amplifier@main
```

---

@my-amplifier:context/user-habits.md

@my-amplifier:context/fleet-awareness.md

@my-amplifier:context/omlx-awareness.md
