#!/usr/bin/env python3
"""Lint: fail if a "lean" bundle transitively composes the FULL amplifier-foundation.

Background
----------
The lean bundle exists to compose only a curated subset. A prior regression pulled in
the ENTIRE ``foundation`` bundle transitively (via a settings.yaml ``app:`` layer that
composed the full context-intelligence bundle), re-adding design-intelligence,
browser-tester, amplifier-tester, routing-matrix, full python-dev+tool-lsp, etc. -- and
clobbering the lean compaction threshold. Opening prompts ballooned to 200K-600K tokens.

This guard inspects Amplifier's already-materialized composition graph
(``~/.amplifier/registry.json``) and fails if the literal node named ``foundation``
(the full bundle root) is reachable from the target bundle's ``includes``. Scoped
lean behaviors from the same repo (e.g. ``exp-lean-amplifier-dev``,
``lean-foundation-behavior``) have ``root_name == foundation`` but are NOT the full
bundle node -- so we key strictly on the node whose own ``name == "foundation"``.

It also flags a settings.yaml ``app:`` layer, since that was the exact injection vector.

Usage
-----
    python3 scripts/check-lean-no-foundation.py [BUNDLE_NAME]
    python3 scripts/check-lean-no-foundation.py --forbid foundation
    python3 scripts/check-lean-no-foundation.py --registry /path/registry.json

If BUNDLE_NAME is omitted it defaults to ``bundle.active`` from settings.yaml.

Exit codes: 0 = clean, 1 = violation found, 2 = usage/environment error.
Dependency-free (stdlib only; PyYAML used opportunistically for the settings check).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import deque
from pathlib import Path
from typing import Any, NoReturn

DEFAULT_REGISTRY = "~/.amplifier/registry.json"
DEFAULT_SETTINGS = "~/.amplifier/settings.yaml"
FORBIDDEN_DEFAULT = "foundation"
FORBIDDEN_REPO = "amplifier-foundation"

# A bundle include line, e.g.:  "- bundle: git+https://.../amplifier-foundation@main#subdirectory=..."
_INCLUDE_RE = re.compile(r"bundle:\s*(?P<uri>\S+)")


def _load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        _die(f"registry not found: {path}", code=2)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        _die(f"could not read registry {path}: {e}", code=2)
    # Some layouts nest under a "bundles" key; accept either.
    reg = data.get("bundles") if isinstance(data, dict) and "bundles" in data else data
    if not isinstance(reg, dict):
        _die(f"unexpected registry shape in {path}", code=2)
    return reg


def _find_path_to_forbidden(
    reg: dict[str, Any], start: str, forbidden: str
) -> list[str] | None:
    """BFS over forward ``includes`` edges; return a start->forbidden path, or None.

    Matches the forbidden node by registry KEY == forbidden OR the entry's own
    ``name`` == forbidden (the full-bundle root), never merely ``root_name``.
    """

    def _is_forbidden(node_key: str) -> bool:
        if node_key == forbidden:
            return True
        entry = reg.get(node_key)
        return isinstance(entry, dict) and entry.get("name") == forbidden

    if start not in reg:
        _die(
            f"bundle '{start}' is not in the registry (not loaded/added yet). "
            f"Add or activate it first, or pass an explicit BUNDLE_NAME.",
            code=2,
        )

    # start itself being the forbidden bundle is trivially a violation
    if _is_forbidden(start):
        return [start]

    parents: dict[str, str] = {start: ""}
    q: deque[str] = deque([start])
    while q:
        cur = q.popleft()
        entry = reg.get(cur) or {}
        for child in entry.get("includes") or []:
            if child in parents:
                continue
            parents[child] = cur
            if _is_forbidden(child):
                # reconstruct path
                path = [child]
                node = cur
                while node:
                    path.append(node)
                    node = parents.get(node, "")
                return list(reversed(path))
            q.append(child)
    return None


def _static_check(files: list[Path], forbidden_repo: str = FORBIDDEN_REPO) -> list[str]:
    """Registry-free source scan (CI-friendly): flag bare full-foundation includes.

    A bundle include that points at the ``amplifier-foundation`` repo WITHOUT a
    ``#subdirectory=`` fragment pulls in the ENTIRE foundation bundle. With a
    ``#subdirectory=`` fragment it is a scoped nested bundle (e.g. the lean experiment
    or a single behavior), which is fine. Returns a list of violation messages.
    """
    violations: list[str] = []
    for f in files:
        if not f.exists():
            violations.append(f"{f}: file not found")
            continue
        for lineno, line in enumerate(
            f.read_text(encoding="utf-8").splitlines(), start=1
        ):
            stripped = line.strip()
            if not stripped.startswith(("- bundle:", "bundle:")):
                continue
            m = _INCLUDE_RE.search(stripped)
            if not m:
                continue
            uri = m.group("uri").strip().strip("\"'")
            if forbidden_repo in uri and "#subdirectory=" not in uri:
                violations.append(
                    f"{f}:{lineno}: bare full-foundation include (no #subdirectory=): {uri}"
                )
    return violations


def _load_settings(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _check_settings_app_layer(settings: dict[str, Any] | None) -> list[str]:
    """Return warnings about known bloat vectors in settings.yaml."""
    warnings: list[str] = []
    if not isinstance(settings, dict):
        return warnings
    bundle = settings.get("bundle") if isinstance(settings.get("bundle"), dict) else {}
    # An `app:` layer (top-level or under bundle:) is the exact vector that caused the
    # regression -- it composes a full bundle ON TOP of the active lean bundle.
    if "app" in settings or (isinstance(bundle, dict) and "app" in bundle):
        warnings.append(
            "settings.yaml declares an `app:` layer -- this composes a bundle ON TOP "
            "of the active bundle and was the original bloat vector. Verify it does not "
            "pull in full foundation."
        )
    return warnings


def _die(msg: str, code: int = 2) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "bundle", nargs="?", help="bundle name (default: settings bundle.active)"
    )
    ap.add_argument(
        "--forbid", default=FORBIDDEN_DEFAULT, help="forbidden bundle node name"
    )
    ap.add_argument(
        "--registry", default=DEFAULT_REGISTRY, help="path to registry.json"
    )
    ap.add_argument(
        "--settings", default=DEFAULT_SETTINGS, help="path to settings.yaml"
    )
    ap.add_argument(
        "--static",
        nargs="+",
        metavar="FILE",
        help="registry-free source scan: flag bare full-foundation includes in these "
        "bundle files (CI mode)",
    )
    ap.add_argument(
        "--allow-missing-registry",
        action="store_true",
        help="exit 0 with a notice when registry.json is absent (CI/portable environments)",
    )
    args = ap.parse_args(argv)

    # Static source scan (registry-free) -- for CI / pre-commit where no materialized
    # registry exists. Runs and returns without touching the graph.
    if args.static:
        files = [Path(os.path.expanduser(p)) for p in args.static]
        violations = _static_check(files)
        if not violations:
            print(
                f"OK (static): no bare full-'{FORBIDDEN_REPO}' includes in "
                f"{len(files)} file(s)."
            )
            return 0
        print("FAIL (static): bare full-foundation include(s) found:")
        for v in violations:
            print(f"  {v}")
        return 1

    registry_path = Path(os.path.expanduser(args.registry))
    if args.allow_missing_registry and not registry_path.exists():
        print(
            f"notice: registry not found ({registry_path}); "
            f"skipping graph check (allowed)."
        )
        return 0
    reg = _load_registry(registry_path)
    settings = _load_settings(Path(os.path.expanduser(args.settings)))

    target = args.bundle
    if not target:
        b = settings.get("bundle") if isinstance(settings, dict) else None
        target = b.get("active") if isinstance(b, dict) else None
        if not target:
            _die(
                "no bundle given and could not read bundle.active from settings.yaml",
                code=2,
            )

    app_warnings = _check_settings_app_layer(settings)
    for w in app_warnings:
        print(f"warning: {w}")

    path = _find_path_to_forbidden(reg, target, args.forbid)
    if path is None:
        print(f"OK: '{target}' does not transitively compose '{args.forbid}'.")
        return 0

    print()
    print(f"FAIL: '{target}' transitively composes the full '{args.forbid}' bundle.")
    print("      composition chain:")
    for i, node in enumerate(path):
        print(f"        {'  ' * i}{'└─ ' if i else ''}{node}")
    print()
    print(
        "      A lean bundle must not pull in full foundation. Check the include that"
    )
    print(
        "      leads to it (and any settings.yaml `app:` layer). See the handoff notes."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
