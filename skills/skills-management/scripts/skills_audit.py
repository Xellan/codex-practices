#!/usr/bin/env python3
"""Read-only installed Skill discovery/validation. Does not install or execute skills."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

FRONT = re.compile(r'\A---\s*\n(.*?)\n---\s*\n',re.S)
FIELD = re.compile(r'^(name|description):\s*(.+)$',re.M)


def check_skill(folder):
    manifest=folder/'SKILL.md'
    if folder.is_symlink() or manifest.is_symlink() or not manifest.is_file():
        return {'path':str(folder),'status':'unsafe_or_missing'}
    if manifest.stat().st_size>64_000:
        return {'path':str(folder),'status':'oversized'}
    text=manifest.read_text(encoding='utf-8')
    match=FRONT.match(text)
    fields=dict(FIELD.findall(match.group(1))) if match else {}
    name=fields.get('name','').strip('"\'')
    description=fields.get('description','').strip('"\'')
    valid=bool(re.fullmatch('[a-z0-9][a-z0-9-]{0,63}',name) and description)
    scripts=(folder/'scripts').exists()
    return {'path':str(folder),'name':name or folder.name,'description':description[:180],
            'status':'valid' if valid else 'invalid_manifest','scripts_present':scripts}


def discover(project, home):
    project=Path(project).resolve(strict=True)
    if not project.is_dir(): raise ValueError('Project must be directory')
    roots=[('project',project/'.agents'/'skills'),('global',Path(home).expanduser()/'skills')]
    found=[]
    for scope,root in roots:
        if not root.exists():continue
        if root.is_symlink():
            found.append({'scope':scope,'path':str(root),'status':'unsafe_root'});continue
        if not root.is_dir():continue
        for path in sorted(root.iterdir()):
            if path.is_dir() or path.is_symlink():
                record=check_skill(path);record['scope']=scope;found.append(record)
    seen={}
    for item in found:
        n=item.get('name','').lower()
        if not n: continue
        if n in seen:
            item['collision_with']=seen[n]
        else:seen[n]=item['path']
    return {'project':str(project),'skills':found,'conflicts':sum('collision_with' in x for x in found)}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',required=True)
    p.add_argument('--codex-home',default=os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))
    a=p.parse_args(argv)
    try:result=discover(a.project,a.codex_home)
    except (OSError,ValueError,UnicodeError) as e:
        print(f'ERROR: {e}',file=sys.stderr);return 2
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__':sys.exit(main())
