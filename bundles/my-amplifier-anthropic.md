---
bundle:
  name: my-amplifier-anthropic
  version: 0.2.2
  description: >
    Anthropic overlay on my-amplifier-base. The generic provider defaults to
    Opus for portable roots; saved settings with the same exact identity
    override that default and all other portable provider settings.

includes:
  # Base included FROM GIT (same repo @main) -- see my-amplifier-oai.md for the
  # full rationale. git+ is CWD-independent and machine-independent, so this
  # overlay resolves identically across the fleet and never reaches into a local
  # worktree. A `./relative.md` include is NOT safe: amplifier_foundation
  # resolves it against Path.cwd(), not this file's dir (foundation #303, still
  # unmerged). COST: base edits take effect only after `git push` to @main.
  - bundle: git+https://github.com/ramparte/my-amplifier@main#subdirectory=bundles/my-amplifier-base.md

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
