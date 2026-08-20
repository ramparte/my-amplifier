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

Answer the question that was asked. If a second problem surfaces mid-task, finish
the first and raise the second separately rather than folding it in.

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
  `~/dev/ANext/dgx-spark-setup/` on the sparks (not in the laptop's
  `~/ANext` tree). Linux Chromium and LibreOffice cover nearly everything;
  the Windows WSL2 box (`samschillace@100.92.254.41`, see
  `fleet-awareness.md`) is the fallback for Edge/Office debugging — but it
  left the tailnet (as of 2026-08-20), so verify it before relying on it.
- **Mac Studio (`macstudio`):** oMLX serves a fast local model on port 8000
  alongside Ollama on 11434. The `fast-local` agent is already wired to it — delegate
  there when asked for fast local inference or when SSD-backed KV caching across a
  long analysis would help.
