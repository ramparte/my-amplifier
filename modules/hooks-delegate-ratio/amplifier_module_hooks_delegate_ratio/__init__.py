# pyright: reportMissingImports=false
"""Delegate-ratio hook: LOG-ONLY instrument of subagent delegation vs. inline heavy work.

CRITICAL DESIGN CONSTRAINT: this hook never injects anything into the model's
context and never surfaces a message to the CLI. It is pure observability --
one line appended to a log file per session. Contrast with the sibling
``hooks-token-warning`` module, which deliberately uses an OBSERVE -> SURFACE
two-phase pattern to inject a ``<system-reminder>``. This hook has no SURFACE
phase at all: it registers a single handler on ``session:end`` that writes to
disk and returns ``HookResult(action="continue")`` unconditionally. There is no
code path in this module that can inject context, emit a system-reminder, or
otherwise nag the user or the model -- there is no ``context_injection`` field
set anywhere below.

What it measures
-----------------
On ``session:end`` (fired once, at session cleanup -- see
``amplifier_core.session.AmplifierSession.cleanup()``), the hook:

  1. Reads ``session_id`` from the event payload (the only two fields
     ``SESSION_END`` carries are ``session_id`` and ``status``).
  2. Locates that session's own ``events.jsonl`` by globbing
     ``<projects_root>/*/sessions/<session_id>/events.jsonl`` (the project slug
     isn't in the event payload, so it must be discovered).
  3. Streams that file (never loads message/transcript bodies -- only the small
     structured ``event``/``data.tool_name``/``data.parent_id`` envelope of each
     line) to tally:
       - turns    = count of this session's own ``prompt:submit`` events
       - delegates = count of ``tool:pre`` events where ``tool_name == "delegate"``
       - heavy     = count of ``tool:pre`` events where ``tool_name`` is one of
                     ``read_file``, ``grep``, ``glob``, ``bash``
     and computes ``ratio = delegates / (delegates + heavy)``.
  4. Appends exactly one line to the log file (default
     ``~/.amplifier/delegate-ratio.log``).

Nothing computed here is ever returned to the coordinator as anything other
than ``action="continue"``. No per-turn hook is registered -- this fires once,
at the natural end of the session's life, so there is no possibility of
per-turn nagging.

Config knobs (all optional):
    enabled:              bool  = True                          -- master switch
    log_path:             str   = "~/.amplifier/delegate-ratio.log"
    projects_root:        str   = "~/.amplifier/projects"
    ratio_flag_threshold: float = 0.40  -- FLAG when ratio is below this...
    heavy_flag_min:       int   = 8     -- ...AND heavy count exceeds this
    priority:             int   = 60    -- handler priority for session:end
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from amplifier_core import HookResult, ModuleCoordinator

from ._logic import (
    DEFAULT_HEAVY_FLAG_MIN,
    DEFAULT_RATIO_FLAG_THRESHOLD,
    compute_ratio,
    find_events_path,
    format_log_line,
)

logger = logging.getLogger(__name__)

DEFAULT_LOG_PATH = "~/.amplifier/delegate-ratio.log"
DEFAULT_PROJECTS_ROOT = "~/.amplifier/projects"


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    config = config or {}
    if not config.get("enabled", True):
        logger.info("hooks-delegate-ratio disabled via config; not registering")
        return
    hook = DelegateRatioHook(config)
    priority = int(config.get("priority", 60))
    # Fires ONCE at session end. No per-turn hook is registered anywhere in
    # this module -- there is no risk of this becoming a per-turn nag.
    coordinator.hooks.register(
        "session:end",
        hook.on_session_end,
        priority=priority,
        name="hooks-delegate-ratio-log",
    )
    logger.info(
        "Mounted hooks-delegate-ratio (log_path=%s, log-only, no context injection)",
        hook.log_path,
    )


class DelegateRatioHook:
    def __init__(self, config: dict[str, Any]):
        self.log_path = Path(config.get("log_path", DEFAULT_LOG_PATH)).expanduser()
        self.projects_root = Path(
            config.get("projects_root", DEFAULT_PROJECTS_ROOT)
        ).expanduser()
        self.ratio_flag_threshold = float(
            config.get("ratio_flag_threshold", DEFAULT_RATIO_FLAG_THRESHOLD)
        )
        self.heavy_flag_min = int(config.get("heavy_flag_min", DEFAULT_HEAVY_FLAG_MIN))

    async def on_session_end(self, event: str, data: dict[str, Any]) -> HookResult:
        """LOG-ONLY. Always returns ``continue``. Never injects, never surfaces."""
        try:
            session_id = data.get("session_id")
            if not session_id:
                return HookResult(action="continue")

            events_path = find_events_path(session_id, self.projects_root)
            if events_path is None:
                logger.debug(
                    "hooks-delegate-ratio: no events.jsonl found for session %s "
                    "under %s; skipping",
                    session_id,
                    self.projects_root,
                )
                return HookResult(action="continue")

            result = compute_ratio(
                events_path,
                ratio_flag_threshold=self.ratio_flag_threshold,
                heavy_flag_min=self.heavy_flag_min,
                session_id=session_id,
            )
            line = format_log_line(result, _iso_now())

            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

            logger.info(
                "hooks-delegate-ratio: wrote log line for session %s", session_id
            )
        except Exception:  # never break session teardown over a log write
            logger.exception("hooks-delegate-ratio: failed to record delegate ratio")
        return HookResult(action="continue")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()
