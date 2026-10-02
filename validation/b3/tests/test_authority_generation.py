from __future__ import annotations
import ast
from pathlib import Path
from validation.b3.authority_common import REPO_ROOT,INPUT_PATH,POLICY_PATH,ROTOR_SPEC_PATH,read_json,validate_spec

def test_b3_entry_gate_and_case_plan_are_fixed_before_native():
    spec=read_json(REPO_ROOT/INPUT_PATH);validate_spec(spec)
    assert spec["baseline_main"]=="c23a5e515480fa28fb6dd770fca235b73dd0198a"
    assert spec["b2_qualified_head"]=="491ae024beeb05a7e08f31ff48ef13c829da88d2"
    assert [x["id"] for x in spec["modal_cases"]]==["AX01","AX02","AX03","TOR01","TOR02","TOR03"]
    assert [x["id"] for x in spec["sweep_cases"]]==["AXC01","TORC01"]

def test_b3_policy_is_fixed_before_native():
    p=read_json(REPO_ROOT/POLICY_PATH)
    assert p["fixed_before_native"] is True
    assert p["scope_contract"]["axial_dof"]=="z"
    assert p["scope_contract"]["torsional_dof"]=="theta"
    assert p["scope_contract"]["faults"] is False
    assert p["modal"]["eigenvector_mac_min"]>0.99

def test_b3_reuses_frozen_b2_rotor_definition_without_mutation():
    p=REPO_ROOT/ROTOR_SPEC_PATH
    assert p.is_file()
    spec=read_json(p)
    assert spec["node_dof_order"]==["x","y","z","alpha","beta","theta"]

def test_generator_uses_real_ross_and_torsional_converter():
    p=REPO_ROOT/"validation/ross_parity/generate_axial_torsional_reference.py"
    text=p.read_text(encoding="utf-8")
    ast.parse(text)
    for token in ("rotor.run_modal(", "rotor.M(", "rotor.K(", "rotor.C(", "rotor.G(", "rotor.Ksdt()",
                  "convert_6dof_to_torsional"):
        assert token in text
    assert "np.linalg.eig" not in text and "scipy.linalg.eig" not in text

def test_native_b3_solver_does_not_exist_before_authority_freeze():
    forbidden=(
        REPO_ROOT/"fortran/src/rd_axial_torsional.f90",
        REPO_ROOT/"fortran/src/rd_axial_torsional_c_api.f90",
        REPO_ROOT/"python/src/drm_core/solver/axial_torsional.py",
    )
    assert not any(p.exists() for p in forbidden)
