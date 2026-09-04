"""Framework-free checks for persistent project-local provider launchers."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import cast

REPO = Path(__file__).resolve().parent.parent
PROFILES = {
    "oai": ("my-amplifier-oai", "openai", "gpt-5.6-sol", "openai"),
    "anthropic": (
        "my-amplifier-anthropic",
        "anthropic",
        "claude-opus-4-8",
        "anthropic",
    ),
}
FAKE_AMPLIFIER = """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
cwd = Path.cwd()
with Path(os.environ["FAKE_LOG"]).open("a", encoding="utf-8") as log:
    log.write(json.dumps({"args": args, "cwd": str(cwd)}) + "\\n")
if args[:2] == ["routing", "use"]:
    if os.environ.get("FAKE_ROUTING_FAIL"):
        print("fake routing failure", file=sys.stderr)
        raise SystemExit(41)
    if os.environ.get("FAKE_ROUTING_NO_APPLY"):
        print("fake success without applying")
        raise SystemExit(0)
    settings = cwd / ".amplifier" / "settings.local.yaml"
    settings.parent.mkdir(exist_ok=True)
    settings.write_text(f"routing:\\n  matrix: {args[2]}\\n", encoding="utf-8")
    print(f"✓ Routing matrix set to '{args[2]}' (local scope)")
    raise SystemExit(0)
if args[:1] == ["run"]:
    raise SystemExit(int(os.environ.get("FAKE_RUN_STATUS", "0")))
raise SystemExit(99)
"""


class ProviderLauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        fake = self.bin_dir / "amplifier"
        fake.write_text(FAKE_AMPLIFIER, encoding="utf-8")
        fake.chmod(0o755)
        for name in PROFILES:
            (self.bin_dir / f"amplifier-{name}").symlink_to(
                REPO / "configs" / f"amplifier-{name}.sh"
            )
        self.log = self.root / "calls.jsonl"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def launch(self, profile: str, project: Path, *args: str, **extra: str):
        environment = (
            os.environ
            | {
                "PATH": f"{self.bin_dir}{os.pathsep}{os.environ['PATH']}",
                "FAKE_LOG": str(self.log),
            }
            | extra
        )
        return subprocess.run(
            [str(self.bin_dir / f"amplifier-{profile}"), *args],
            cwd=project,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def calls(self) -> list[dict[str, object]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def assert_only_routing(self, project: Path, matrix: str) -> None:
        self.assertEqual(
            self.calls(),
            [
                {
                    "args": ["routing", "use", matrix, "--scope", "local"],
                    "cwd": str(project),
                }
            ],
        )

    def test_profiles_persist_matrix_and_exec_exactly(self) -> None:
        arguments = ["--max-tokens", "123", "--verbose", "-v", "test prompt"]
        for profile, (bundle, provider, model, matrix) in PROFILES.items():
            with self.subTest(profile=profile):
                project = self.root / f"project with spaces {profile}"
                project.mkdir()
                result = self.launch(profile, project, *arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("PROJECT-LOCAL", result.stdout)
                self.assertIn("persists", result.stdout)
                self.assertNotIn("Routing matrix set to", result.stdout)
                self.assertEqual(
                    (project / ".amplifier" / "settings.local.yaml").read_text(),
                    f"routing:\n  matrix: {matrix}\n",
                )
                self.assertEqual(
                    self.calls(),
                    [
                        {
                            "args": ["routing", "use", matrix, "--scope", "local"],
                            "cwd": str(project),
                        },
                        {
                            "args": [
                                "run",
                                "--mode",
                                "chat",
                                "--bundle",
                                bundle,
                                "--provider",
                                provider,
                                "--model",
                                model,
                                *arguments,
                            ],
                            "cwd": str(project),
                        },
                    ],
                )
                self.log.unlink()

    def test_incompatible_selectors_fail_before_routing(self) -> None:
        rejected = (
            "-B",
            "-Bother",
            "--bundle",
            "--bundle=other",
            "-p",
            "-pother",
            "--provider",
            "--provider=other",
            "-m",
            "-mother",
            "--model",
            "--model=other",
            "--mode",
            "--mode=single",
            "--resume",
            "--resume=session",
            "-vpother",
            "-vBother",
            "-vmother",
        )
        for index, argument in enumerate(rejected):
            with self.subTest(argument=argument):
                project = self.root / f"selector {index}"
                project.mkdir()
                result = self.launch("oai", project, argument)
                self.assertEqual(result.returncode, 2)
                self.assertIn("fixed by amplifier-oai", result.stderr)
                self.assertFalse((project / ".amplifier").exists())
                self.assertEqual(self.calls(), [])
        for index, argument in enumerate(("--output-format", "--output-format=json")):
            with self.subTest(argument=argument):
                project = self.root / f"format {index}"
                project.mkdir()
                result = self.launch("oai", project, argument)
                self.assertEqual(result.returncode, 2)
                self.assertIn("--output-format is incompatible", result.stderr)
                self.assertFalse((project / ".amplifier").exists())
                self.assertEqual(self.calls(), [])

    def test_routing_failures_prevent_run(self) -> None:
        for profile, matrix, extra, status, messages in (
            (
                "anthropic",
                "anthropic",
                {"FAKE_ROUTING_FAIL": "1"},
                41,
                ("fake routing failure",),
            ),
            (
                "oai",
                "openai",
                {"FAKE_ROUTING_NO_APPLY": "1"},
                1,
                ("without confirming", "fake success without applying"),
            ),
        ):
            with self.subTest(profile=profile, extra=extra):
                project = self.root / f"routing {profile}"
                project.mkdir()
                result = self.launch(profile, project, **extra)
                self.assertEqual(result.returncode, status)
                for message in messages:
                    self.assertIn(message, result.stderr)
                self.assert_only_routing(project, matrix)
                self.log.unlink()

    def test_child_exit_status_is_propagated_after_double_dash(self) -> None:
        project = self.root / "child failure"
        project.mkdir()
        result = self.launch("oai", project, "--", "--provider", FAKE_RUN_STATUS="23")
        self.assertEqual(result.returncode, 23)
        arguments = cast(list[str], self.calls()[-1]["args"])
        self.assertEqual(arguments[-2:], ["--", "--provider"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
