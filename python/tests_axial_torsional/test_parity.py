from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pytest

from drm_core.domain.model import RotorModel,Node,ShaftElement,TaperedShaftElement,Disk
from drm_core.domain.bearings import CoefficientBearing
from drm_core.solver.axial_torsional import (
    run_family_modal_6dof,run_family_sweep_6dof,
    run_axial_modal_6dof,run_torsional_modal_6dof,
)
from drm_core.solver.sixdof_global import run_modal_6dof

ROOT=Path(__file__).resolve().parents[2]
FROZEN=ROOT/"validation/ross_parity/axial_torsional"
CASES=json.loads((FROZEN/"cases.json").read_text(encoding="utf-8"))
ROTOR=json.loads((FROZEN/"rotor_specification.json").read_text(encoding="utf-8"))
POLICY=json.loads((FROZEN/"tolerances.json").read_text(encoding="utf-8"))


def _tuple(v):
    if isinstance(v,list):return tuple(_tuple(x) for x in v)
    return v


def model_for(rotor_id):
    r=ROTOR["rotors"][rotor_id];m=ROTOR["materials"]["steel"]
    z=[0.0]
    for s in r["shafts"]:z.append(z[-1]+float(s["L"]))
    nodes=[Node(i+1,p) for i,p in enumerate(z)]
    shafts=[]
    for i,s in enumerate(r["shafts"],1):
        tapered=float(s["idl"])!=float(s["idr"]) or float(s["odl"])!=float(s["odr"])
        if tapered:
            shafts.append(TaperedShaftElement(
                22,i,i+1,float(s["odl"]),float(s["odr"]),float(s["idl"]),float(s["idr"]),
                float(m["rho"]),float(m["E"]),float(m["G_s"]),float(s.get("axial_force",0.0))
            ))
        else:
            shafts.append(ShaftElement(
                2,i,i+1,float(s["odl"]),float(s["idl"]),float(m["rho"]),float(m["E"]),
                float(m["G_s"]),0.0,float(s.get("axial_force",0.0)),float(s.get("torque",0.0))
            ))
    disks=[Disk.inertial(int(d["n"])+1,float(d["m"]),float(d["Id"]),float(d["Ip"])) for d in r["disks"]]
    bearings=[]
    for b in r["bearings"]:
        bearings.append(CoefficientBearing(
            node=int(b["n"])+1,kxx=_tuple(b["kxx"]),kyy=_tuple(b["kyy"]),
            kxy=_tuple(b["kxy"]),kyx=_tuple(b["kyx"]),cxx=_tuple(b["cxx"]),cyy=_tuple(b["cyy"]),
            cxy=_tuple(b["cxy"]),cyx=_tuple(b["cyx"]),mxx=_tuple(b["mxx"]),myy=_tuple(b["myy"]),
            mxy=_tuple(b["mxy"]),myx=_tuple(b["myx"]),
            speed_rad_s=tuple(float(x) for x in b.get("speed",[])),
            frequency_rad_s=tuple(float(x) for x in b.get("frequency",[])),
            interpolation=b.get("interpolation","pchip"),tag=f"B3-{rotor_id}-{b['n']}",
            provenance={"authority":"B3","map_contract":"ROSS_B3"} if ("speed" in b or "frequency" in b) else {"authority":"B3"},
        ))
    return RotorModel(nodes=nodes,shafts=shafts,disks=disks,advanced_bearings=bearings)


def mac(u,v):
    den=float(np.vdot(u,u).real*np.vdot(v,v).real)
    return float(abs(np.vdot(u,v))**2/den) if den>0 else 0.0


def assert_close(a,b,policy):
    np.testing.assert_allclose(a,b,rtol=policy["rtol"],atol=policy["atol"])


