---
bundle:
  name: my-amplifier-lean
  version: 3.0.0-lean
  description: >
    LEAN variant of my-amplifier. Identical capabilities to my-amplifier EXCEPT
    the per-turn team-knowledge KB dump is disabled. It keeps the team_knowledge
    TOOL (on-demand search/list/lookup/publish) but turns OFF the
    hooks-team-knowledge-context session-start context injection that was dumping
    the full ~2249-capability summary into EVERY turn (the source of 350K-token
    laptop sessions). See context/REDESIGN-NOTES.md for the parent rationale.

config:
  allowed_write_dirs:
    - ~/amplifier-dev-memory      # dev-memory YAML store
    - ~/.amplifier/memory         # agent-memory Qdrant store

tools:
  # Skills: re-declare tool-skills at the ROOT (highest merge precedence) to (a) add
  # extra skill sources and (b) force visibility OFF. (Identical to my-amplifier.)
  - module: tool-skills
    source: git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=modules/tool-skills
    config:
      skills:
        - "git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=skills"
        - "git+https://github.com/ramparte/cranky-old-sam@main#subdirectory=skills"
      visibility:
        enabled: false

# ===== THE LEAN FIX: kill the per-turn KB dump, keep the tool =====
# made-support -> team-knowledge-base -> upstream team-knowledge.yaml declares the
# `hooks-team-knowledge-context` hook, which on session:start injects a team summary
# + per-repo capability nudges (the ~2249-capability dump) into EVERY turn.
#
# The injection is gated by BOTH `enabled` AND `context_injection` (see the hook's
# __init__.py guards: `if not enabled: return` / `if not context_injection: return`).
# Sam's ~/.amplifier/settings.yaml has a GLOBAL override forcing `enabled: true`,
# but that override does NOT touch `context_injection`. So re-declaring the hook here
# with `context_injection: false` (+ `auto_generate: false`) deep-merges and wins,
# disabling the dump WITHOUT modifying settings.yaml or the active bundle.
#
# IMPORTANT: this only kills the *injection hook*. The `team_knowledge` TOOL
# (tool-team-knowledge: search/list/lookup/publish) stays fully available on demand.
hooks:
  - module: hooks-team-knowledge-context
    config:
      context_injection: false   # <-- kills the per-turn ~2249-cap summary dump
      auto_generate: false       # <-- no background capability fast-gen scans
      enabled: false             # belt-and-suspenders (settings.yaml override may flip
                                 # this back to true; context_injection:false still gates
                                 # the dump off regardless)

  # ===== INBOX-DRAIN: out-of-band notes into a running CLI session =====
  # Companion sender `amplifier-note <tmux-window> <text>` appends notes to
  # ~/.amplifier/inbox/<window>.jsonl. This hook drains THIS session's inbox
  # (keyed by its own tmux window name) at provider:request -- the same safe
  # checkpoint a soft Ctrl-C honors -- and injects them mid-task. Lets you nudge
  # a busy pane without interrupting it or typing into it.
  - module: hooks-inbox-drain
    source: ../modules/hooks-inbox-drain
    config:
      inbox_dir: ~/.amplifier/inbox
      priority: 5

  # ===== TOKEN-WARNING: early warning when context bloats =====
  # Registers on llm:response and reads the normalized per-turn usage dict. When a
  # turn's effective input crosses the budget it emits a CLI-visible warning (via
  # HookResult.user_message -- UI only, does NOT touch the agent's context) and
  # re-warns once per additional `step` of growth (no per-turn spam). This is the
  # runtime safety net against the 200K-600K bloat regression: it fires regardless
  # of WHAT caused the bloat. `effective = input_tokens + cache_write_tokens`
  # (cache_read is already folded into input_tokens by the Anthropic provider).
  - module: hooks-token-warning
    source: ../modules/hooks-token-warning
    config:
      threshold: 75000          # budget in tokens
      # step defaults to threshold -> re-warn at 75K, 150K, 225K, ...
      user_message_level: warning
      priority: 50

