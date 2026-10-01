"""Actual Fortran corrective parity, invariance, persistence and isolation gates."""
from __future__ import annotations
from copy import deepcopy
import hashlib,json,os,subprocess,sys,types
from pathlib import Path
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
PARITY=ROOT/'validation'/'ross_parity'
sys.path.insert(0,str(PARITY))
from ucs_bearing_order_cases import BASE_SHA,specifications,native_model
from verify_ucs_bearing_order import load_authority,check_native,compare_arrays
from drm_core import run_ucs,RotorProject,AnalysisCase,AnalysisService,save_project,load_project
from drm_core.solver.backend import FortranBackend

CASES=tuple(specifications())
A5_PROMOTED='c2073acc0085900e72f0b17ad90cbf1090eec495'
A8_PRE_RECONCILIATION='ad394e109fa356015b8ed183c6df246ef6efe586'
A8_NATIVE_ADDITIONS={
    'fortran/src/rd_clearance.f90',
    'fortran/src/rd_clearance_c_api.f90',
    'fortran/tests/test_clearance.f90',
}
B1_NATIVE_IMPLEMENTATION='7c1d505da1d2bf5fee872cb68a3bc4e474722d4f'
B1_NATIVE_ADDITIONS={
    'fortran/src/rd_shaft_6dof.f90',
    'fortran/src/rd_disk_6dof.f90',
    'fortran/src/rd_6dof_element_c_api.f90',
    'fortran/tests/test_6dof_elements.f90',
}
B1_PARITY_ADDITIVE_PATHS=(
    'validation/ross_parity/6dof_elements',
    'validation/ross_parity/generate_6dof_elements_reference.py',
    'validation/ross_parity/verify_6dof_elements_candidate.py',
)
B2_AUTHORITY_FREEZE='d9be588c71bfd7116f61d1f5f5be3a2ee0e06726'
B2_NATIVE_IMPLEMENTATION='e26a38e14e76f26541dbd028409bb378cf340096'
B2_NATIVE_ADDITIONS={
    'fortran/src/rd_6dof_assembly.f90',
    'fortran/src/rd_6dof_modal.f90',
    'fortran/src/rd_6dof_campbell.f90',
    'fortran/src/rd_6dof_global_c_api.f90',
    'fortran/tests/test_6dof_global.f90',
}
B2_PARITY_ADDITIVE_PATHS=(
    'validation/ross_parity/6dof_global',
    'validation/ross_parity/generate_6dof_global_reference.py',
    'validation/ross_parity/verify_6dof_global_candidate.py',
)
A5_ADDITIVE_PATHS=(
    'validation/ross_parity/ucs_bearing_order',
    'validation/ross_parity/ucs_bearing_order_cases.py',
    'validation/ross_parity/generate_ucs_bearing_order_reference.py',
    'validation/ross_parity/verify_ucs_bearing_order.py',
)
A8_ADDITIVE_PATHS=(
    'validation/ross_parity/clearance',
    'validation/ross_parity/generate_clearance_reference.py',
    'validation/ross_parity/verify_clearance_candidate.py',
)


def _git_diff_unchanged(ref,*paths):
    subprocess.run(['git','diff','--no-ext-diff','--no-textconv',
                    '--exit-code',ref,'--',*paths],cwd=ROOT,check=True)


def _changed_status(ref,*paths):
    return subprocess.check_output(
        ['git','diff','--no-ext-diff','--no-textconv','--no-renames',
         '--name-status',ref,'--',*paths],cwd=ROOT,text=True).splitlines()


def _assert_allowed_delta(rows,allowed):
    # Check statuses as well as exact paths: an allowed addition must not hide
    # deletion, renaming, type changes or edits to a historical baseline file.
    for row in rows:
        fields=row.split('\t')
        assert len(fields)==2,('unexpected diff record',row)
        status,path=fields
        assert allowed.get(path)==status,('out-of-scope change',row)


def _snapshot_paths(ref,paths):
    return subprocess.check_output(
        ['git','ls-tree','-r','--name-only',ref,'--',*paths],
        cwd=ROOT,text=True).splitlines()


