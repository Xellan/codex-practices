import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/permissions/scripts"))
import codex_start as launcher


class TestPermissionsHardening(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "src").mkdir()

    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = launcher.main(["--project", str(self.root), *args])
        return result, out.getvalue(), err.getvalue()

    def test_advisory_only_preflight(self):
        status, out, _ = self.call("--profile", "infrastructure", "--broad-infra")
        self.assertEqual(status, 0)
        report = json.loads(out)
        self.assertEqual(report["critical_action_enforcement"], "NOT_GUARANTEED")
        self.assertFalse(report["config_audit"]["effective_permissions_verified"])

    def test_launch_requires_profile_or_interactive(self):
        code, _, err = self.call("--launch", "--confirm", "LAUNCH_PROFILE")
        self.assertEqual(code, 2)
        self.assertIn("--profile", err)

    def test_symlinked_project_config_prevents_launch(self):
        folder = self.root / ".codex"
        folder.mkdir()
        (folder / "config.toml").symlink_to(self.root / "src")
        code, _, err = self.call("--launch", "--profile", "review", "--confirm", "LAUNCH_PROFILE")
        self.assertEqual(code, 2)
        self.assertIn("manual review", err)

    def test_invalid_project_config_prevents_launch(self):
        folder = self.root / ".codex"
        folder.mkdir()
        (folder / "config.toml").write_text("[[")
        code, _, err = self.call("--launch", "--profile", "review", "--confirm", "LAUNCH_PROFILE")
        self.assertEqual(code, 2)
        self.assertIn("manual review", err)

    def test_broad_requires_separate_confirmation(self):
        code, _, err = self.call("--launch", "--profile", "infrastructure", "--broad-infra",
                                 "--confirm", "LAUNCH_PROFILE")
        self.assertEqual(code, 2)
        self.assertIn("BROAD_INFRA", err)

    def test_interactive_nonterminal_refused(self):
        with patch.object(launcher.sys.stdin, "isatty", return_value=False):
            code, _, err = self.call("--launch", "--interactive")
        self.assertEqual(code, 2)
        self.assertIn("terminal", err)

    def test_interactive_cancel(self):
        with patch.object(launcher.sys.stdin, "isatty", return_value=True), patch("builtins.input", return_value="cancel"):
            code, _, err = self.call("--launch", "--interactive")
        self.assertEqual(code, 2)
        self.assertIn("cancelled", err)

    def test_interactive_launch_requires_confirmation(self):
        with patch.object(launcher.sys.stdin, "isatty", return_value=True), patch("builtins.input", side_effect=["development", "wrong"]):
            code, _, err = self.call("--launch", "--interactive")
        self.assertEqual(code, 2)
        self.assertIn("rejected", err)

    def test_successful_interactive_launch_passes_explicit_flags(self):
        class Process:
            returncode = 0
        with patch.object(launcher.sys.stdin, "isatty", return_value=True), \
             patch("builtins.input", side_effect=["development", "LAUNCH_PROFILE"]), \
             patch.object(launcher.shutil, "which", return_value="/usr/bin/codex"), \
             patch.object(launcher.subprocess, "run", return_value=Process()) as run:
            code, _, _ = self.call("--launch", "--interactive")
        self.assertEqual(code, 0)
        self.assertIn("workspace-write", run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
