"""Require nonempty test collections and matching fresh platform reports."""
import argparse
import json
import hashlib
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def verify(root, head, platform):
    if (root/'source_head.txt').read_text(encoding='utf-8').strip()!=head:
        raise ValueError('Checked-out source does not match the expected HEAD.')
    for filename in ('pytest.xml','ctest.xml'):
        tree=ET.parse(root/filename)
        cases=list(tree.iter('testcase'))
        if not cases or any(c.find(tag) is not None for c in cases for tag in ('failure','error','skipped')):
            raise ValueError('Empty, failed, errored or skipped tests: '+filename)
    required=['source_desktop','frozen_desktop']
    if platform=='linux':required+=['source_web','frozen_web']
    reports={};run_ids=set()
    for key in required:
        r=json.loads((root/key/'DISTRIBUTION_RESULT.json').read_text(encoding='utf-8'))
        if r.get('status')!='PASS' or r.get('source_head')!=head or not r.get('file_dialogs'):
            raise ValueError('Missing exact-head qualification: '+key)
        if r['run_id'] in run_ids:raise ValueError('Duplicate run identity.')
        client_path=root/key/'all_screens_smoke.json'
        if hashlib.sha256(client_path.read_bytes()).hexdigest()!=r.get('client_report_sha256'):
            raise ValueError('Client report digest mismatch: '+key)
        client=json.loads(client_path.read_text(encoding='utf-8'))
        if client.get('status')!='PASS' or client.get('run_id')!=r['run_id'] or client.get('sessions_started')!=1:
            raise ValueError('Client result or session identity mismatch: '+key)
        if len(client.get('checks',[]))<131 or len(client.get('screenshots',{}))<199:
            raise ValueError('Incomplete inventory rendering: '+key)
        for name,meta in client['screenshots'].items():
            path=root/key/(name+'.png')
            if path.parent.resolve()!=(root/key).resolve() or hashlib.sha256(path.read_bytes()).hexdigest()!=meta['sha256']:
                raise ValueError('Screenshot integrity failure: '+name)
        run_ids.add(r['run_id'])
        if r.get('clean_extraction')!=key.startswith('frozen_'):
            raise ValueError('Source/frozen scope mismatch: '+key)
        reports[key]=r
    return {'status':'PASS','source_head':head,'platform':platform,'reports':reports,
            'scope':'Rendered inventory and handler/native integration; real file dialogs. Not normative certification or full manual UX review.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--head',required=True)
    a=p.parse_args();result=verify(a.root,a.head,sys.platform)
    (a.root/'PLATFORM_GATE.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
