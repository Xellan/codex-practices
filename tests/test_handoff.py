import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/project-memory/scripts/handoff.py"


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args], text=True, capture_output=True)

    def save(self, *args):
        return self.run_cli("save", "--goal", "Build MVP", "--next-step", "Run tests", *args)

    def test_fresh_save_show_and_overwrite_with_digest(self):
        self.assertEqual(self.run_cli("show").returncode, 3)
        result = self.save("--done", "Created module", "--check", "NOT RUN: network integration")
        self.assertEqual(result.returncode, 0, result.stderr)
        f = self.root / "docs/context/HANDOFF.md"
        before = f.read_text()
        digest = hashlib.sha256(before.encode()).hexdigest()
        self.assertIn(digest, self.run_cli("check").stdout)
        stale = self.save("--done", "Another step", "--expect-sha", "deadbeef")
        self.assertEqual(stale.returncode, 2)
        self.assertEqual(f.read_text(), before)
        result = self.save("--done", "Another step", "--expect-sha", digest)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Another step", f.read_text())

    def test_existing_unmanaged_file_is_preserved(self):
        path = self.root / "docs/context/HANDOFF.md"
        path.parent.mkdir(parents=True)
        path.write_text("User created file")
        result = self.save()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(path.read_text(), "User created file")

    def test_refuse_traversal_and_symlinks(self):
        self.assertEqual(self.run_cli("--file", "../bad.md", "show").returncode, 2)
        other = self.root / "elsewhere"
        other.mkdir()
        (self.root / "docs").symlink_to(other, target_is_directory=True)
        self.assertEqual(self.save().returncode, 2)
        self.assertFalse((other / "context/HANDOFF.md").exists())

    def test_blocked_status_and_no_secret_interpolation(self):
        result = self.save("--status", "blocked", "--blocker", "Awaiting approval", "--reference", "docs/plan.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.root / "docs/context/HANDOFF.md").read_text()
        self.assertIn("Status: blocked", content)
        self.assertIn("Awaiting approval", content)

    def test_empty_data_rejected(self):
        result = self.run_cli("save", "--goal", " ", "--next-step", "X")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.root / "docs/context/HANDOFF.md").exists())


if __name__ == "__main__":
    unittest.main()
