---
bundle:
  name: my-amplifier-oai
  version: 0.1.0
  description: >
    OpenAI-tuned personal bundle. Built on the Anchors base (~1.9 KB of static
    guidance) rather than exp-lean (~68.8 KB), and carrying provider-scoped
    settings that address the specific ways gpt-5.x sessions run away:
    server-side response chaining, unbounded orchestrator iteration, a
    Claude-shaped context ceiling, and high reasoning effort applied to a dense
    instruction stack. Does not modify my-amplifier-lean or my-amplifier-safe;
    switch back with `amplifier bundle use my-amplifier-lean` at any time.

# =====================================================================
# WHY THIS BUNDLE EXISTS
# ---------------------------------------------------------------------
# Forensics on session 01336022 (gpt-5.6, my-amplifier-lean, 6 user turns):
#
#   ~34,700 tokens  fixed preamble per call (instructions 17.9K + tools 16.8K)
#      190,354      input tokens on the final call (started at 31,380)
#           28      tool calls, of which ZERO did task work
#            6      identical load_skill(systematic-debugging) calls
#            4      mode(set, debug) attempts, 2 gated and denied
#            3      user-issued cancels
#            0      HTTP errors -- nothing failed; it just would not stop
#
# Three compounding causes, addressed below:
#   1. Instruction density  -> fixed by basing on Anchors (see `includes`)
#   2. Response chaining    -> fixed by `providers:` block
#   3. No iteration ceiling -> fixed by `session.orchestrator.config`
# Plus a Claude-shaped context window -> fixed by `session.context.config`.
#
# Deliberately NOT included (available on demand instead -- switch bundles, or
# re-add a single line): superpowers-methodology, made-support/stories/recipes
# behaviors, team-knowledge, dev-memory, agent-memory. Together those accounted
# for roughly 60 KB of the old preamble, and 12 stories agents inflated the
# `delegate` tool schema to 28.5 KB (42.5% of the entire tool block).
# =====================================================================

includes:
  # ===== BASE: Anchors (~1.9 KB static context, 6 thin agents) =====
  # Provides: filesystem, bash, web, search, todo, apply-patch, delegate,
  # skills (visibility off), mode, recipes tools; explorer/architect/builder/
  # debugger/git-ops/researcher agents; streaming-ui, status-context, redaction,
  # logging, context-intelligence behaviors. One context file: context/system.md
  # (1,712 bytes, four behavioral principles) -- versus 71,580 bytes under
  # my-amplifier-lean.
  #
  # Note: Anchors registers hooks-mode with `search_paths: []`, so no external
  # mode files are discovered. That incidentally removes the superpowers `debug`
  # mode, which ships `allow_clear: false` and produced the `clear_denied`
  # response that trapped session 01336022 when the user typed `mode off`.
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/anchors/bundle.md

  # ===== RESTORED: Python tooling (python_check + LSP/pyright) =====
  # The one capability from exp-lean worth its context cost for this workload.
  # Brings the `python_check` and `LSP` tools plus the python-dev and code-intel
  # agents. To slim further, replace with the python-quality sub-behavior only.
  - bundle: git+https://github.com/microsoft/amplifier-bundle-python-dev@main

# =====================================================================
# PROVIDER TUNING -- scoped to this bundle, merged by module id.
# ~/.amplifier/settings.yaml sets api_key / default_model / raw / priority for
# provider-openai and does NOT set any of the keys below, so these survive the
# merge. provider-anthropic is untouched: an Anthropic session under this bundle
# behaves exactly as it does today.
# =====================================================================
providers:
  - module: provider-openai
    config:
      # THE PRIMARY FIX. Default is "auto", which resolves to ON for every
      # reasoning model (provider __init__.py:746-751). Chaining sets store=true
      # and passes previous_response_id, so the SERVER holds the growing context
      # while the local transcript sees only a 1-5 item delta. Local compaction
      # therefore measures the wrong thing and never fires. The provider's own
      # comments (__init__.py:142-155, 605-613) state that this "drives unbounded
      # input-token growth -> context_length_exceeded"; its only guards are a
      # one-shot compaction-event chain reset and a reactive retry AFTER a 400.
      # Setting false makes OpenAI stateless per call, exactly like Anthropic,
      # so `compact_threshold` below becomes meaningful again.
      # Prefix caching still applies via prompt_cache_key / prompt_cache_retention
      # -- those are separate knobs and are left at their defaults.
      enable_response_chaining: false

      # Session 01336022 ran every main-loop call at effort "high". High effort
      # applied to a dense instruction stack is what turns standing orders into
      # an executable program -- 28 tool calls, none of them work. Anchors'
      # preamble is small enough that medium is sufficient; raise per-delegation
      # with model_role (the routing matrix still maps reasoning/critique/
      # security-audit to xhigh where that is warranted).
      reasoning_effort: medium

      # Default is "detailed" (_constants.py:22). Valid: auto | concise | detailed.
      # Summaries were 10 KB of the session for no operational benefit.
      reasoning_summary: concise

session:
  context:
    config:
      # gpt-5.6's measured hard ceiling is ~900K, but the provider's capability
      # table reports the long-context PRICING threshold of 272,000 as the
      # effective window, so unpinned sessions compact before incurring the ~2x
      # long-context rate (_capabilities.py:360-369). Match that number.
      # my-amplifier-lean used 200000 -- correct for Claude Opus, wrong here.
      max_tokens: 272000
      # 0.7 fires at ~190K, just below the pricing cliff. Session 01336022
      # reached 190,354 input tokens with no compaction at all.
      compact_threshold: 0.7
      compaction_notice_enabled: true
      compaction_notice_min_level: 1

  orchestrator:
    config:
      # Default is -1 = unlimited (loop-streaming __init__.py:581-582, 2346).
      # Turn 1 of session 01336022 drove 10 internal orchestrator turns off a
      # single prompt with nothing to stop it. 40 is a backstop, not a leash --
      # normal turns use a handful of iterations.
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
  # Worth keeping through this trial: it is the cheapest way to see whether the
  # Anchors base actually changes the delegate-vs-direct-work ratio.
  - module: hooks-delegate-ratio
    source: ../modules/hooks-delegate-ratio
    config:
      log_path: ~/.amplifier/delegate-ratio.log
      ratio_flag_threshold: 0.40
      heavy_flag_min: 8
      priority: 60

agents:
  include:
    # Fast local inference via oMLX on the Mac Studio.
    - my-amplifier:agents/fast-local
---

# my-amplifier-oai

An OpenAI-tuned personal bundle on the Anchors base. Anchors' four behavioral
principles carry the session; the file below states working preferences rather
than procedures, because gpt-5.x follows procedural language literally.

@my-amplifier:context/oai-preferences.md
