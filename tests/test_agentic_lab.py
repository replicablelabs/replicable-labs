"""Tests for the agentic-coding-superuser lab: it loads the replicable-harness plugin, on the host."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from replicable import cli

LAB = Path(__file__).resolve().parents[1] / "src" / "replicable" / "labs" / "agentic-coding-superuser"
SPEC = {"name": "harness", "repository": "https://example.com/harness.git", "ref": "v1.2.3"}


def make_plugin(path: Path) -> Path:
    (path / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (path / ".claude-plugin" / "plugin.json").write_text("{}")
    return path


class HostLabTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.labs = self.tmp / "labs"
        lab = self.labs / "plugin-lab"
        lab.mkdir(parents=True)
        (lab / "lab.json").write_text(json.dumps({"kind": "claude-code-plugin", "plugin": SPEC}))
        self.cache = self.tmp / "root" / ".data" / "plugins"
        for patcher in (patch.object(cli, "LABS_ROOT", self.labs), patch.object(cli, "ROOT", self.tmp / "root"),
                        patch.object(cli, "PLUGIN_CACHE", self.cache),
                        patch.object(cli.shutil, "which", lambda name: "/usr/bin/" + name),
                        patch.dict(os.environ)):  # restored after the test
            patcher.start()
            self.addCleanup(patcher.stop)
        os.environ.pop("REPLICABLE_HARNESS_DIR", None)

    def test_the_real_lab_pins_a_tagged_plugin_release(self):
        config = json.loads((LAB / "lab.json").read_text())
        self.assertEqual(config["kind"], "claude-code-plugin")
        self.assertRegex(config["plugin"]["ref"], r"^v\d+\.\d+\.\d+$")
        self.assertTrue(cli._is_host_lab(LAB))
        self.assertEqual(sorted(p.name for p in LAB.iterdir()), ["README.md", "lab.json"])  # no copied plugin code

    def test_clones_the_pinned_tag_once_then_runs_claude_with_it(self):
        target = self.cache / "harness-v1.2.3"

        def fake_clone(cmd, **kwargs):
            make_plugin(target)
            return type("Done", (), {"returncode": 0})()

        with patch.object(cli.subprocess, "run", side_effect=fake_clone) as run, \
                patch.object(cli.subprocess, "call", return_value=0) as call:
            self.assertEqual(cli.start_lab("plugin-lab", extra_args=["--model", "opus"]), 0)
            self.assertEqual(cli.start_lab("plugin-lab"), 0)
        run.assert_called_once_with(["git", "-c", "advice.detachedHead=false", "clone", "--quiet", "--depth", "1",
                                     "--branch", "v1.2.3",
                                     SPEC["repository"], str(target)])
        call.assert_any_call(["claude", "--plugin-dir", str(target), "--model", "opus"], cwd=cli.ROOT)

    def test_local_checkout_override(self):
        local = make_plugin(self.tmp / "checkout")
        with patch.dict(os.environ, {"REPLICABLE_HARNESS_DIR": str(local)}), \
                patch.object(cli.subprocess, "run") as run, patch.object(cli.subprocess, "call", return_value=0) as call:
            cli.start_lab("plugin-lab")
        run.assert_not_called()
        call.assert_called_once_with(["claude", "--plugin-dir", str(local.resolve())], cwd=cli.ROOT)
        with patch.dict(os.environ, {"REPLICABLE_HARNESS_DIR": str(self.tmp)}):
            with self.assertRaisesRegex(SystemExit, "is not a Claude Code plugin"):
                cli.start_lab("plugin-lab")

    def test_failed_clone_is_explained(self):
        with patch.object(cli.subprocess, "run", return_value=type("Failed", (), {"returncode": 128})()):
            with self.assertRaisesRegex(SystemExit, "Could not fetch https://example.com/harness.git at v1.2.3"):
                cli.start_lab("plugin-lab")

    def test_missing_tools_are_explained(self):
        with patch.object(cli.shutil, "which", return_value=None):
            with self.assertRaisesRegex(SystemExit, "Claude Code CLI"):
                cli.start_lab("plugin-lab")
        with patch.object(cli.shutil, "which", lambda name: None if name == "git" else "/usr/bin/" + name):
            with self.assertRaisesRegex(SystemExit, "needs git"):
                cli.start_lab("plugin-lab")


if __name__ == "__main__":
    unittest.main()