@pytest.mark.parametrize("case",CASES["modal_cases"],ids=lambda c:c["id"])
def test_b3_modal_frozen_ross_parity(case):
    result=run_family_modal_6dof(model_for(case["rotor"]),case["speed_rad_s"],case["family"])
    cid=case["id"]
    assert result.family==case["family"]
    assert len(result.wn_rad_s)==case["expected_modes"]
    assert result.max_decoupling_ratio<=POLICY["decoupling"]["relative_frobenius_max"]
    for name in ("M","K","C","G","Ksdt"):
        expected=np.load(FROZEN/f"modal/{cid}_{name}.npy",allow_pickle=False)
        assert_close(getattr(result,name),expected,POLICY["matrix"][name])
    expected=np.load(FROZEN/f"modal/{cid}_evalues.npy",allow_pickle=False)
    pr=POLICY["modal"]["eigenvalue_real"];pi=POLICY["modal"]["eigenvalue_imag"]
    assert_close(result.eigenvalues.real,expected.real,pr);assert_close(result.eigenvalues.imag,expected.imag,pi)
    for attr,suffix,key in [
        ("wn_rad_s","wn","wn"),("wd_rad_s","wd","wd"),
        ("damping_ratio","damping_ratio","damping_ratio"),("log_dec","log_dec","log_dec"),
    ]:
        exp=np.load(FROZEN/f"modal/{cid}_{suffix}.npy",allow_pickle=False)
        assert_close(getattr(result,attr),exp,POLICY["modal"][key])
    expected_vec=np.load(FROZEN/f"modal/{cid}_evectors.npy",allow_pickle=False)
    assert result.eigenvectors.shape==expected_vec.shape
    scores=[mac(expected_vec[:,j],result.eigenvectors[:,j]) for j in range(expected_vec.shape[1])]
    assert min(scores,default=1.0)>=POLICY["modal"]["eigenvector_mac_min"]
    assert float(np.max(result.residual,initial=0.0))<=POLICY["modal"]["residual_max"]


@pytest.mark.parametrize("case",CASES["sweep_cases"],ids=lambda c:c["id"])
def test_b3_sweep_frozen_ross_parity_and_speed_invariance(case):
    result=run_family_sweep_6dof(model_for(case["rotor"]),case["speed_range_rad_s"],case["family"])
    cid=case["id"]
    np.testing.assert_array_equal(result.speed_rad_s,np.load(FROZEN/f"sweep/{cid}_speed.npy"))
    for attr,suffix,key in [
        ("wn_rad_s","wn","wn"),("wd_rad_s","wd","wd"),
        ("damping_ratio","damping_ratio","damping_ratio"),("log_dec","log_dec","log_dec"),
    ]:
        expected=np.load(FROZEN/f"sweep/{cid}_{suffix}.npy",allow_pickle=False)
        assert_close(getattr(result,attr),expected,POLICY["sweep"][key])
    assert float(np.max(np.abs(result.wn_rad_s-result.wn_rad_s[0:1,:]),initial=0.0))<=POLICY["sweep"]["speed_invariance_abs_rad_s"]
    assert np.max(result.max_decoupling_ratio,initial=0.0)<=POLICY["decoupling"]["relative_frobenius_max"]


@pytest.mark.parametrize("family",["Axial","Torsional"])
def test_b3_crosscheck_against_qualified_b2_full_6dof_family(family):
    model=model_for("R03");w=160.0
    dedicated=run_family_modal_6dof(model,w,family)
    full=run_modal_6dof(model,w,48)
    selected=np.flatnonzero(np.asarray(full.mode_type,dtype=object)==family)
    positive=selected[full.wd_rad_s[selected]>0]
    assert len(positive)==len(dedicated.wn_rad_s)
    np.testing.assert_allclose(
        dedicated.wn_rad_s,full.wn_rad_s[positive],
        rtol=POLICY["modal"]["wn"]["rtol"],atol=POLICY["modal"]["wn"]["atol"],
    )
    offset=2 if family=="Axial" else 5
    dofs=np.arange(offset,6*len(model.nodes),6)
    for j,k in enumerate(positive):
        assert mac(dedicated.eigenvectors[:,j],full.eigenvectors_displacement[dofs,k])>=POLICY["modal"]["eigenvector_mac_min"]


def test_b3_convenience_functions_and_metadata():
    model=model_for("R01")
    a=run_axial_modal_6dof(model,0.0);t=run_torsional_modal_6dof(model,0.0)
    assert a.family=="Axial" and a.metadata["family_dof"]=="z"
    assert t.family=="Torsional" and t.metadata["family_dof"]=="theta"
    assert a.metadata["workflow"]=="B3_DEDICATED_INVARIANT_SUBSPACE"
    assert t.metadata["matched_whirl"] is False


def test_b3_invalid_family_and_sweep_fail_closed():
    model=model_for("R01")
    with pytest.raises(ValueError,match="family"):
        run_family_modal_6dof(model,0.0,"Lateral")
    for grid in ([],[0.0],[0.0,0.0],[0.0,-1.0],[0.0,float("nan")]):
        with pytest.raises(ValueError,match="speed_range_rad_s"):
            run_family_sweep_6dof(model,grid,"Axial")
