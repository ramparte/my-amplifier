"""Guard shared instructions and provider-only overlay bundle architecture."""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path
from typing import NamedTuple

ANCHORS_MENTION = "@anchors:context/system.md"
PREFERENCES_MENTION = "@my-amplifier:context/preferences.md"
MAX_PROMPT_BYTES = 8_000
BUNDLE_NAMES = (
    "my-amplifier-base",
    "my-amplifier-oai",
    "my-amplifier-anthropic",
)


class BundleSource(NamedTuple):
    """The frontmatter and instruction body of a bundle source file."""

    frontmatter: str
    body: str


def split_bundle(path: Path) -> BundleSource:
    """Split a bundle without requiring a YAML dependency."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise AssertionError(f"{path}: missing opening frontmatter delimiter")
    try:
        closing = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration as error:
        raise AssertionError(
            f"{path}: missing closing frontmatter delimiter"
        ) from error
    return BundleSource("".join(lines[1:closing]), "".join(lines[closing + 1 :]))


def bundle_name(frontmatter: str, path: Path) -> str:
    """Read the required bundle.name scalar from frontmatter text."""
    match = re.search(r"(?m)^  name: ([a-z0-9-]+)\s*$", frontmatter)
    if not match:
        raise AssertionError(f"{path}: missing bundle.name")
    return match.group(1)


def check_static(repo: Path) -> None:
    """Enforce provider-neutral instructions in the base source only."""
    sources = {
        name: split_bundle(repo / "bundles" / f"{name}.md") for name in BUNDLE_NAMES
    }
    for name, source in sources.items():
        path = repo / "bundles" / f"{name}.md"
        assert bundle_name(source.frontmatter, path) == name, path

    base = sources["my-amplifier-base"]
    assert base.body.count(ANCHORS_MENTION) == 1, (
        "base must mention Anchors exactly once"
    )
    assert base.body.count(PREFERENCES_MENTION) == 1, (
        "base must mention preferences exactly once"
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

    expected_overlays = {
        "my-amplifier-oai": ("matrix: openai", "module: provider-openai"),
        "my-amplifier-anthropic": (
            "matrix: anthropic",
            "module: provider-anthropic",
        ),
    }
    base_include_pattern = re.compile(
        r"(?m)^  - bundle: file:///.+/bundles/my-amplifier-base\.md\s*$"
    )
    for name, markers in expected_overlays.items():
        source = sources[name]
        assert not source.body.strip(), (
            f"{name}: overlay instruction body must be empty"
        )
        assert len(base_include_pattern.findall(source.frontmatter)) == 1, (
            f"{name}: must include the shared base exactly once"
        )
        for marker in markers:
            assert marker in source.frontmatter, f"{name}: expected {marker!r}"


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
                expected = {ANCHORS_MENTION, PREFERENCES_MENTION}
                assert set(found) == expected, f"{name}: resolved {set(found)!r}"
                assert all(found[mention].found for mention in expected)
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
                assert prompt_bytes <= MAX_PROMPT_BYTES, (
                    f"{name}: prompt is {prompt_bytes} bytes"
                )
                max_prompt_bytes = max(max_prompt_bytes, prompt_bytes)
    finally:
        os.chdir(original_cwd)

    return max_prompt_bytes


def main() -> int:
    """Run static checks and the optional installed-runtime regression."""
    repo = Path(__file__).resolve().parent.parent
    check_static(repo)
    prompt_bytes = asyncio.run(check_runtime(repo))
    if prompt_bytes is None:
        print("OK: provider overlay source architecture (runtime unavailable; skipped)")
    else:
        print(
            "OK: provider overlay source architecture and prompts "
            f"(largest: {prompt_bytes} bytes)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
