# my-amplifier Redesign Notes (v3.0.0 — 2026-06-11)

Rationale, evidence, and revert path for the v2.0.0 → v3.0.0 redesign. Read this first
if the bundle misbehaves or you need to roll back.

---

## TL;DR

The bundle uses the **lean base** (`exp-lean-amplifier-dev`, ~18K tokens) specifically to
avoid the full `amplifier-foundation`. But v2.0.0 then included the **root** `superpowers`
and `made-support` bundles — **each of which re-includes the full foundation** — silently
negating the savings and ballooning spawned sub-agent prompts past **213K tokens**.

v3.0.0 fixes this by composing **behaviors instead of root bundles**, plus removing a global
`bundle.app` entry that force-injected dot-graph into every session.

---

## The problem (observed)

- A spawned `git-ops` sub-agent showed a **constant 213,172-token** assembled prompt —
  identical with `context_depth="none"`, proving it was baseline composition, not conversation.
- `self`, `zen-architect`, and the expert agents did **not** tip over 200K because they declare
  narrow `tools:` sets and don't inherit the giant `delegate` roster + skills tool.
- The `delegate` roster had grown to ~70–80 agents (design-intelligence ×8, dot-graph ×13–16,
  stories ×12, browser-tester ×3, amplifier-tester ×2, DTU, gitea, llm-wiki, evaluation, …).

## Root cause (proven by tracing the cache)

1. **`amplifier-bundle-superpowers/bundle.md:8`** → `include: amplifier-foundation@main`
2. **`amplifier-bundle-made-support/bundle.md:8`** → `include: amplifier-foundation@main`

The full foundation (`amplifier-foundation/bundle.md:21-38`) pulls in design-intelligence,
amplifier-tester (→ DTU → gitea), browser-tester, llm-wiki, evaluation, routing-matrix, **plus**
the heavy delegation context (`delegation-instructions.md` ~15K + `multi-agent-patterns.md` ~7.5K).
The lean base was built to exclude exactly these. Including the *root* bundles re-pulled them.

3. **`~/.amplifier/settings.yaml` `bundle.app`** listed the dot-graph behavior, force-injecting
   ~13–16 dot-graph agents into **every** session and sub-agent (independent of the bundle).

4. **Skills visibility was ON** despite the lean base disabling it: multiple composed behaviors
   (`skills.yaml`, `superpowers-methodology`, `made-support-skills`) re-declare `tool-skills`
   with `visibility.enabled: true`, and the configs accumulate.

## Key fact that makes the fix safe

Both bundles expose **behaviors that do NOT re-include foundation**:
- `superpowers:behaviors/superpowers-methodology.yaml` → modes + 6 agents + tool-skills only.
- `made-support:behaviors/made-support.yaml` → fans into support-tickets, story-submissions,
  team-knowledge-base, made-support-skills. Provides **recipes**, **team-knowledge**, the
  **12 stories agents**, and the `trigger-rules.md` context — **with no foundation pull-through**.

---

## Findings on specific questions

- **Base bundle:** No graduated "thin"/"minimal" dev base exists. `foundation-minimal` is
  `loop-basic` + filesystem-only (not a dev bundle). `exp-lean-amplifier-dev` is still the
  canonical lean base and is actively maintained. **Stay on it.**

- **recipes / team-knowledge double-load:** v2.0.0 included both *directly* AND transitively via
  made-support, with **different bundle identities** (`recipes` vs `recipes-behavior`), so they
  did not dedupe at the bundle level (Python tool installs once; awareness context could inject
  twice). **Decision:** drop the direct includes; let `made-support` provide them.

- **Stories agents — must stay registered (NOT delegate-only):** the story recipes
  (`stories:recipes/session-to-case-study.yaml`, `blog-post-generator.yaml`) reference agents by
  **bare name** (`agent: "story-researcher"`, `"content-strategist"`, `"case-study-writer"`,
  `"marketing-writer"`, `"technical-writer"`). Bare names only resolve against the **registered
  roster**, so the 12 stories agents cannot be delegate-only without breaking the recipes.
  amplifier-stories is the #1 use case (52% of sessions), so this is acceptable cost.

