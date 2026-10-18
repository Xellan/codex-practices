#!/usr/bin/env python3
"""Read-only bounded prompt-injection heuristic scanner. No content is executed."""
import argparse
import base64
import json
from pathlib import Path
import re
import sys

HIGH_NAMES = {'agents.md', 'agents.override.md', 'claude.md', '.cursorrules', '.github/copilot-instructions.md'}
TEXT_TYPES = {'.md','.txt','.rst','.yaml','.yml','.toml','.json','.sh','.py'}
OVERRIDE = re.compile(r'(ignore|override|disregard|forget).{0,80}(previous|prior|system|developer|instructions|rules)|(?:игнорируй|забудь|отмени).{0,70}(инструкц|правил|системн)',re.I|re.S)
EXFIL = re.compile(r'(send|upload|post|transmit|leak|exfiltrat|отправь|передай).{0,110}(secret|token|credential|password|api.key|ключ|парол|\.env)|curl.{0,80}(\.env|private.key|token)',re.I|re.S)
ROLE = re.compile(r'\b(system|developer)\s*:\s*|<\|im_start\|>|\[INST\]',re.I)
UNICODE = re.compile('[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]')
B64 = re.compile(r'(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{64,}={0,2}(?![A-Za-z0-9+/])')
MAX_FILE = 256_000


def inspect(content):
    signs=[]
    override=bool(OVERRIDE.search(content))
    exfil=bool(EXFIL.search(content))
    if override: signs.append('instruction_override')
    if exfil: signs.append('possible_exfiltration')
    if ROLE.search(content): signs.append('role_spoofing')
    if UNICODE.search(content): signs.append('hidden_unicode')
    if B64.search(content):
        signs.append('encoded_block')
        for match in list(B64.finditer(content))[:5]:
            try:
                decoded=base64.b64decode(match.group(), validate=True)[:800].decode('utf-8')
                if OVERRIDE.search(decoded) or EXFIL.search(decoded):
                    signs.append('encoded_instruction')
                    break
            except (ValueError, UnicodeError):
                pass
    risk='high' if (override and (exfil or 'role_spoofing' in signs)) or 'encoded_instruction' in signs else ('medium' if signs else 'low')
    return risk, sorted(set(signs))


def scan(root, max_files=250):
    root=Path(root).resolve(strict=True)
    if not root.is_dir(): raise ValueError('root must be a directory')
    findings=[]; inspected=0; skipped=0
    ranked=[]
    for path in root.rglob('*'):
        if any(part in {'.git','node_modules','.venv','vendor'} for part in path.relative_to(root).parts): continue
        if not path.is_file() or path.is_symlink():
            if path.is_symlink(): skipped+=1
            continue
        rel=path.relative_to(root).as_posix()
        if path.suffix.lower() not in TEXT_TYPES and path.name.lower() not in HIGH_NAMES: continue
        priority=0 if rel.lower() in HIGH_NAMES or path.name.lower() in HIGH_NAMES else (1 if path.name.lower()=='readme.md' else 2)
        ranked.append((priority,rel,path))
        if len(ranked)>5000: break
    for _,rel,path in sorted(ranked)[:max_files]:
        try:
            if path.stat().st_size>MAX_FILE: skipped+=1;continue
            raw=path.read_bytes()
            if b'\x00' in raw:skipped+=1;continue
            content=raw.decode('utf-8')
            risk,signals=inspect(content)
            inspected+=1
            if signals:
                findings.append({'source':rel,'risk':risk,'signals':signals})
        except (OSError,UnicodeError):skipped+=1
    result={'root':str(root),'inspected':inspected,'skipped':skipped,'truncated':len(ranked)>max_files or len(ranked)>5000,'findings':findings}
    result['risk']='high' if any(f['risk']=='high' for f in findings) else ('medium' if findings or result['truncated'] else 'low')
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True)
    p.add_argument('--max-files',type=int,default=250)
    a=p.parse_args(argv)
    if not 1<=a.max_files<=1000:p.error('--max-files must be 1..1000')
    try:r=scan(a.root,a.max_files)
    except (ValueError,OSError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);return 2
    print(json.dumps(r,ensure_ascii=False,sort_keys=True))
    return 3 if r['risk']=='high' else 0

if __name__=='__main__':sys.exit(main())
