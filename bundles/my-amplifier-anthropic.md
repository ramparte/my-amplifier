---
bundle:
  name: my-amplifier-anthropic
  version: 0.1.0
  description: >
    Anthropic overlay. my-amplifier-base plus provider-scoped caching settings
    for Claude. Everything else -- tools, agents, hooks, preferences -- comes
    from the base and is provider-neutral. Anchors' low instruction density is
    not an OpenAI accommodation; it is better here too.

includes:
  # ABSOLUTE path, not relative -- see my-amplifier-oai.md for the full
  # explanation. `amplifier_foundation.registry.BundleRegistry` resolves
  # `./relative.md` includes against `Path.cwd()` at registry-construction
  # time (the CLI invocation directory), not the including file's own
  # directory, so a relative include here silently drops (warning-only,
  # not raised) whenever `amplifier run` is invoked from any directory
  # other than this bundles/ folder -- leaving this overlay with no
  # session/tools/hooks/agents and triggering "Configuration must specify
  # session.orchestrator". Absolute file:// is CWD-independent.
  - bundle: file:///home/ramparte/dev/ANext/my-amplifier/bundles/my-amplifier-base.md

# Bundle-declared routing matrix. Weakest source: anything set in
# ~/.amplifier/settings.yaml or a project .amplifier/settings*.yaml still wins,
# and with no matrix declared anywhere the global default applies as before.
#
# STATUS: inert today (Bundle.from_dict does not read a `routing:` key -- it is
# parsed and dropped). Declared so intent is recorded and it activates when the
# upstream PR lands. Until then, pair a bundle switch with
# `amplifier routing use anthropic`.
#
# This matrix is PURE Anthropic by design. Mixing a Claude planner with OpenAI
# workers is a legitimate thing to want, but it should be its own explicitly
# authored matrix -- that is what matrices are for. The per-provider matrices
# stay single-provider so that "which provider am I on" has one answer.
routing:
  matrix: anthropic

# =====================================================================
# THE ONLY THING THAT MAKES THIS THE "Anthropic" BUNDLE
# ---------------------------------------------------------------------
# Merged by module id, so this extends rather than replaces what
# ~/.amplifier/settings.yaml sets for provider-anthropic (api_key, base_url,
# default_model, priority). Settings win on conflict. provider-openai untouched.
#
# Note how short this is compared to the OpenAI overlay. That asymmetry is the
# finding, not an oversight: provider-anthropic is stateless per call with
# explicit cache_control breakpoints, so there is no chaining knob to disable
# and no hidden server-side context to bound. Reasoning effort is handled by the
# routing matrix per role rather than as a provider default.
# =====================================================================
providers:
  - module: provider-anthropic
    config:
      # Explicit cache_control breakpoints on system / tools / last message
      # (_format_system_with_cache, __init__.py:2113-2141). This is Anthropic's
      # equivalent of OpenAI's implicit prefix caching, and unlike chaining it
      # holds no server-side conversation state -- so local compaction always
      # measures what the model actually sees.
      enable_prompt_caching: "true"
      cache_ttl: 1h

      # Opus 1M-token context. Safe to leave on: the context budget is derived
      # from the provider's capability table at request time, so compaction
      # tracks whatever window is actually in effect.
      enable_1m_context: "true"
---

# my-amplifier-anthropic

Anthropic overlay on `my-amplifier-base`. See `context/provider-differences.md`
for the mechanical differences between the two providers.
