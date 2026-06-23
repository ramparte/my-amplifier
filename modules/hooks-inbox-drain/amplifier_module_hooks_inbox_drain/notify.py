#!/usr/bin/env python3
"""amplifier-note: drop a note into a running amplifier CLI session's inbox.

Usage:
    amplifier-note <window> <text...> [-p PRIORITY] [-l LABEL]
    amplifier-note --list

<window> is the tmux window NAME of the target session (the label in your tmux
status line). The target session's inbox-drain hook reads the note before its next
LLM call and folds it into whatever it is doing -- no need to interrupt it or type
into the busy pane.

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
PRIORITIES = ["info", "low", "med", "high", "critical"]


def _safe_filename(label: str) -> str:
    return label.replace(os.sep, "_").strip()


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
        description="Drop a note into a running amplifier session's inbox (by tmux window name).",
    )
    p.add_argument("window", nargs="?", help="target tmux window name")
    p.add_argument("text", nargs="*", help="note text")
    p.add_argument("-p", "--priority", choices=PRIORITIES, default="low")
    p.add_argument("-l", "--label", default=None, help="optional card label / tag")
    p.add_argument("--inbox-dir", default=os.environ.get("AMPLIFIER_INBOX_DIR", DEFAULT_INBOX_DIR))
    p.add_argument(
        "--list", action="store_true", help="list active tmux windows + pending note counts"
    )
    args = p.parse_args(argv)

    inbox_dir = Path(args.inbox_dir).expanduser()

    if args.list:
        wins = _list_windows()
        if not wins:
            print("(no tmux windows found / not in tmux)")
            return 0
        for w in wins:
            print(f"{w}\t({_pending(inbox_dir, w)} pending)")
        return 0

    if not args.window or not args.text:
        p.error("need <window> and <text> (or --list)")

    text = " ".join(args.text).strip()
    if not text:
        p.error("empty note text")

    inbox_dir.mkdir(parents=True, exist_ok=True)
    f = inbox_dir / f"{_safe_filename(args.window)}.jsonl"

    note = {
        "ts": time.time(),
        "from": _own_window(),
        "priority": args.priority,
        "label": args.label,
        "text": text,
    }
    line = json.dumps({k: v for k, v in note.items() if v is not None}, separators=(",", ":"))
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    print(f"noted -> {args.window} ({_pending(inbox_dir, args.window)} pending)")
    if args.window not in _list_windows():
        print(
            f"  (no live tmux window named {args.window!r} yet -- it'll be read when one appears)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
