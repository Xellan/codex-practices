import json
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/project-inventory/scripts'))
from inventory import InventoryError, apply_fixes, digest, inspect, load_map, read_safe, relative, restore, write_report, main


class InventoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'project'
        self.root.mkdir()
        self.external_backup = str(Path(temp.name) / 'backups')
        self.mk('fact-owners.toml', '''schema_version = 1
[[facts]]
id = "version"
description = "Release version"
source_type = "file"
source = "VERSION.md"
[[facts]]
id = "external_state"
description = "External tracker"
source_type = "external"
source = "tracker:release"
''')
        self.mk('VERSION.md', '1.2\n')

    def mk(self, path, text):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding='utf-8')
        return file

    def test_load_fact_owners(self):
        self.assertEqual(len(load_map(self.root)), 2)

    def test_duplicate_fact_id_rejected(self):
        self.mk('fact-owners.toml', '''schema_version=1
[[facts]]
id='dup'
description='A'
source_type='file'
source='VERSION.md'
[[facts]]
id='dup'
description='B'
source_type='file'
source='VERSION.md'
''')
        with self.assertRaises(InventoryError): load_map(self.root)

    def test_escape_and_symlink_refused(self):
        self.assertRaises(InventoryError, relative, self.root, '../secret')
        self.assertRaises(InventoryError, relative, self.root, '/tmp/secret')
        (self.root/'link.md').symlink_to(self.root/'VERSION.md')
        self.assertRaises(InventoryError, relative, self.root, 'link.md')

    def test_missing_owner_reported_not_inferred(self):
        (self.root/'VERSION.md').unlink()
        findings = inspect(self.root, load_map(self.root))['findings']
        self.assertTrue(any(x['kind'] == 'missing_owner' for x in findings))

    def test_external_status_is_unverified(self):
        findings = inspect(self.root, load_map(self.root))['findings']
        self.assertTrue(any(x['kind'] == 'external_unverified' for x in findings))

    def test_case_only_link_candidate(self):
        self.mk('docs/Guide.md', 'hello')
        self.mk('README.md', '[Guide](docs/guide.md)')
        report = inspect(self.root, load_map(self.root), ['README.md'])
        self.assertEqual(report['candidate_fixes'][0]['replacements'][0][2], 'docs/Guide.md')

    def test_moved_link_not_auto_fixed(self):
        self.mk('docs/guide.md', 'hello')
        self.mk('README.md', '[Guide](guide.md)')
        report = inspect(self.root, load_map(self.root), ['README.md'])
        self.assertEqual(report['candidate_fixes'], [])
        self.assertEqual(next(x for x in report['findings'] if x['kind']=='broken_link')['suggested'], None)

    def test_code_block_ignored(self):
        self.mk('README.md', '```md\n[x](missing.md)\n```\n`[y](missing.md)`\n')
        report = inspect(self.root, load_map(self.root), ['README.md'])
        self.assertFalse(any(x['kind']=='broken_link' for x in report['findings']))

    def test_safe_fix_backup_and_rollback(self):
        self.mk('docs/Guide.md', 'hello')
        doc = self.mk('README.md', '[Guide](docs/guide.md)')
        report = inspect(self.root, load_map(self.root), ['README.md'])
        result = apply_fixes(self.root, report, self.external_backup)
        self.assertEqual(result[0]['status'], 'fixed')
        self.assertEqual(doc.read_text(), '[Guide](docs/Guide.md)')
        self.assertEqual(restore(self.root, result[0]['backup_manifest'])['status'], 'restored')
        self.assertEqual(doc.read_text(), '[Guide](docs/guide.md)')

    def test_conflicting_edit_blocks_fix(self):
        self.mk('docs/Guide.md', 'hello')
        doc=self.mk('README.md', '[Guide](docs/guide.md)')
        report = inspect(self.root, load_map(self.root), ['README.md'])
        doc.write_text('user changed')
        result = apply_fixes(self.root, report, self.external_backup)
        self.assertEqual(result[0]['status'], 'blocked')
        self.assertEqual(doc.read_text(), 'user changed')

    def test_conflicting_edit_blocks_restore(self):
        self.mk('docs/Guide.md', 'hello')
        doc=self.mk('README.md', '[Guide](docs/guide.md)')
        result = apply_fixes(self.root, inspect(self.root, load_map(self.root), ['README.md']), self.external_backup)
        doc.write_text('later human update')
        self.assertRaises(InventoryError, restore, self.root, result[0]['backup_manifest'])
        self.assertEqual(doc.read_text(), 'later human update')

    def test_full_report_previous_comparison(self):
        self.mk('README.md', '[Broken](missing.md)')
        report=inspect(self.root, load_map(self.root))
        a=write_report(self.root, report)
        b=write_report(self.root, report)
        self.assertNotEqual(a, b)
        self.assertIn('Previous counts', (self.root / b).read_text())

    def test_targeted_no_report(self):
        self.mk('README.md', '[Broken](missing.md)')
        report=inspect(self.root, load_map(self.root), ['VERSION.md'])
        self.assertEqual(report['scanned_docs'], 1)
        self.assertFalse(any(x['kind']=='broken_link' for x in report['findings']))

    def test_map_symlink_refused(self):
        original=self.root/'fact-owners.toml'
        backup=self.root/'owner.bak';original.rename(backup)
        original.symlink_to(backup)
        self.assertRaises(InventoryError, load_map, self.root)

    def test_no_file_write_without_opt_in(self):
        self.mk('docs/Guide.md', 'hello')
        doc=self.mk('README.md', '[Guide](docs/guide.md)')
        result=inspect(self.root, load_map(self.root), ['README.md'])
        self.assertTrue(result['candidate_fixes'])
        self.assertEqual(doc.read_text(), '[Guide](docs/guide.md)')

    def test_report_requires_full_scan_cli(self):
        self.assertEqual(main(['--root', str(self.root), '--changed', 'VERSION.md', '--save-report']), 2)

    def test_read_safe_rejects_oversize(self):
        self.mk('large.md', 'x'*1025)
        self.assertRaises(InventoryError, read_safe, self.root, 'large.md', 1024)

    def test_case_ambiguity_disables_fix(self):
        self.mk('docs/Guide.md','A')
        self.mk('docs/GUIDE.md','B')
        self.mk('README.md','[Guide](docs/guide.md)')
        result=inspect(self.root, load_map(self.root), ['README.md'])
        self.assertEqual(result['candidate_fixes'], [])

    def test_backup_cannot_be_within_project(self):
        self.mk('docs/Guide.md','A')
        self.mk('README.md','[Guide](docs/guide.md)')
        self.assertRaises(InventoryError,apply_fixes,self.root,inspect(self.root,load_map(self.root), ['README.md']),str(self.root/'baks'))

if __name__ == '__main__': unittest.main()
