#!/usr/bin/env python3
"""Conservative, session-triggered Codex project MCP manager (Python 3.11+).

Never downloads or launches MCPs. Auto-updates only already approved local
release files with exact SHA-256 and unchanged declared tool contracts/rights.
Configuration writes are confined to a uniquely owned TOML block, with CAS,
locked private backups, and explicit approval for initial installation/rollback.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import tomllib
import fcntl
from contextlib import contextmanager

START = '# BEGIN CODEX-PRACTICES-MCP-MANAGED\n'
END = '# END CODEX-PRACTICES-MCP-MANAGED\n'
NAME = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{0,40}$')
SHA = re.compile(r'^[a-f0-9]{64}$')
VERSION = re.compile(r'^\d+\.\d+\.\d+$')
MODES = {'auto', 'prompt', 'writes', 'approve'}
MAX_POLICY = 128_000

class Error(Exception):
    pass

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read_regular(path, maximum=1_000_000, required=True):
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        if required: raise Error('File absent: ' + str(path))
        return b''
    if path.is_symlink() or not path.is_file():
        raise Error('Unsafe non-regular or symlink file: ' + str(path))
    if path.stat().st_size > maximum:
        raise Error('Input too large: ' + str(path))
    return path.read_bytes()

def parse_toml(data):
    try:
        return tomllib.loads(data.decode('utf-8')) if data else {}
    except (UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise Error('Invalid Codex config.toml') from exc

def policy_load(path):
    raw = read_regular(path, MAX_POLICY)
    try: p = json.loads(raw)
    except ValueError as exc: raise Error('Invalid trust policy JSON') from exc
    if not isinstance(p, dict) or set(p) != {'version','servers'} or p['version'] != 1 or not isinstance(p['servers'], list):
        raise Error('Unexpected policy schema')
    if not 1 <= len(p['servers']) <= 30: raise Error('Policy must list 1..30 servers')
    seen = set()
    for s in p['servers']:
        if not isinstance(s, dict): raise Error('Invalid server')
        shared = {'name','transport','enabled_tools','approval','required','auto_disable_after'}
        transport = s.get('transport')
        needed = shared | ({'url'} if transport=='http' else {'root','releases','initial_version','contract_sha256','auto_update'} if transport=='stdio' else {'INVALID'})
        if set(s) != needed: raise Error('Unexpected server schema for '+str(s.get('name')))
        n=s['name']
        if not isinstance(n,str) or not NAME.fullmatch(n) or n in seen: raise Error('Invalid or duplicate server name')
        seen.add(n)
        if not isinstance(s['enabled_tools'],list) or not s['enabled_tools'] or len(s['enabled_tools'])>40 or any(not isinstance(t,str) or not NAME.fullmatch(t) for t in s['enabled_tools']) or len(set(s['enabled_tools']))!=len(s['enabled_tools']):
            raise Error('Invalid explicit tool allowlist')
        if s['approval'] not in MODES or type(s['required']) is not bool or type(s['auto_disable_after']) is not int or not (2<=s['auto_disable_after']<=20):
            raise Error('Invalid approval/required/threshold')
        if s['required'] and s['auto_disable_after'] != 3:
            raise Error('Required servers use default threshold of 3 (not auto-disabled)')
        if transport=='http':
            from urllib.parse import urlsplit
            u=urlsplit(s['url']) if isinstance(s['url'],str) else None
            if not u or u.scheme!='https' or not u.netloc or u.username or u.password or u.fragment or u.query:
                raise Error('HTTP MCP must have an absolute HTTPS URL without credentials')
        else:
            root=Path(s['root']) if isinstance(s['root'],str) else Path('.')
            if not root.is_absolute() or '..' in root.parts: raise Error('stdio trusted release root must be absolute')
            if not isinstance(s['auto_update'],bool) or not isinstance(s['contract_sha256'],str) or not SHA.fullmatch(s['contract_sha256']):
                raise Error('Invalid stdio trust specification')
            releases=s['releases']
            if not isinstance(releases,list) or not 1<=len(releases)<=30: raise Error('Invalid release list')
            versions=set()
            for release in releases:
                if not isinstance(release,dict) or set(release)!={'version','file','sha256','contract_sha256'}: raise Error('Invalid release schema')
                v=release['version']
                if not isinstance(v,str) or not VERSION.fullmatch(v) or v in versions: raise Error('Invalid or duplicate version')
                versions.add(v)
                if not isinstance(release['file'],str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,90}',release['file']) or release['file'] in ('.','..'):
                    raise Error('Release file must be a basename under trusted root')
                if not isinstance(release['sha256'],str) or not SHA.fullmatch(release['sha256']) or release['contract_sha256']!=s['contract_sha256']:
                    raise Error('Release hash/contract not preapproved')
            if s['initial_version'] not in versions: raise Error('Missing initial_version')
    return p,digest(raw)

def project_paths(project, state_root=None):
    p=Path(project).expanduser().resolve(strict=True)
    if not p.is_dir(): raise Error('Not a project directory')
    config=p/'.codex/config.toml'
    if config.parent.is_symlink() or config.is_symlink(): raise Error('Refusing symlinked Codex configuration')
    root=Path(state_root).expanduser().absolute() if state_root else Path.home()/'.local/state/codex-practices/mcp'/digest(str(p).encode())[:18]
    if root==p or p in root.parents: raise Error('Private state/backup directory cannot be inside project')
    return p,config,root

@contextmanager
def lock(root):
    if root.is_symlink(): raise Error('Symlinked state directory')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(root,0o700)
    path=root/'lock'
    if path.is_symlink(): raise Error('Symlinked lock')
    with path.open('a+b') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try: yield
        finally: fcntl.flock(f,fcntl.LOCK_UN)

def state_read(root, required=True):
    raw=read_regular(root/'state.json',MAX_POLICY,required=required)
    if not raw: return None
    try: data=json.loads(raw)
    except ValueError as exc: raise Error('Invalid private state') from exc
    if not isinstance(data,dict) or data.get('version')!=1: raise Error('Invalid state version')
    return data

def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.mcp-tmp-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            os.fchmod(f.fileno(),mode)
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
        dirfd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(dirfd)
        finally:os.close(dirfd)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def state_write(root,state):
    atomic_write(root/'state.json',json.dumps(state,indent=2,sort_keys=True).encode()+b'\n')

def release_valid(s,r):
    root=Path(s['root'])
    if root.is_symlink() or not root.is_dir():return False
    for parent in (root,*root.parents):
        if parent.is_symlink():return False
    if root.stat().st_mode & 0o022:return False
    path=root/r['file']
    if path.is_symlink() or not path.is_file():return False
    st=path.stat()
    if not (st.st_mode & stat.S_IXUSR) or (st.st_mode & 0o022) or st.st_size>50_000_000:return False
    return digest(path.read_bytes())==r['sha256']

def versions(s):
    return {r['version']:r for r in s['releases']}

def desired(s,current=None,disabled=False):
    keys=['[mcp_servers.'+s['name']+']']
    if s['transport']=='http':keys.append('url = '+json.dumps(s['url']))
    else:
        r=versions(s)[current or s['initial_version']]
        keys.append('command = '+json.dumps(str(Path(s['root'])/r['file'])))
    keys+=['enabled = '+('false' if disabled else 'true'),'required = '+('true' if s['required'] else 'false'),
           'enabled_tools = '+json.dumps(s['enabled_tools']),
           'default_tools_approval_mode = '+json.dumps(s['approval'])]
    return '\n'.join(keys)+'\n'

def replace_block(data,servers,current,disabled):
    text=data.decode('utf-8')
    has=START in text or END in text
    if has and (text.count(START)!=1 or text.count(END)!=1 or text.index(END)<text.index(START)):
        raise Error('Invalid managed markers')
    block=START+('\n'.join(desired(s,current.get(s['name']),s['name'] in disabled) for s in servers))+END
    if has:
        a=text.index(START);b=text.index(END)+len(END)
        output=text[:a]+block+text[b:]
    else:
        previous=parse_toml(data).get('mcp_servers',{})
        if not isinstance(previous,dict):raise Error('mcp_servers table must be a map')
        if set(previous).intersection({s['name'] for s in servers}):raise Error('Refusing to overwrite user-owned MCP entries')
        output=text.rstrip('\n')+'\n\n'+block if text else block
    parsed=parse_toml(output.encode())
    if not all(s['name'] in parsed.get('mcp_servers',{}) for s in servers):raise Error('Generated config missing servers')
    return output.encode()

def backup(root,data):
    folder=root/'backups'
    if folder.is_symlink():raise Error('Unsafe backup dir')
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    name='cfg-'+digest(data)+'-'+os.urandom(5).hex()+'.bak'
    atomic_write(folder/name,data)
    return name

def mutate(config,root,state,new_config,new_current,new_disabled):
    old=read_regular(config,required=False)
    if digest(old)!=state['config_sha']:raise Error('Codex config changed since snapshot; no write')
    if old==new_config:return False
    b=backup(root,old)
    entry={'file':b,'before_sha':digest(old),'after_sha':digest(new_config),
           'current':state['current'],'disabled':state['disabled']}
    if config.exists(): mode=stat.S_IMODE(config.stat().st_mode)&0o600
    else: mode=0o600
    atomic_write(config,new_config,mode or 0o600)
    state['history'].append(entry)
    state['config_sha']=digest(new_config)
    state['current']=new_current
    state['disabled']=sorted(new_disabled)
    state_write(root,state)
    return True

def audit(config):
    data=read_regular(config,required=False)
    parsed=parse_toml(data)
    services=parsed.get('mcp_servers',{})
    if not isinstance(services,dict):raise Error('Invalid mcp_servers')
    names=[{'name':n, 'enabled':v.get('enabled',True),
            'tools':v.get('enabled_tools',[]),'approval':v.get('default_tools_approval_mode','unset')}
           for n,v in services.items() if isinstance(v,dict)]
    return {'config_present':bool(data),'config_sha256':digest(data),
            'managed_block':START in data.decode('utf-8'), 'servers':names}

def fresh_config(config,root,state,polsha):
    if not state or state['policy_sha']!=polsha:raise Error('Trust policy changed or not approved; explicit new review required')
    old=read_regular(config,required=False)
    if digest(old)!=state['config_sha']:raise Error('External changes to Codex config; refusing automation')
    return old

def plan(policy,state):
    changes=[]
    for s in policy['servers']:
        n=s['name']
        if s['transport']=='stdio':
            current=(state['current'].get(n) if state else s['initial_version'])
            candidates=[r for r in s['releases'] if tuple(map(int,r['version'].split('.')))>tuple(map(int,current.split('.'))) and release_valid(s,r)]
            if candidates and s['auto_update']:
                latest=max(candidates,key=lambda r:tuple(map(int,r['version'].split('.'))))
                changes.append({'name':n,'action':'upgrade','from':current,'to':latest['version']})
        if state and not s['required']:
            if n not in state['disabled'] and state['failures'][n]>=s['auto_disable_after']:
                changes.append({'name':n,'action':'disable','failures':state['failures'][n]})
            if n in state['disabled'] and state['failures'][n]==0:
                changes.append({'name':n,'action':'enable','reason':'successful independently verified health evidence recorded'})
    return changes

def preview_configuration(config, policy, state):
    """Read-only, redacted preview of the precise proposed managed TOML change.

    Never return existing config bodies, endpoint URLs or executable locations.
    """
    before=read_regular(config,required=False)
    planned=plan(policy,state)
    current=dict(state['current']) if state else {
        s['name']:s['initial_version'] for s in policy['servers'] if s['transport']=='stdio'
    }
    disabled=set(state['disabled']) if state else set()
    for item in planned:
        if item['action']=='upgrade': current[item['name']]=item['to']
        elif item['action']=='disable': disabled.add(item['name'])
        elif item['action']=='enable': disabled.discard(item['name'])
    after=replace_block(before,policy['servers'],current,disabled)
    servers=[]
    for item in policy['servers']:
        info={'name':item['name'],'transport':item['transport'],
              'tools':item['enabled_tools'],'approval':item['approval'],
              'required':item['required'],'enabled':item['name'] not in disabled}
        if item['transport']=='stdio':
            version=current[item['name']]
            info['local_version']=version
            info['local_executable_hash_verified']=release_valid(item,versions(item)[version])
        else:
            info['endpoint']='redacted: review approved trust policy locally'
        servers.append(info)
    return {'config_path':str(config),'before_sha256':digest(before),
            'after_sha256':digest(after),
            'will_create_config':not config.exists(),
            'would_modify_config':before!=after,
            'managed_block_action':'update' if state else 'create',
            'planned_mcp_entries':servers,
            'user_config_body_redacted':True,
            'effective_runtime_permissions_verified':False}


def initial(project,config,root,policy,sha,expected):
    if state_read(root,required=False):raise Error('Already managed; use maintain, not initial apply')
    old=read_regular(config,required=False)
    if START.encode() in old or END.encode() in old:
        raise Error('Managed markers already exist but ownership is unknown')
    if digest(old)!=expected:raise Error('Config SHA mismatch')
    current={s['name']:s['initial_version'] for s in policy['servers'] if s['transport']=='stdio'}
    for s in policy['servers']:
        if s['transport']=='stdio' and not release_valid(s,versions(s)[s['initial_version']]):
            raise Error('Initial executable absent/untrusted: '+s['name'])
    new=replace_block(old,policy['servers'],current,set())
    state={'version':1,'policy_sha':sha,'config_sha':digest(old),'current':{},'disabled':[],
           'failures':{s['name']:0 for s in policy['servers']},'evidence':{s['name']:[] for s in policy['servers']},'history':[]}
    mutate(config,root,state,new,current,set())
    return {'action':'installed','servers':[s['name'] for s in policy['servers']]}

def maintain(config,root,policy,sha):
    st=state_read(root)
    old=fresh_config(config,root,st,sha)
    changes=plan(policy,st)
    if not changes:return {'action':'unchanged','changes':[]}
    current=dict(st['current']);disabled=set(st['disabled'])
    for change in changes:
        if change['action']=='upgrade':current[change['name']]=change['to']
        if change['action']=='disable':disabled.add(change['name'])
        if change['action']=='enable':disabled.remove(change['name'])
    new=replace_block(old,policy['servers'],current,disabled)
    mutate(config,root,st,new,current,disabled)
    return {'action':'maintained','changes':changes}

def record(root,config,sha,policy,name,result,evidence_path,attested_sha=None,confirmation=None):
    st=state_read(root)
    fresh_config(config,root,st,sha)
    if name not in st['failures']:raise Error('Server not enrolled')
    evidence=read_regular(evidence_path,512_000)
    if not evidence.strip():raise Error('Empty evidence')
    h=digest(evidence)
    attested=attested_sha is not None
    if attested:
        if not isinstance(attested_sha,str) or not SHA.fullmatch(attested_sha) or h!=attested_sha:
            raise Error('Evidence hash differs from explicit independent review')
        if confirmation!='VERIFIED_HEALTH_EVIDENCE':
            raise Error('Verified evidence requires explicit operator confirmation')
    elif confirmation is not None:
        raise Error('Confirmation without an attested SHA is invalid')
    if h in st['evidence'][name]:raise Error('Evidence already recorded')
    st['evidence'][name]=(st['evidence'][name]+[h])[-30:]
    # Mere log files/observations cannot drive automatic disabling or recovery.
    if attested:
        st['failures'][name]=st['failures'][name]+1 if result=='fail' else 0
    state_write(root,st)
    return {'name':name,'consecutive_verified_failures':st['failures'][name],
            'recorded':True,'eligible_for_automation':attested,
            'attestation_limit':'SHA and token prove operator intent, not the truth or origin of evidence'}

def rollback(config,root,sha):
    st=state_read(root)
    if st['policy_sha']!=sha:raise Error('Trust policy mismatch')
    old=read_regular(config,required=False)
    if digest(old)!=st['config_sha']:raise Error('Config changed, cannot rollback automatically')
    if not st['history']:raise Error('No backup to restore')
    prev=st['history'][-1]
    restore=read_regular(root/'backups'/prev['file'])
    if digest(restore)!=prev['before_sha']:raise Error('Backup hash mismatch')
    if not restore and len(st['history'])==1:
        if config.exists():config.unlink()
    else:
        atomic_write(config,restore)
    st['config_sha']=digest(restore)
    st['current']=prev['current'];st['disabled']=prev['disabled']
    st['history'].pop()
    if st['history']:state_write(root,st)
    else:(root/'state.json').unlink()
    return {'action':'rolled_back','restored_sha256':digest(restore)}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project',required=True)
    ap.add_argument('--policy',help='Approved local JSON trust policy')
    ap.add_argument('--state-root',help='Private state outside project; for testing/custom deployment')
    sub=ap.add_subparsers(dest='action',required=True)
    sub.add_parser('audit');sub.add_parser('plan')
    a=sub.add_parser('apply');a.add_argument('--expected-config-sha',required=True);a.add_argument('--expected-policy-sha',required=True);a.add_argument('--confirm',required=True)
    sub.add_parser('maintain')
    rec=sub.add_parser('record');rec.add_argument('--server',required=True);rec.add_argument('--result',choices=['pass','fail'],required=True);rec.add_argument('--evidence',required=True)
    rec.add_argument('--attest-evidence-sha',help='SHA-256 reviewed separately by an operator')
    rec.add_argument('--confirm',help='Required for attested evidence only')
    rb=sub.add_parser('rollback');rb.add_argument('--confirm',required=True)
    args=ap.parse_args(argv)
    try:
        project,config,root=project_paths(args.project,args.state_root)
        if args.action=='audit':result=audit(config)
        else:
            if not args.policy:raise Error('--policy required')
            policy,sha=policy_load(args.policy)
            if args.action=='plan':
                # A preview must not create the private state/lock directory.
                st=state_read(root,required=False)
                if st: fresh_config(config,root,st,sha)
                result={'policy_sha256':sha,'approved':bool(st),'changes':plan(policy,st),
                        'initial_install_requires_approval':not bool(st),
                        'config_preview':preview_configuration(config,policy,st)}
            else:
              with lock(root):
                st=state_read(root,required=False)
                if args.action=='apply':
                    if args.confirm!='INSTALL_APPROVED_MCP' or sha!=args.expected_policy_sha:raise Error('Initial installation consent/policy hash mismatch')
                    result=initial(project,config,root,policy,sha,args.expected_config_sha)
                elif args.action=='maintain':result=maintain(config,root,policy,sha)
                elif args.action=='record':result=record(root,config,sha,policy,args.server,args.result,args.evidence,args.attest_evidence_sha,args.confirm)
                elif args.action=='rollback':
                    if args.confirm!='RESTORE_PREVIOUS_MCP':raise Error('Rollback requires explicit confirmation')
                    result=rollback(config,root,sha)
                else:raise Error('Unexpected action')
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
        return 0
    except (Error,OSError,KeyError,TypeError,UnicodeError,ValueError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
