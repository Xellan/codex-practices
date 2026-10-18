#!/usr/bin/env python3
"""Validate signed-off verification evidence, never execute tests or assert unknown PASS."""
import argparse
import json
from pathlib import Path
import sys

OUTCOMES={'PASS','FAIL','NOT_RUN','BLOCKED'}
LEVELS={'light','standard','strict'}


def evaluate(data):
    if not isinstance(data,dict) or set(data)!={'level','checks'} or data['level'] not in LEVELS or not isinstance(data['checks'],list):
        raise ValueError('Expected {level: light|standard|strict, checks: [...]}')
    if not data['checks']:
        raise ValueError('At least one check is required')
    checked=[]
    for c in data['checks']:
        if not isinstance(c,dict) or set(c)!={'name','status','evidence','critical'}:
            raise ValueError('Each check requires name,status,evidence,critical')
        if not isinstance(c['name'],str) or not c['name'].strip() or c['status'] not in OUTCOMES or type(c['critical']) is not bool:
            raise ValueError('Invalid check')
        if not isinstance(c['evidence'],str):raise ValueError('evidence must be text')
        if c['status']=='PASS' and not c['evidence'].strip():
            raise ValueError('PASS requires an evidence reference; do not fabricate it')
        checked.append(c)
    statuses={c['status'] for c in checked}
    if 'FAIL' in statuses: result='Failed'
    elif 'BLOCKED' in statuses:result='Blocked'
    elif 'NOT_RUN' in statuses:result='Partially Verified'
    else:result='Verified'
    return {'status':result,'level':data['level'],'checks_total':len(checked),
            'critical_incomplete':[c['name'] for c in checked if c['critical'] and c['status']!='PASS'],
            'counts':{s:sum(c['status']==s for c in checked) for s in sorted(OUTCOMES)}}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True)
    a=p.parse_args(argv)
    try:
        path=Path(a.input)
        if path.is_symlink() or path.stat().st_size>128_000:raise ValueError('Input unsafe or too large')
        report=evaluate(json.loads(path.read_text(encoding='utf-8')))
    except (ValueError,OSError,KeyError,TypeError) as e:
        print(f'ERROR: {e}',file=sys.stderr);return 2
    print(json.dumps(report,sort_keys=True))
    return 0 if report['status']=='Verified' else 1
if __name__=='__main__':sys.exit(main())
