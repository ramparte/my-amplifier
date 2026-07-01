"""Standalone tests for the pure token-accounting logic.

Runs with a bare interpreter: ``python3 tests/test_logic.py`` (no framework install,
no pytest required). Exits non-zero on the first failed assertion.
"""

from __future__ import annotations

import os
import sys

# Import the pure-logic module directly (by path) so we never execute the package
# __init__.py, which imports amplifier_core. This keeps the test framework-free.
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "amplifier_module_hooks_token_warning"
    ),
)

from _logic import (  # noqa: E402
    band_for,
    effective_input_tokens,
    format_warning,
)


def test_effective_matches_audited_opening_prompt() -> None:
    # Real emitted shape for the audited opening turn:
    #   input_tokens already folds in cache_read (2 + 20,120 = 20,122)
    #   cache_write (creation) = 25,329 (NOT in input_tokens)
    usage = {
        "input_tokens": 20_122,
        "cache_read_tokens": 20_120,
        "cache_write_tokens": 25_329,
        "output_tokens": 82,
    }
    # Default (cache_write only) reproduces the true 45,451 context size.
    assert effective_input_tokens(usage) == 45_451
    # Counting cache_read too would double-count -> demonstrably wrong.
    assert effective_input_tokens(usage, count_cache_read=True) == 65_571


def test_effective_handles_missing_and_none() -> None:
    assert effective_input_tokens({}) == 0
    assert (
        effective_input_tokens({"input_tokens": None, "cache_write_tokens": None}) == 0
    )
    assert effective_input_tokens({"input_tokens": 100}) == 100  # no cache fields


def test_band_thresholds() -> None:
    threshold, step = 75_000, 75_000
    assert band_for(0, threshold, step) == 0
    assert band_for(74_999, threshold, step) == 0
    assert band_for(75_000, threshold, step) == 1
    assert band_for(120_000, threshold, step) == 1
    assert band_for(150_000, threshold, step) == 2
    assert band_for(300_000, threshold, step) == 4


def test_band_zero_step_is_safe() -> None:
    assert band_for(80_000, 75_000, 0) == 1  # no ZeroDivisionError


def test_warns_once_per_band_progression() -> None:
    # Simulate a growing session: warn only when crossing into a new band.
    threshold, step = 75_000, 75_000
    last = 0
    warned_at = []
    for effective in (40_000, 60_000, 80_000, 90_000, 160_000, 170_000):
        band = band_for(effective, threshold, step)
        if band > last:
            last = band
            warned_at.append(effective)
    assert warned_at == [80_000, 160_000]  # not 90k (same band), not 170k (same band)


def test_format_warning_contains_numbers() -> None:
    msg = format_warning(120_000, 75_000, "claude-opus-4")
    assert "120,000" in msg
    assert "75,000" in msg
    assert "claude-opus-4" in msg


def _run() -> int:
    tests = [
        v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run())
