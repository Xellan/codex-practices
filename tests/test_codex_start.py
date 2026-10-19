import contextlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/permissions/scripts"))
from codex_start import main, preview, recommend, config_audit, require_acks, inspect_external


class TtyStringIO(io.StringIO):
    def isatty(self):
        return True


class TestLauncher(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "src").mkdir()
        self.codex_home = self.root / "codex-home"
        self.codex_home.mkdir()
        self.env = patch.dict(os.environ, {"CODEX_HOME": str(self.codex_home)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.scan = patch("codex_start.inspect_external", return_value={"risk": "low", "incomplete": False})
        self.scan.start()
        self.addCleanup(self.scan.stop)

    def invoke(self, *args):
        out, err = (TtyStringIO() if getattr(self, "use_tty", False) else io.StringIO()), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(["--project", str(self.project), *args])
        return rc, out.getvalue(), err.getvalue()

    def fake_cli(self, valid=True):
        path = self.root / "fake-codex"
        log = self.root / "cli.log"
        flags = "--sandbox --ask-for-approval --cd" if valid else "unsupported"
        path.write_text(f'''#!/usr/bin/env python3
import sys, pathlib
if '--help' in sys.argv:
    print({flags!r});sys.exit(0)
pathlib.Path({str(log)!r}).write_text(' '.join(sys.argv[1:]))
''')
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return str(path), log

    def test_preview_and_recommend(self):
        rc, out, _ = self.invoke()
        data = json.loads(out)
        self.assertEqual(rc, 0)
        self.assertEqual(data["recommended_profile"], "development")
        self.assertIsNone(data["selected_profile"])
        self.assertEqual(data["external_scan_risk"], "low")
        self.assertIn("NOT_ENFORCED", data["critical_actions"])

    def test_infrastructure_filenames_only(self):
        (self.project / "ansible").mkdir()
        self.assertEqual(recommend(self.project), "infrastructure")

    def test_unconfirmed_launch_refused(self):
        rc, _, err = self.invoke("--profile", "development", "--launch")
        self.assertEqual(rc, 2)
        self.assertIn("--confirm", err)

    def test_auto_selection_not_allowed(self):
        rc, _, err = self.invoke("--launch", "--confirm", "LAUNCH_PROFILE")
        self.assertEqual(rc, 2)
        self.assertIn("--profile", err)

    def test_broad_requires_infrastructure(self):
        self.assertRaises(ValueError, preview, self.project, "development", True)
        rc, _, err = self.invoke("--profile", "infrastructure", "--broad-infra", "--launch", "--confirm", "LAUNCH_PROFILE")
        self.assertEqual(rc, 2)
        self.assertIn("BROAD_INFRA_THIS_SESSION", err)

    def test_profile_flags(self):
        self.assertIn("read-only", preview(self.project, "review", False))
        self.assertIn("workspace-write", preview(self.project, "infrastructure", False))
        self.assertIn("danger-full-access", preview(self.project, "infrastructure", True))
        self.assertNotIn("--yolo", preview(self.project, "infrastructure", True))

    def test_valid_launch_uses_exact_flags(self):
        binary, log = self.fake_cli()
        rc, out, err = self.invoke("--profile", "development", "--launch", "--confirm", "LAUNCH_PROFILE", "--codex-bin", binary)
        self.assertEqual(rc, 0, err)
        self.assertEqual(log.read_text(), "--cd " + str(self.project) + " --sandbox workspace-write --ask-for-approval on-request")

    def test_invalid_cli_help_is_refused(self):
        binary, log = self.fake_cli(valid=False)
        rc, _, err = self.invoke("--profile", "development", "--launch", "--confirm", "LAUNCH_PROFILE", "--codex-bin", binary)
        self.assertEqual(rc, 2)
        self.assertIn("does not confirm", err)
        self.assertFalse(log.exists())

    def test_config_partial_audit_redacts_sensitive_values(self):
        (self.codex_home / "config.toml").write_text('approval_policy = "never"\n[mcp_servers.secretname]\nenv = { API_KEY = "abc-private" }\n')
        audit = config_audit(self.project)
        self.assertTrue(audit["files"][0]["contains_approval_policy"])
        self.assertNotIn("abc-private", str(audit))
        self.assertNotIn("secretname", str(audit))
        self.assertIn("partial", audit["scope"])

    def test_bad_config_refuses_launch_but_preview_works(self):
        (self.codex_home / "config.toml").write_text("[[[invalid")
        rc, out, _ = self.invoke()
        self.assertEqual(rc, 0)
        self.assertTrue(json.loads(out)["config_audit"]["errors"])
        rc, _, err = self.invoke("--profile", "development", "--launch", "--confirm", "LAUNCH_PROFILE")
        self.assertEqual(rc, 2)
        self.assertIn("Configuration audit", err)

    def test_project_config_symlink_rejected(self):
        (self.project / ".codex").mkdir()
        (self.project / ".codex" / "config.toml").symlink_to(self.codex_home / "config.toml")
        self.assertTrue(config_audit(self.project)["errors"])

    def test_conflicting_config_reported_not_automatically_changed(self):
        file = self.codex_home / "config.toml"
        data = 'sandbox_mode = "workspace-write"\n[default_permissions]\nfilesystem = "read-only"\n'
        file.write_text(data)
        self.assertTrue(config_audit(self.project)["warnings"])
        self.assertEqual(file.read_text(), data)

    def test_high_risk_requires_explicit_ack(self):
        self.assertRaises(ValueError, require_acks, {"risk": "high", "incomplete": False}, [])
        with patch("codex_start.inspect_external", return_value={"risk": "high", "incomplete": False}):
            rc, _, err = self.invoke("--profile", "review", "--launch", "--confirm", "LAUNCH_PROFILE")
        self.assertEqual(rc, 2)
        self.assertIn("HIGH_RISK_REVIEWED", err)

    def test_incomplete_scan_requires_ack(self):
        with patch("codex_start.inspect_external", return_value={"risk": "low", "incomplete": True}):
            rc, _, err = self.invoke("--profile", "review", "--launch", "--confirm", "LAUNCH_PROFILE")
        self.assertEqual(rc, 2)
        self.assertIn("INCOMPLETE_SCAN_REVIEWED", err)

    def test_double_risk_acks_are_both_required(self):
        with patch("codex_start.inspect_external", return_value={"risk": "high", "incomplete": True}):
            rc, _, err = self.invoke("--profile", "review", "--launch", "--confirm", "LAUNCH_PROFILE", "--risk-ack", "HIGH_RISK_REVIEWED")
        self.assertEqual(rc, 2)
        self.assertIn("INCOMPLETE_SCAN_REVIEWED", err)

    def test_not_tty_refuses_interactive(self):
        rc, _, err = self.invoke("--interactive")
        self.assertEqual(rc, 2)
        self.assertIn("TTY", err)

    def test_interactive_development_launch(self):
        binary, log = self.fake_cli()
        self.use_tty = True
        with patch.object(sys.stdin, "isatty", return_value=True), patch("builtins.input", side_effect=["", "LAUNCH_PROFILE"]):
            rc, _, err = self.invoke("--interactive", "--codex-bin", binary)
        self.assertEqual(rc, 0, err)
        self.assertIn("workspace-write", log.read_text())

    def test_interactive_infra_broad_needs_distinct_phrase(self):
        binary, log = self.fake_cli()
        self.use_tty = True
        with patch.object(sys.stdin, "isatty", return_value=True), patch("builtins.input", side_effect=["3", "BROAD", "LAUNCH_PROFILE"]):
            rc, _, err = self.invoke("--interactive", "--codex-bin", binary)
        self.assertEqual(rc, 2)
        self.assertFalse(log.exists())

    def test_interactive_infra_broad_approved(self):
        binary, log = self.fake_cli()
        self.use_tty = True
        with patch.object(sys.stdin, "isatty", return_value=True), patch("builtins.input", side_effect=["3", "BROAD", "BROAD_INFRA_THIS_SESSION"]):
            rc, out, err = self.invoke("--interactive", "--codex-bin", binary)
        self.assertEqual(rc, 0, err)
        self.assertIn("danger-full-access", log.read_text())
        self.assertIn("NOT_ENFORCED", out)

    def test_scanner_missing_does_not_prove_clean(self):
        with patch("codex_start.__file__", str(self.root / "x" / "y" / "launcher.py")):
            info = inspect_external(self.project)
        self.assertEqual(info["risk"], "unavailable")
        self.assertTrue(info["incomplete"])

    def test_read_only_preview_does_not_create_files(self):
        before = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*"))
        self.invoke()
        after = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*"))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
