# Fleet Awareness

You are running on a multi-machine development fleet. This context tells you
what machines exist, what they can do, and when to use each one.

## Topology

Fleet config: `~/dev/ANext/dgx-spark-setup/fleet.yaml`

| Machine | OS | Tailscale | Role |
|---------|----|-----------|------|
| **windows** | Windows 11 + WSL2 | 100.92.254.41 | Debug fallback (Office, Edge) |
| **spark-1** | Linux ARM64 (DGX Spark) | 100.123.54.55 | Primary compute |
| **spark-2** | Linux ARM64 (DGX Spark) | 100.77.120.35 | Secondary / backup |

Check `fleet.yaml` for the current `primary:` value to know which machine is
active. ANext is synced identically across all three machines.

## Default: Everything Runs Locally

All work happens on whichever machine you are currently running on. Do not
reach out to other machines unless you have a specific reason.

| Task | Local tool | No remote needed |
|------|-----------|-----------------|
| Browser UI testing | agent-browser + Playwright Chromium | Native ARM64 or x86 |
| Document rendering | LibreOffice headless (`libreoffice --headless --convert-to`) | Handles PPTX, DOCX, PDF |
| Visual QA | amplifier-ux-analyzer (screenshot comparison, SSIM) | Runs locally |
| Code, tests, builds | pytest, cargo, npm, docker | Always local |

## When to Fall Back to Windows

Use the Windows machine ONLY when:

1. **You detect a visual discrepancy** that you suspect is platform-specific
   (font rendering, scrollbar width, DPI scaling, ClearType vs FreeType).

2. **You need real Office fidelity** -- the user says a deck or doc "doesn't
   look right" and LibreOffice rendering isn't trustworthy enough to diagnose.

3. **The user explicitly asks** for Windows-side verification.

Do NOT proactively use Windows "just to be safe." Linux Chromium catches 95%
of browser issues. LibreOffice catches 80% of document issues. Only escalate
when those aren't sufficient.

## How to Use the Windows Machine

The Windows machine runs WSL2. Amplifier is installed inside WSL. SSH access
is via Tailscale.

**Run a command on Windows (WSL):**
```bash
ssh samschillace@100.92.254.41 "command here"
```

**Run an Amplifier session on Windows:**
```bash
ssh samschillace@100.92.254.41 "cd ~/dev/ANext && amplifier run 'your prompt here'"
```

**Access native Windows from WSL (Office, Edge, PowerShell):**
```bash
# From within WSL on the Windows box:
powershell.exe -Command "Start-Process 'C:\Program Files\Microsoft Office\...\POWERPNT.EXE' '/path/to/file.pptx'"
cmd.exe /c start msedge "http://url"
```

**Copy files to/from Windows:**
```bash
scp file.pptx samschillace@100.92.254.41:~/dev/ANext/project/
scp samschillace@100.92.254.41:~/screenshot.png ./
```

## Browser Debug Repos

Three repos in `ramparte/` handle browser and visual testing:

### amplifier-ux-analyzer
Visual QA and screenshot comparison. Uses PyTorch for perceptual similarity
(SSIM, feature extraction). Compares "expected" vs "actual" screenshots.
- **Runs on:** Any machine (Python + PyTorch)
- **Use for:** Automated visual regression detection
- **Windows fallback:** When a visual diff is detected and you need to verify
  it appears the same on Windows Edge

### amplifier-bundle-browser-tester
Agent-browser integration for Amplifier sessions. Provides browser-operator,
browser-researcher, and visual-documenter agents via Playwright.
- **Runs on:** Any machine with agent-browser + Chromium
- **Use for:** Browser automation, form filling, UX testing, screenshots
- **Windows fallback:** When behavior differs between Linux Chromium and
  Windows Edge (rare for Chromium-based browsers, mostly font/scrollbar issues)

### amplifier-browser-debugger
Browser DevTools automation. Connects to Chrome DevTools Protocol for
performance profiling, network inspection, console log capture.
- **Runs on:** Any machine with Chromium
- **Use for:** Performance debugging, network analysis, JS error capture
- **Windows fallback:** When a JS error or performance issue only reproduces
  on Windows (very rare)

### Testing Pattern

The standard pattern for all three repos:

1. **Test locally first** (Linux Chromium) -- this is the fast path
2. **If a visual or behavioral issue is found**, determine if it could be
   platform-specific
3. **If yes**, SSH to the Windows box and reproduce there
4. **If the issue reproduces on both**, it's a real bug -- fix it
5. **If it only reproduces on Windows**, it's a platform issue -- decide
   whether to fix or document

## Fleet Management

Scripts in `~/dev/ANext/dgx-spark-setup/`:

| Script | Purpose |
|--------|---------|
| `audit-anext-repos.sh` | Check all repos for uncommitted/unpushed work |
| `snapshot-anext.sh` | Create timestamped ANext tarball (keeps last 3) |
| `verify-sync.sh` | Compare ANext between two machines |
| `switch-primary.sh` | Safely migrate primary to another machine |
| `backup-anext.sh` | Cron job: rsync ANext along the sync chain |

### Switching Primary

When the user says "switch to spark-1 as primary" (or similar):

```bash
cd ~/dev/ANext/dgx-spark-setup && ./switch-primary.sh spark-1
```

The script will:
1. Audit all repos (blocks if dirty)
2. Create a safety snapshot
3. Sync ANext to the target
4. Update fleet.yaml on both machines
5. Recreate tmux session on target
6. Verify sync

Use `--dry-run` to preview without changes.

### Backup Chain

Current chain (updates when primary changes):
- Windows -> spark-1 -> spark-2 (cron every 15 min)

After switching primary to spark-1:
- spark-1 -> spark-2 (keep existing cron on spark-1)
- spark-1 -> windows (new cron, or on-demand)
