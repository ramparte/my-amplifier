---
bundle:
  name: my-amplifier-qwen
  version: 0.3.1
  description: >
    Full-provider overlay. my-amplifier-base plus all personal provider mounts,
    local Qwen via oMLX, and a Qwen-specific prompt layer.

includes:
  # Namespace includes resolve through the registered `my-amplifier` source,
  # keeping the base resolvable from any working directory on either Mac.
  - bundle: my-amplifier:bundles/my-amplifier-base.md

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
      # This applies only to the unnamed provider-openai mount; named instances
      # are separate entries with their own saved configuration.
      reasoning_effort: medium
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

agents:
  include:
    - my-amplifier:agents/fast-local
---

# my-amplifier-qwen

Shared, provider-neutral base. Anchors' behavioral principles carry the session;
the file below states working preferences rather than procedures.

@anchors:context/system.md
@my-amplifier:context/preferences.md
@my-amplifier:context/qwen.md
