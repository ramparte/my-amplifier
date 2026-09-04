"""Guard shared instructions and provider-specific overlay architecture."""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

ANCHORS_MENTION = "@anchors:context/system.md"
PREFERENCES_MENTION = "@my-amplifier:context/preferences.md"
USER_AGENTS_MENTION = "@user:AGENTS.md"
MAX_PROMPT_BYTES = 8_000
BUNDLE_NAMES = (
    "my-amplifier-base",
    "my-amplifier-oai",
    "my-amplifier-anthropic",
)
BASE_INCLUDE_PATTERN = re.compile(
    r"(?m)^  - bundle: git\+https://github\.com/ramparte/my-amplifier@main"
    r"#subdirectory=bundles/my-amplifier-base\.md\s*$"
)


class BundleSource(NamedTuple):
    """The frontmatter and instruction body of a bundle source file."""

    frontmatter: str
    body: str


class ProviderEntry(NamedTuple):
    """One provider entry parsed from constrained bundle frontmatter."""

    identity: str | None
    module: str
    config: tuple[tuple[str, str], ...]


def split_bundle(path: Path) -> BundleSource:
    """Split a bundle without requiring a YAML dependency."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{path}: missing opening frontmatter delimiter")
    try:
        closing = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as error:
        raise AssertionError(f"{path}: missing closing frontmatter delimiter") from error
    return BundleSource("".join(lines[1:closing]), "".join(lines[closing + 1 :]))


def bundle_name(frontmatter: str, path: Path) -> str:
    """Read the required bundle.name scalar from frontmatter text."""
    match = re.search(r"(?m)^  name: ([a-z0-9-]+)\s*$", frontmatter)
    if not match:
        raise AssertionError(f"{path}: missing bundle.name")
    return match.group(1)


def parse_provider_entries(frontmatter: str, path: Path) -> tuple[ProviderEntry, ...]:
    """Extract top-level provider entries from constrained bundle frontmatter."""
    lines = frontmatter.splitlines(keepends=True)
    provider_sections = [
        index for index, line in enumerate(lines) if re.fullmatch(r"providers:\s*", line)
    ]
    assert len(provider_sections) == 1, (
        f"{path}: expected exactly one top-level providers section, found {len(provider_sections)}"
    )
    start = provider_sections[0]

    blocks: list[str] = []
    current: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() and not line.startswith((" ", "\t", "#")):
            break
        if line.startswith("  - "):
            if current:
                blocks.append("".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append("".join(current))

    entries: list[ProviderEntry] = []
    for block in blocks:
        identity_match = re.search(r"(?m)^  - id: ([a-z0-9-]+)\s*$", block)
        module_match = re.search(r"(?m)^(?:  - |    )module: ([a-z0-9-]+)\s*$", block)
        if not module_match:
            raise AssertionError(f"{path}: provider entry lacks module: {block!r}")
        config = parse_provider_config(block, path)
        entries.append(
            ProviderEntry(
                identity_match.group(1) if identity_match else None,
                module_match.group(1),
                config,
            )
        )
    return tuple(entries)


def parse_provider_config(block: str, path: Path) -> tuple[tuple[str, str], ...]:
    """Extract scalar settings from one provider entry's actual config mapping."""
    lines = block.splitlines(keepends=True)
    config_sections = [
        index for index, line in enumerate(lines) if re.fullmatch(r"    config:\s*", line)
    ]
    assert len(config_sections) <= 1, f"{path}: provider entry contains multiple config mappings"
    if not config_sections:
        return ()

    config: dict[str, str] = {}
    for line in lines[config_sections[0] + 1 :]:
        if line.strip() and not line.startswith("      "):
            break
        match = re.fullmatch(r"      ([a-z][a-z0-9_]*):\s*(\S.*?)\s*", line)
        if not match:
            continue
        key, value = match.groups()
        assert key not in config, f"{path}: provider entry repeats config key {key!r}"
        config[key] = value
    return tuple(config.items())


def assert_provider_contract(
    source: BundleSource,
    *,
    path: Path,
    expected: tuple[tuple[str | None, str], ...],
    required_config: tuple[tuple[str, str], ...],
    forbidden_markers: tuple[str, ...],
) -> None:
    """Validate exact identities, modules, controls, and forbidden stale keys."""
    entries = parse_provider_entries(source.frontmatter, path)
    actual = tuple((entry.identity, entry.module) for entry in entries)
    assert actual == expected, f"{path}: providers {actual!r}, expected {expected!r}"
    for entry in entries:
        config = dict(entry.config)
        for key, value in required_config:
            assert config.get(key) == value, (
                f"{path}: {entry.identity or 'generic'} must set "
                f"{key!r} to {value!r}; found {config.get(key)!r}"
            )
    for marker in forbidden_markers:
        assert marker not in source.frontmatter, f"{path}: contains {marker!r}"


