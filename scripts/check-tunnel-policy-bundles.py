"""Guard the versioned Spark-to-Windows tunnel policy bundle contract."""

from pathlib import Path


def split_bundle(path: Path) -> tuple[str, str]:
    """Return frontmatter and body without requiring a YAML dependency."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    assert lines and lines[0].strip() == "---", f"{path}: missing frontmatter"
    closing = next(
        index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
    )
    return "".join(lines[1:closing]), "".join(lines[closing + 1 :])


def main() -> int:
    """Validate the policy, system invariant, and context-only app bundle."""
    repo = Path(__file__).resolve().parent.parent
    policy = (repo / "context" / "spark-windows-tunnels.md").read_text(encoding="utf-8")
    required_policy_markers = (
        "TUNNEL-ARCHITECTURE.md",
        "`8400-8500`",
        "`travelerPC`",
        "`WILaptopRebuild`",
        "concern-os/tunnel/spark-tunnel.ps1",
        "Spark `127.0.0.1:N`, WSL `localhost:N`, and",
        "`http://localhost:<port>/...`",
        "Never silently change",
        "terminating a WSL",
    )
    for marker in required_policy_markers:
        assert marker in policy, f"tunnel policy is missing {marker!r}"

    anchors_frontmatter, anchors_body = split_bundle(
        repo / "bundles" / "my-amplifier-anchors.md"
    )
    assert "bundles/anchors/bundle.md" in anchors_frontmatter
    for action in ("**allocate**", "**publish**", "**repair**", "**verify**"):
        assert action in anchors_body, f"system invariant is missing {action}"
    mention = "@my-amplifier-anchors:context/spark-windows-tunnels.md"
    assert anchors_body.count(mention) == 1
    assert anchors_body.count("@user:AGENTS.md") == 1

    app_frontmatter, app_body = split_bundle(
        repo / "bundles" / "my-amplifier-tunnel-policy.md"
    )
    required_app_markers = (
        "name: my-amplifier-tunnel-policy",
        "version: 1.0.0",
        "namespace_root: ..",
        "context:",
        "my-amplifier-tunnel-policy:context/spark-windows-tunnels.md",
    )
    for marker in required_app_markers:
        assert marker in app_frontmatter, f"app bundle is missing {marker!r}"
    assert not app_body, "context-only app bundle must have no Markdown body"

    print("OK: versioned Spark-to-Windows tunnel policy bundle contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
