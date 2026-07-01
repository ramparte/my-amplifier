# pyright: reportMissingImports=false
"""Token-warning hook: warn when a turn's effective input token count crosses a budget.

Delivery is a two-phase OBSERVE -> SURFACE pattern, dictated by a real constraint in
the engine: ``llm:response`` (the only event carrying per-turn token usage) is a
provider-emitted, fire-and-forget event -- the dispatcher discards whatever a handler
returns, so a ``HookResult`` produced there (``user_message`` OR ``context_injection``)
never reaches the CLI. ``provider:request`` return values, by contrast, ARE consumed and
injected (this is exactly how the sibling ``hooks-inbox-drain`` works). So:

  1. OBSERVE on ``llm:response``: read the normalized ``usage`` dict, compute the
     effective input size, and if it crosses a NEW budget band, stash a pending
     warning. (The return value here is intentionally ignored by the engine.)
  2. SURFACE on ``provider:request`` (fires at the start of the next LLM call): if a
     warning is pending, inject it as an ephemeral ``<system-reminder>`` so the agent
     sees it and relays it to the user, then clear it.

Net effect: crossing the budget on turn N surfaces at the top of turn N+1 -- a one-turn
deferral, which is fine for a budget nudge. Escalates once per band (see
``_logic.band_for``): nudged at the budget and again each time context grows by another
``step`` -- never every turn.

Config knobs (all optional):
    enabled:           bool = True      -- master switch
    threshold:         int  = 75000     -- budget in tokens
    step:              int  = threshold -- re-warn interval above the budget
    count_cache_read:  bool = False     -- add cache-read tokens (see _logic docstring)
    count_cache_write: bool = True      -- add cache-write/creation tokens
    priority:          int  = 60        -- handler priority for both events
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
    priority = int(config.get("priority", 60))
    # OBSERVE: record usage after each LLM call (return value ignored by the engine).
    coordinator.hooks.register(
        "llm:response",
        hook.on_llm_response,
        priority=priority,
        name="hooks-token-warning-observe",
    )
    # SURFACE: inject any pending warning at the start of the next LLM call.
    coordinator.hooks.register(
        "provider:request",
        hook.on_provider_request,
        priority=priority,
        name="hooks-token-warning-surface",
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
        # Highest band we've already warned about this session (hysteresis: only
        # warn when we cross UP into a new band, never repeat the same band).
        self._last_warned_band = 0
        # A one-line warning waiting to be surfaced on the next provider:request.
        self._pending_warning: str | None = None

    async def on_llm_response(self, event: str, data: dict[str, Any]) -> HookResult:
        """OBSERVE phase: record usage; queue a warning when a new band is crossed."""
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
                self._pending_warning = format_warning(
                    effective, self.threshold, data.get("model")
                )
                logger.info(
                    "hooks-token-warning: effective input %d crossed budget %d "
                    "(band %d); queued for next provider:request",
                    effective,
                    self.threshold,
                    band,
                )
        except Exception:  # never break a turn over a warning
            logger.exception("hooks-token-warning: observe failed; continuing")
        return HookResult(action="continue")

    async def on_provider_request(self, event: str, data: dict[str, Any]) -> HookResult:
        """SURFACE phase: inject any queued warning as an ephemeral system-reminder."""
        try:
            if not self._pending_warning:
                return HookResult(action="continue")
            warning = self._pending_warning
            self._pending_warning = None
            injection = (
                '<system-reminder source="hooks-token-warning">\n'
                f"{warning}\n"
                "Surface this to the user in your next message and suggest they run "
                "/compact, start a fresh session, or trim context. This is a system "
                "notice about context size, not user input.\n"
                "</system-reminder>"
            )
            logger.info("hooks-token-warning: surfacing queued budget warning")
            return HookResult(
                action="inject_context",
                context_injection=injection,
                context_injection_role="user",
                ephemeral=True,
                suppress_output=True,
            )
        except Exception:  # never break a turn over a warning
            logger.exception("hooks-token-warning: surface failed; continuing")
            return HookResult(action="continue")
