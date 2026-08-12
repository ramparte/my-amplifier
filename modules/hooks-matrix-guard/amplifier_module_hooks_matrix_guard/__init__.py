# pyright: reportMissingImports=false
"""Matrix-guard hook: warn loudly when the active routing matrix cannot
serve the session's actual providers.

Real incident this prevents: a stale project settings file pinned
``routing: matrix: anthropic`` while the session ran on OpenAI, so every
``model_role`` delegation resolved to zero candidates and failed silently.
``hooks-routing`` unconditionally announces "Active routing matrix: X"
without ever checking that X's candidates intersect the session's
configured providers -- this module fills that gap.

Design
------
On ``session:start``, at a priority *after* ``hooks-routing``'s own
``session:start`` handler (priority 5) so the matrix's ``model_role_resolver``
capability is already registered:

1. Read the active matrix's name off the ``model_role_resolver`` capability
   (``.name`` -- documented as public diagnostic metadata by
   ``resolver_class.MatrixModelRoleResolver``). If no such capability is
   registered, there's nothing to audit -- no-op.
2. Best-effort locate and parse that matrix's YAML file (mirrors
   ``matrix_loader.load_matrix``'s shape: a top-level ``roles:`` mapping) by
   searching the user's custom routing dir first, then any bundle-shipped
   ``routing/`` directory found under the Amplifier cache -- the two
   locations ``hooks-routing`` itself searches. If it can't be found or
   parsed, no-op (this is a diagnostic hook; it must never be the thing that
   breaks a session over a missing file).
3. Read the session's mounted providers the same way ``hooks-routing``
   does: ``coordinator.get("providers") or {}``.
4. Hand the (roles, provider names) pair to the pure ``_logic.classify_matrix``
   to determine OK / DEGRADED / BROKEN, then log accordingly.

Degraded/broken warnings are logged at WARNING immediately, AND queued for a
one-time context injection on the next ``provider:request`` -- mirroring
``hooks-routing``'s own "Active routing matrix: X" injection mechanism, but
injected at most once per session (tracked on the hook instance) rather than
every request.

This never resolves glob model patterns and never calls a provider's
``list_models()`` -- no network calls are made anywhere in this module.

Config knobs (all optional):
    enabled:            bool = True   -- master switch
    fail_on_broken:      bool = False  -- raise at session start on BROKEN
                                          instead of warning (never aborts by
                                          default)
    priority:            int  = 10    -- handler priority (session:start AND
                                          provider:request both use this)
    custom_routing_dir:  str  = "~/.amplifier/routing"
                                        -- user's custom/override matrix dir,
                                          searched first (not in the original
                                          spec's 3-key list; added because
                                          locating the matrix YAML requires
                                          knowing where to look -- see
                                          IMPLEMENTATION NOTES in the repo
                                          for why this couldn't be avoided)
    bundle_cache_glob:   str  = "~/.amplifier/cache/*/routing"
                                        -- glob pattern for bundle-shipped
                                          routing/ directories (same caveat
                                          as above)
"""

from __future__ import annotations

import glob
import logging
from pathlib import Path
from typing import Any

import yaml
from amplifier_core import HookResult, ModuleCoordinator

from ._logic import classify_matrix, format_warning

logger = logging.getLogger(__name__)

DEFAULT_CUSTOM_ROUTING_DIR = "~/.amplifier/routing"
DEFAULT_BUNDLE_CACHE_GLOB = "~/.amplifier/cache/*/routing"
DEFAULT_PRIORITY = 10


class _FailOnBroken(RuntimeError):
    """Raised from ``_audit`` only when ``fail_on_broken`` is set and the
    matrix is BROKEN. Deliberately allowed to propagate out of
    ``on_session_start`` -- this is the one case where the hook is meant to
    abort the session rather than silently continue. It is NOT caught by the
    broad ``except Exception`` in ``on_session_start`` (checked first).
    """


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    """Mount the matrix-guard hook.

    Registers a ``session:start`` handler (audits the active matrix against
    mounted providers) and a ``provider:request`` handler (delivers at most
    one queued warning as context injection).
    """
    config = config or {}
    if not config.get("enabled", True):
        logger.info("hooks-matrix-guard disabled via config; not registering")
        return

    hook = MatrixGuardHook(coordinator, config)
    priority = int(config.get("priority", DEFAULT_PRIORITY))

    coordinator.hooks.register(
        "session:start",
        hook.on_session_start,
        priority=priority,
        name="matrix-guard-audit",
    )
    coordinator.hooks.register(
        "provider:request",
        hook.on_provider_request,
        priority=priority,
        name="matrix-guard-inject",
    )
    logger.info(
        "Mounted hooks-matrix-guard (priority=%s, fail_on_broken=%s)",
        priority,
        hook.fail_on_broken,
    )


