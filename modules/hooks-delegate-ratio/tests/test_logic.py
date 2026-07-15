"""Standalone tests for the pure delegate-ratio accounting logic.

Runs with a bare interpreter: ``python3 tests/test_logic.py`` (no framework
install, no pytest required). Exits non-zero on the first failed assertion.
Mirrors the convention used by the sibling ``hooks-token-warning`` module.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Import the pure-logic module directly (by path) so we never execute the
# package __init__.py, which imports amplifier_core. Keeps this test
# framework-free.
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "amplifier_module_hooks_delegate_ratio"
    ),
)

from _logic import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    compute_ratio,
    find_events_path,
    format_log_line,
)


def _write_events(lines: list[dict]) -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    )
    for rec in lines:
        tmp.write(json.dumps(rec) + "\n")
    tmp.close()
    return Path(tmp.name)


def test_basic_counts_and_ratio() -> None:
    events = (
        [{"event": "prompt:submit", "data": {"parent_id": None}}] * 2
        + [{"event": "tool:pre", "data": {"parent_id": None, "tool_name": "delegate"}}]
        * 3
        + [{"event": "tool:pre", "data": {"parent_id": None, "tool_name": "bash"}}] * 1
        + [{"event": "tool:pre", "data": {"parent_id": None, "tool_name": "read_file"}}]
        * 1
    )
    path = _write_events(events)
    try:
        result = compute_ratio(path, session_id="abc")
        assert result.turns == 2
        assert result.delegates == 3
        assert result.heavy == 2
        assert abs(result.ratio - 0.6) < 1e-9
        assert result.flagged is False  # heavy (2) not > 8
    finally:
        path.unlink()


def test_flag_fires_only_when_both_conditions_met() -> None:
    # Low ratio but low heavy count -> not flagged.
    events_low_heavy = [
        {"event": "tool:pre", "data": {"parent_id": None, "tool_name": "delegate"}}
    ] + [{"event": "tool:pre", "data": {"parent_id": None, "tool_name": "bash"}}] * 3
    path = _write_events(events_low_heavy)
    try:
        result = compute_ratio(path, ratio_flag_threshold=0.40, heavy_flag_min=8)
        assert result.ratio == 0.25
        assert result.heavy == 3
        assert result.flagged is False  # heavy not > 8
    finally:
        path.unlink()

    # Low ratio AND heavy > 8 -> flagged.
    events_flagged = [
        {"event": "tool:pre", "data": {"parent_id": None, "tool_name": "delegate"}}
    ] + [{"event": "tool:pre", "data": {"parent_id": None, "tool_name": "bash"}}] * 9
    path2 = _write_events(events_flagged)
    try:
        result2 = compute_ratio(path2, ratio_flag_threshold=0.40, heavy_flag_min=8)
        assert result2.heavy == 9
        assert result2.ratio == 0.1
        assert result2.flagged is True
    finally:
        path2.unlink()


def test_no_activity_is_safe() -> None:
    path = _write_events([])
    try:
        result = compute_ratio(path)
        assert result.turns == 0
        assert result.delegates == 0
        assert result.heavy == 0
        assert result.ratio == 0.0
        assert result.flagged is False  # heavy (0) not > 8
    finally:
        path.unlink()


def test_malformed_lines_are_skipped() -> None:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    )
    tmp.write("not json at all\n")
    tmp.write(
        json.dumps(
            {"event": "tool:pre", "data": {"parent_id": None, "tool_name": "delegate"}}
        )
        + "\n"
    )
    tmp.write("\n")  # blank line
    tmp.close()
    path = Path(tmp.name)
    try:
        result = compute_ratio(path)
        assert result.delegates == 1
    finally:
        path.unlink()


def test_non_top_level_events_are_excluded() -> None:
    events = [
        {
            "event": "tool:pre",
            "data": {"parent_id": "some-parent", "tool_name": "delegate"},
        },
        {"event": "tool:pre", "data": {"parent_id": None, "tool_name": "bash"}},
    ]
    path = _write_events(events)
    try:
        result = compute_ratio(path)
        assert result.delegates == 0  # excluded: had a parent_id
        assert result.heavy == 1
    finally:
        path.unlink()


def test_find_events_path_globs_project_slug() -> None:
    with tempfile.TemporaryDirectory() as root:
        root_path = Path(root)
        session_dir = root_path / "-some-project-slug" / "sessions" / "sess-123"
        session_dir.mkdir(parents=True)
        events_file = session_dir / "events.jsonl"
        events_file.write_text("", encoding="utf-8")

        found = find_events_path("sess-123", root_path)
        assert found == events_file

        not_found = find_events_path("does-not-exist", root_path)
        assert not_found is None


def test_format_log_line_shape() -> None:
    from _logic import DelegateRatioResult  # pyright: ignore[reportMissingImports]

    result = DelegateRatioResult(
        session_id="abc-123",
        turns=11,
        delegates=25,
        heavy=13,
        ratio=0.6579,
        flagged=False,
    )
    line = format_log_line(result, "2026-07-14T18:00:00+00:00")
    assert line == (
        "2026-07-14T18:00:00+00:00  session=abc-123  turns=11  "
        "delegates=25  heavy=13  ratio=0.66  OK"
    )

    flagged_result = DelegateRatioResult(
        session_id="xyz", turns=5, delegates=1, heavy=20, ratio=0.047, flagged=True
    )
    flagged_line = format_log_line(flagged_result, "2026-07-14T18:00:00+00:00")
    assert flagged_line.endswith("FLAG")


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
