---
bundle:
  name: my-amplifier-qwen
  version: 0.2.1
  description: >
    Full-provider overlay. my-amplifier-base plus all personal provider mounts,
    local Qwen via oMLX, and a Qwen-specific prompt layer.

includes:
  # Relative file includes are currently resolved from the CLI invocation CWD,
  # not this file's directory. This Mac-specific absolute path keeps the base
  # resolvable when Amplifier runs from another project directory.
  - bundle: file:///Users/samschillace/ANext/my-amplifier/bundles/my-amplifier-base.md

providers:
  - id: qwen
    module: provider-chat-completions
    source: git+https://github.com/microsoft/amplifier-module-provider-chat-completions@main
    config:
      base_url: http://127.0.0.1:8000/v1
      api_key: not-needed
      default_model: Qwen3.8-27B-4bit
      priority: 0
      use_streaming: true
      timeout: 600
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
  - module: provider-anthropic
  - module: provider-github-copilot
  - id: runpod
    module: provider-vllm
  - id: runpod-qwen
    module: provider-vllm
  - id: fable
    module: provider-anthropic
  - id: opus
    module: provider-anthropic
  - id: sonnet
    module: provider-anthropic
  - id: "5.5"
    module: provider-openai
  - id: "5.6"
    module: provider-openai
---

# my-amplifier-base

Shared, provider-neutral base. Anchors' behavioral principles carry the session;
the file below states working preferences rather than procedures.

@anchors:context/system.md
@my-amplifier:context/preferences.md
@my-amplifier:context/qwen.md
