import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "skills/model-efficiency/scripts"


class ModelPolicyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.catalog = self.dir / "models.json"
        self.catalog.write_text(json.dumps({"version": 1, "tiers": {
            "routine": [{"model": "budget", "effort": "low"}],
            "balanced": [{"model": "standard", "effort": "medium"}],
            "advanced": [{"model": "power", "effort": "high"}],
        }}))

    def choose(self, tier, *available):
        return subprocess.run([sys.executable, str(ROOT / "model_policy.py"), "--tier", tier,
                               "--catalog", str(self.catalog), "--available", *available], capture_output=True, text=True)

    def test_routine_model_selected(self):
        p = self.choose("routine", "budget", "standard", "power")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["model"], "budget")

    def test_fallback_never_downgrades_advanced(self):
        p = self.choose("advanced", "budget", "standard")
        self.assertEqual(json.loads(p.stdout)["status"], "inherit")
        self.assertEqual(p.returncode, 0)

    def test_routine_may_escalate(self):
        p = self.choose("routine", "standard")
        self.assertEqual(json.loads(p.stdout)["selected_tier"], "balanced")

    def test_bad_catalog_refused(self):
        self.catalog.write_text('{"version": 1, "tiers": {}}')
        self.assertEqual(self.choose("routine", "budget").returncode, 2)

    def test_symlink_refused(self):
        other = self.dir / "other.json"
        self.catalog.rename(other)
        self.catalog.symlink_to(other)
        self.assertEqual(self.choose("routine", "budget").returncode, 2)


class RTKAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.raw = self.dir / "raw.txt"
        self.compact = self.dir / "compact.txt"

    def check(self, raw, compact, raw_rc=0, compact_rc=0):
        self.raw.write_text(raw)
        self.compact.write_text(compact)
        p = subprocess.run([sys.executable, str(ROOT / "rtk_audit.py"), "--raw", str(self.raw),
                            "--compressed", str(self.compact), "--raw-rc", str(raw_rc),
                            "--compressed-rc", str(compact_rc)], capture_output=True, text=True)
        return p, json.loads(p.stdout)

    def test_exact_equal(self):
        p, report = self.check("same\n", "same\n")
        self.assertEqual((p.returncode, report["status"]), (0, "identical"))

    def test_json_equivalence(self):
        p, report = self.check('{"a":1,"b":[2]}', '{"b": [2], "a": 1}')
        self.assertEqual((p.returncode, report["status"]), (0, "equivalent_json"))

    def test_json_loss_rejected(self):
        p, report = self.check('{"a":1,"b":[2]}', '{"a":1}')
        self.assertEqual((p.returncode, report["status"]), (1, "reject"))

    def test_json_type_change_rejected(self):
        p, report = self.check('{"ok":true}', '{"ok":1}')
        self.assertEqual((p.returncode, report["status"]), (1, "reject"))

    def test_exit_code_change_rejected(self):
        p, report = self.check("ok", "ok", 0, 1)
        self.assertEqual(report["status"], "reject")

    def test_diagnostic_loss_rejected(self):
        p, report = self.check("ERROR: timeout\n", "fine\n")
        self.assertEqual(report["status"], "reject")

    def test_changes_need_human_review(self):
        p, report = self.check("line one\nline two\n", "line one\n")
        self.assertEqual((p.returncode, report["status"]), (1, "review_required"))

    def test_empty_lost_output(self):
        p, report = self.check("meaningful data", "")
        self.assertEqual(report["status"], "reject")


if __name__ == "__main__":
    unittest.main()
