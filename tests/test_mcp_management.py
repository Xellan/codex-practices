import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'skills/mcp-management/scripts/mcp_manager.py'
def sha(data):return hashlib.sha256(data).hexdigest()

class MCPManagementTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.project=self.root/'project';self.project.mkdir()
        self.private=self.root/'private';self.releases=self.root/'trusted';self.releases.mkdir()
        self.stage('1.0.0',b'#!/bin/sh\necho v1\n')
        self.policy_file=self.root/'policy.json'
        self.policy={'version':1,'servers':[
            {'name':'alpha','transport':'stdio','root':str(self.releases),'initial_version':'1.0.0',
             'contract_sha256':'a'*64,'auto_update':True,
             'releases':[self.stage('1.0.0',b'#!/bin/sh\necho v1\n')],
             'enabled_tools':['search'],'approval':'auto','required':False,'auto_disable_after':3},
            {'name':'docs','transport':'http','url':'https://example.org/mcp',
             'enabled_tools':['search'],'approval':'prompt','required':True,'auto_disable_after':3}
        ]}
        self.save_policy();self.config=self.project/'.codex/config.toml'

    def stage(self,v,content):
        path=self.releases/('server-'+v);path.write_bytes(content);path.chmod(0o700)
        return {'version':v,'file':path.name,'sha256':sha(content),'contract_sha256':'a'*64}

    def save_policy(self):
        self.policy_file.write_text(json.dumps(self.policy))

    def run_cli(self,action,*args):
        return subprocess.run([sys.executable,str(SCRIPT),'--project',str(self.project),
                               '--policy',str(self.policy_file),'--state-root',str(self.private),
                               action,*args],capture_output=True,text=True)

    def approved_install(self):
        before=self.config.read_bytes() if self.config.exists() else b''
        result=self.run_cli('apply','--expected-config-sha',sha(before),
                            '--expected-policy-sha',sha(self.policy_file.read_bytes()),
                            '--confirm','INSTALL_APPROVED_MCP')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_audit_is_read_only(self):
        result=self.run_cli('audit')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(self.config.exists())
        self.assertTrue(json.loads(self.run_cli('plan').stdout)['initial_install_requires_approval'])

    def test_requires_explicit_consent(self):
        result=self.run_cli('apply','--expected-config-sha',sha(b''),
                            '--expected-policy-sha',sha(self.policy_file.read_bytes()),
                            '--confirm','NO')
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(self.config.exists())

    def test_preserves_user_configuration_and_rollback(self):
        self.config.parent.mkdir();initial=b'model = "custom"\n\n[features]\nx = true\n'
        self.config.write_bytes(initial)
        self.approved_install()
        self.assertIn('model = "custom"',self.config.read_text())
        self.assertIn('enabled_tools = ["search"]',self.config.read_text())
        result=self.run_cli('rollback','--confirm','RESTORE_PREVIOUS_MCP')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.config.read_bytes(),initial)

    def test_refuse_user_owned_mcp_and_unknown_block(self):
        self.config.parent.mkdir()
        self.config.write_text('[mcp_servers.docs]\nurl="https://another.example/mcp"\n')
        before=self.config.read_bytes()
        result=self.run_cli('apply','--expected-config-sha',sha(before),
                            '--expected-policy-sha',sha(self.policy_file.read_bytes()),
                            '--confirm','INSTALL_APPROVED_MCP')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.config.read_bytes(),before)

    def test_upgrade_staged_immutable_artifact(self):
        future=self.stage('1.1.0',b'#!/bin/sh\necho v2\n')
        self.policy['servers'][0]['releases'].append(future);self.save_policy()
        self.approved_install()
        (self.releases/future['file']).unlink()
        self.assertEqual(json.loads(self.run_cli('maintain').stdout)['action'],'unchanged')
        self.stage('1.1.0',b'#!/bin/sh\necho v2\n')
        self.assertEqual(self.run_cli('maintain').returncode,0)
        self.assertIn('server-1.1.0',self.config.read_text())

    def test_unapproved_artifact_is_not_upgraded(self):
        future=self.stage('1.1.0',b'#!/bin/sh\necho v2\n')
        self.policy['servers'][0]['releases'].append(future);self.save_policy()
        self.approved_install()
        (self.releases/future['file']).write_text('different bytes')
        self.assertEqual(json.loads(self.run_cli('maintain').stdout)['action'],'unchanged')
        self.assertIn('server-1.0.0',self.config.read_text())

    def test_policy_tampering_fails_closed(self):
        self.approved_install()
        self.policy['servers'][0]['enabled_tools'].append('write');self.save_policy()
        self.assertNotEqual(self.run_cli('maintain').returncode,0)
        self.assertNotIn('write',self.config.read_text())

    def test_external_config_changes_not_overwritten(self):
        self.approved_install()
        self.config.write_text(self.config.read_text()+'\n# user change\n')
        self.assertNotEqual(self.run_cli('maintain').returncode,0)
        self.assertIn('user change',self.config.read_text())

    def test_distinct_health_failures_disable_optional_only(self):
        self.approved_install()
        for i in range(3):
            evidence=self.root/f'fail-{i}.txt';evidence.write_text(f'Observation #{i}')
            for name in ['alpha','docs']:
                r=self.run_cli('record','--server',name,'--result','fail','--evidence',str(evidence))
                self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(self.run_cli('maintain').returncode,0)
        import tomllib
        with self.config.open('rb') as f:servers=tomllib.load(f)['mcp_servers']
        self.assertFalse(servers['alpha']['enabled'])
        self.assertTrue(servers['docs']['enabled'])
        good=self.root/'good.txt';good.write_text('verified healthy')
        self.assertEqual(self.run_cli('record','--server','alpha','--result','pass','--evidence',str(good)).returncode,0)
        self.assertEqual(self.run_cli('maintain').returncode,0)
        with self.config.open('rb') as f:servers=tomllib.load(f)['mcp_servers']
        self.assertTrue(servers['alpha']['enabled'])

    def test_duplicate_evidence_refused(self):
        self.approved_install()
        p=self.root/'fail.txt';p.write_text('startup failed')
        self.assertEqual(self.run_cli('record','--server','alpha','--result','fail','--evidence',str(p)).returncode,0)
        self.assertNotEqual(self.run_cli('record','--server','alpha','--result','fail','--evidence',str(p)).returncode,0)

    def test_config_symlink_refused(self):
        other=self.root/'original';other.write_text('model="safe"')
        self.config.parent.mkdir();self.config.symlink_to(other)
        self.assertNotEqual(self.run_cli('audit').returncode,0)
        self.assertEqual(other.read_text(),'model="safe"')

if __name__=='__main__':unittest.main()
