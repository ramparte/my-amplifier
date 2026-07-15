"""Pure delegate-ratio accounting logic for the hooks-delegate-ratio hook.

Kept free of any ``amplifier_core`` imports so it can be unit-tested with a bare
``python3`` interpreter (no framework install required) -- same convention as the
sibling ``hooks-token-warning`` module's ``_logic.py``.

What this measures
-------------------
For a single (top-level) session's own ``events.jsonl``, how much of its own work
was delegated to subagents (``tool_name == "delegate"``) versus done directly via
"heavy" tools (``read_file``, ``grep``, ``glob``, ``bash``) that a subagent could
have done instead.

    ratio = delegates / (delegates + heavy)

A session's ``events.jsonl`` only ever contains that session's OWN ``tool:pre``
events -- a spawned subagent's internal tool calls are logged to the subagent's
own session file under a different session id, never mixed into the parent's
file. So no cross-session filtering is needed to isolate "this session's own
work". We additionally check ``data.parent_id is None`` defensively (matches the
"top-level" framing exactly) in case a future engine version nests call records.

This module does NOT read message/transcript content, only structured event
envelopes (``event``, ``data.tool_name``, ``data.parent_id``) -- token-safe by
construction, no risk of pulling prompt/response bodies into memory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

HEAVY_TOOLS = frozenset({"read_file", "grep", "glob", "bash"})

DEFAULT_RATIO_FLAG_THRESHOLD = 0.40
DEFAULT_HEAVY_FLAG_MIN = 8


@dataclass(frozen=True)
class DelegateRatioResult:
    session_id: str
    turns: int
    delegates: int
    heavy: int
    ratio: float
    flagged: bool


def find_events_path(
    session_id: str, projects_root: Path | str = "~/.amplifier/projects"
) -> Path | None:
    """Locate ``events.jsonl`` for a session id under the projects root.

    Sessions live at ``<projects_root>/<project-slug>/sessions/<session_id>/events.jsonl``.
    The project slug isn't known to a session-lifecycle hook, so we glob for it.
    Returns ``None`` if no match is found (never raises).
    """
    root = Path(projects_root).expanduser()
    if not root.is_dir():
        return None
    matches = sorted(root.glob(f"*/sessions/{session_id}/events.jsonl"))
    if not matches:
        return None
    return matches[0]


def compute_ratio(
    events_path: Path | str,
    *,
    ratio_flag_threshold: float = DEFAULT_RATIO_FLAG_THRESHOLD,
    heavy_flag_min: int = DEFAULT_HEAVY_FLAG_MIN,
    session_id: str | None = None,
) -> DelegateRatioResult:
    """Stream ``events.jsonl`` and tally delegate vs. heavy tool usage and turns.

    Reads the file line-by-line (never loads the whole transcript at once) and
    only inspects the small structured envelope of each JSON line -- ``event``
    and a couple of ``data`` fields -- never message/prompt/response bodies.

    Malformed lines are skipped silently; this is a best-effort instrument, not
    a strict parser. Never raises on missing/malformed data.
    """
    path = Path(events_path).expanduser()
    turns = 0
    delegates = 0
    heavy = 0

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(record, dict):
                continue

            event = record.get("event")
            data = record.get("data")
            if not isinstance(data, dict):
                data = {}

            # Defensive top-level check; in practice a session's own events.jsonl
            # only ever contains its own (parent_id is None) records.
            if data.get("parent_id") is not None:
                continue

            if event == "prompt:submit":
                turns += 1
            elif event == "tool:pre":
                tool_name = data.get("tool_name")
                if tool_name == "delegate":
                    delegates += 1
                elif tool_name in HEAVY_TOOLS:
                    heavy += 1

    denom = delegates + heavy
    ratio = (delegates / denom) if denom else 0.0
    flagged = ratio < ratio_flag_threshold and heavy > heavy_flag_min

    return DelegateRatioResult(
        session_id=session_id or "",
        turns=turns,
        delegates=delegates,
        heavy=heavy,
        ratio=ratio,
        flagged=flagged,
    )


def format_log_line(result: DelegateRatioResult, iso_ts: str) -> str:
    """Format the single log line appended to ``delegate-ratio.log``.

    Example:
        2026-07-14T18:00:00+00:00  session=6bc020e6-...  turns=11  delegates=25  heavy=13  ratio=0.66  OK
    """
    flag = "FLAG" if result.flagged else "OK"
    return (
        f"{iso_ts}  session={result.session_id}  turns={result.turns}  "
        f"delegates={result.delegates}  heavy={result.heavy}  "
        f"ratio={result.ratio:.2f}  {flag}"
    )
