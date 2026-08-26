# Working Preferences

Preferences, not procedures. Apply judgment; these describe what good output looks
like here, not a checklist to execute.

## Reporting effort

Describe work by effort level, never by wall-clock time: trivial, easy, medium,
large, complex. Time estimates are noise — Amplifier's speed makes them wrong and
they create false pressure. "Medium — touches 3 files and the auth flow" is useful.
"About two hours" is not.

## Evidence

"Done" means evidence was shown: actual test output, actual command output, an
actual diff. A summary of a result is not the result.

Work that is blocked is not done. Say what blocks it and what would unblock it,
rather than closing it out.

Uncommitted work is not finished work. If a change is complete, push it.

## Context discipline

The main thread's context is the scarce resource. Multi-file exploration, broad
searches, and log scanning belong in a subagent, which absorbs the token cost and
returns a summary. Reserve the main thread for synthesis and decisions.

Before a broad `grep`, `glob`, or read: if it would return more than a couple of
screenfuls, narrow it or delegate it.

## Scope

Treat a request as authorization to deliver its stated outcomes, not to improve
adjacent systems or absorb newly found defects; report those separately. For
setup, configuration plus one relevant smoke test is sufficient; a failure is
a blocker, not permission to repair the platform. Do not turn reviews or
retries into loops. If part of a request is blocked, say so and continue
independent requested work.

## Environment

- **SSH user convention (tailscale fleet):** use `ramparte@<host>` for
  spark-1, spark-2, and the other `ramparte@` nodes in `tailscale status`
  (`lazarus`, `traveler-pc`, `sodahouse-computer*`) — never guess the local
  username.
  - **`macstudio` exception:** use `sam@macstudio`. Tailscale on the Mac
    Studio fails user lookup for the other local accounts (`failed to look
    up local user ...`); `sam` is the working account.
  - **Fleet key:** the laptop (`sams-m5` / `Sams-M5.local` — "the M5
    laptop") holds the authorized fleet key `~/.ssh/id_ed25519`
    (SHA256:XZh2nWGiPLZ6iB0620kOFAj6uMvZiafxxe9+faZDzNk). Plain key login
    works from there to `ramparte@spark-1` and `ramparte@spark-2`
    (verified 2026-08-20). `sam@macstudio` needs no key at all — its
    tailscale authenticates with `none`. If the sparks start returning
    `Permission denied (publickey,password)`, their
    `~/.ssh/authorized_keys` was likely rotated — re-publish the key.
  - **Naming:** "M5" is ambiguous — the Mac Studio (`macstudio`) and the
    laptop (`sams-m5`) are both M5 machines. Always disambiguate by
    hostname or tailscale name.
  - Probe with `ssh -o BatchMode=yes ...` before assuming login works.
- **DGX Spark hosts (spark-1, spark-2):** fleet management scripts live in
  `~/dev/ANext/dgx-spark-setup/` on the sparks. Linux Chromium and LibreOffice
  cover nearly everything; use `wilaptop-rebuild` (`WILaptopRebuild`; Tailscale
  node `wilaptoprebuild` at `100.74.32.82`; WSL user `samschillace`) only for a
  genuine Windows-specific Edge or Office issue.
- **Spark-to-Windows service URLs:** a persistent WSL-initiated SSH tunnel
  identity-forwards localhost ports **8400-8500 inclusive** from
  `wilaptop-rebuild` to `spark-1` (`100.123.54.55`; SSH user `ramparte`). Choose
  an unclaimed port only after checking live Spark listeners, bind the Spark
  service to `127.0.0.1:<port>`, and give the user
  `http://localhost:<port>/...` for Windows. The canonical contract and
  allocation ledger is
  `/home/ramparte/dev/ANext/dgx-spark-setup/TUNNEL-ARCHITECTURE.md`. Every
  allocation, release, range/destination/launcher change must update that ledger
  and the deployment source, then be verified Spark -> WSL -> Windows end to end.
- **Mac Studio (`macstudio`):** oMLX serves a fast local model on port 8000
  alongside Ollama on 11434. The `fast-local` agent is already wired to it — delegate
  there when asked for fast local inference or when SSD-backed KV caching across a
  long analysis would help.
