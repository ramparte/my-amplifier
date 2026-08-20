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
  - **`macstudio` exception (broken as of 2026-08-19):** tailscale on
    `macstudio` fails user lookup for *both* `ramparte` and `samschillace`
    (`failed to look up local user ...`). No account is reachable — ask the
    user which account to use; do not guess.
  - **Key map (2026-08-19):** the working fleet key lives on the laptop
    (`WILaptopRebuild`, 100.74.32.82). The M5 (`sams-m5`, 100.101.114.84)
    holds its own key (`~/.ssh/id_ed25519`,
    SHA256:XZh2nWGiPLZ6iB0620kOFAj6uMvZiafxxe9+faZDzNk) which is NOT yet on
    the fleet — from the M5, fleet ssh returns `Permission denied
    (publickey,password)`. If a session on the M5 needs fleet access, have the
    user append the M5's `~/.ssh/id_ed25519.pub` to the target's
    `~/.ssh/authorized_keys` from wherever their ramparte login works.
    The WSL2 box `100.92.254.41` (Windows fallback in `fleet-awareness.md`)
    is no longer in the tailnet — unreachable until it rejoins.
  - Always probe with `ssh -o BatchMode=yes ...` before assuming login works.
- **DGX Spark hosts (spark-1, spark-2):** a Windows box is reachable at
  `samschillace@100.92.254.41` (WSL2, same ANext tree at `~/dev/ANext`) for Edge or
  Office debugging. Linux Chromium and LibreOffice cover nearly everything; use
  Windows only for a genuine platform-specific issue. Fleet scripts live in
  `~/dev/ANext/dgx-spark-setup/`.
- **Mac Studio (`macstudio`):** oMLX serves a fast local model on port 8000
  alongside Ollama on 11434. The `fast-local` agent is already wired to it — delegate
  there when asked for fast local inference or when SSD-backed KV caching across a
  long analysis would help.
