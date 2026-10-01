from __future__ import annotations
import inspect,json,os,subprocess,sys
from pathlib import Path
import numpy as np
import pytest

from drm_core import (
    RotorModel,Node,ShaftElement,TaperedShaftElement,Disk,Bearing,CoefficientBearing,
)
from drm_core.solver.sixdof_global import (
    assemble_6dof,run_modal_6dof,run_campbell_6dof,
)
from validation.ross_parity.verify_6dof_global_candidate import evec_group_parity

ROOT=Path(__file__).resolve().parents[2]
FROZEN=ROOT/"validation/ross_parity/6dof_global"
AUTH=FROZEN/"initial_reproduction/windows_candidate" if sys.platform=="win32" else FROZEN
SPEC=json.loads((FROZEN/"input_specification.json").read_text(encoding="utf-8"))
POLICY=json.loads((FROZEN/"tolerances.json").read_text(encoding="utf-8"))


def _tuple(v):
    if isinstance(v,list):return tuple(_tuple(x) for x in v)
    return v


def model_for(rotor_id):
    r=SPEC["rotors"][rotor_id]
    lengths=[float(s["L"]) for s in r["shafts"]]
    z=[0.0]
    for L in lengths:z.append(z[-1]+L)
    nodes=[Node(i+1,p) for i,p in enumerate(z)]
    shafts=[]
    m=SPEC["materials"]["steel"]
    for i,s in enumerate(r["shafts"],1):
        tapered=not (float(s["idl"])==float(s["idr"]) and float(s["odl"])==float(s["odr"]))
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
    advanced=[]
    for b in r["bearings"]:
        advanced.append(CoefficientBearing(
            node=int(b["n"])+1,
            kxx=_tuple(b["kxx"]),kyy=_tuple(b["kyy"]),kxy=_tuple(b["kxy"]),kyx=_tuple(b["kyx"]),
            cxx=_tuple(b["cxx"]),cyy=_tuple(b["cyy"]),cxy=_tuple(b["cxy"]),cyx=_tuple(b["cyx"]),
            mxx=_tuple(b["mxx"]),myy=_tuple(b["myy"]),mxy=_tuple(b["mxy"]),myx=_tuple(b["myx"]),
            speed_rad_s=tuple(float(x) for x in b.get("speed",[])),
            frequency_rad_s=tuple(float(x) for x in b.get("frequency",[])),
            interpolation=b.get("interpolation","pchip"),
            tag=f"B2-{rotor_id}-{b['n']}",
            provenance={"authority":"B2","map_contract":"ROSS_B2"} if ("speed" in b or "frequency" in b) else {"authority":"B2"},
        ))
    return RotorModel(nodes=nodes,shafts=shafts,disks=disks,advanced_bearings=advanced)


def assert_close(actual,expected,key):
    p=POLICY["matrix"][key]
    np.testing.assert_array_equal(actual==0,expected==0) if p.get("exact_zero_pattern") else None
    np.testing.assert_allclose(actual,expected,rtol=p["rtol"],atol=p["atol"],err_msg=key)


@pytest.mark.parametrize("case",SPEC["matrix_cases"],ids=lambda x:x["id"])
def test_global_matrix_frozen_parity(case):
    result=assemble_6dof(model_for(case["rotor"]),case["speed_rad_s"],case["frequency_rad_s"])
    for key in ("M","K","C","G","Ksdt"):
        expected=np.load(AUTH/f"global/{case['id']}_{key}.npy",allow_pickle=False)
        assert_close(getattr(result,key),expected,key)


@pytest.mark.parametrize("case",SPEC["modal_cases"],ids=lambda x:x["id"])
def test_modal_frozen_parity(case):
    result=run_modal_6dof(model_for(case["rotor"]),case["speed_rad_s"],case["num_modes"])
    cid=case["id"]
    A=np.load(AUTH/f"modal/{cid}_A.npy",allow_pickle=False)
    p=POLICY["matrix"]["A"];np.testing.assert_allclose(result.state_space,A,rtol=p["rtol"],atol=p["atol"])
    expected_all=np.load(AUTH/f"modal/{cid}_evalues_all.npy",allow_pickle=False)
    expected=np.load(AUTH/f"modal/{cid}_evalues.npy",allow_pickle=False)
    assert len(result.eigenvalues_all)==len(expected_all)
    pr=POLICY["modal"]["eigenvalue_real"];pi=POLICY["modal"]["eigenvalue_imag"]
    np.testing.assert_allclose(result.eigenvalues_all.real,expected_all.real,rtol=pr["rtol"],atol=pr["atol"])
    np.testing.assert_allclose(result.eigenvalues_all.imag,expected_all.imag,rtol=pi["rtol"],atol=pi["atol"])
    np.testing.assert_allclose(result.eigenvalues.real,expected.real,rtol=pr["rtol"],atol=pr["atol"])
    np.testing.assert_allclose(result.eigenvalues.imag,expected.imag,rtol=pi["rtol"],atol=pi["atol"])
    vectors=np.load(AUTH/f"modal/{cid}_evectors_displacement.npy",allow_pickle=False)
    ok,metrics=evec_group_parity(vectors,result.eigenvectors_displacement,expected,POLICY)
    assert ok,metrics
    for attr,suffix,policy_key in [
        ("wn_rad_s","wn","wn"),("wd_rad_s","wd","wd"),
        ("damping_ratio","damping_ratio","damping_ratio"),("log_dec","log_dec","log_dec"),
    ]:
        exp=np.load(AUTH/f"modal/{cid}_{suffix}.npy",allow_pickle=False)
        p=POLICY["modal"][policy_key]
        np.testing.assert_allclose(getattr(result,attr),exp,rtol=p["rtol"],atol=p["atol"],equal_nan=True)
    assert list(result.mode_type)==json.loads((AUTH/f"modal/{cid}_mode_types.json").read_text(encoding="utf-8"))
    exp_whirl=np.load(AUTH/f"modal/{cid}_whirl.npy",allow_pickle=False)
    np.testing.assert_allclose(result.whirl_value,exp_whirl,rtol=0,atol=0,equal_nan=True)
    assert float(np.max(result.residual,initial=0))<=POLICY["modal"]["residual_max"]


