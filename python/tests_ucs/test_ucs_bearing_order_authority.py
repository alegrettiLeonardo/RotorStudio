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
    # real current ABI/Fortran library, whose sources must remain unchanged.
    source=subprocess.check_output(['git','show',BASE_SHA+':python/src/drm_core/solver/ucs_backend.py'],cwd=ROOT)
    blob=hashlib.sha1(b'blob '+str(len(source)).encode()+b'\0'+source).hexdigest()
    assert blob=='6217f22db20882fbfce23057b0942f46b7c22ef6'
    subprocess.run(['git','diff','--exit-code',BASE_SHA,'--','fortran'],cwd=ROOT,check=True)
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
    # New authority lives in a separate directory. The original A0-A7 data and
    # their generators/qualifiers are immutable preservation targets.
    changed=subprocess.check_output(['git','diff','--name-only',BASE_SHA,'--','validation/ross_parity'],cwd=ROOT,text=True).splitlines()
    allowed={'validation/ross_parity/ucs_bearing_order_cases.py',
             'validation/ross_parity/generate_ucs_bearing_order_reference.py',
             'validation/ross_parity/verify_ucs_bearing_order.py'}
    assert all(p in allowed or p.startswith('validation/ross_parity/ucs_bearing_order/') for p in changed),changed
    subprocess.run(['git','diff','--exit-code',BASE_SHA,'--','fortran',
        'python/src/drm_core/solver/level1_backend.py',
        'python/src/drm_core/solver/api617_unbalance_backend.py'],cwd=ROOT,check=True)