def assert_rejected(description: str, expected_message: str, check: Callable[[], object]) -> None:
    """Assert a no-argument validation callable rejects malformed input."""
    try:
        check()
    except AssertionError as error:
        assert expected_message in str(error), (
            f"{description} failed with unexpected assertion: {error}"
        )
        return
    raise AssertionError(f"negative parser self-test accepted {description}")


def check_parser_negative_cases() -> None:
    """Prove duplicate sections and comment-only settings cannot satisfy the guard."""
    duplicate_providers = """\
providers:
  - id: openai
    module: provider-openai
providers:
  - id: terra
    module: provider-openai
"""
    assert_rejected(
        "a duplicate top-level providers section",
        "expected exactly one top-level providers section",
        lambda: parse_provider_entries(duplicate_providers, Path("<duplicate-providers>")),
    )

    comment_only_setting = """\
providers:
  - id: openai
    module: provider-openai
    config:
      # reasoning_effort: medium
"""
    assert_rejected(
        "a comment in place of a provider configuration value",
        "must set 'reasoning_effort' to 'medium'",
        lambda: assert_provider_contract(
            BundleSource(comment_only_setting, ""),
            path=Path("<comment-only-setting>"),
            expected=(("openai", "provider-openai"),),
            required_config=(("reasoning_effort", "medium"),),
            forbidden_markers=(),
        ),
    )


def check_static(repo: Path) -> None:
    """Enforce provider-neutral base and exact provider overlay composition."""
    sources = {name: split_bundle(repo / "bundles" / f"{name}.md") for name in BUNDLE_NAMES}
    for name, source in sources.items():
        path = repo / "bundles" / f"{name}.md"
        assert bundle_name(source.frontmatter, path) == name, path

    base = sources["my-amplifier-base"]
    assert base.body.count(ANCHORS_MENTION) == 1, "base must mention Anchors exactly once"
    assert base.body.count(PREFERENCES_MENTION) == 1, "base must mention preferences exactly once"
    assert base.body.count(USER_AGENTS_MENTION) == 1, (
        "base must mention user instructions exactly once"
    )
    assert base.body.index(ANCHORS_MENTION) < base.body.index(PREFERENCES_MENTION), (
        "Anchors must precede preferences"
    )
    anchors_include = (
        "git+https://github.com/microsoft/amplifier-foundation@main"
        "#subdirectory=bundles/anchors/bundle.md"
    )
    assert base.frontmatter.count(anchors_include) == 1, (
        "base must retain exactly one Anchors bundle include"
    )
    assert not re.search(r"(?m)^providers:\s*$", base.frontmatter)
    assert not re.search(r"(?m)^routing:\s*$", base.frontmatter)
    assert not re.search(r"(?m)^agents:\s*$", base.frontmatter)
    assert "fast-local" not in base.frontmatter + base.body

    expected_oai = (
        ("openai", "provider-openai"),
        ("terra", "provider-openai"),
        ("luna", "provider-openai"),
        ("luna-max", "provider-openai"),
    )
    oai = sources["my-amplifier-oai"]
    assert not oai.body.strip(), "my-amplifier-oai: instruction body must be empty"
    assert len(BASE_INCLUDE_PATTERN.findall(oai.frontmatter)) == 1, (
        "my-amplifier-oai: must include the shared base exactly once"
    )
    assert_provider_contract(
        oai,
        path=repo / "bundles" / "my-amplifier-oai.md",
        expected=expected_oai,
        required_config=(("reasoning_summary", "concise"),),
        forbidden_markers=(
            "enable_response_chaining",
            "routing:",
            "provider-anthropic",
            "provider-github-copilot",
            "provider-vllm",
        ),
    )

    oai_configs = {
        entry.identity: dict(entry.config)
        for entry in parse_provider_entries(
            oai.frontmatter, repo / "bundles" / "my-amplifier-oai.md"
        )
    }
    for identity, config in oai_configs.items():
        assert "reasoning_effort" not in config, (
            f"my-amplifier-oai: {identity!r} must not pin reasoning_effort "
            "(owned by settings.yaml, which wins the same-id merge)"
        )

    expected_anthropic = (
        (None, "provider-anthropic"),
        ("fable", "provider-anthropic"),
        ("opus", "provider-anthropic"),
        ("sonnet", "provider-anthropic"),
    )
    anthropic = sources["my-amplifier-anthropic"]
    assert not anthropic.body.strip(), "my-amplifier-anthropic: instruction body must be empty"
    assert len(BASE_INCLUDE_PATTERN.findall(anthropic.frontmatter)) == 1, (
        "my-amplifier-anthropic: must include the shared base exactly once"
    )
    assert_provider_contract(
        anthropic,
        path=repo / "bundles" / "my-amplifier-anthropic.md",
        expected=expected_anthropic,
        required_config=(
            ("enable_prompt_caching", "true"),
            ("cache_stable_region_ttl_1h", "true"),
            ("enable_1m_context", "true"),
        ),
        forbidden_markers=(
            "cache_ttl:",
            "routing:",
            "provider-openai",
            "provider-github-copilot",
            "provider-vllm",
        ),
    )
    anthropic_configs = {
        entry.identity: dict(entry.config)
        for entry in parse_provider_entries(
            anthropic.frontmatter, repo / "bundles" / "my-amplifier-anthropic.md"
        )
    }
    assert anthropic_configs[None].get("default_model") == "claude-opus-4-8", (
        "my-amplifier-anthropic: generic provider must default to claude-opus-4-8"
    )
    for identity in ("fable", "opus", "sonnet"):
        assert "default_model" not in anthropic_configs[identity], (
            "my-amplifier-anthropic: named provider "
            f"{identity!r} must not set a bundle-local default_model"
        )

    qwen_path = repo / "bundles" / "my-amplifier-qwen.md"
    qwen = split_bundle(qwen_path)
    assert bundle_name(qwen.frontmatter, qwen_path) == "my-amplifier-qwen"
    assert qwen.frontmatter.count("my-amplifier:agents/fast-local") == 1, (
        "my-amplifier-qwen must retain fast-local explicitly"
    )
    for source, path in (
        *[(source, repo / "bundles" / f"{name}.md") for name, source in sources.items()],
        (qwen, qwen_path),
    ):
        assert "enable_response_chaining" not in source.frontmatter, f"{path}: stale OpenAI setting"
        assert "cache_ttl:" not in source.frontmatter, f"{path}: stale Anthropic setting"
        assert not re.search(r"(?m)^routing:\s*$", source.frontmatter), (
            f"{path}: inert routing declaration"
        )


