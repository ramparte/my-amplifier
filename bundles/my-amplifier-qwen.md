---
bundle:
  name: my-amplifier-qwen
  version: 0.1.0
  description: >
    Qwen overlay. my-amplifier-base plus an OpenAI Chat Completions-compatible
    provider instance for a local oMLX server.

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
      # provider-chat-completions uses config.name, not instance_id, as its
      # mounted provider identity. Keep it aligned with id for routing.
      name: qwen
      base_url: http://127.0.0.1:8000/v1
      api_key: not-needed
      default_model: Qwen3.8-27B-4bit
      use_streaming: true
      timeout: 600
---
