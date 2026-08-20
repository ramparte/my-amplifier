# Windows Testing Fallback

When running on a DGX Spark (spark-1 or spark-2), you have a Windows machine
available via Tailscale for Edge/Office debugging.

**When to use it:** Only when you detect a platform-specific visual issue, need
real Office COM automation, or the user explicitly asks for Windows-side testing.
Do NOT use Windows proactively. Linux Chromium and LibreOffice handle 95% of cases.

**Windows/WSL client:** friendly name `wilaptop-rebuild`; Windows/WSL hostname
`WILaptopRebuild`; Tailscale node `wilaptoprebuild` (`100.74.32.82`); WSL user
`samschillace`; same ANext tree at `~/dev/ANext`.

**Spark endpoint:** friendly name `spark-1`; OS hostname `spark-832a`; Tailscale
IP `100.123.54.55`; SSH user `ramparte`.

**Windows-facing Spark services:** the laptop initiates a persistent SSH tunnel
that identity-forwards localhost ports **8400-8500 inclusive** to Spark. The
canonical topology, operating procedure, and allocation ledger is
`/home/ramparte/dev/ANext/dgx-spark-setup/TUNNEL-ARCHITECTURE.md`.
Do not infer availability from WSL's SSH listeners; check live Spark listeners
and the ledger.

**Fleet management scripts:** `~/dev/ANext/dgx-spark-setup/` -- see `AGENTS.md`
there.
