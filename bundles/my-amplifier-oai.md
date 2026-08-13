---
bundle:
  name: my-amplifier-oai
  version: 0.2.0
  description: >
    OpenAI overlay. my-amplifier-base plus the provider-scoped settings that
    keep gpt-5.x sessions from running away: response chaining off, medium
    reasoning effort, concise reasoning summaries. Everything else -- tools,
    agents, hooks, preferences -- comes from the base and is provider-neutral.

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
  # still reports 13 tools / 15 hooks / 11 agents.
  - bundle: file:///home/ramparte/dev/ANext/my-amplifier/bundles/my-amplifier-base.md

# Bundle-declared routing matrix. The bundle is the WEAKEST source: any matrix
# set in ~/.amplifier/settings.yaml or a project .amplifier/settings*.yaml still
# wins, and with no matrix declared anywhere the global default applies exactly
# as before.
#
# STATUS: inert today. Bundle.from_dict() reads only bundle/includes/session/
# providers/tools/hooks/spawn/agents/context, so a `routing:` key is parsed and
# silently dropped. Declared here anyway so intent is recorded and this starts
# working the moment the upstream PR lands. Until then, pair a bundle switch
# with `amplifier routing use openai`.
routing:
  matrix: openai

# =====================================================================
# THE ONLY THING THAT MAKES THIS THE "OpenAI" BUNDLE
# ---------------------------------------------------------------------
# Merged by module id, so this extends rather than replaces whatever
# ~/.amplifier/settings.yaml already sets for provider-openai (api_key,
# default_model, priority). Settings win on conflict; none of the keys below
# are set there. provider-anthropic is untouched.
# =====================================================================
providers:
  - module: provider-openai
    config:
      # Default is "auto" -> ON for every reasoning model (__init__.py:746-751).
      # Chaining sets store=true and passes previous_response_id, so the SERVER
      # holds a growing context that local compaction cannot see and therefore
      # never compacts. Measured: 31,380 -> 190,354 input tokens across 30 calls
      # with a 140K compaction threshold that never fired. The provider's own
      # comments (__init__.py:142-155, 605-613) call this "unbounded input-token
      # growth -> context_length_exceeded". Off = stateless per call, exactly
      # like Anthropic. Prefix caching is unaffected (separate knobs:
      # prompt_cache_key / prompt_cache_retention); measured 81% hit rate with
      # chaining disabled.
      enable_response_chaining: false

      # High effort on a dense instruction stack is what turns standing orders
      # into an executable program. Raise per-delegation with model_role instead;
      # the openai matrix still maps reasoning/critique/security-audit to xhigh.
      reasoning_effort: medium

      # Default is "detailed" (_constants.py:22). Valid: auto | concise | detailed.
      reasoning_summary: concise
---