def _assert_native_baseline_unchanged():
    # The PR31-only whole-directory equality is stale on additive A8. Preserve
    # EVERY historical Fortran file, admitting only the three reviewed A8 files
    # and the exact already-published CMake integration. No solver is exempted.
    allowed={path:'A' for path in A8_NATIVE_ADDITIONS|B1_NATIVE_ADDITIONS|B2_NATIVE_ADDITIONS}
    allowed['fortran/CMakeLists.txt']='M'
    _assert_allowed_delta(_changed_status(BASE_SHA,'fortran'),allowed)
    _git_diff_unchanged(B1_NATIVE_IMPLEMENTATION,*sorted(B1_NATIVE_ADDITIONS))
    _git_diff_unchanged(B2_NATIVE_IMPLEMENTATION,*sorted(B2_NATIVE_ADDITIONS))
    from validation.b2.preservation import verify as verify_b2_preservation
    assert verify_b2_preservation()['status']=='PASS'


@pytest.mark.parametrize('row',[
    'M\tfortran/src/rd_ucs.f90',
    'D\tfortran/src/rd_eigensystem.f90',
    'A\tfortran/src/unreviewed.f90',
    'T\tfortran/src/rd_clearance.f90',
    'D\tfortran/src/rd_clearance.f90',
    'R100\tfortran/src/rd_ucs.f90\tfortran/src/renamed.f90',
    'M\tvalidation/ross_parity/ucs/isotropic_constant.json',
    'D\tvalidation/ross_parity/ucs/isotropic_constant.json',
])
def test_preservation_scope_rejects_historical_changes(row):
    allowed={path:'A' for path in A8_NATIVE_ADDITIONS|B1_NATIVE_ADDITIONS|B2_NATIVE_ADDITIONS}
    allowed['fortran/CMakeLists.txt']='M'
    with pytest.raises(AssertionError):
        _assert_allowed_delta([row],allowed)


def test_preservation_scope_accepts_only_declared_native_additions():
    allowed={path:'A' for path in A8_NATIVE_ADDITIONS|B1_NATIVE_ADDITIONS|B2_NATIVE_ADDITIONS}
    allowed['fortran/CMakeLists.txt']='M'
    _assert_allowed_delta([status+'\t'+path for path,status in allowed.items()],allowed)


@pytest.mark.parametrize('name',CASES)
def test_additive_frozen_ross_native_parity_and_matrix_first(name):
    gold=load_authority();check_native(name,gold[name])


@pytest.mark.parametrize('name',CASES)
def test_actual_fortran_permutation_save_reopen_and_model_immutability(name,tmp_path):
    spec=specifications()[name];model=native_model(spec)
    canonical=deepcopy(model.canonical_dict());before=model.model_hash()
    case=AnalysisCase('ucs',dict(stiffness_range_exponents=[6,10],num=7,num_modes=16,
        synchronous=spec['synchronous'],bearing_speed_range=spec['bearing_speed_range']),name)
    project=RotorProject(name,model,[case]);service=AnalysisService()
    first=service.execute(project,case)
    assert model.canonical_dict()==canonical and model.model_hash()==before
    save_project(project,tmp_path/'original.rds')
    reopened=load_project(tmp_path/'original.rds')
    assert reopened.model.canonical_dict()==canonical and reopened.model.model_hash()==before
    second=service.execute(reopened,reopened.analyses[0])
    assert first.analysis_hash==second.analysis_hash
    for k,v in vars(first.result).items():
        if isinstance(v,np.ndarray):np.testing.assert_array_equal(v,getattr(second.result,k),err_msg=k)
    # Sorting a COPY retains same-node tie order, unlike reversing tied entries.
    ordered_spec=deepcopy(spec)
    ordered_spec['supports']=sorted(ordered_spec['supports'],key=lambda b:b['node'])
    ordered=run_ucs(native_model(ordered_spec),**case.parameters)
    for k,v in vars(first.result).items():
        if isinstance(v,np.ndarray):np.testing.assert_array_equal(v,getattr(ordered,k),err_msg=k)
    assert model.canonical_dict()==canonical and model.model_hash()==before


