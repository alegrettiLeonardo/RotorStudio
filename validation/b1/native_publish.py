"""Explicit post-local-test publication, or read-only exact-head CI status.

Never merges. Refuses to commit if local evidence is missing/stale, any source
snapshot changed, the remote branch advanced, or unrelated files are staged.
GitHub CLI must already be authenticated. --status never writes repository data.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from validation.b1.native_preservation import MAIN,NEW_FILES,MODIFIED_FILES,source_snapshot,verify
REPO='alegrettiLeonardo/RotorStudio'
BRANCH='feature/ross-analysis-b1-6dof-element-matrices'
REQUIRED_PATHS={'.github/workflows/'+p for p in (
    'ross-analysis-parity.yml','ross-analysis-static.yml','ross-analysis-general-frf.yml',
    'ross-analysis-forced-response.yml','ross-analysis-time-response.yml','ross-analysis-ucs.yml',
    'a5-ucs-bearing-order.yml','ross-analysis-level1.yml','ross-analysis-api617-unbalance.yml',
    'ross-analysis-clearance.yml','ross-analysis-a8-freeze-authority.yml',
    'stage1-m7-qualification.yml','stage1-final-qualification.yml','g14-book-problems.yml',
    'stage2-ui.yml','stage2-final-qualification.yml','stage2-visual-conformance.yml',
    'dyrobes-sketch-qualification.yml','ross-bearings-native.yml',
    'b13-advanced-bearing-crud.yml','b14-async-field-visualization.yml',
    'b15-irdin-coefficient-import.yml','b16-operating-map-cache.yml',
    'b17-matched-whirl.yml','b18-synchronous-runup.yml','b13-b18-integrated-qualification.yml',
    'b1-6dof-authority.yml','ross-analysis-b1-6dof-elements.yml')}


def read(*command):
    return subprocess.check_output(command,cwd=ROOT,text=True).strip()


def execute(*command):
    print('+ '+' '.join(map(str,command)),flush=True)
    subprocess.run(command,cwd=ROOT,check=True)


def remote_head(branch):
    lines=read('git','ls-remote','--heads','origin','refs/heads/'+branch).splitlines()
    if len(lines)!=1: raise RuntimeError('Remote branch not uniquely resolved: '+branch)
    return lines[0].split()[0]


def status():
    head=read('git','rev-parse','HEAD')
    runs=[];page=1
    while True:
        endpoint=f'repos/{REPO}/actions/runs?'+urlencode({'head_sha':head,'per_page':100,'page':page})
        data=json.loads(read('gh','api',endpoint))
        batch=data.get('workflow_runs',[]);runs.extend(batch)
        if len(batch)<100: break
        page+=1
    selected={}
    for path in sorted(REQUIRED_PATHS):
        matches=[r for r in runs if r['head_sha']==head and r['path'].split('@')[0]==path and r['event'] in ('pull_request','push','workflow_dispatch')]
        pr=[r for r in matches if r['event']=='pull_request']
        candidates=pr or matches
        selected[path]=max(candidates,key=lambda r:(r['created_at'],r['run_attempt'],r['id'])) if candidates else None
    rows=[]
    for path,run in selected.items():
        row={'path':path,'run_id':run['id'] if run else None,'event':run['event'] if run else None,
             'status':run['status'] if run else 'MISSING','conclusion':run['conclusion'] if run else None}
        rows.append(row); print(json.dumps(row,sort_keys=True))
    green=all(r and r['status']=='completed' and r['conclusion']=='success' for r in selected.values())
    print(json.dumps({'head':head,'required_workflows':len(rows),'all_success':green,
                      'verdict':'REMOTE_CHECKS_SUCCESS_AWAITING_EVIDENCE_REVIEW' if green else 'REMOTE_QUALIFICATION_PENDING_OR_FAILED',
                      'promotion':'NOT_PERFORMED'},indent=2))
    return 0 if green else 2


def publish(evidence):
    evidence=evidence.resolve()
    result=json.loads((evidence/'PLATFORM_RESULT.json').read_text())
    if result['status'] not in ('SOURCE_TREE_LINUX_PASS','PLATFORM_QUALIFICATION_PASS'):
        raise RuntimeError('Local Linux qualification did not pass')
    if not result['platform'].startswith('Linux'):
        raise RuntimeError('This publication gate requires the requested local Linux run')
    if any(v['tests']<1 or any(v[k] for k in ('failures','errors','skips')) for v in result['junit'].values()):
        raise RuntimeError('Local mandatory JUnit evidence is incomplete')
    before=json.loads((evidence/'SOURCE_AFTER.json').read_text())
    current=source_snapshot(ROOT)
    if current!=before or current['sha256']!=result['source_snapshot_sha256']:
        raise RuntimeError('Source snapshot changed since local tests; rerun qualification, never relabel old evidence')
    head=read('git','rev-parse','HEAD')
    if head!=result['head']: raise RuntimeError('HEAD changed after the recorded local run')
    if read('git','branch','--show-current')!=BRANCH: raise RuntimeError('Not on the existing B1 branch')
    if read('git','diff','--cached','--name-only'): raise RuntimeError('Index is not empty; do not combine unrelated staged work')
    execute('gh','auth','status')
    execute('git','fetch','origin','--prune')
    if remote_head(BRANCH)!=head: raise RuntimeError('STOP: remote B1 advanced; preserve parallel work and reconcile before publishing')
    if remote_head('main')!=MAIN: raise RuntimeError('STOP: main advanced; revalidate inherited baseline before publishing')
    paths=sorted(NEW_FILES|MODIFIED_FILES)
    for path in paths:
        if not (ROOT/path).is_file(): raise RuntimeError('Missing payload file: '+path)
    execute('git','status','--short','--branch')
    execute('git','diff','--stat')
    # No git add -A: only the explicit B1 paths are staged.
    execute('git','add','--',*paths)
    staged=set(read('git','diff','--cached','--name-only').splitlines())
    if not staged or not staged.issubset(set(paths)): raise RuntimeError('Unexpected staged publication scope')
    execute('git','commit','-m','B1: add native 6-DOF element matrices and qualification gates',
            '-m','Local Linux source-snapshot tests passed: '+current['sha256']+'\nWindows and full exact-head CI remain pending. No B1 promotion is authorized by this commit.')
    committed=read('git','rev-parse','HEAD')
    if source_snapshot(ROOT)['sha256']!=current['sha256']: raise RuntimeError('Commit hooks changed tested source; do not push')
    execute('git','push','origin','HEAD:refs/heads/'+BRANCH)
    body=evidence/'DRAFT_PR_BODY.md'
    body.write_text(f'''## B1 native element implementation — qualification pending

Base main: `{MAIN}`
Initial local-test HEAD: `{head}`
Native candidate HEAD: `{committed}`
Local tested source SHA256: `{current['sha256']}`
Frozen ROSS: `6320eab9f890f1b3cc1710d508b446fe063ca68d`

Local Linux Release/Debug builds, all CTest, native shaft/disk comparisons,
113 primary matrices, 63 lateral selections, legacy common-domain comparison,
independent invariants, ABI/buffer negatives and inherited source-tree regressions
passed for the source snapshot recorded above. These are local execution results,
not yet the final exact-head Linux/Windows/product qualification.

Production remains Fortran 2018 with a thin internal Python binding. Historical
A0–A8 sources and frozen authorities are preserved. The B1 authority workflow stays
separate. New B1 symbols do not change existing analysis dispatch.

B1_6DOF_ELEMENT_MATRICES_ROSS_PARITY = PENDING_EXACT_HEAD_CI
PROMOTION = NOT_AUTHORIZED

Do not merge automatically. B2/B3 and fault dynamics are outside this PR.
''',encoding='utf-8')
    prs=json.loads(read('gh','pr','list','--repo',REPO,'--head',BRANCH,'--base','main','--state','open','--json','number,url,isDraft'))
    if not prs:
        execute('gh','pr','create','--repo',REPO,'--head',BRANCH,'--base','main','--draft',
                '--title','B1: native 6-DOF shaft and disk element matrices','--body-file',str(body))
    else:
        print('Existing PR preserved, not recreated:',json.dumps(prs))
    print('\nB1_PUBLISHED_CANDIDATE_HEAD='+committed)
    print('CI qualification remains pending. No merge performed.')
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--evidence',type=Path,help='Explicitly commit/push and create a draft after this local Linux run')
    group.add_argument('--status',action='store_true',help='Read-only exact-head CI state')
    args=parser.parse_args()
    try:
        raise SystemExit(status() if args.status else publish(args.evidence))
    except (RuntimeError,ValueError,KeyError,OSError,subprocess.CalledProcessError) as error:
        print('STOP: '+str(error),file=sys.stderr)
        raise SystemExit(1)