def runtime_cache_home() -> Path:
    """Return the persistent cache used for runtime-only bundle dependencies."""
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return cache_root / "my-amplifier" / "provider-overlay-check"


async def check_runtime(repo: Path) -> int | None:
    """Check strict prompt resolution when Amplifier Foundation is installed."""
    try:
        from amplifier_foundation import (  # pyright: ignore[reportMissingImports]
            BundleRegistry,
        )
        from amplifier_foundation.mentions import (  # pyright: ignore[reportMissingImports]
            BaseMentionResolver,
            ContentDeduplicator,
            load_mentions,
        )
    except ModuleNotFoundError as error:
        if error.name and error.name.startswith("amplifier_foundation"):
            return None
        raise

    original_cwd = Path.cwd()
    max_prompt_bytes = 0
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            arbitrary_cwd = Path(temp_dir) / "arbitrary" / "cwd"
            arbitrary_cwd.mkdir(parents=True)
            os.chdir(arbitrary_cwd)
            registry = BundleRegistry(
                home=runtime_cache_home(),
                strict=True,
            )
            for name in BUNDLE_NAMES:
                bundle = await registry.load(
                    (repo / "bundles" / f"{name}.md").as_uri(),
                    auto_register=False,
                )
                assert bundle.name == name
                assert bundle.instruction
                prepared = await bundle.prepare(install_deps=False, strict=True)
                mentions = await load_mentions(
                    bundle.instruction,
                    resolver=BaseMentionResolver(
                        bundles=prepared._build_bundles_for_resolver(bundle),
                        base_path=bundle.base_path,
                    ),
                    deduplicator=ContentDeduplicator(),
                )
                found = {item.mention: item for item in mentions}
                required_mentions = {
                    ANCHORS_MENTION,
                    PREFERENCES_MENTION,
                }
                assert required_mentions.issubset(found), f"{name}: resolved {set(found)!r}"
                assert set(found) - required_mentions <= {USER_AGENTS_MENTION}, (
                    f"{name}: unexpected mentions {set(found)!r}"
                )
                assert all(found[mention].found for mention in required_mentions)
                anchors_text = found[ANCHORS_MENTION].content
                preferences_text = found[PREFERENCES_MENTION].content
                assert anchors_text and preferences_text
                prompt = await prepared._create_system_prompt_factory(
                    bundle,
                    None,
                    session_cwd=arbitrary_cwd,
                )()
                assert prompt.count(anchors_text) == 1
                assert prompt.count(preferences_text) == 1
                prompt_bytes = len(prompt.encode("utf-8"))
                assert prompt_bytes <= MAX_PROMPT_BYTES, f"{name}: prompt is {prompt_bytes} bytes"
                max_prompt_bytes = max(max_prompt_bytes, prompt_bytes)
    finally:
        os.chdir(original_cwd)

    return max_prompt_bytes


def main() -> int:
    """Run static checks and the optional installed-runtime regression."""
    repo = Path(__file__).resolve().parent.parent
    check_parser_negative_cases()
    print("OK: provider parser rejects duplicate sections and comment-only settings")
    check_static(repo)
    prompt_bytes = asyncio.run(check_runtime(repo))
    if prompt_bytes is None:
        print("OK: provider overlay source architecture (runtime unavailable; skipped)")
    else:
        print(
            f"OK: provider overlay source architecture and prompts (largest: {prompt_bytes} bytes)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
