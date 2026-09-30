"""B1 exact-head preservation after reconciliation with promoted main.

The current promoted main is byte-preserved in full except for the single,
reviewed additive CMake suffix that wires the isolated B1 element kernels.
All other B1 content is additive. The frozen ROSS authority remains immutable.
"""
from __future__ import annotations
import argparse
import functools
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

BASE='0904bf5940a5006a57bb3292b46dcedcab7e3dd5'
MAIN=BASE
NATIVE_IMPLEMENTATION_COMMIT='7c1d505da1d2bf5fee872cb68a3bc4e474722d4f'
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
FROZEN_PREFIX='validation/ross_parity/6dof_elements/'
NATIVE_WORKFLOW='.github/workflows/ross-analysis-b1-6dof-elements.yml'
PINNED_NEW_BLOBS={
    NATIVE_WORKFLOW:'2a1940b5dfc32acc576f3a8f18b47d204c72e7ec',
    '.github/workflows/b1-6dof-authority.yml':'f6a9a3548e32eebb167ed95eb5f90d19789a6288',
}
NEW_FILES=frozenset({
    '.github/workflows/b1-6dof-authority.yml',
    '.github/workflows/ross-analysis-b1-6dof-elements.yml',
    'fortran/src/rd_shaft_6dof.f90',
    'fortran/src/rd_disk_6dof.f90',
    'fortran/src/rd_6dof_element_c_api.f90',
    'fortran/tests/test_6dof_elements.f90',
    'python/src/drm_core/solver/sixdof_elements.py',
    'python/tests_6dof_elements/conftest.py',
    'python/tests_6dof_elements/test_parity.py',
    'python/tests_6dof_elements/test_contract.py',
    'python/tests_6dof_elements/test_preservation.py',
    'validation/b1/FREEZE_REVIEW.json',
    'validation/b1/PLAN.md',
    'validation/b1/TOLERANCE_POLICY.json',
    'validation/b1/authority_common.py',
    'validation/b1/element_cases.json',
    'validation/b1/freeze_reviewed_authority.py',
    'validation/b1/inspect_candidate.py',
    'validation/b1/native_preservation.py',
    'validation/b1/native_validation.py',
    'validation/b1/native_runner.py',
    'validation/b1/native_publish.py',
    'validation/b1/NATIVE.md',
    'validation/b1/ROSS-LICENSE.md',
    'validation/b1/tests/test_authority_comparison.py',
    'validation/b1/tests/test_authority_generation.py',
    'validation/b1/tests/test_frozen_authority.py',
    'validation/ross_parity/generate_6dof_elements_reference.py',
    'validation/ross_parity/verify_6dof_elements_candidate.py',
})
ADAPTED_FILES=frozenset({'fortran/CMakeLists.txt','scripts/verify_a1_legacy_preservation.py'})
MODIFIED_FILES=ADAPTED_FILES
ARTIFACT_ROOTS=frozenset({'review','b1-evidence','b1-native-evidence','b1-native-preflight',
                         'b1-platform-artifacts','b1-aggregate-evidence','_ross_b1'})
CMAKE_APPEND=b'''\n# B1 isolated 6-DOF element kernels. Existing A1-A8 dispatch is unchanged.
target_sources(drmrotor PRIVATE
 src/rd_shaft_6dof.f90
 src/rd_disk_6dof.f90
 src/rd_6dof_element_c_api.f90)
add_executable(test_6dof_elements tests/test_6dof_elements.f90)
target_link_libraries(test_6dof_elements PRIVATE drmrotor)
target_include_directories(test_6dof_elements PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_6dof_elements PRIVATE -ffree-line-length-none)
endif()
add_test(NAME sixdof_element_native_contract COMMAND test_6dof_elements)
'''


def git(root,*args):
    return subprocess.check_output(['git',*args],cwd=root)


def require(ok,message):
    if not ok: raise ValueError(message)


