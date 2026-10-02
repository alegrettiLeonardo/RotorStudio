from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pytest

from drm_core import (
    RotorModel,Node,ShaftElement,Disk,Bearing,
    AnalysisCase,AnalysisService,RotorProject,save_project,load_project,
    run_misalignment_6dof,node_orbit,response_dfft,
)

ROOT=Path(__file__).resolve().parents[2]
AUTH=ROOT/"validation/ross_parity/misalignment"
SPEC=json.loads((ROOT/"validation/c1/cases.json").read_text(encoding="utf-8"))
POLICY=json.loads((ROOT/"validation/c1/TOLERANCE_POLICY.json").read_text(encoding="utf-8"))


def model_from_spec():
    m=SPEC["model"];z=[0.0]
    for L in m["lengths_m"]:z.append(z[-1]+L)
    nodes=[Node(i+1,v) for i,v in enumerate(z)]
    shafts=[
        ShaftElement(2,i+1,i+2,m["outer_diameter_m"],m["inner_diameter_m"],
                     m["rho_kg_m3"],m["E_pa"],m["G_pa"],0.0,0.0,0.0)
        for i in range(len(m["lengths_m"]))
    ]
    d=m["disk"]
    disks=[Disk.inertial(int(d["node_ross"])+1,d["m_kg"],d["Id_kg_m2"],d["Ip_kg_m2"])]
    bearings=[
        Bearing(3,int(b["node_ross"])+1,
                (b["kxx_n_m"],b["kyy_n_m"],b["cxx_ns_m"],b["cyy_ns_m"]))
        for b in m["bearings"]
    ]
    return RotorModel(nodes=nodes,shafts=shafts,disks=disks,bearings=bearings)


def params(case):
    tr=SPEC["transient"];nt=int(round((tr["time_stop_s"]-tr["time_start_s"])/tr["dt_s"]))+1
    p=dict(
        coupling=case["coupling"],
        shaft_index=int(SPEC["model"]["coupling_element_ross"]),
        time_s=np.linspace(tr["time_start_s"],tr["time_stop_s"],nt),
        speed_rad_s=tr["speed_rad_s"],
        unbalance_nodes=[int(x["node_ross"])+1 for x in tr["unbalance"]],
        unbalance_magnitude_kg_m=[x["magnitude_kg_m"] for x in tr["unbalance"]],
        unbalance_phase_rad=[x["phase_rad"] for x in tr["unbalance"]],
        input_torque_nm=case.get("input_torque_nm",0.0),
        load_torque_nm=case.get("load_torque_nm",0.0),
        gamma=tr["gamma"],beta=tr["beta"],tol=tr["tol"],
    )
    if case["coupling"]=="flex":
        p.update(
            mis_type=case["mis_type"],
            mis_distance_x_m=case["mis_distance_x_m"],
            mis_distance_y_m=case["mis_distance_y_m"],
            mis_angle_rad=case["mis_angle_rad"],
            radial_stiffness_n_m=case["radial_stiffness_n_m"],
            bending_stiffness_n=case["bending_stiffness_n"],
        )
    else:
        p.update(mis_distance_m=case["mis_distance_m"])
    return p


def close(group,actual,expected):
    t=POLICY["groups"][group]
    np.testing.assert_allclose(actual,expected,rtol=t["rtol"],atol=t["atol"],equal_nan=True)


@pytest.mark.parametrize("case",SPEC["cases"],ids=lambda c:c["id"])
def test_c1_native_parity_against_immutable_ross_authority(case):
    result=run_misalignment_6dof(model_from_spec(),**params(case))
    d=AUTH/"cases"/case["id"]
    close("time",result.time_s,np.load(d/"time.npy",allow_pickle=False))
    close("theta",result.angle_rad,np.load(d/"theta.npy",allow_pickle=False))
    close("base_force",result.force_unbalance,np.load(d/"base_force.npy",allow_pickle=False))
    close("misalignment_force",result.force_misalignment,np.load(d/"misalignment_force.npy",allow_pickle=False))
    close("total_force",result.force_total,np.load(d/"total_force.npy",allow_pickle=False))
    close("displacement",result.displacement.T,np.load(d/"q.npy",allow_pickle=False))
    observation=int(SPEC["transient"]["observation_node_ross"])+1
    close("orbit",node_orbit(result,observation),np.load(d/"orbit.npy",allow_pickle=False))
    freq,amp=response_dfft(result,observation,"x")
    close("fft_frequency",freq,np.load(d/"fft_frequency_hz.npy",allow_pickle=False))
    close("fft_amplitude",amp,np.load(d/"fft_amplitude.npy",allow_pickle=False))
    expected_rigid=np.load(d/"rigid_parameters.npy",allow_pickle=False)
    close("rigid_parameters",result.rigid_parameters,expected_rigid)
    assert result.metadata["ross_authority_sha"]==SPEC["ross_sha"]
    assert result.metadata["python_numerical_fallback"] is False


