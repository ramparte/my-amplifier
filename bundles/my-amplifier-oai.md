---
bundle:
  name: my-amplifier-oai
  version: 0.3.0
  description: >
    OpenAI overlay on my-amplifier-base. Saved settings provide credentials,
    endpoints, models, priorities, long-context choices, and identity-specific
    effort values; they override these portable defaults by exact identity.

includes:
  # ABSOLUTE path, not relative. `amplifier_foundation.registry.BundleRegistry`
  # constructs its FileSourceHandler with `base_path=Path.cwd()` captured ONCE
  # at registry-construction time (the CLI process's invocation directory) --
  # NOT the directory of the bundle file declaring the include. A `./relative.md`
  # include here only resolves when the CLI happens to be invoked from this
  # bundles/ directory; from any project dir (e.g. `cd /tmp/x && amplifier run`)
  # it fails ("File not found: <cwd>/my-amplifier-base.md"), the include is
  # silently dropped (logged as a warning, not raised), and this overlay ends up
  # with NO session/tools/hooks/agents at all -- `session.orchestrator` is then
  # simply absent, not merely misconfigured, and create_session() raises
  # "Configuration must specify session.orchestrator". Absolute file:// makes
  # resolution independent of CWD.
  #
  # COST OF THIS WORKAROUND: the absolute path is machine-specific, so a clone of
  # this repo on another host (spark-2, macstudio, the Windows WSL box where the
  # home dir is /home/samschillace) will NOT resolve the base.
  #
  # TODO(revert): fixed upstream by microsoft/amplifier-foundation#303, which
  # anchors relative includes to the declaring bundle's base_path. Once that
  # merges and this machine's foundation is updated, change this line back to:
  #     - bundle: ./my-amplifier-base.md
  # and delete this comment block. Verify by running `amplifier bundle show
  # my-amplifier-oai` from a directory OTHER than bundles/ and confirming it
  # still reports 13 tools / 15 hooks / 10 agents.
  - bundle: file:///home/ramparte/dev/ANext/my-amplifier/bundles/my-amplifier-base.md

providers:
  - id: openai
    module: provider-openai
    config:
      reasoning_effort: medium
      reasoning_summary: concise
  - id: terra
    module: provider-openai
    config:
      reasoning_effort: medium
      reasoning_summary: concise
  - id: luna
    module: provider-openai
    config:
      reasoning_effort: medium
      reasoning_summary: concise
  - id: luna-max
    module: provider-openai
    config:
      reasoning_effort: medium
      reasoning_summary: concise
---