def blob_hash(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def one_replace(data,old,new):
    require(data.count(old)==1,'Baseline adaptation anchor is not unique')
    return data.replace(old,new,1)


def expected_adaptation(path,before):
    if path=='fortran/CMakeLists.txt': return before+CMAKE_APPEND
    if path=='scripts/verify_a1_legacy_preservation.py':
        old=(b" # A8 close-clearance remains additive to the promoted A7 implementation.\n"
             b" 'fortran/src/rd_clearance.f90','fortran/src/rd_clearance_c_api.f90','fortran/tests/test_clearance.f90',\n")
        new=(old+
             b" # B1 remains additive to the promoted A0-A8 implementation.\n"
             b" 'fortran/src/rd_shaft_6dof.f90','fortran/src/rd_disk_6dof.f90',\n"
             b" 'fortran/src/rd_6dof_element_c_api.f90','fortran/tests/test_6dof_elements.f90',\n")
        data=one_replace(before,old,new)
        old_msg=b"only additive A2/A3/A4/A5/A6/A7/A8 modules/ABIs/tests added"
        new_msg=b"only additive A2/A3/A4/A5/A6/A7/A8/B1 modules/ABIs/tests added"
        return one_replace(data,old_msg,new_msg)
    raise ValueError('No historical adaptation is allowed for '+path)


@functools.lru_cache(maxsize=8)
def baseline_entries(root_string):
    result={}
    for record in git(root_string,'ls-tree','-rz','--full-tree',BASE).split(b'\0'):
        if not record: continue
        metadata,path=record.split(b'\t',1); mode,kind,sha=metadata.decode().split()
        require(kind=='blob','Unexpected baseline submodule/tree entry: '+path.decode())
        result[path.decode()]=(mode,sha)
    require(bool(result),'Empty current-main inventory')
    return result


def approve_change(path,before,after):
    if before is None:
        require(after is not None,'Missing B1 addition: '+path)
        if path.startswith(FROZEN_PREFIX):
            return
        require(path in NEW_FILES,'Unapproved new path: '+path)
        if path in PINNED_NEW_BLOBS:
            require(blob_hash(after)==PINNED_NEW_BLOBS[path],'Pinned workflow bytes changed: '+path)
        return
    require(after is not None,'Removal of promoted-main path: '+path)
    if before==after: return
    if path in ADAPTED_FILES:
        require(after==expected_adaptation(path,before),'Historical adaptation differs from exact permitted patch: '+path)
    else:
        raise ValueError('Promoted-main file changed: '+path)


def read_bytes(path):
    if path.is_symlink(): return os.readlink(path).encode()
    return path.read_bytes()


def verify(root=ROOT):
    root=Path(root).resolve()
    subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=root,check=True)
    subprocess.run(['git','merge-base','--is-ancestor',NATIVE_IMPLEMENTATION_COMMIT,'HEAD'],cwd=root,check=True)
    entries=baseline_entries(str(root))
    for name,(mode,sha) in entries.items():
        file=root/name
        require(file.is_file() or file.is_symlink(),'Missing promoted-main file: '+name)
        require(file.is_symlink()==(mode=='120000'),'Promoted-main file type changed: '+name)
        data=read_bytes(file)
        if blob_hash(data)!=sha:
            approve_change(name,git(root,'show',f'{BASE}:{name}'),data)
    names=set(git(root,'ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    for name in names-set(entries):
        file=root/name
        if not file.exists() and not file.is_symlink():
            raise ValueError('Missing tracked/additional path: '+name)
        tracked=bool(git(root,'ls-files','--cached','--',name).strip())
        if not tracked and name.split('/')[0] in ARTIFACT_ROOTS: continue
        require(not file.is_symlink(),'New symlink is not a B1 source file: '+name)
        approve_change(name,None,file.read_bytes() if file.is_file() else None)
    for name in NEW_FILES:
        require((root/name).is_file() and not (root/name).is_symlink(),'Missing B1 file: '+name)
    for name in sorted(ADAPTED_FILES):
        before=git(root,'show',f'{BASE}:{name}')
        approve_change(name,before,(root/name).read_bytes())
    from validation.b1.tests.test_frozen_authority import locked_integrity,FREEZE_COMMIT
    from validation.b1.authority_common import FROZEN_PATH
    frozen=root/FROZEN_PATH
    integrity=locked_integrity(frozen)
    subprocess.run(['git','diff','--exit-code',FREEZE_COMMIT,'HEAD','--',FROZEN_PATH],cwd=root,check=True)
    flet_paths=[p for p in entries if p.startswith(('python/src/drm_flet/','python/tests_flet/','scripts/flet_',
                                                    '.github/workflows/flet-','docs/FLET_'))
                or p in ('python/pyproject.toml',)]
    return {'status':'PASS','promoted_main':BASE,'native_implementation_commit':NATIVE_IMPLEMENTATION_COMMIT,
            'historical_files':len(entries),'explicit_b1_files':len(NEW_FILES),
            'flet_files_preserved':len(flet_paths),'authority':integrity}


def source_snapshot(root=ROOT):
    root=Path(root).resolve(); verify(root)
    names=set(baseline_entries(str(root)))|set(NEW_FILES)
    frozen=root/'validation/ross_parity/6dof_elements'
    names.update(p.relative_to(root).as_posix() for p in frozen.rglob('*') if p.is_file())
    records={name:hashlib.sha256(read_bytes(root/name)).hexdigest() for name in sorted(names)}
    canonical=json.dumps(records,sort_keys=True,separators=(',',':')).encode()
    return {'sha256':hashlib.sha256(canonical).hexdigest(),'file_sha256':records}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    result=verify()
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('B1_RECONCILED_PRESERVATION',json.dumps(result,sort_keys=True))
