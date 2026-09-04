---
bundle:
  name: my-amplifier-oai
  version: 0.4.0
  description: >
    OpenAI overlay on my-amplifier-base. Adds only the wire-level settings that
    genuinely differ for OpenAI AND are not managed elsewhere. reasoning_effort
    is deliberately NOT set here: it is a live, machine-specific knob owned by
    settings.yaml (which wins the same-id provider merge), so pinning it here
    would be a silent no-op. Only reasoning_summary is governed here.

includes:
  # Base is included FROM GIT (same repo @main), not by an absolute file:// path.
  # This resolves identically on every fleet machine (spark-1/2, macstudio,
  # sams-m5, and any /home/<other> clone) and never reaches back into a local
  # worktree. A git+ include is CWD-independent; a `./relative.md` include is
  # NOT -- amplifier_foundation resolves relative includes against Path.cwd()
  # (the CLI's invocation dir) rather than this file's own directory, so from
  # any project dir it silently drops (warning-only) and the session dies with
  # "Configuration must specify session.orchestrator". Upstream fix is
  # microsoft/amplifier-foundation#303, still UNMERGED in the installed build.
  #
  # COST: edits to my-amplifier-base.md take effect only after `git push` to
  # @main -- this fetches the pushed copy. That is already the operating model,
  # since this overlay is itself registered by git+@main in settings.
  - bundle: git+https://github.com/ramparte/my-amplifier@main#subdirectory=bundles/my-amplifier-base.md

providers:
  # reasoning_effort is intentionally ABSENT. It is owned per provider-id by
  # settings.yaml, which wins the same-id config deep-merge, so any value here
  # never reaches the wire. reasoning_summary IS set (settings leaves it unset,
  # so this governs): concise, instead of the provider default 'detailed'.
  - id: openai
    module: provider-openai
    config:
      reasoning_summary: concise
  - id: terra
    module: provider-openai
    config:
      reasoning_summary: concise
  - id: luna
    module: provider-openai
    config:
      reasoning_summary: concise
  - id: luna-max
    module: provider-openai
    config:
      reasoning_summary: concise
---
