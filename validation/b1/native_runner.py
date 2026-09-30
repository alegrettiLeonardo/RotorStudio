"""Execute B1 local/CI qualification and preserve source-snapshot evidence.

Run with the project's Python environment. No install, commit, push, PR mutation,
reference generation or merge occurs here. A local uncommitted tree may PASS
for its SHA256 snapshot, but is never labelled an exact-commit qualification.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from validation.b1.native_preservation import ROOT as SOURCE_ROOT,BASE,NEW_FILES,blob_hash,read_bytes,source_snapshot,verify


def store(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def junit(path):
    root=ET.parse(path).getroot()
    cases=root.findall('.//testcase')
    result={'tests':len(cases),'failures':sum(c.find('failure') is not None for c in cases),
            'errors':sum(c.find('error') is not None for c in cases),'skips':sum(c.find('skipped') is not None for c in cases)}
    if not cases or any(result[k] for k in ('failures','errors','skips')):
        raise RuntimeError(f'Incomplete or failed mandatory JUnit: {path}: {result}')
    return result


def library(build,stem):
    names=[f'lib{stem}.so'] if sys.platform.startswith('linux') else [f'{stem}.dll',f'lib{stem}.dll']
    files=[p.resolve() for name in names for p in build.rglob(name)]
    if len(files)!=1: raise RuntimeError(f'Expected exactly one {stem} library in {build}; found {files}')
    return files[0]


def run_campaign(args):
    if not __debug__: raise RuntimeError('Run qualification without Python -O/PYTHONOPTIMIZE')
    if sys.platform!='win32' and not sys.platform.startswith('linux'): raise RuntimeError('Declared platforms are Linux and Windows')
    out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    if (out/'PLATFORM_RESULT.json').exists(): raise RuntimeError('Use a new evidence directory; previous results are not overwritten')
    env=dict(os.environ)
    for key in ('PYTHONHOME','PYTHONOPTIMIZE','PYTEST_ADDOPTS'): env.pop(key,None)
    env.update(PYTHONPATH=os.pathsep.join([str(ROOT/'python/src'),str(ROOT)]),PYTHONNOUSERSITE='1',
               PYTHONDONTWRITEBYTECODE='1',QT_QPA_PLATFORM='offscreen',OPENBLAS_NUM_THREADS='1',
               OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONHASHSEED='0')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    expected=env.get('B1_EXPECTED_HEAD')
    if expected and head!=expected: raise RuntimeError(f'Unexpected HEAD: {head}; expected {expected}')
    verify(ROOT)
    before=source_snapshot(ROOT)
    store(out/'SOURCE_BEFORE.json',before)
    steps=[]; junits={}
    def run(label,command,jobenv=None):
        log=out/(label+'.log'); started=time.monotonic()
        print(f'\n[{label}] '+' '.join(map(str,command)),flush=True)
        with log.open('w',encoding='utf-8') as stream:
            proc=subprocess.Popen(list(map(str,command)),cwd=ROOT,env=jobenv or env,stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
            try:
                for line in proc.stdout:
                    stream.write(line);stream.flush();print(line,end='',flush=True)
                rc=proc.wait()
            except BaseException:
                proc.terminate();proc.wait();raise
        steps.append({'step':label,'command':list(map(str,command)),'return_code':rc,'elapsed_seconds':time.monotonic()-started})
        store(out/'STEPS.json',steps)
        if rc:
            store(out/'STOP.json',{'status':'FAIL','step':label,'return_code':rc,'log':str(log),'head':head})
            raise RuntimeError(f'STOP: {label}; code {rc}; log {log}')
        return log
    run('01-pip-check',[sys.executable,'-m','pip','check'])
    run('02-environment',[sys.executable,'-m','pip','freeze','--all'])
    run('03-compiler',['gfortran','--version'])
    run('04-cmake-version',['cmake','--version'])
    def pytest_suite(label,paths,jobenv):
        collect=run(label+'-collection',[sys.executable,'-m','pytest',*paths,'--collect-only','-q'],jobenv)
        match=re.search(r'(\d+) tests? collected',collect.read_text(encoding='utf-8'))
        if not match or int(match.group(1))<1: raise RuntimeError('Empty/unreadable collection: '+label)
        expected_count=int(match.group(1))
        report=out/(label+'.xml')
        run(label,[sys.executable,'-m','pytest',*paths,'-q',f'--junitxml={report}',
                   '-o',f'cache_dir={out/(label+"-cache")}'],jobenv)
        parsed=junit(report)
        if parsed['tests']!=expected_count:
            raise RuntimeError(f'Collected/executed mismatch in {label}: {expected_count} vs {parsed}')
        junits[label]=parsed
    release_env=None
    for config,directory in [('Release',args.build_dir),('Debug',args.debug_dir)]:
        build=directory.resolve(); tag=config.lower()
        if not args.no_configure:
            run(f'10-{tag}-configure',['cmake','-S','fortran','-B',build,f'-DCMAKE_BUILD_TYPE={config}'])
            run(f'11-{tag}-build',['cmake','--build',build,'--parallel',str(args.jobs)])
        if not (build/'CMakeCache.txt').is_file(): raise RuntimeError('Missing completed build: '+str(build))
        rotor,bearing=library(build,'drmrotor'),library(build,'drmbearings')
        jobenv=dict(env);jobenv['DRMROTOR_LIB']=str(rotor);jobenv['DRMBEARINGS_LIB']=str(bearing)
        jobenv['B1_NATIVE_EVIDENCE']=str(out/tag/'numerical')
        jobenv['A5_ORDER_EVIDENCE']=str(out/'a5-before-after')
        jobenv['A8_QUALIFICATION_EVIDENCE']=str(out/'a8-independent')
        store(out/f'{tag}-libraries.json',{
            str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (rotor,bearing)})
        listing=run(f'12-{tag}-ctest-collection',['ctest','--test-dir',build,'--show-only=json-v1'],jobenv)
        tests=json.loads(listing.read_text(encoding='utf-8-sig'))['tests']
        if not tests or 'sixdof_element_native_contract' not in {t['name'] for t in tests}:
            raise RuntimeError('B1 native CTest is missing or collection is empty')
        report=out/f'{tag}-ctest.xml'
        run(f'13-{tag}-ctest',['ctest','--test-dir',build,'--output-on-failure','--output-junit',report],jobenv)
        parsed=junit(report)
        if parsed['tests']!=len(tests): raise RuntimeError('Not all native CTests were executed')
        junits[f'{tag}-ctest']=parsed
        pytest_suite(f'14-{tag}-b1',['python/tests_6dof_elements'],jobenv)
        native=json.loads((out/tag/'numerical/NATIVE_SUMMARY.json').read_text())
        if native['status']!='PASS': raise RuntimeError('Native matrix/invariant/legacy gate failed: '+tag)
        if config=='Release': release_env=jobenv
    for label,paths in [
        ('20-a5-ucs',['python/tests_ucs']),
        ('21-a6-level1',['python/tests_level1']),
        ('22-a7-unbalance',['python/tests_api617_unbalance']),
        ('23-a8-clearance',['python/tests_clearance']),
        ('24-a0-a4-stage1',['python/tests_time','python/tests_forced','python/tests_frf','python/tests_static','python/tests']),
        ('25-bearings',['python/tests_bearings']),
        ('26-stage2-ui',['python/tests_ui']),
    ]:
        pytest_suite(label,paths,release_env)
    for label,path in [('27-a1-preservation','scripts/verify_a1_legacy_preservation.py'),
                       ('28-a2-preservation','scripts/verify_a2_preservation.py'),
                       ('29-a3-preservation','scripts/verify_a3_preservation.py')]:
        run(label,[sys.executable,path],release_env)
    run('30-independent-ucs',[sys.executable,'validation/ross_parity/qualify_ucs.py','--out',out/'independent-ucs.json'],release_env)
    if json.loads((out/'independent-ucs.json').read_text())['status']!='PASS':
        raise RuntimeError('Independent UCS qualifier did not report PASS')
    for name in ('static','static_extended','frf','forced','time_response','ucs','level1','api617_unbalance','clearance'):
        run('31-authority-'+name,[sys.executable,'validation/ross_parity/verify_reference.py','validation/ross_parity/'+name],release_env)
    after=source_snapshot(ROOT)
    store(out/'SOURCE_AFTER.json',after)
    if after!=before: raise RuntimeError('Source/reference snapshot changed during qualification')
    tree={}
    for line in subprocess.check_output(['git','ls-tree','-rz','HEAD'],cwd=ROOT).split(b'\0'):
        if line:
            meta,path=line.split(b'\t',1);tree[path.decode()]=meta.split()[2].decode()
    clean=all(tree.get(name)==blob_hash(read_bytes(ROOT/name)) for name in before['file_sha256'])
    release=json.loads((out/'release/numerical/NATIVE_SUMMARY.json').read_text())
    debug=json.loads((out/'debug/numerical/NATIVE_SUMMARY.json').read_text())
    result={'status':'PLATFORM_QUALIFICATION_PASS' if clean else 'SOURCE_TREE_LINUX_PASS',
            'head':head,'source_tree_clean':clean,'source_snapshot_sha256':before['sha256'],
            'platform':platform.platform(),'python':sys.version,'run_id':env.get('GITHUB_RUN_ID'),
            'completed_utc':datetime.now(timezone.utc).isoformat(),'junit':junits,
            'native':release,'native_debug':debug,'authority_integrity':verify(ROOT)['authority'],
            'promotion':'NOT_AUTHORIZED_BY_THIS_RUN',
            'separate_remaining_gates':['same-head authority workflow','same-head broad PR product workflows','explicit promotion authorization']}
    store(out/'PLATFORM_RESULT.json',result)
    print('\nB1_LOCAL_SOURCE_QUALIFICATION=PASS' if not clean else '\nB1_PLATFORM_QUALIFICATION=PASS')
    print('HEAD='+head+'\nSOURCE_SNAPSHOT_SHA256='+before['sha256']+'\nEVIDENCE='+str(out))
    print('No commit, push, PR creation or merge was performed by native_runner.py.')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--build-dir',type=Path,default=ROOT/'build-b1-release')
    parser.add_argument('--debug-dir',type=Path,default=ROOT/'build-b1-debug')
    parser.add_argument('--jobs',type=int,default=2)
    parser.add_argument('--no-configure',action='store_true',help='Use builds already compiled with the CI platform toolchain')
    args=parser.parse_args()
    if not 1<=args.jobs<=16: parser.error('--jobs must be 1..16')
    try:
        run_campaign(args)
    except BaseException as error:
        args.out.resolve().mkdir(parents=True,exist_ok=True)
        store(args.out.resolve()/'RUNNER_ERROR.json',{'status':'FAIL','error':str(error),'type':type(error).__name__})
        print('\nB1_LOCAL_QUALIFICATION=FAIL\n'+str(error),file=sys.stderr)
        raise