def test_c1_flexible_force_hierarchy_and_action_reaction():
    model=model_from_spec()
    cases={c["id"]:c for c in SPEC["cases"]}
    p=run_misalignment_6dof(model,**params(cases["C1F01"]))
    a=run_misalignment_6dof(model,**params(cases["C1F02"]))
    c=run_misalignment_6dof(model,**params(cases["C1F03"]))
    np.testing.assert_allclose(c.force_misalignment,p.force_misalignment+a.force_misalignment,rtol=1e-13,atol=1e-11)
    # Coupling element 2 (zero-based index 1) connects RotorStudio nodes 2 and 3.
    left=6;right=12
    for r in (p,a,c):
        np.testing.assert_allclose(r.force_misalignment[left]+r.force_misalignment[right],0,atol=POLICY["independent"]["force_action_reaction_atol_n"])
        np.testing.assert_allclose(r.force_misalignment[left+1]+r.force_misalignment[right+1],0,atol=POLICY["independent"]["force_action_reaction_atol_n"])


def test_c1_rigid_zero_offset_zero_torque_has_no_fault_force():
    case=dict(SPEC["cases"][3])
    case["mis_distance_m"]=0.0
    p=params(case)
    p.update(unbalance_nodes=[],unbalance_magnitude_kg_m=[],unbalance_phase_rad=[])
    result=run_misalignment_6dof(model_from_spec(),**p)
    np.testing.assert_array_equal(result.force_misalignment,np.zeros_like(result.force_misalignment))
    np.testing.assert_array_equal(result.displacement,np.zeros_like(result.displacement))


@pytest.mark.parametrize("case",SPEC["cases"],ids=lambda c:c["id"])
def test_c1_newmark_equation_scaled_residual_gate(case):
    result=run_misalignment_6dof(model_from_spec(),**params(case))
    assert np.max(result.residual[1:])<=POLICY["independent"]["max_newmark_equation_scaled_residual"]


def test_c1_fail_closed_inputs():
    model=model_from_spec();case=SPEC["cases"][0];p=params(case)
    with pytest.raises(ValueError,match="mis_distance_y_m"):
        run_misalignment_6dof(model,**{**p,"mis_distance_y_m":0.0})
    with pytest.raises(ValueError,match="shaft_index"):
        run_misalignment_6dof(model,**{**p,"shaft_index":99})
    with pytest.raises(ValueError,match="equal length"):
        run_misalignment_6dof(model,**{**p,"unbalance_phase_rad":[]})
    with pytest.raises(ValueError,match="strictly increasing"):
        run_misalignment_6dof(model,**{**p,"time_s":[0.0,0.01,0.01]})


def test_c1_analysis_service_and_project_roundtrip(tmp_path):
    model=model_from_spec();p=params(SPEC["cases"][2])
    case=AnalysisCase("misalignment",p,"C1 combined")
    project=RotorProject("C1",model,[case])
    saved=save_project(project,tmp_path/"c1.rds")
    reopened=load_project(saved)
    result=AnalysisService().execute(reopened,reopened.analyses[0])
    assert result.result.coupling=="flex" and result.result.mis_type=="combined"
    assert result.result.metadata["analysis_hash"]==result.analysis_hash
    direct=run_misalignment_6dof(model,**p)
    close("displacement",result.result.displacement,direct.displacement)


def test_c1_authority_is_frozen_before_production():
    record=json.loads((AUTH/"FREEZE_RECORD.json").read_text(encoding="utf-8"))
    assert record["production_solver"]=="NOT_STARTED"
    assert record["ross_sha"]==SPEC["ross_sha"]
    assert record["cross_platform_status"]=="PASS"
    assert record["array_count"]==60
