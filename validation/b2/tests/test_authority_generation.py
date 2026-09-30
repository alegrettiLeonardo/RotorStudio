from __future__ import annotations
import ast,json
from pathlib import Path
import numpy as np
from validation.b2.authority_common import REPO_ROOT,INPUT_PATH,POLICY_PATH,read_json,validate_spec

def test_case_plan_is_frozen_before_native():
    spec=read_json(REPO_ROOT/INPUT_PATH);validate_spec(spec)
    assert [x["id"] for x in spec["matrix_cases"]]==[f"G{i:02d}" for i in range(1,12)]
    assert [x["id"] for x in spec["modal_cases"]]==[f"M{i:02d}" for i in range(1,9)]
    assert [x["id"] for x in spec["campbell_cases"]]==[f"C{i:02d}" for i in range(1,5)]

def test_policy_is_block_specific_and_pre_native():
    p=read_json(REPO_ROOT/POLICY_PATH);assert p["fixed_before_native"] is True
    assert set(p["matrix"])=={"M","K","C","G","Ksdt","A"}
    assert p["campbell"]["tracking_mac_min"]==0.9
    assert p["modal"]["eigenvector_mac_min"]>0.99

def test_generator_calls_real_ross_global_modal_campbell_methods():
    path=REPO_ROOT/"validation/ross_parity/generate_6dof_global_reference.py"
    tree=ast.parse(path.read_text(encoding="utf-8"));text=path.read_text(encoding="utf-8")
    for token in ("rs.Rotor","rotor.M(","rotor.K(","rotor.C(","rotor.G(","rotor.Ksdt(","rotor.A(","rotor.run_modal(","rotor.run_campbell("):
        assert token in text
    assert "np.linalg.eig" not in text and "scipy.linalg.eig" not in text

def test_bearing_scope_has_explicit_zero_axial_terms():
    spec=read_json(REPO_ROOT/INPUT_PATH)
    for rotor in spec["rotors"].values():
        for b in rotor["bearings"]:
            assert b["kzz"]==b["czz"]==b["mzz"]==0.0


def test_whirl_contract_is_the_only_nan_array_contract():
    common=(REPO_ROOT/"validation/b2/authority_common.py").read_text(encoding="utf-8")
    assert 'group in {"modal_whirl","campbell_whirl"}' in common
    assert 'not np.isinf(arr).any()' in common


def test_campbell_authority_records_actual_ross_tracking_decision():
    text=(REPO_ROOT/"validation/ross_parity/generate_6dof_global_reference.py").read_text(encoding="utf-8")
    for token in ("decision=np.array", "mask=decision>threshold", "found_order=np.where",
                  "modes_not_found=np.where", "missing_modes=sorted", "previous_tracked=tracked_v"):
        assert token in text
    assert 'frequency_type="wn"' in text or '"wn"' in text
    assert "phase_normalize_columns" in text

def test_cross_platform_policy_distinguishes_degenerate_basis_and_tracking_diagnostics():
    policy=read_json(REPO_ROOT/POLICY_PATH)
    assert "subspace MAC" in policy["platform_semantics"]["modal_eigenvectors"]
    assert "same-platform" in policy["platform_semantics"]["modal_whirl"]
    assert policy["campbell"]["tracking_mac_min"]==0.9
