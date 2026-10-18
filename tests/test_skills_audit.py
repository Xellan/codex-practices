from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "skills/skills-management/scripts"))
from skills_audit import discover
class SkillsAuditTests(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);self.project=root/'project';self.project.mkdir();self.home=root/'home';self.home.mkdir()
 def add(self,root,name,meta=None):
  p=root/'skills'/name;p.mkdir(parents=True)
  (p/'SKILL.md').write_text(meta or f'---\nname: {name}\ndescription: Useful when checking this workflow\n---\n\n# Skill\n')
 def test_discovery_valid(self):
  self.add(self.project/'.agents','review');r=discover(self.project,self.home)
  self.assertEqual(r['skills'][0]['status'],'valid')
 def test_collision(self):
  self.add(self.project/'.agents','review');self.add(self.home,'review')
  self.assertEqual(discover(self.project,self.home)['conflicts'],1)
 def test_malformed(self):
  self.add(self.home,'oops','missing header');self.assertEqual(discover(self.project,self.home)['skills'][0]['status'],'invalid_manifest')
 def test_symlink_not_followed(self):
  target=self.home/'skills';target.mkdir();(self.project/'.agents').mkdir();(self.project/'.agents'/'skills').symlink_to(target)
  r=discover(self.project,self.home);self.assertEqual(r['skills'][0]['status'],'unsafe_root')
 def test_project_must_exist(self):
  with self.assertRaises(FileNotFoundError):discover(self.project/'missing',self.home)
if __name__=='__main__':unittest.main()