def test_real_unpatched_to_patched_map_isolation_and_numeric_consequence(tmp_path):
    # Load the exact historical binding AS CODE, not a mock. Both paths use the
    # real current ABI/Fortran library. All pre-A8 native sources are preserved.
    source=subprocess.check_output(['git','show',BASE_SHA+':python/src/drm_core/solver/ucs_backend.py'],cwd=ROOT)
    blob=hashlib.sha1(b'blob '+str(len(source)).encode()+b'\0'+source).hexdigest()
    assert blob=='6217f22db20882fbfce23057b0942f46b7c22ef6'
    _assert_native_baseline_unchanged()
    old=types.ModuleType('drm_core.solver._ucs_historical_validation_only')
    old.__package__='drm_core.solver'
    exec(compile(source,'ucs_backend@'+BASE_SHA,'exec'),old.__dict__)
    model=native_model(specifications()['legacy_unsorted_isotropic_first_node'])
    before=model.model_hash()
    old_result=old.execute(FortranBackend(),model,(6,10),num=7,num_modes=16)
    current=run_ucs(model,(6,10),num=7,num_modes=16)
    assert old._validate_model(None,model,(6,10),7,16,None,False)[5][0].node==4
    np.testing.assert_array_equal(old_result['bearing_kxx_n_m'],21e6)
    np.testing.assert_array_equal(old_result['bearing_kyy_n_m'],36e6)
    assert old_result['coefficient_families']==('kxx','kyy')
    np.testing.assert_array_equal(current.bearing_kxx_n_m,12.5e6)
    np.testing.assert_array_equal(current.bearing_kyy_n_m,12.5e6)
    assert current.coefficient_families==('kxx',)
    for key in ['stiffness_log_n_m','natural_frequency_rad_s']:
        np.testing.assert_array_equal(old_result[key],getattr(current,key),err_msg=key)
    assert len(old_result['intersection_speed_rad_s'])==8
    assert len(current.intersection_speed_rad_s)==4
    assert old_result['critical_wn_rad_s'].shape==(6,8)
    assert current.critical_wn_rad_s.shape==(6,4)
    assert model.model_hash()==before and [b.node for b in model.bearings]==[4,1]
    # Preserve complete before/after arrays for numerical review, including all
    # real/imag eigenvalues, wd, damping and log decrement, not only plot points.
    def encode(x):
        if isinstance(x,np.ndarray):return x.tolist()
        if isinstance(x,np.generic):return x.item()
        raise TypeError(type(x).__name__)
    directory=Path(os.environ.get('A5_ORDER_EVIDENCE',str(tmp_path)))
    directory.mkdir(parents=True,exist_ok=True)
    payload=dict(status='PASS',old_binding_commit=BASE_SHA,old_binding_blob=blob,
        expected_node=1,old_node=4,fixed_node=1,order_before=[4,1],order_after=[4,1],
        model_hash_before=before,model_hash_after=model.model_hash(),
        map_max_difference=0.,old=old_result,fixed=vars(current))
    (directory/'native_before_after.json').write_text(json.dumps(payload,default=encode,indent=2),encoding='utf-8')


def test_historical_goldens_and_unrelated_production_are_unchanged():
    # Enumerate exact additive files from their frozen commits, rather than
    # exempting all of ross_parity. Original A0-A7 files cannot change at all.
    additions=_snapshot_paths(A5_PROMOTED,A5_ADDITIVE_PATHS)
    additions+=_snapshot_paths(A8_PRE_RECONCILIATION,A8_ADDITIVE_PATHS)
    additions+=_snapshot_paths(B1_NATIVE_IMPLEMENTATION,B1_PARITY_ADDITIVE_PATHS)
    additions+=_snapshot_paths(B2_AUTHORITY_FREEZE,B2_PARITY_ADDITIVE_PATHS)
    assert additions
    _assert_allowed_delta(_changed_status(BASE_SHA,'validation/ross_parity'),
                          {path:'A' for path in additions})
    # Pin the corrective authority, A8 goldens and immutable B1 authority independently.
    _git_diff_unchanged(A5_PROMOTED,*A5_ADDITIVE_PATHS)
    _git_diff_unchanged(A8_PRE_RECONCILIATION,'validation/ross_parity/clearance')
    _git_diff_unchanged(B1_NATIVE_IMPLEMENTATION,*B1_PARITY_ADDITIVE_PATHS)
    _git_diff_unchanged(B2_AUTHORITY_FREEZE,*B2_PARITY_ADDITIVE_PATHS)
    _assert_native_baseline_unchanged()
    _git_diff_unchanged(BASE_SHA,
        'python/src/drm_core/solver/level1_backend.py',
        'python/src/drm_core/solver/api617_unbalance_backend.py')
    _git_diff_unchanged(A5_PROMOTED,
        'python/src/drm_core/solver/ucs_backend.py',
        'python/src/drm_studio/ucs_qualification.py',
        '.gitattributes')
