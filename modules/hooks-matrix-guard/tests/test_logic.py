"""Pytest tests for the pure matrix/provider intersection logic.

Imports ``_logic`` directly by path (not through the package ``__init__``)
so these tests don't require ``amplifier_core`` or ``pyyaml`` to be
installed -- same convention as the sibling ``hooks-delegate-ratio``
module's tests.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "amplifier_module_hooks_matrix_guard"
    ),
)

from _logic import (  # pyright: ignore[reportMissingImports]
    MAX_ROLES_SHOWN,
    classify_matrix,
    format_warning,
    normalize_provider_name,
)


def _role(provider: str, model: str = "some-model") -> dict:
    return {"description": "d", "candidates": [{"provider": provider, "model": model}]}


def test_all_roles_resolve_is_ok() -> None:
    roles = {
        "general": _role("anthropic"),
        "fast": _role("anthropic"),
    }
    result = classify_matrix(roles, {"anthropic", "openai"})
    assert result.outcome == "ok"
    assert result.resolvable_roles == ("general", "fast")
    assert result.unresolvable_roles == ()
    assert format_warning(result, "anthropic") == ""


def test_no_roles_resolve_is_broken() -> None:
    roles = {
        "general": _role("anthropic"),
        "fast": _role("anthropic"),
    }
    result = classify_matrix(roles, {"openai"})
    assert result.outcome == "broken"
    assert result.resolvable_roles == ()
    assert result.unresolvable_roles == ("general", "fast")

    message = format_warning(result, "anthropic")
    assert "anthropic" in message
    assert "Remediation" in message
    assert "amplifier routing use <matrix>" in message
    assert "settings.local.yaml" in message


def test_partial_resolution_is_degraded_with_correct_roles() -> None:
    roles = {
        "general": _role("anthropic"),
        "fast": _role("anthropic"),
        "coding": _role("openai"),
    }
    result = classify_matrix(roles, {"anthropic"})
    assert result.outcome == "degraded"
    assert result.resolvable_roles == ("general", "fast")
    assert result.unresolvable_roles == ("coding",)

    message = format_warning(result, "anthropic")
    assert "coding" in message
    assert "Remediation" not in message


def test_empty_roles_is_handled_without_exception() -> None:
    result = classify_matrix({}, {"anthropic"})
    assert result.outcome == "ok"
    assert result.total_roles == 0
    assert result.resolvable_roles == ()
    assert result.unresolvable_roles == ()
    assert format_warning(result, "anthropic") == ""


def test_non_dict_roles_input_is_handled_without_exception() -> None:
    result = classify_matrix(None, {"anthropic"})  # type: ignore[arg-type]
    assert result.outcome == "ok"
    assert result.total_roles == 0
    assert format_warning(result, "anthropic") == ""


def test_more_than_five_unresolvable_roles_truncates_message() -> None:
    # 7 unresolvable + 1 resolvable -> DEGRADED, isolating the truncation
    # behavior from the BROKEN-only remediation text.
    unresolved_names = [f"role-{i}" for i in range(7)]
    roles = {name: _role("openai") for name in unresolved_names}
    roles["general"] = _role("anthropic")

    result = classify_matrix(roles, {"anthropic"})
    assert result.outcome == "degraded"
    assert len(result.unresolvable_roles) == 7

    message = format_warning(result, "anthropic")
    for name in unresolved_names[:MAX_ROLES_SHOWN]:
        assert name in message
    assert "+2 more" in message
    for name in unresolved_names[MAX_ROLES_SHOWN:]:
        assert name not in message


def test_provider_name_comparison_is_case_insensitive() -> None:
    roles = {"general": _role("Anthropic")}
    result = classify_matrix(roles, {"ANTHROPIC"})
    assert result.outcome == "ok"
    assert result.resolvable_roles == ("general",)

    assert normalize_provider_name("Anthropic") == normalize_provider_name("ANTHROPIC")


def test_malformed_roles_and_candidates_are_skipped_safely() -> None:
    roles = {
        "weird": {
            "description": "d",
            "candidates": ["base", 123, {"no_provider": True}, None],
        },
        "good": _role("anthropic"),
    }
    result = classify_matrix(roles, {"anthropic"})
    assert result.outcome == "degraded"
    assert "weird" in result.unresolvable_roles
    assert "good" in result.resolvable_roles


def test_role_data_that_is_not_a_mapping_is_treated_as_unresolvable() -> None:
    roles = {"broken-role": None, "good": _role("anthropic")}
    result = classify_matrix(roles, {"anthropic"})
    assert result.outcome == "degraded"
    assert "broken-role" in result.unresolvable_roles


def test_matrix_and_available_providers_preserve_original_casing_for_display() -> None:
    roles = {"general": _role("Anthropic"), "fast": _role("OpenAI")}
    result = classify_matrix(roles, {"anthropic"})
    assert result.matrix_providers == frozenset({"Anthropic", "OpenAI"})
    assert result.available_providers == frozenset({"anthropic"})
