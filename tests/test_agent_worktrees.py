"""Isolated Git tests. No Codex API calls or changes outside temp directories."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/multi-agent/scripts/agent_worktrees.py"


class AgentWorktreeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "repo"
        self.repo.mkdir()
        self.git(self.repo, "init", "-q")
        self.git(self.repo, "config", "user.email", "test@example.invalid")
        self.git(self.repo, "config", "user.name", "Local Test")
        (self.repo / "README.md").write_text("original\n")
        self.git(self.repo, "add", "README.md")
        self.git(self.repo, "commit", "-qm", "base")
        self.base = self.git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def git(self, cwd, *args):
        p = subprocess.run(["git", "-C", str(cwd), *args], text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo), *args],
                              text=True, capture_output=True)

    def require(self, *args):
        p = self.cli(*args)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p

    def tree(self, w):
        return self.repo.parent / ".repo-codex-worktrees" / "job" / w

    def prepare(self):
        self.require("prepare", "--run", "job", "--workers", "alpha", "beta")

    def change(self, worker, filename, text):
        tree = self.tree(worker)
        (tree / filename).write_text(text)
        self.git(tree, "add", filename)
        self.git(tree, "commit", "-qm", "update " + filename)

    def verify(self, worker):
        return self.require("verify", "--run", "job", "--worker", worker, "--", sys.executable, "-c", "pass")

    def test_parallel_workers_integration_cleanup_preserves_branches_and_master(self):
        self.prepare()
        self.change("alpha", "alpha.txt", "a")
        self.change("beta", "beta.txt", "b")
        self.verify("alpha")
        self.verify("beta")
        self.require("integrate", "--run", "job", "--workers", "alpha", "beta")
        self.assertTrue((self.tree("integration") / "alpha.txt").exists())
        self.assertTrue((self.tree("integration") / "beta.txt").exists())
        self.assertEqual(self.git(self.repo, "rev-parse", "HEAD").stdout.strip(), self.base)
        self.verify("integration")
        self.require("cleanup", "--run", "job")
        self.assertFalse(self.tree("alpha").exists())
        self.assertFalse(self.tree("integration").exists())
        self.assertTrue(self.git(self.repo, "show-ref", "--verify", "refs/heads/codex-ma/job/alpha"))
        self.assertTrue(self.git(self.repo, "show-ref", "--verify", "refs/heads/codex-ma/job/integration"))
        self.assertTrue((self.repo.parent / ".repo-codex-worktrees/job/manifest.json").exists())

    def test_refuses_dirty_initial_checkout_and_invalid_run(self):
        (self.repo / "untracked").write_text("unsaved")
        self.assertNotEqual(self.cli("prepare", "--run", "job", "--workers", "alpha").returncode, 0)
        (self.repo / "untracked").unlink()
        self.assertNotEqual(self.cli("prepare", "--run", "../escape", "--workers", "alpha").returncode, 0)

    def test_stale_verification_and_missing_final_verification_prevent_cleanup(self):
        self.prepare()
        self.change("alpha", "alpha.txt", "a")
        self.verify("alpha")
        self.change("alpha", "extra.txt", "new unverified commit")
        self.assertNotEqual(self.cli("integrate", "--run", "job", "--workers", "alpha").returncode, 0)
        self.verify("alpha")
        self.require("integrate", "--run", "job", "--workers", "alpha")
        self.assertNotEqual(self.cli("cleanup", "--run", "job").returncode, 0)
        self.verify("integration")
        self.require("cleanup", "--run", "job")

    def test_conflict_preserves_existing_merge_and_aborts_failed_merge(self):
        self.prepare()
        self.change("alpha", "README.md", "from alpha\n")
        self.change("beta", "README.md", "from beta\n")
        self.verify("alpha")
        self.verify("beta")
        result = self.cli("integrate", "--run", "job", "--workers", "alpha", "beta")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.tree("integration") / "README.md").read_text(), "from alpha\n")
        self.assertEqual(self.git(self.tree("integration"), "status", "--porcelain").stdout.strip(), "")
        self.assertIn("integrated=alpha", self.require("status", "--run", "job").stdout)
        self.assertTrue(self.tree("beta").exists())

    def test_ignored_file_blocks_cleanup_even_when_git_status_is_clean(self):
        self.prepare()
        self.change("alpha", "alpha.txt", "a")
        self.verify("alpha")
        self.require("integrate", "--run", "job", "--workers", "alpha")
        self.verify("integration")
        (self.tree("alpha") / ".gitignore").write_text("cache/\n")
        self.git(self.tree("alpha"), "add", ".gitignore")
        self.git(self.tree("alpha"), "commit", "-qm", "ignore cache")
        (self.tree("alpha") / "cache").mkdir()
        (self.tree("alpha") / "cache" / "valuable.bin").write_text("data")
        self.assertNotEqual(self.cli("cleanup", "--run", "job").returncode, 0)
        self.assertTrue((self.tree("alpha") / "cache/valuable.bin").exists())

    def test_nonzero_verification_and_symlink_manifest_refused(self):
        self.prepare()
        self.change("alpha", "alpha.txt", "a")
        result = self.cli("verify", "--run", "job", "--worker", "alpha", "--", sys.executable, "-c", "raise SystemExit(1)")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("verified=True", self.require("status", "--run", "job").stdout.splitlines()[1])
        state = self.repo.parent / ".repo-codex-worktrees/job/manifest.json"
        state.rename(state.with_suffix(".backup"))
        state.symlink_to(state.with_suffix(".backup"))
        self.assertNotEqual(self.cli("status", "--run", "job").returncode, 0)


if __name__ == "__main__":
    unittest.main()
