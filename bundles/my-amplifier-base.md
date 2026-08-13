---
bundle:
  name: my-amplifier-base
  version: 0.1.0
  description: >
    Shared base for the provider-specific personal bundles. Everything that is
    NOT provider-specific lives here: the Anchors foundation, python tooling,
    local hooks, the fast-local agent, and one declarative preferences file.
    Not meant to be activated directly -- use my-amplifier-oai or
    my-amplifier-anthropic, which include this and add only their provider block.

# =====================================================================
# THE RULE THAT KEEPS THIS FROM ROTTING
# ---------------------------------------------------------------------
# Fork on MECHANICAL KNOBS, never on guidance.
#
# Everything a model reads -- context files, agent definitions, tool rosters,
# preferences -- is provider-neutral and lives HERE. Anchors' low instruction
# density is better for Claude too; there is no reason to maintain two copies of
# prose that would immediately drift.
#
# The overlays contain ONLY what genuinely differs at the wire level: the
# `providers:` block and the `routing:` matrix. If an overlay ever grows past
# ~30 lines, something has leaked out of this file and should be pushed back in.
#
# Composition mechanics that make this work (amplifier_foundation Bundle.compose):
#   - `session` / `spawn` are dicts -> deep_merge, LATER (overlay) wins per key
#   - `providers` / `tools` / `hooks` are lists -> merged by module id
#   - `agents` -> dict update, later wins by key
#   - `instruction` -> later fully replaces
# CAVEAT: list fields concatenate-and-dedupe. A child bundle can ADD to a list
# but CANNOT remove a parent's entry. Design this base as the intersection of
# what both overlays want, never the union.
# =====================================================================

includes:
  # ===== FOUNDATION: Anchors (~1.9 KB static context, 6 thin agents) =====
  # Four behavioral principles + a standard tool roster, versus ~68 KB for the
  # older exp-lean base and ~107 KB for full Foundation. Provides: filesystem,
  # bash, web, search, todo, apply-patch, delegate, skills (visibility off),
  # mode, recipes; explorer/architect/builder/debugger/git-ops/researcher agents.
  #
  # Anchors registers hooks-mode with `search_paths: []`, so no external mode
  # files load. That incidentally removes the superpowers `debug` mode, which
  # ships `allow_clear: false` and can refuse a user's `mode off`.
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/anchors/bundle.md

  # ===== Python tooling: python_check (ruff/pyright) + LSP (pyright) =====
  # Its context docs load into the code-intel agent's own context, not the
  # parent's, so this costs ~0 static tokens in the main system prompt.
  - bundle: git+https://github.com/microsoft/amplifier-bundle-python-dev@main

session:
  context:
    config:
      # NOTE: `max_tokens` is deliberately NOT set here. loop-streaming always
      # calls context.get_messages_for_request(provider=provider), and
      # context-simple._calculate_budget() derives
      #   context_window - (max_output x reserve) - safety_margin
      # from the provider's own capability table. Hand-setting max_tokens per
      # bundle duplicates knowledge the provider already has and goes stale the
      # moment a model's window changes. `compact_threshold` is a FRACTION of
      # that derived budget and has no automatic equivalent -- so it stays.
      compact_threshold: 0.7
      compaction_notice_enabled: true
      compaction_notice_min_level: 1

  orchestrator:
    config:
      # Default is -1 = unlimited (loop-streaming __init__.py:581-582, 2346).
      # A single prompt was once observed driving 10 internal orchestrator turns
      # with nothing to stop it. This is a backstop, not a leash -- normal turns
      # use a handful of iterations.
      max_iterations: 40

tools:
  # Attention firewall query tool (local, this repo).
  - module: attention_firewall
    source: ../tools/attention-firewall

hooks:
  # Out-of-band notes into a running CLI session. Companion sender:
  # `amplifier-note <tmux-window> <text>`. Drains at provider:request.
  - module: hooks-inbox-drain
    source: ../modules/hooks-inbox-drain
    config:
      inbox_dir: ~/.amplifier/inbox
      priority: 5

  # LOG-ONLY delegation instrument -- fires once at session:end, injects nothing.
  - module: hooks-delegate-ratio
    source: ../modules/hooks-delegate-ratio
    config:
      log_path: ~/.amplifier/delegate-ratio.log
      ratio_flag_threshold: 0.40
      heavy_flag_min: 8
      priority: 60

  # Guard rail: at session:start, intersect the active routing matrix's provider
  # set against the providers actually available to this session, and warn if
  # roles cannot resolve. Catches the silent failure where a stale
  # .amplifier/settings.local.yaml pins a matrix that shares no provider with
  # the running session -- every model_role delegation then resolves to zero
  # candidates with no error. Warn-only by default; never aborts a session.
  - module: hooks-matrix-guard
    source: ../modules/hooks-matrix-guard
    config:
      enabled: true
      fail_on_broken: false
      priority: 10

agents:
  include:
    # Fast local inference via oMLX on the Mac Studio.
    - my-amplifier:agents/fast-local
---

# my-amplifier-base

Shared, provider-neutral base. Anchors' behavioral principles carry the session;
the file below states working preferences rather than procedures.

@anchors:context/system.md
@my-amplifier:context/preferences.md
