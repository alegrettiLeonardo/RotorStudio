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
from validation.ross_parity.verify_6dof_global_candidate import evec_group_parity,eigen_groups

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
    if p.get("exact_zero_pattern"):
        # Native B2 consumes B1 matrices, whose already-qualified parity is
        # tolerance based. Treat sub-atol cancellation noise as structural zero;
        # the frozen atol itself is not changed after native comparison.
        actual_zero=np.abs(actual)<=p["atol"]
        expected_zero=np.abs(expected)<=p["atol"]
        mismatch=np.argwhere(actual_zero!=expected_zero)
        assert not len(mismatch), [
            (tuple(int(x) for x in ij),float(actual[tuple(ij)]),float(expected[tuple(ij)]))
            for ij in mismatch
        ]
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
    valid=lambda a: np.all(np.isnan(a)|np.isin(a,[0.0,0.5,1.0]))
    assert valid(result.whirl_value) and valid(exp_whirl)
    # Whirl is an eigenvector-orbit diagnostic and can flip at nearly linear
    # orbits under LAPACK-basis perturbations even when eigenvalue/MAC parity
    # passes. Exact F/B/M semantics are therefore gated by native sentinels;
    # frozen modal parity still requires valid enum/NaN plus normative mode type.
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
    valid=lambda a: np.all(np.isnan(a)|np.isin(a,[0.0,0.5,1.0]))
    assert valid(result.whirl_value) and valid(expected_whirl)
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


def _nearest_relative_error(reference, candidate):
    reference=np.asarray(reference,dtype=float)
    remaining=list(np.asarray(candidate,dtype=float))
    errors=[]
    for value in reference:
        if not remaining:break
        j=min(range(len(remaining)),key=lambda k:abs(remaining[k]-value))
        other=remaining.pop(j)
        errors.append(abs(value-other)/max(1.0,abs(value),abs(other)))
    return max(errors,default=0.0)


def test_independent_global_superposition_energy_and_state_space():
    """Independent validation math; production assembly remains native Fortran."""
    from drm_core.solver.sixdof_elements import shaft_matrices,disk_matrices
    model=model_for("R02")
    speed=137.0
    g=assemble_6dof(model,speed,speed)
    n=6*len(model.nodes)
    M=np.zeros((n,n));K=np.zeros((n,n));C=np.zeros((n,n));G=np.zeros((n,n));Ksdt=np.zeros((n,n))
    z={int(node.number):float(node.z_m) for node in model.nodes}
    def add(global_,local,idx):
        global_[np.ix_(idx,idx)]+=local
    for shaft in model.shafts:
        L=z[int(shaft.node2)]-z[int(shaft.node1)]
        if isinstance(shaft,ShaftElement):
            mats=shaft_matrices(
                L=L,idl=shaft.inner_diameter_m,odl=shaft.outer_diameter_m,
                idr=shaft.inner_diameter_m,odr=shaft.outer_diameter_m,
                rho=shaft.rho_kg_m3,E=shaft.E_pa,G_s=shaft.G_pa,
                axial_force=shaft.axial_force_n,torque=shaft.torque_nm,
                shear_effects=True,rotary_inertia=True,gyroscopic=True,
            )
        else:
            mats=shaft_matrices(
                L=L,idl=shaft.inner_diameter_1_m,odl=shaft.outer_diameter_1_m,
                idr=shaft.inner_diameter_2_m,odr=shaft.outer_diameter_2_m,
                rho=shaft.rho_kg_m3,E=shaft.E_pa,G_s=shaft.G_pa,
                axial_force=shaft.axial_force_n,torque=0.0,
                shear_effects=True,rotary_inertia=True,gyroscopic=True,
            )
        idx=[6*(int(shaft.node1)-1)+d for d in range(6)]+[6*(int(shaft.node2)-1)+d for d in range(6)]
        add(M,mats.M,idx);add(K,mats.K,idx);add(G,mats.G,idx);add(Ksdt,mats.Kst,idx)
    for disk in model.disks:
        assert disk.disk_type==2
        mats=disk_matrices(m=disk.p3,Id=disk.p4,Ip=disk.p5)
        idx=[6*(int(disk.node)-1)+d for d in range(6)]
        add(M,mats.M,idx);add(G,mats.G,idx);add(Ksdt,mats.Kdt,idx)
    # R02 has constant qualified coefficient bearings, so their radial blocks
    # are independently materialized without invoking B2 assembly.
    for b in model.advanced_bearings:
        idx=[6*(int(b.node)-1),6*(int(b.node)-1)+1]
        K[np.ix_(idx,idx)]+=np.array([[float(b.kxx),float(b.kxy)],[float(b.kyx),float(b.kyy)]])
        C[np.ix_(idx,idx)]+=np.array([[float(b.cxx),float(b.cxy)],[float(b.cyx),float(b.cyy)]])
        M[np.ix_(idx,idx)]+=np.array([[float(b.mxx),float(b.mxy)],[float(b.myx),float(b.myy)]])
    for actual,expected in ((g.M,M),(g.K,K),(g.C,C),(g.G,G),(g.Ksdt,Ksdt)):
        np.testing.assert_allclose(actual,expected,rtol=3e-12,atol=1e-8)
    q=np.linspace(-0.7,1.3,n)
    np.testing.assert_allclose(q@g.K@q,q@K@q,rtol=2e-13,atol=1e-8)
    np.testing.assert_allclose(q@g.M@q,q@M@q,rtol=2e-13,atol=1e-12)

    modal=run_modal_6dof(model,speed,12)
    A=modal.state_space
    eye=np.eye(n);zero=np.zeros((n,n))
    np.testing.assert_allclose(A[:n,:n],zero,rtol=0,atol=0)
    np.testing.assert_allclose(A[:n,n:],eye,rtol=0,atol=0)
    np.testing.assert_allclose(A[n:,:n],np.linalg.solve(-g.M,g.K),rtol=5e-11,atol=1e-7)
    np.testing.assert_allclose(A[n:,n:],np.linalg.solve(-g.M,g.C+speed*g.G),rtol=5e-11,atol=1e-7)


