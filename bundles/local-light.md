---
bundle:
  name: my-amplifier-local
  version: 1.0.0
  description: Lightweight bundle for local models (Ollama/oMLX). Same tools, minimal context injection to fit within local model context windows.

includes:
  # Foundation core only - tools, bash, filesystem, web, delegation
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/foundation.yaml
---

# My Amplifier (Local Lightweight)

A minimal bundle for local model inference on the Mac Studio. Provides all
standard tools (filesystem, bash, web, search, delegation) with minimal
system prompt overhead to fit within local model context windows (32-64K).

The full `my-amplifier` bundle injects ~40K+ tokens of context (delegation
patterns, superpowers philosophy, dev-memory rules, made-support triggers,
routing matrix docs, skills visibility, etc.). Local 35B models cannot
effectively attend to this much context.

This bundle strips all of that, keeping only:
- Core tools (filesystem, bash, web_fetch, web_search, grep, glob)
- Agent delegation (delegate tool)
- Basic system instructions

For full capabilities (superpowers, dev-memory, projector, MADE support,
stories, etc.), use the main `my-amplifier` bundle with a cloud provider.

## Usage

On Mac Studio, set in settings.yaml:
```yaml
bundle:
  active: my-amplifier-local
  added:
    my-amplifier-local: /Users/sam/ANext/my-amplifier/bundles/local-light.md
```

@foundation:context/shared/common-system-base.md
