"""Narrow B1 native-stage preservation, for committed and local source trees.

Every baseline file is byte-preserved except three exact scripted adaptations
and the one dedicated, hash-pinned B1 native workflow. No directory-wide native
allowlist, no historical-golden rewrite, no line-ending normalization.
"""
from __future__ import annotations
import argparse
import functools
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE='ba43bc78f0dc943e34e3a5288b8f27e44923efd7'
MAIN='fcdac252974aeeded6961dbe3310677e234a6495'
ROOT=Path(__file__).resolve().parents[2]
NATIVE_WORKFLOW='.github/workflows/ross-analysis-b1-6dof-elements.yml'
NATIVE_WORKFLOW_BLOB='4c06bbd6987add960381c02301950913c2a5fbda'
NEW_FILES=frozenset({
    'fortran/src/rd_shaft_6dof.f90',
    'fortran/src/rd_disk_6dof.f90',
    'fortran/src/rd_6dof_element_c_api.f90',
    'fortran/tests/test_6dof_elements.f90',
    'python/src/drm_core/solver/sixdof_elements.py',
    'python/tests_6dof_elements/conftest.py',
    'python/tests_6dof_elements/test_parity.py',
    'python/tests_6dof_elements/test_contract.py',
    'python/tests_6dof_elements/test_preservation.py',
    'validation/b1/native_preservation.py',
    'validation/b1/native_validation.py',
    'validation/b1/native_runner.py',
    'validation/b1/native_publish.py',
    'validation/b1/NATIVE.md',
    'validation/b1/ROSS-LICENSE.md',
})
ADAPTED_FILES=frozenset({'fortran/CMakeLists.txt',
    'validation/b1/tests/test_frozen_authority.py',
    '.github/workflows/b1-6dof-authority.yml'})
MODIFIED_FILES=ADAPTED_FILES|{NATIVE_WORKFLOW}
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
    if path=='validation/b1/tests/test_frozen_authority.py':
        old=b'    assert not git(REPO_ROOT, "diff", BASE_MAIN, "HEAD", "--", "fortran", "python", "reference").strip()\n'
        new=b'    from validation.b1.native_preservation import verify\n    verify(REPO_ROOT)\n'
        return one_replace(before,old,new)
    if path=='.github/workflows/b1-6dof-authority.yml':
        old=(f'          git diff --exit-code {MAIN} HEAD -- fortran python reference\n'
             f'          git diff --exit-code --diff-filter=CDMRTUXB {MAIN} HEAD\n').encode()
        data=one_replace(before,old,b'          python validation/b1/native_preservation.py\n')
        # This workflow still performs ROSS-only authority reproduction.
        # It must not assert that no native implementation exists after B1.
        old=b"'native_implementation':'NOT_STARTED','ABI':'NOT_STARTED'"
        require(data.count(old)==2,'Unexpected authority job-summary structure')
        return data.replace(old,b"'native_implementation':'NOT_ASSESSED_BY_AUTHORITY_WORKFLOW','ABI':'NOT_ASSESSED_BY_AUTHORITY_WORKFLOW'")
    raise ValueError('No historical adaptation is allowed for '+path)


@functools.lru_cache(maxsize=8)
def baseline_entries(root_string):
    result={}
    for record in git(root_string,'ls-tree','-rz','--full-tree',BASE).split(b'\0'):
        if not record: continue
        metadata,path=record.split(b'\t',1); mode,kind,sha=metadata.decode().split()
        require(kind=='blob','Unexpected baseline submodule/tree entry: '+path.decode())
        result[path.decode()]=(mode,sha)
    require(bool(result),'Empty baseline inventory')
    return result


def approve_change(path,before,after):
    """Pure permission predicate exercised with negative legacy mutations."""
    if before is None:
        require(path in NEW_FILES and after is not None,'Unapproved new path: '+path)
        return
    require(after is not None,'Removal of historical path: '+path)
    if before==after: return
    if path in ADAPTED_FILES:
        require(after==expected_adaptation(path,before),'Historical adaptation differs from exact permitted patch: '+path)
    elif path==NATIVE_WORKFLOW:
        require(blob_hash(after)==NATIVE_WORKFLOW_BLOB,'Unreviewed dedicated native workflow bytes')
    else:
        raise ValueError('Historical file changed: '+path)


def read_bytes(path):
    if path.is_symlink(): return os.readlink(path).encode()
    return path.read_bytes()


def verify(root=ROOT):
    root=Path(root).resolve()
    subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=root,check=True)
    entries=baseline_entries(str(root))
    for name,(mode,sha) in entries.items():
        file=root/name
        require(file.is_file() or file.is_symlink(),'Missing historical file: '+name)
        require(file.is_symlink()==(mode=='120000'),'Historical file type changed: '+name)
        data=read_bytes(file)
        if blob_hash(data)!=sha:
            before=git(root,'show',f'{BASE}:{name}')
            approve_change(name,before,data)
    # Check additions in HEAD/index and untracked files, not only git diff HEAD.
    names=set(git(root,'ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0'))-{''}
    for name in names-set(entries):
        file=root/name
        tracked=bool(git(root,'ls-files','--cached','--',name).strip())
        if not tracked and name.split('/')[0] in ARTIFACT_ROOTS: continue
        require(not file.is_symlink(),'New symlink is not a B1 source file: '+name)
        approve_change(name,None,file.read_bytes() if file.is_file() else None)
    for name in NEW_FILES:
        require((root/name).is_file() and not (root/name).is_symlink(),'Missing native-stage file: '+name)
    for name in MODIFIED_FILES:
        before=git(root,'show',f'{BASE}:{name}')
        approve_change(name,before,(root/name).read_bytes())
    from validation.b1.tests.test_frozen_authority import locked_integrity
    integrity=locked_integrity(root/'validation/ross_parity/6dof_elements')
    return {'status':'PASS','baseline':BASE,'historical_files':len(entries),
            'explicit_new_files':len(NEW_FILES),'authority':integrity}


def source_snapshot(root=ROOT):
    root=Path(root).resolve(); verify(root)
    names=set(baseline_entries(str(root)))|set(NEW_FILES)
    records={name:hashlib.sha256(read_bytes(root/name)).hexdigest() for name in sorted(names)}
    canonical=json.dumps(records,sort_keys=True,separators=(',',':')).encode()
    return {'sha256':hashlib.sha256(canonical).hexdigest(),'file_sha256':records}


def apply_stage_adaptations(root=ROOT):
    root=Path(root).resolve()
    require(git(root,'rev-parse','HEAD').decode().strip()==BASE,'Installer must start from exact preflight HEAD')
    for name in sorted(ADAPTED_FILES):
        before=git(root,'show',f'{BASE}:{name}')
        target=root/name; expected=expected_adaptation(name,before)
        require(target.read_bytes() in (before,expected),'Local historical modification would be overwritten: '+name)
        target.write_bytes(expected)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    result=verify()
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('B1_NATIVE_PRESERVATION',json.dumps(result,sort_keys=True))
