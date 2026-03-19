# Windows Testing Fallback

When running on a DGX Spark (spark-1 or spark-2), you have a Windows machine
available via Tailscale for Edge/Office debugging.

**When to use it:** Only when you detect a platform-specific visual issue, need
real Office COM automation, or the user explicitly asks for Windows-side testing.
Do NOT use Windows proactively. Linux Chromium and LibreOffice handle 95% of cases.

**SSH:** `samschillace@100.92.254.41` (WSL2 on Windows, same ANext at ~/dev/ANext)

**Fleet management scripts:** `~/dev/ANext/dgx-spark-setup/` -- see AGENTS.md there.