- **Persona skills:** `cranky-old-sam`, `crusty-old-engineer`, `personafy` live in
  `amplifier-bundle-skills` (curated collection) and previously arrived via the full foundation.
  After cutting the foundation pull-through they **must** be included explicitly via
  `skills:behaviors/skills.yaml` — which is why v3.0.0 adds it (with visibility forced off).

- **dev-memory vs agent-memory — NOT redundant; keep both (user decision):**
  | | dev-memory | agent-memory |
  |---|---|---|
  | Store | YAML flat file (`~/amplifier-dev-memory/`) | Qdrant vector DB (`~/.amplifier/memory/`) |
  | Search | linear text scan | semantic similarity |
  | Deps | none, offline | Qdrant + OpenAI embeddings |
  Migration (dev-memory → agent-memory) is feasible (`content`→content, `category`→tag, IDs lost)
  but needs Qdrant + OpenAI live. Not done; both retained.

## 30-day usage signal (94 sessions, this machine)

- Sessions: amplifier-stories 52%, ansible 20%, flights 13%.
- Tools: `delegate` 48%, `team_knowledge` 44%, `load_skill` 7%, `mode` 4%.
- Skills loaded: all persona reviewers (cranky-old-sam, crusty-old-engineer, restless-old-brian, personafy).
- Feature refs: stories 42%, dev-memory 17%, team_knowledge 15%, made-support 11%, agent-memory 10%.
- Every capability kept in v3.0.0 maps to real usage; everything dropped showed no direct use.

---

## What changed in v3.0.0

**`bundle.md`:**
- superpowers: root bundle → `behaviors/superpowers-methodology.yaml`
- made-support: root bundle → `behaviors/made-support.yaml`
- **removed** direct `recipes` and `team-knowledge-base` includes (now via made-support)
- **added** `skills:behaviors/skills.yaml` (preserve persona skills after foundation cut)
- **added** a ROOT-level `tool-skills` re-declaration with `visibility.enabled: false`
  (force visibility off). NOTE: a bundle-level `overrides:` key is NOT supported — it is
  silently ignored (only `~/.amplifier/settings.yaml` honors `overrides:`). Re-declaring the
  module at the root is the portable mechanism; root config wins over included behaviors and
  skill SOURCES still accumulate (verified empirically). Saves ~3.9K tokens/turn.
- kept: dev-memory, agent-memory, attention_firewall tool, fast-local agent

**`~/.amplifier/settings.yaml`** (NOT in this repo — machine-local):
- removed dot-graph from `bundle.app` (set `app: []`). Kept under `bundle.added` as
  `dot-graph-behavior` so `delegate(agent="dot-graph:...")` still resolves.
- backup saved at `~/.amplifier/settings.yaml.bak-20260611`.

## Expected effect

Dropping the foundation pull-through removes from the roster/baseline: design-intelligence ×8,
browser-tester ×3, amplifier-tester ×2, DTU, gitea, llm-wiki, evaluation, routing-matrix hook,
dot-graph ×13–16 — plus ~22K of foundation delegation context — while keeping every actually-used
capability. All of these remain reachable via `delegate(agent="<ns>:<agent>", ...)`.

---

## Revert path

1. **Bundle:** `git revert` the v3.0.0 commit in this repo, or `git checkout <prev-sha> -- bundle.md`.
   The v2.0.0 composition is in git history.
2. **Settings:** `cp ~/.amplifier/settings.yaml.bak-20260611 ~/.amplifier/settings.yaml`
   (restores the dot-graph `bundle.app` entry).
3. **Full fallback:** `amplifier bundle use my-amplifier-safe` (full v1.14.0 bundle).

## Open / future

- If a clean token measure shows visibility still on, confirm the `overrides:` block is applied
  to the merged `tool-skills` config (the override should win last).
- Consider migrating dev-memory → agent-memory later to drop one always-on memory context (~500 tok/turn).
- Watch for new transitive foundation pulls if any added bundle switches from behavior → root include.
