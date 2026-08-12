"""Pure matrix/provider intersection logic for hooks-matrix-guard.

Kept free of any ``amplifier_core``, filesystem, or network imports so it can
be unit-tested with a bare interpreter (no framework install required) --
same convention as the sibling ``hooks-delegate-ratio`` module's
``_logic.py``. All coordinator/filesystem access lives in ``__init__.py``;
this module only ever sees plain dicts/iterables and returns a plain
dataclass and strings.

What this checks
-----------------
Given a routing matrix's ``roles:`` mapping (``role_name -> {description,
candidates: [{provider, model, config?}]}``, per the schema used by
``hooks-routing``'s ``matrix_loader``) and the set of provider names actually
mounted for this session, determine whether each role has at least one
candidate whose ``provider`` is mounted.

This is deliberately a coarse, network-free check: it only inspects the
static ``provider`` field of each candidate. It never resolves glob model
patterns and never calls a provider's ``list_models()`` -- that HTTP-calling
work belongs to ``hooks-routing``'s resolver at actual delegation time, and
is exactly what this diagnostic hook must avoid triggering.

Outcomes
--------
    ok       -- every role has >=1 candidate whose provider is available
                (vacuously true when there are no roles at all -- an empty
                ``roles:`` mapping has nothing that can fail to resolve).
    degraded -- some roles resolve, some do not.
    broken   -- there is at least one role, and NONE of them resolve (the
                matrix and the session share no providers at all).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

Outcome = Literal["ok", "degraded", "broken"]

# "list the unresolvable roles (max 5, then '+N more')" -- per spec.
MAX_ROLES_SHOWN = 5


@dataclass(frozen=True)
class MatrixGuardResult:
    """Result of classifying one matrix's roles against available providers."""

    outcome: Outcome
    total_roles: int
    resolvable_roles: tuple[str, ...]
    unresolvable_roles: tuple[str, ...]
    matrix_providers: frozenset[str]
    available_providers: frozenset[str]


def normalize_provider_name(name: str) -> str:
    """Case-fold a provider name for comparison purposes.

    Provider name comparison is case-insensitive by requirement -- a matrix
    candidate's ``provider: Anthropic`` must match a mounted provider keyed
    as ``anthropic``.
    """
    return name.strip().lower()


def _candidate_providers(role_data: Any) -> list[str]:
    """Extract raw ``provider`` strings from a single role's candidates list.

    Silently skips anything that doesn't look like a candidate mapping --
    e.g. the ``"base"`` override keyword (a bare string, valid only in user
    overrides per ``matrix_loader.compose_matrix``), or a malformed entry.
    This is a best-effort diagnostic, not a strict schema validator, so it
    never raises on unexpected shapes.
    """
    if not isinstance(role_data, dict):
        return []
    candidates = role_data.get("candidates", [])
    if not isinstance(candidates, list):
        return []
    providers: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        provider = candidate.get("provider")
        if isinstance(provider, str) and provider:
            providers.append(provider)
    return providers


def extract_matrix_providers(roles: dict[str, Any]) -> frozenset[str]:
    """Collect every (raw-case) provider name referenced across all roles."""
    if not isinstance(roles, dict):
        return frozenset()
    found: set[str] = set()
    for role_data in roles.values():
        found.update(_candidate_providers(role_data))
    return frozenset(found)


def _role_resolves(role_data: Any, available_normalized: frozenset[str]) -> bool:
    """True if at least one of this role's candidates has a mounted provider."""
    for provider in _candidate_providers(role_data):
        if normalize_provider_name(provider) in available_normalized:
            return True
    return False


def classify_matrix(
    roles: dict[str, Any] | None,
    available_providers: Iterable[Any],
) -> MatrixGuardResult:
    """Classify a matrix's roles against the session's available providers.

    Args:
        roles: Matrix ``roles`` mapping (``role_name -> {description,
            candidates}``). Anything that isn't a ``dict`` (``None``, a
            malformed matrix file, etc.) is treated as an empty matrix --
            this function never raises on bad input.
        available_providers: Iterable of provider names mounted for this
            session (e.g. ``coordinator.get("providers").keys()``).
            Non-string entries are ignored.

    Returns:
        A :class:`MatrixGuardResult` describing which roles resolve, which
        don't, and the overall outcome. Never raises.
    """
    if not isinstance(roles, dict):
        roles = {}

    raw_available = frozenset(p for p in available_providers if isinstance(p, str))
    available_normalized = frozenset(normalize_provider_name(p) for p in raw_available)

    resolvable: list[str] = []
    unresolvable: list[str] = []
    for role_name, role_data in roles.items():
        if _role_resolves(role_data, available_normalized):
            resolvable.append(role_name)
        else:
            unresolvable.append(role_name)

    total = len(roles)
    outcome: Outcome
    if total == 0 or not unresolvable:
        outcome = "ok"
    elif not resolvable:
        outcome = "broken"
    else:
        outcome = "degraded"

    return MatrixGuardResult(
        outcome=outcome,
        total_roles=total,
        resolvable_roles=tuple(resolvable),
        unresolvable_roles=tuple(unresolvable),
        matrix_providers=extract_matrix_providers(roles),
        available_providers=raw_available,
    )


def _format_role_list(roles: tuple[str, ...], max_shown: int = MAX_ROLES_SHOWN) -> str:
    """Render a role list, truncating with ``"+N more"`` beyond *max_shown*."""
    if len(roles) <= max_shown:
        return ", ".join(roles)
    shown = roles[:max_shown]
    remaining = len(roles) - max_shown
    return f"{', '.join(shown)} +{remaining} more"


def format_warning(
    result: MatrixGuardResult,
    matrix_name: str,
    *,
    max_roles_shown: int = MAX_ROLES_SHOWN,
) -> str:
    """Build the human-readable warning body for a degraded/broken result.

    Returns an empty string for an ``ok`` result -- there is nothing to warn
    about, by design (callers should skip logging/injection entirely rather
    than special-case an empty message).
    """
    if result.outcome == "ok":
        return ""

    role_list = _format_role_list(result.unresolvable_roles, max_roles_shown)
    wants = ", ".join(sorted(result.matrix_providers)) or "(none declared)"
    have = ", ".join(sorted(result.available_providers)) or "(none mounted)"

    lines = [
        (
            f"Routing matrix '{matrix_name}' has {len(result.unresolvable_roles)} of "
            f"{result.total_roles} role(s) that cannot resolve to any mounted "
            f"provider: {role_list}"
        ),
        f"Matrix wants providers: {wants} -- session has available: {have}",
    ]

    if result.outcome == "broken":
        lines.append(
            "Remediation: the matrix and this session share NO providers. "
            "Likely fix: run `amplifier routing use <matrix>` (choose a "
            "matrix whose providers match what's configured for this "
            "session), or check for a stale `.amplifier/settings.local.yaml` "
            f"pinning an incompatible matrix (currently '{matrix_name}')."
        )

    return "\n".join(lines)
