#!/usr/bin/env python3
"""amplifier-note: drop a note into a running amplifier CLI session's inbox.

Usage:
    amplifier-note <window> <text...> [-p PRIORITY] [-l LABEL]   # legacy: target by window
    amplifier-note --session <uuid> <text...>                    # target by session id
    amplifier-note --here <text...>                              # target THIS pane's session
    amplifier-note --list

Targeting (notes-unification Phase 2). A note now carries a stable routing
identity -- the target's `session_uuid` -- resolved at submit time from the
recorder's `~/.amplifier/pane-sessions.tsv` (window+cwd -> session_uuid). The
window NAME is kept only as a fallback hint. This makes routing survive tmux
window renames and lets the drain hook accept only notes addressed to its own
session id.

- `<window>` (legacy positional) / `--window NAME`: target by tmux window NAME;
  resolves to a session id when the recorder knows one (else null -> legacy
  window-file delivery, still works).
- `--session <uuid>`: target a specific session id directly.
- `--here`: target the session running in the current tmux pane.

The target session's inbox-drain hook reads the note before its next LLM call and
folds it into whatever it is doing -- no need to interrupt it or type into the
busy pane.

Stdlib-only and self-contained so it can be symlinked onto PATH and run by any
python3, independent of the amplifier venv.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_INBOX_DIR = "~/.amplifier/inbox"
DEFAULT_PANE_SESSIONS = "~/.amplifier/pane-sessions.tsv"
PRIORITIES = ["info", "low", "med", "high", "critical"]


def _safe_filename(label: str) -> str:
    return label.replace(os.sep, "_").strip()


# ---------------------------------------------------------------------------
# Session-identity resolution (via the recorder's pane-sessions.tsv)
# columns: window_name \t cwd \t session_uuid \t confidence \t iso_timestamp
# ISO8601-Z timestamps sort lexicographically == chronologically, so "newest
# row wins" (the recorder's own ambiguity policy: most-recently-active).
# ---------------------------------------------------------------------------
def _pane_rows(pane_sessions: Path) -> list[tuple[str, str, str, str]]:
    if not pane_sessions.exists():
        return []
    rows: list[tuple[str, str, str, str]] = []
    for ln in pane_sessions.read_text(encoding="utf-8").splitlines():
        ln = ln.rstrip("\n")
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split("\t")
        if len(parts) < 3:
            continue
        window, _cwd, uuid = parts[0], parts[1], parts[2]
        ts = parts[4] if len(parts) > 4 else ""
        rows.append((window, uuid, ts, _cwd))
    return rows


def _window_to_session(window: str, pane_sessions: Path) -> str | None:
    cands = [
        (ts, uuid) for (w, uuid, ts, _c) in _pane_rows(pane_sessions) if w == window
    ]
    if not cands:
        return None
    cands.sort()  # newest iso timestamp last
    return cands[-1][1]


def _session_to_window(uuid: str, pane_sessions: Path) -> str | None:
    cands = [(ts, w) for (w, u, ts, _c) in _pane_rows(pane_sessions) if u == uuid]
    if not cands:
        return None
    cands.sort()
    return cands[-1][1]


def _own_window() -> str | None:
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return None
    try:
        out = subprocess.run(
            ["tmux", "display-message", "-t", pane, "-p", "#{window_name}"],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def _list_windows() -> list[str]:
    try:
        out = subprocess.run(
            ["tmux", "list-windows", "-a", "-F", "#{window_name}"],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    seen: list[str] = []
    for n in out.stdout.splitlines():
        n = n.strip()
        if n and n not in seen:
            seen.append(n)
    return seen


def _pending(inbox_dir: Path, window: str) -> int:
    f = inbox_dir / f"{_safe_filename(window)}.jsonl"
    if not f.exists():
        return 0
    return sum(1 for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="amplifier-note",
        description="Drop a note into a running amplifier session's inbox "
        "(target by tmux window name, session id, or --here).",
    )
    p.add_argument("window", nargs="?", help="legacy: target tmux window name")
    p.add_argument("text", nargs="*", help="note text")
    p.add_argument("-p", "--priority", choices=PRIORITIES, default="low")
    p.add_argument("-l", "--label", default=None, help="optional card label / tag")
    p.add_argument(
        "--inbox-dir", default=os.environ.get("AMPLIFIER_INBOX_DIR", DEFAULT_INBOX_DIR)
    )
    p.add_argument(
        "--pane-sessions",
        default=os.environ.get("AMPLIFIER_PANE_SESSIONS", DEFAULT_PANE_SESSIONS),
        help="recorder's window+cwd -> session_uuid map",
    )
    p.add_argument("--session", default=None, help="target a specific session_uuid")
    p.add_argument(
        "--window", dest="window_flag", default=None, help="target tmux window NAME"
    )
    p.add_argument(
        "--origin",
        default="cli",
        help="provenance tag for the note (e.g. cli, dashboard)",
    )
    p.add_argument(
        "--here",
        action="store_true",
        help="target the session in the CURRENT tmux pane",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="list active tmux windows + pending note counts",
    )
    args = p.parse_args(argv)

    inbox_dir = Path(args.inbox_dir).expanduser()
    pane_sessions = Path(args.pane_sessions).expanduser()

    if args.list:
        wins = _list_windows()
        if not wins:
            print("(no tmux windows found / not in tmux)")
            return 0
        for w in wins:
            sid = _window_to_session(w, pane_sessions)
            sid_bit = f"  [{sid[:8]}]" if sid else ""
            print(f"{w}\t({_pending(inbox_dir, w)} pending){sid_bit}")
        return 0

    # ---- Resolve target -> (target_session, target_window, dest_key) --------
    # dest_key is the inbox filename stem. Session-targeted notes go to a file
    # keyed by session id (the drain hook reads its own <session_id>.jsonl);
    # window-targeted notes keep the legacy <window>.jsonl channel for backward
    # compatibility (old hooks + dashboard/notes-watcher still work).
    targeted = bool(args.session or args.here or args.window_flag)
    if targeted:
        # a targeting flag was given, so any positional "window" is really text
        text_tokens = ([args.window] if args.window else []) + list(args.text)
    else:
        text_tokens = list(args.text)

    text = " ".join(text_tokens).strip()

    target_session: str | None = None
    target_window: str | None = None
    dest_key: str | None = None

    if args.session:
        target_session = str(args.session)
        target_window = _session_to_window(target_session, pane_sessions)
        dest_key = target_session
    elif args.here:
        w = _own_window()
        if not w:
            p.error("--here: not inside a tmux pane (no TMUX_PANE)")
        target_window = w
        target_session = _window_to_session(w, pane_sessions)  # may be None
        dest_key = target_session or w
    else:
        # legacy window target (positional or --window)
        w = args.window_flag or args.window
        if not w:
            p.error(
                "need a target: <window> | --window NAME | --session UUID | --here (or --list)"
            )
        target_window = w
        target_session = _window_to_session(w, pane_sessions)  # hint only; may be None
        dest_key = w  # keep legacy window-keyed delivery channel

    if not text:
        p.error("empty note text")

    inbox_dir.mkdir(parents=True, exist_ok=True)
    assert dest_key is not None
    f = inbox_dir / f"{_safe_filename(dest_key)}.jsonl"

    note = {
        "ts": time.time(),
        "from": _own_window(),
        "priority": args.priority,
        "label": args.label,
        "text": text,
        "origin": args.origin,
        "target_session": target_session,
        "target_window": target_window,
    }
    line = json.dumps(
        {k: v for k, v in note.items() if v is not None}, separators=(",", ":")
    )
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    tgt = target_session or target_window or dest_key
    pending = _pending(inbox_dir, dest_key)
    print(f"noted -> {tgt} ({pending} pending)")
    if target_session:
        print(f"  routed by session id ({target_session[:8]})", file=sys.stderr)
    elif target_window and target_window not in _list_windows():
        print(
            f"  (no live tmux window named {target_window!r} yet -- "
            "it'll be read when one appears)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