@pytest.mark.parametrize("case",SPEC["campbell_cases"],ids=lambda x:x["id"])
def test_campbell_frozen_parity(case):
    result=run_campbell_6dof(model_for(case["rotor"]),case["speed_range_rad_s"],case["frequencies"])
    cid=case["id"]
    np.testing.assert_array_equal(result.speed_rad_s,np.load(AUTH/f"campbell/{cid}_speed.npy"))
    for attr,suffix,key in [
        ("wd_rad_s","wd","wd"),("wn_rad_s","wn","wn"),
        ("damping_ratio","damping_ratio","damping_ratio"),("log_dec","log_dec","log_dec"),
    ]:
        p=POLICY["campbell"][key];expected=np.load(AUTH/f"campbell/{cid}_{suffix}.npy",allow_pickle=False)
        np.testing.assert_allclose(getattr(result,attr).T,expected,rtol=p["rtol"],atol=p["atol"],equal_nan=True)
    expected_whirl=np.load(AUTH/f"campbell/{cid}_whirl.npy",allow_pickle=False)
    np.testing.assert_allclose(result.whirl_value.T,expected_whirl,rtol=0,atol=0,equal_nan=True)
    expected_types=json.loads((AUTH/f"campbell/{cid}_mode_types.json").read_text(encoding="utf-8"))
    assert result.mode_type.T.tolist()==expected_types
    tracking=json.loads((AUTH/f"campbell/{cid}_tracking.json").read_text(encoding="utf-8"))
    for s,station in enumerate(tracking):
        np.testing.assert_array_equal(result.tracking_index[:,s],station["found_order"])
        if s:
            flags=np.asarray(station["threshold_match"],bool)
            assert np.all(result.tracking_mac[:,s][flags]>POLICY["campbell"]["tracking_mac_min"])


def test_scope_rejects_asymmetric_and_physics_bearing():
    from drm_core import AsymmetricShaftElement,PlainJournalPhysicsBearing
    model=model_for("R02")
    bad=RotorModel(nodes=model.nodes,shafts=[
        AsymmetricShaftElement(11,1,2,1.,1.,0.,0.,1.,1.),
        model.shafts[1],
    ],disks=model.disks,advanced_bearings=model.advanced_bearings)
    with pytest.raises(ValueError,match="Asymmetric"):
        assemble_6dof(bad)
    # Direct physical providers must be materialized before B2.
    p=PlainJournalPhysicsBearing(
        node=1,weight_n=1000.,journal_diameter_m=.05,radial_clearance_m=5e-5,
        oil_viscosity_pa_s=.02,pivot_angle_rad=(0.,),pad_arc_rad=(3.0,),
        pad_axial_length_m=(.05,),preload=(0.,),offset=(.5,)
    )
    bad2=RotorModel(nodes=model.nodes,shafts=model.shafts,disks=model.disks,advanced_bearings=[p])
    with pytest.raises(ValueError,match="pre-materialized"):
        assemble_6dof(bad2,100.)


def test_binding_contains_no_production_linear_algebra_or_mac_tracking():
    import drm_core.solver.sixdof_global as module
    source=inspect.getsource(module)
    forbidden=("np.linalg","scipy.linalg","np.linalg.eig","modal_assurance","def mac(","MAC_GLOBAL")
    assert not any(token in source for token in forbidden)


def test_frozen_b2_authority_is_immutable():
    subprocess.run([
        "git","diff","--exit-code","d9be588c71bfd7116f61d1f5f5be3a2ee0e06726","HEAD",
        "--","validation/ross_parity/6dof_global"
    ],cwd=ROOT,check=True)
