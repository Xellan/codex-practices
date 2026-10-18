import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/permissions/scripts"))
from codex_start import main, preview, recommend

class TestLauncher(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.project = Path(t.name); (self.project / "src").mkdir()

    def invoke(self,*args):
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            rc=main(["--project",str(self.project),*args])
        return rc,out.getvalue(),err.getvalue()

    def test_preview_and_recommend(self):
        rc,out,_ = self.invoke()
        data=json.loads(out)
        self.assertEqual(rc,0)
        self.assertEqual(data["recommended_profile"],"development")
        self.assertEqual(data["selected_profile"],None)

    def test_unconfirmed_launch_refused(self):
        rc,_,err=self.invoke("--profile","development","--launch")
        self.assertEqual(rc,2);self.assertIn("--confirm",err)

    def test_auto_selection_not_allowed_for_launch(self):
        rc,_,err=self.invoke("--launch","--confirm","LAUNCH_PROFILE")
        self.assertEqual(rc,2);self.assertIn("--profile",err)

    def test_broad_requires_infra_and_explicit_confirmation(self):
        self.assertRaises(ValueError, preview, self.project, "development", True)
        rc,_,err=self.invoke("--profile","infrastructure","--broad-infra","--launch","--confirm","LAUNCH_PROFILE")
        self.assertEqual(rc,2);self.assertIn("BROAD_INFRA",err)

    def test_profile_flags(self):
        self.assertIn("read-only",preview(self.project,"review",False))
        self.assertIn("workspace-write",preview(self.project,"infrastructure",False))
        self.assertIn("danger-full-access",preview(self.project,"infrastructure",True))
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox",preview(self.project,"infrastructure",True))

if __name__=="__main__":unittest.main()