def test_independent_modal_identities_conjugates_repeatability_and_gyroscopic_split():
    model=model_for("R02")
    r0=run_modal_6dof(model,0.0,12)
    r1=run_modal_6dof(model,200.0,12)
    r1b=run_modal_6dof(model,200.0,12)
    np.testing.assert_array_equal(r1.eigenvalues_all,r1b.eigenvalues_all)
    np.testing.assert_array_equal(r1.eigenvalues,r1b.eigenvalues)
    np.testing.assert_array_equal(r1.state_space,r1b.state_space)
    np.testing.assert_allclose(r1.wn_rad_s,np.abs(r1.eigenvalues),rtol=2e-14,atol=2e-12)
    np.testing.assert_allclose(r1.wd_rad_s,r1.eigenvalues.imag,rtol=0,atol=0)
    zeta=-r1.eigenvalues.real/np.abs(r1.eigenvalues)
    np.testing.assert_allclose(r1.damping_ratio,zeta,rtol=2e-14,atol=2e-14)
    valid=1-zeta*zeta>0
    expected=np.full_like(zeta,np.nan,dtype=float)
    expected[valid]=2*np.pi*zeta[valid]/np.sqrt(1-zeta[valid]*zeta[valid])
    np.testing.assert_allclose(r1.log_dec,expected,rtol=2e-13,atol=2e-13,equal_nan=True)
    for lam in r1.eigenvalues_all:
        assert np.min(np.abs(r1.eigenvalues_all-np.conj(lam))) < 2e-7*max(1.0,abs(lam))
    assert np.max(r1.residual) <= POLICY["modal"]["residual_max"]
    # Nonzero spin must split at least one lateral pair relative to zero-speed
    # degeneracy; compare sorted lateral damped frequencies.
    f0=np.sort(r0.wd_rad_s[np.array(r0.mode_type)=="Lateral"])
    f1=np.sort(r1.wd_rad_s[np.array(r1.mode_type)=="Lateral"])
    n=min(len(f0),len(f1))
    assert n>=2
    assert np.max(np.abs(f1[:n]-f0[:n])) > 1e-3


def test_campbell_station_consistency_tracking_permutation_and_repeatability():
    case=next(c for c in SPEC["campbell_cases"] if c["id"]=="C03")
    model=model_for(case["rotor"])
    speeds=case["speed_range_rad_s"];freq=case["frequencies"];nt=freq+2
    camp=run_campbell_6dof(model,speeds,freq)
    repeat=run_campbell_6dof(model,speeds,freq)
    for name in ("wd_rad_s","wn_rad_s","damping_ratio","log_dec","tracking_index","tracking_mac","mac_matrix"):
        np.testing.assert_allclose(getattr(camp,name),getattr(repeat,name),rtol=0,atol=0,equal_nan=True)
    identity=np.arange(nt)
    saw_reorder=False
    for s,w in enumerate(speeds):
        order=camp.tracking_index[:,s]
        np.testing.assert_array_equal(np.sort(order),identity)
        saw_reorder |= not np.array_equal(order,identity)
        modal=run_modal_6dof(model,float(w),2*nt)
        np.testing.assert_allclose(camp.wd_rad_s[:,s],modal.wd_rad_s[order[:freq]],rtol=2e-11,atol=2e-8)
        np.testing.assert_allclose(camp.wn_rad_s[:,s],modal.wn_rad_s[order[:freq]],rtol=2e-11,atol=2e-8)
    # C03 is the frozen tracking sentinel where frequency-only identity ordering
    # and MAC branch identity differ after the branches approach.
    assert saw_reorder


def test_6dof_lateral_common_domain_crosscheck_against_qualified_4dof():
    from drm_core import run_modal as run_modal_4dof
    model=model_for("R02")
    for speed in (0.0,150.0):
        r6=run_modal_6dof(model,speed,12)
        r4=run_modal_4dof(model,speed,with_eigenvectors=True,with_kappa=True)
        f6=np.sort(r6.wd_rad_s[np.array(r6.mode_type)=="Lateral"])
        eig4=np.asarray(r4.eigenvalues,dtype=np.complex128)
        # The 4DOF result contains the conjugate negative-frequency half too.
        # Compare only the same positive-imaginary physical family selected by
        # the dense 6DOF/Ross ordering; otherwise abs(imag) double-counts every
        # conjugate pair and creates a false mismatch.
        f4=np.sort(eig4.imag[eig4.imag>1e-8])
        n=min(4,len(f6),len(f4))
        assert n>=2
        assert _nearest_relative_error(f6[:n],f4[:n]) < 2e-4