includes:
  # ===== BASE: exp-lean-amplifier-dev (~18K tokens) =====
  # Core tools (fs, bash, web, search, todo, delegate, apply_patch), python-dev
  # (ruff, pyright, LSP), 7 dev agents (explorer, bug-hunter, git-ops,
  # zen-architect, modular-builder, file-ops, post-task-cleanup), UX hooks,
  # tool-skills (visibility off), compact system-base.md. NO full foundation.
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=experiments/exp-lean/exp-lean-amplifier-dev.md

  # ===== ADDITIONS - BEHAVIORS ONLY (behaviors do NOT re-pull foundation) =====
  # Superpowers methodology: brainstorm/write-plan/execute-plan/debug/verify/finish
  # modes + implementer/spec-reviewer/code-quality-reviewer/code-reviewer/
  # brainstormer/plan-writer agents.
  - bundle: git+https://github.com/microsoft/amplifier-bundle-superpowers@main#subdirectory=behaviors/superpowers-methodology.yaml

  # MADE support behavior: support-ticket filing + amplifier-story submission +
  # team-knowledge (TOOL kept; dump disabled via the hooks block above) + made team
  # skills. Also provides recipes + the 12 stories agents transitively.
  - bundle: git+https://github.com/microsoft-amplifier/amplifier-bundle-made-support@main#subdirectory=behaviors/made-support.yaml

  # Curated skills collection (persona reviewers: cranky-old-sam, crusty-old-engineer,
  # personafy + the standard skill library). Visibility forced off by root tool-skills.
  - bundle: git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=behaviors/skills.yaml

  # ===== MEMORY (both kept - mechanically distinct, both actively used) =====
  # dev-memory: offline YAML flat-file (~/amplifier-dev-memory), text scan, zero deps.
  - bundle: git+https://github.com/ramparte/amplifier-collection-dev-memory@main#subdirectory=behaviors/dev-memory.yaml
  # agent-memory: Qdrant vector store (~/.amplifier/memory), semantic search.
  - bundle: git+https://github.com/ramparte/amplifier-bundle-agent-memory@main

agents:
  include:
    # Fast local inference agent (oMLX on Mac Studio)
    - my-amplifier:agents/fast-local
---

# My Personal Amplifier - LEAN

Identical to **my-amplifier** in every capability, with ONE difference: the
per-turn **team-knowledge KB dump is disabled**. The `team_knowledge` tool is
still here for on-demand search/list/lookup/publish - only the session-start
context injection (which was dumping the full ~2249-capability summary into
**every turn**, bloating laptop sessions toward 350K tokens) is turned off.

> **The injector:** `made-support -> team-knowledge-base -> team-knowledge.yaml`
> declares the `hooks-team-knowledge-context` hook. Its `session:start` handler
> injects the team summary + capability nudges every turn. The guard is
> `enabled AND context_injection`. Sam's `~/.amplifier/settings.yaml` globally
> forces `enabled: true`, but never sets `context_injection`, so this bundle's
> `context_injection: false` wins and kills the dump - non-destructively.

## What's KEPT (same as my-amplifier)
- Base **exp-lean-amplifier-dev**: core tools, **python-dev** (ruff/pyright) + **LSP**,
  7 dev agents (explorer, bug-hunter, git-ops, **zen-architect**, modular-builder, file-ops,
  post-task-cleanup), UX hooks, compact common-system-base
- **Superpowers methodology** (modes + reviewer/plan-writer/implementer agents)
- **MADE Support** + recipes + 12 stories agents + the **team_knowledge TOOL**
- Curated **skills** (cranky-old-sam, crusty-old-engineer, personafy)
- **Dev-Memory** (YAML) + **Agent-Memory** (Qdrant)
- **Attention Firewall**, **fast-local** (oMLX) agent
- `@my-amplifier:context/*` - user-habits, fleet-awareness, omlx-awareness

## What's DROPPED
- **ONLY** the per-turn `hooks-team-knowledge-context` injection (the ~2249-cap dump)
  and its background `auto_generate` capability scans. Nothing else.

## Switch / Revert
```bash
amplifier bundle use my-amplifier-lean   # switch to lean (no per-turn KB dump)
amplifier bundle use my-amplifier        # revert to the original
```

---

@my-amplifier:context/user-habits.md

@my-amplifier:context/fleet-awareness.md

@my-amplifier:context/omlx-awareness.md
