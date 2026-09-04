---
bundle:
  name: my-amplifier-anthropic
  version: 0.2.1
  description: >
    Anthropic overlay on my-amplifier-base. The generic provider defaults to
    Opus for portable roots; saved settings with the same exact identity
    override that default and all other portable provider settings.

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
  #
  # TODO(revert): fixed upstream by microsoft/amplifier-foundation#303. Once that
  # merges and foundation is updated here, change this back to
  # `- bundle: ./my-amplifier-base.md` and drop this comment block.
  # The absolute path is machine-specific and will not resolve on a clone with a
  # different home directory.
  - bundle: file:///home/ramparte/dev/ANext/my-amplifier/bundles/my-amplifier-base.md

providers:
  - module: provider-anthropic
    config:
      default_model: claude-opus-4-8
      enable_prompt_caching: true
      cache_stable_region_ttl_1h: true
      enable_1m_context: true
  - id: fable
    module: provider-anthropic
    config:
      enable_prompt_caching: true
      cache_stable_region_ttl_1h: true
      enable_1m_context: true
  - id: opus
    module: provider-anthropic
    config:
      enable_prompt_caching: true
      cache_stable_region_ttl_1h: true
      enable_1m_context: true
  - id: sonnet
    module: provider-anthropic
    config:
      enable_prompt_caching: true
      cache_stable_region_ttl_1h: true
      enable_1m_context: true
---
