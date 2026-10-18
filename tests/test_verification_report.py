from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "skills/verification/scripts"))
from verification_report import evaluate

def check(status,evidence='pytest -q: 7 passed',critical=False):
 return {'name':'pytest','status':status,'evidence':evidence,'critical':critical}
class ReportTests(unittest.TestCase):
 def test_verified(self):self.assertEqual(evaluate({'level':'standard','checks':[check('PASS')]})['status'],'Verified')
 def test_no_fake_pass(self):
  with self.assertRaises(ValueError):evaluate({'level':'strict','checks':[check('PASS','',True)]})
 def test_incomplete_strict(self):
  r=evaluate({'level':'strict','checks':[check('PASS'),check('NOT_RUN','awaiting staging',True)]})
  self.assertEqual(r['status'],'Partially Verified');self.assertEqual(r['critical_incomplete'],['pytest'])
 def test_blocker(self):self.assertEqual(evaluate({'level':'light','checks':[check('BLOCKED')]})['status'],'Blocked')
 def test_failure_precedence(self):self.assertEqual(evaluate({'level':'standard','checks':[check('FAIL'),check('NOT_RUN')]})['status'],'Failed')
 def test_empty_checks_rejected(self):
  with self.assertRaises(ValueError):evaluate({'level':'light','checks':[]})
 def test_extra_fields_rejected(self):
  with self.assertRaises(ValueError):evaluate({'level':'light','checks':[dict(check('PASS'),unexpected=True)]})
if __name__=='__main__':unittest.main()
