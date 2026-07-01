# pyright: reportMissingImports=false
"""Token-warning hook: surface a CLI-visible warning when a turn's effective input
token count crosses a configured budget.

Registers on ``llm:response`` -- emitted by the provider module after every LLM call
with a normalized ``usage`` dict. ``usage.input_tokens`` on that event already reflects
the entire prompt sent for that call (system + history + tools), so checking it per call
is the correct granularity for a "context is getting large" warning.

The warning goes to the human via ``HookResult.user_message`` (UI-only; it does NOT
touch the agent's context). It escalates once per budget band (see ``_logic.band_for``)
so a long session is nudged at the budget and again each time context grows by another
``step`` -- never every single turn.

Config knobs (all optional):
    enabled:          bool  = True     -- master switch
    threshold:        int   = 75000    -- budget in tokens
    step:             int   = threshold -- re-warn interval above the budget
    count_cache_read: bool  = False    -- add cache-read tokens (see _logic docstring)
    count_cache_write:bool  = True     -- add cache-write/creation tokens
    user_message_level:str  = "warning" -- "info" | "warning" | "error"
    priority:         int   = 50
"""

from __future__ import annotations

import logging
from typing import Any

from amplifier_core import HookResult, ModuleCoordinator

from ._logic import band_for, effective_input_tokens, format_warning

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 75_000


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    config = config or {}
    if not config.get("enabled", True):
        logger.info("hooks-token-warning disabled via config; not registering")
        return
    hook = TokenWarningHook(coordinator, config)
    coordinator.hooks.register(
        "llm:response",
        hook.on_llm_response,
        priority=int(config.get("priority", 50)),
        name="hooks-token-warning",
    )
    logger.info(
        "Mounted hooks-token-warning (threshold=%d, step=%d)",
        hook.threshold,
        hook.step,
    )


class TokenWarningHook:
    def __init__(self, coordinator: ModuleCoordinator, config: dict[str, Any]):
        self.coordinator = coordinator
        self.threshold = int(config.get("threshold", DEFAULT_THRESHOLD))
        self.step = int(config.get("step", self.threshold) or self.threshold)
        self.count_cache_read = bool(config.get("count_cache_read", False))
        self.count_cache_write = bool(config.get("count_cache_write", True))
        self.level = str(config.get("user_message_level", "warning"))
        # Highest band we've already warned about this session (hysteresis: only
        # warn when we cross UP into a new band, never repeat the same band).
        self._last_warned_band = 0

    async def on_llm_response(self, event: str, data: dict[str, Any]) -> HookResult:
        try:
            usage = data.get("usage")
            if not isinstance(usage, dict):
                return HookResult(action="continue")

            effective = effective_input_tokens(
                usage,
                count_cache_read=self.count_cache_read,
                count_cache_write=self.count_cache_write,
            )
            band = band_for(effective, self.threshold, self.step)

            if band > self._last_warned_band:
                self._last_warned_band = band
                logger.info(
                    "hooks-token-warning: effective input %d crossed budget %d (band %d)",
                    effective,
                    self.threshold,
                    band,
                )
                return HookResult(
                    action="continue",
                    user_message=format_warning(
                        effective, self.threshold, data.get("model")
                    ),
                    user_message_level=self.level,
                    user_message_source="hooks-token-warning",
                )

            return HookResult(action="continue")
        except Exception:  # never break a turn over a warning
            logger.exception("hooks-token-warning: check failed; continuing")
            return HookResult(action="continue")
