---
bundle:
  name: my-amplifier-anchors
  version: 0.1.0
  description: Thin personal overlay on Microsoft Anchors.
  namespace_root: ..

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/anchors/bundle.md

tools:
  - module: tool-lsp
    source: git+https://github.com/microsoft/amplifier-bundle-lsp@main#subdirectory=modules/tool-lsp
    config:
      timeout_seconds: 30
      languages:
        python:
          extensions:
            - .py
            - .pyi
          workspace_markers:
            - pyproject.toml
            - setup.py
            - setup.cfg
            - requirements.txt
            - .git
          server:
            command:
              - pyright-langserver
              - --stdio
            install_check:
              - pyright
              - --version
            install_hint: "Install with: npm install -g pyright"
          capabilities:
            diagnostics: true
            rename: true
            codeAction: false
            inlayHints: false
            customRequest: false
            goToImplementation: false
          initialization_options:
            python:
              analysis:
                autoSearchPaths: true
                useLibraryCodeForTypes: true
                diagnosticMode: workspace

  - module: tool-python-check
    source: git+https://github.com/microsoft/amplifier-bundle-python-dev@main#subdirectory=modules/tool-python-check

hooks:
  - module: hooks-inbox-drain
    source: ../modules/hooks-inbox-drain
    config:
      inbox_dir: ~/.amplifier/inbox
      priority: 5

  - module: hooks-delegate-ratio
    source: ../modules/hooks-delegate-ratio
    config:
      log_path: ~/.amplifier/delegate-ratio.log
      ratio_flag_threshold: 0.40
      heavy_flag_min: 8
      priority: 60

agents:
  include:
    - my-amplifier-anchors:fast-local
---

# my-amplifier-anchors

Anchors supplies the operating principles. Concise working preferences are the
only added always-on guidance.

## Mandatory Spark-to-Windows invariant

Direct Windows-to-Spark access never works, including through Tailscale. For
every Windows-facing Spark service: **allocate** an unclaimed identity-mapped
port in `8400-8500` after checking the canonical ledger and live listeners;
**publish** the service or loopback proxy on that same Spark port; proactively
**repair** or install and maintain the persistent WSL tunnel with the versioned
Concern OS installer and the machine's required profile; **record** the
allocation; and **verify** the exact URL from Spark, WSL, and Windows. Report
only `http://localhost:<port>/...`, and never silently change an assigned port.

@anchors:context/system.md
@my-amplifier-anchors:context/preferences.md
@my-amplifier-anchors:context/spark-windows-tunnels.md

# Local machine supplement
@user:AGENTS.md
