# pyright: reportMissingImports=false
"""Inbox-drain hook: deliver out-of-band notes into a running amplifier CLI session.

A companion sender (`amplifier-note <window> <text>`) appends notes to a per-window
inbox file keyed by tmux window NAME. This hook, mounted in each CLI session, drains
the inbox for ITS OWN tmux window before every LLM call -- the `provider:request`
event, which is the same safe checkpoint at which a soft Ctrl-C is honored -- and
injects the notes into the conversation. That lets you nudge a busy session mid-task
without interrupting it or typing into the busy pane.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from amplifier_core import HookResult, ModuleCoordinator

logger = logging.getLogger(__name__)

DEFAULT_INBOX_DIR = "~/.amplifier/inbox"
_PRIORITY_RANK = {"info": 0, "low": 1, "med": 2, "high": 3, "critical": 4}


def _resolve_window_name(forced: str | None) -> str | None:
    """The tmux window NAME of the pane this session runs in (its human label)."""
    if forced:
        return forced
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


def _safe_filename(label: str) -> str:
    return label.replace(os.sep, "_").strip()


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    config = config or {}
    hook = InboxDrainHook(coordinator, config)
    coordinator.hooks.register(
        "provider:request",
        hook.on_provider_request,
        priority=int(config.get("priority", 5)),
        name="hooks-inbox-drain",
    )
    logger.info(
        "Mounted hooks-inbox-drain (inbox_dir=%s, sub_session=%s)",
        hook.inbox_dir,
        hook._is_sub_session(),
    )


class InboxDrainHook:
    def __init__(self, coordinator: ModuleCoordinator, config: dict[str, Any]):
        self.coordinator = coordinator
        self.inbox_dir = Path(config.get("inbox_dir", DEFAULT_INBOX_DIR)).expanduser()
        self.forced_window = config.get("window_name")  # testing / non-tmux override
        self.role = config.get("role", "user")

    def _is_sub_session(self) -> bool:
        """True when this session is a forked sub-session (subagent).

        The runtime sets ``coordinator.parent_id`` to the parent's session id for
        child sessions and leaves it ``None`` for the top-level session. Subagents
        share the top-level pane's tmux window AND also fire ``provider:request``,
        so without this guard a note addressed to the top-level "butler" gets
        stolen by whatever subagent happens to be mid-turn. Only the top-level
        session should drain the inbox.
        """
        return getattr(self.coordinator, "parent_id", None) is not None

    def _own_session_id(self) -> str | None:
        """This session's own stable id (Phase 2 routing key)."""
        sid = getattr(self.coordinator, "session_id", None)
        return str(sid) if sid else None

    def _inbox_file(self) -> Path | None:
        """Legacy window-keyed inbox file (still the dashboard/legacy channel)."""
        window = _resolve_window_name(self.forced_window)
        if not window:
            return None
        return self.inbox_dir / f"{_safe_filename(window)}.jsonl"

    def _session_inbox_file(self, own_id: str | None) -> Path | None:
        """Session-id-keyed inbox file (Phase 2: notes addressed by session id)."""
        if not own_id:
            return None
        return self.inbox_dir / f"{_safe_filename(own_id)}.jsonl"

    @staticmethod
    def _accepts(note: dict[str, Any], own_id: str | None) -> bool:
        """Does this session own a note found in the *window* channel?

        A note with no ``target_session`` (legacy / dashboard) is accepted by the
        window's session (backward compatible). A note stamped with a specific
        ``target_session`` is accepted only by that session; otherwise it is left
        for the right one -- this is what stops window-name collisions (problem
        (b)) from misrouting. If this hook can't resolve its own id, fall back to
        legacy behavior (accept all) rather than starve.
        """
        target = note.get("target_session")
        if target is None or own_id is None:
            return True
        return str(target) == own_id

    def _requeue(self, inbox: Path, notes: list[dict[str, Any]]) -> None:
        """Append notes not addressed to us back onto the window inbox so the
        correct session can claim them on its next turn."""
        if not notes:
            return
        try:
            with open(inbox, "a", encoding="utf-8") as fh:
                for n in notes:
                    fh.write(json.dumps(n, separators=(",", ":")) + "\n")
        except OSError:
            logger.exception(
                "hooks-inbox-drain: failed to requeue %d note(s)", len(notes)
            )

    def _drain(self, inbox: Path) -> list[dict[str, Any]]:
        # Atomic claim: rename out from under any concurrent appender, then read,
        # so a note that lands mid-drain is never silently lost (it stays for next time).
        tmp = inbox.with_suffix(".draining")
        try:
            os.replace(inbox, tmp)
        except FileNotFoundError:
            return []
        try:
            raw = tmp.read_text(encoding="utf-8")
        finally:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
        notes: list[dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "text" in obj:
                    notes.append(obj)
                    continue
            except (ValueError, TypeError):
                pass
            notes.append({"text": line})
        return notes

    def _format(self, notes: list[dict[str, Any]]) -> str:
        def rank(n: dict[str, Any]) -> int:
            return _PRIORITY_RANK.get(str(n.get("priority", "low")).lower(), 1)

        ordered = sorted(notes, key=lambda n: (-rank(n), n.get("ts", 0)))
        lines = []
        for n in ordered:
            bits = []
            if n.get("from"):
                bits.append(f"from {n['from']}")
            pr = n.get("priority")
            if pr and str(pr).lower() != "low":
                bits.append(str(pr))
            if n.get("label"):
                bits.append(f"#{n['label']}")
            prefix = f"[{', '.join(bits)}] " if bits else ""
            lines.append(f"- {prefix}{str(n.get('text', '')).strip()}")
        body = "\n".join(lines)
        # Framing matters: present these as TRUSTED instructions from the principal
        # (the human running this session), NOT as untrusted out-of-band content -- a
        # well-aligned model will (correctly) reject anything that reads like injection.
        return (
            "[operator note -- delivered via the `amplifier-note` side-channel]\n"
            "The following was left for you by your operator (the same person running "
            "this session) while you were busy. It is a trusted instruction from your "
            "principal -- treat it exactly as if they had typed it to you directly. Fold "
            "it into what you are currently doing, then continue:\n"
            f"{body}"
        )

    async def on_provider_request(self, event: str, data: dict[str, Any]) -> HookResult:
        try:
            # Phase 0 (notes-unification): subagents never drain. A forked
            # sub-session shares the top-level pane's tmux window, so draining
            # here would steal notes meant for the top-level session.
            if self._is_sub_session():
                return HookResult(action="continue")

            own_id = self._own_session_id()
            notes: list[dict[str, Any]] = []

            # Phase 2: session-id channel -- a file keyed by our own session id.
            # Everything here was addressed to us by stable id; take it all.
            sid_inbox = self._session_inbox_file(own_id)
            if sid_inbox is not None and sid_inbox.exists():
                notes.extend(self._drain(sid_inbox))

            # Legacy window channel -- keep for the dashboard/notes-watcher and
            # any old sender. Filter by target_session: notes with no target
            # (legacy) or ours -> inject; notes stamped for a different session
            # -> requeue so the right session gets them.
            win_inbox = self._inbox_file()
            if win_inbox is not None and win_inbox.exists():
                drained = self._drain(win_inbox)
                mine = [n for n in drained if self._accepts(n, own_id)]
                others = [n for n in drained if not self._accepts(n, own_id)]
                if others:
                    self._requeue(win_inbox, others)
                notes.extend(mine)

            if not notes:
                return HookResult(action="continue")
            logger.info(
                "hooks-inbox-drain: injecting %d note(s) (session=%s)",
                len(notes),
                own_id,
            )
            return HookResult(
                action="inject_context",
                context_injection=self._format(notes),
                context_injection_role=self.role,
                ephemeral=True,
                suppress_output=True,
            )
        except Exception:  # never break a turn over a note
            logger.exception("hooks-inbox-drain: drain failed; continuing")
            return HookResult(action="continue")