class MatrixGuardHook:
    def __init__(self, coordinator: ModuleCoordinator, config: dict[str, Any]):
        self.coordinator = coordinator
        self.fail_on_broken = bool(config.get("fail_on_broken", False))
        self.custom_routing_dir = Path(
            config.get("custom_routing_dir", DEFAULT_CUSTOM_ROUTING_DIR)
        ).expanduser()
        self.bundle_cache_glob = str(
            config.get("bundle_cache_glob", DEFAULT_BUNDLE_CACHE_GLOB)
        )
        self._pending_warning: str | None = None
        self._injected = False

    async def on_session_start(self, event: str, data: dict[str, Any]) -> HookResult:
        """Audit the active matrix against mounted providers.

        Never raises, EXCEPT when ``fail_on_broken`` is set and the matrix is
        BROKEN -- that is the one deliberate, user-opted-in abort path. Any
        other failure (missing capability, missing/unparsable YAML, unexpected
        shape) is caught and logged at DEBUG; the hook then no-ops.
        """
        try:
            self._audit()
        except _FailOnBroken:
            raise
        except Exception:
            logger.debug(
                "hooks-matrix-guard: audit failed unexpectedly; no-op",
                exc_info=True,
            )
        return HookResult(action="continue")

    def _audit(self) -> None:
        resolver = (
            self.coordinator.get_capability("model_role_resolver")
            if hasattr(self.coordinator, "get_capability")
            else None
        )
        if resolver is None:
            logger.debug(
                "hooks-matrix-guard: no model_role_resolver capability "
                "registered (no routing matrix active); nothing to audit"
            )
            return

        matrix_name = getattr(resolver, "name", None) or "unknown"
        roles = self._load_matrix_roles(matrix_name)
        if roles is None:
            logger.debug(
                "hooks-matrix-guard: could not locate/parse matrix '%s'; "
                "skipping audit",
                matrix_name,
            )
            return

        providers = self.coordinator.get("providers") or {}
        result = classify_matrix(roles, providers.keys())

        if result.outcome == "ok":
            logger.debug(
                "hooks-matrix-guard: matrix '%s' OK -- all %d role(s) "
                "resolve to a mounted provider",
                matrix_name,
                result.total_roles,
            )
            return

        message = format_warning(result, matrix_name)
        logger.warning("hooks-matrix-guard: %s", message)
        # Queued for a single context injection at the next provider:request
        # -- see on_provider_request below.
        self._pending_warning = f"[routing matrix warning]\n{message}"

        if result.outcome == "broken" and self.fail_on_broken:
            raise _FailOnBroken(message)

    def _load_matrix_roles(self, matrix_name: str) -> dict[str, Any] | None:
        """Best-effort YAML load of the named matrix's ``roles:`` mapping.

        Searches the user's custom routing dir first (matches
        ``hooks-routing``'s override priority: custom dirs win), then any
        bundle-shipped ``routing/`` directory found under the Amplifier
        cache. Returns ``None`` on any failure -- missing file, unreadable
        YAML, wrong shape -- never raises.
        """
        search_paths: list[Path] = [self.custom_routing_dir / f"{matrix_name}.yaml"]
        try:
            cache_hits = sorted(
                glob.glob(str(Path(self.bundle_cache_glob).expanduser()))
            )
        except OSError:
            cache_hits = []
        for hit in cache_hits:
            search_paths.append(Path(hit) / f"{matrix_name}.yaml")

        for path in search_paths:
            try:
                if not path.is_file():
                    continue
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except (OSError, yaml.YAMLError):
                continue
            if not isinstance(data, dict):
                continue
            roles = data.get("roles", {})
            return roles if isinstance(roles, dict) else {}

        return None

    async def on_provider_request(self, event: str, data: dict[str, Any]) -> HookResult:
        """Deliver the queued warning (if any) as context injection, once."""
        if not self._pending_warning or self._injected:
            return HookResult(action="continue")
        try:
            self._injected = True
            return HookResult(
                action="inject_context",
                context_injection=self._pending_warning,
                ephemeral=True,
            )
        except Exception:
            logger.debug("hooks-matrix-guard: injection failed; no-op", exc_info=True)
            return HookResult(action="continue")
