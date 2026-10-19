"""Offline regression scenarios for the final acceptance phase; not run on PR creation."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import codex_practices_setup as setup


class UnifiedInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp = Path(temporary.name)
        self.project = self.tmp / "project"
        self.project.mkdir()
        self.package = self.tmp / "package"
        (self.package / "skills").mkdir()

    def skill(self, folder, name, body="Text"):
        source = self.package / "skills" / folder
        source.mkdir(parents=True, exist_ok=True)
        (source / "SKILL.md").write_text("---\nname: " + name + "\n"
                                         "description: test\n---\n" + body)
        return source

    def test_empty_package_does_not_plan_invented_modules(self):
        plan = setup.build_plan(str(self.project), "available", self.package)
        self.assertEqual(plan["modules"], [])
        self.assertFalse(plan["runs_tests"])

    def test_explicit_missing_module_is_unavailable(self):
        plan = setup.build_plan(str(self.project), "3", self.package)
        self.assertEqual(plan["modules"][0]["status"], "unavailable")

    def test_dependencies_are_included_once(self):
        self.assertEqual(set(setup.selected_modules("10", self.package)), {4, 5, 10})

    def test_existing_identical_skill_not_overwritten(self):
        self.skill("project-memory", "project-memory")
        with patch.object(setup, "package_root", return_value=self.package), \
             patch.object(setup.Path, "home", return_value=self.tmp):
            plan = setup.build_plan(str(self.project), "3")
            self.assertEqual(plan["modules"][0]["status"], "create")
            self.assertEqual(setup.install(str(self.project), "3", plan["plan_sha256"], setup.CONFIRM_INSTALL)["status"], "applied")
            next_plan = setup.build_plan(str(self.project), "3")
            self.assertEqual(next_plan["modules"][0]["status"], "unchanged")

    def test_changed_source_invalidates_plan(self):
        source = self.skill("project-memory", "project-memory")
        with patch.object(setup, "package_root", return_value=self.package), \
             patch.object(setup.Path, "home", return_value=self.tmp):
            before = setup.build_plan(str(self.project), "3")
            (source / "SKILL.md").write_text("---\nname: project-memory\ndescription: new\n---\n")
            with self.assertRaises(setup.SetupError):
                setup.install(str(self.project), "3", before["plan_sha256"], setup.CONFIRM_INSTALL)

    def test_existing_different_skill_blocks_write(self):
        self.skill("project-memory", "project-memory")
        installed = self.project / ".agents" / "skills" / "project-memory"
        installed.mkdir(parents=True)
        (installed / "SKILL.md").write_text("---\nname: project-memory\ndescription: custom\n---\n")
        with patch.object(setup, "package_root", return_value=self.package), \
             patch.object(setup.Path, "home", return_value=self.tmp):
            plan = setup.build_plan(str(self.project), "3")
            self.assertEqual(plan["modules"][0]["status"], "conflict")
            with self.assertRaises(setup.SetupError):
                setup.install(str(self.project), "3", plan["plan_sha256"], setup.CONFIRM_INSTALL)

    def test_rollback_removes_only_new_unchanged_skill(self):
        self.skill("project-memory", "project-memory")
        with patch.object(setup, "package_root", return_value=self.package), \
             patch.object(setup.Path, "home", return_value=self.tmp):
            plan = setup.build_plan(str(self.project), "3")
            result = setup.install(str(self.project), "3", plan["plan_sha256"], setup.CONFIRM_INSTALL)
            self.assertEqual(setup.rollback(str(self.project), result["manifest"], setup.CONFIRM_ROLLBACK)["status"], "rolled_back")

    def test_rollback_refuses_modified_skill(self):
        self.skill("project-memory", "project-memory")
        with patch.object(setup, "package_root", return_value=self.package), \
             patch.object(setup.Path, "home", return_value=self.tmp):
            plan = setup.build_plan(str(self.project), "3")
            result = setup.install(str(self.project), "3", plan["plan_sha256"], setup.CONFIRM_INSTALL)
            installed = self.project / ".agents" / "skills" / "project-memory" / "SKILL.md"
            installed.write_text(installed.read_text() + "\nuser addition")
            with self.assertRaises(setup.SetupError):
                setup.rollback(str(self.project), result["manifest"], setup.CONFIRM_ROLLBACK)


if __name__ == "__main__":
    unittest.main()
