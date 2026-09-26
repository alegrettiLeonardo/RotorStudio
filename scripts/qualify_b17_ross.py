#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from drm_core import (
    AnalysisCase, AnalysisService, Bearing, CoefficientBearing, Node,
    PlainJournalPhysicsBearing, RotorModel, RotorProject, ShaftElement,
    TiltingPadPhysicsBearing, generate_operating_map,
)
from drm_core.analysis.modal import FIXED_WHIRL, MATCHED_WHIRL, run_modal
from drm_core.solver.bearings_backend import AdvancedBearingBackend

ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"


def _source_bearing(node=1):
    speed=(50.0,150.0,250.0)
    frequency=(20.0,120.0,320.0)
    def surf(base,a,b):
        return tuple(tuple(base+a*s+b*w for w in frequency) for s in speed)
    return CoefficientBearing(
        node=node,speed_rad_s=speed,frequency_rad_s=frequency,interpolation="linear",
        kxx=surf(1.20e6,250.0,650.0),kxy=surf(2.0e4,10.0,-12.0),
        kyx=surf(-3.0e4,-8.0,15.0),kyy=surf(1.45e6,180.0,520.0),
        cxx=surf(180.0,.03,.10),cxy=surf(8.0,.002,-.003),
        cyx=surf(-6.0,-.002,.004),cyy=surf(210.0,.02,.08),
    )


def _plain():
    return PlainJournalPhysicsBearing(
        node=1,weight_n=112814.90696191376,journal_diameter_m=0.3999992,
        radial_clearance_m=0.000194564,oil_viscosity_pa_s=0.01901574061455835,
        pivot_angle_rad=(np.pi/2,3*np.pi/2),pad_arc_rad=(3.07177948351002,)*2,
        pad_axial_length_m=(0.263144,)*2,preload=(0.0,0.0),offset=(0.5,0.5),
        total_e_x_film=8,total_e_z_film=4,total_e_y_pad=4,total_e_y_film=4,
        xj_ratio_initial=.15,yj_ratio_initial=-.2,force_tolerance=5e-3,
        outer_iterations=12,
    )


def _tilting():
    return TiltingPadPhysicsBearing(
        node=1,weight_n=112814.90696191376,journal_diameter_m=0.3999992,
        radial_clearance_m=0.000194564,oil_viscosity_pa_s=0.01901574061455835,
        pad_thickness_m=0.149614636,pad_density_kg_m3=7835.631544657211,
        pivot_angle_rad=(0.9424777960769379,2.199114857512855,3.4557519189487724,4.71238898038469,5.969026041820607),
        pad_arc_rad=(1.0471975511965976,)*5,pad_axial_length_m=(0.263144,)*5,
        preload=(0.3,)*5,offset=(0.5,)*5,k_rotate_nm_rad=(0.0,)*5,
        total_e_x_film=8,total_e_z_film=4,total_e_y_pad=4,total_e_y_film=4,
        xj_ratio_initial=.15,yj_ratio_initial=-.2,force_tolerance=5e-3,outer_iterations=12,
    )


def _model(bearing):
    return RotorModel(
        nodes=[Node(1,0.0),Node(2,1.0)],
        shafts=[ShaftElement(2,1,2,.05,0.0,7810.0,211e9,81.2e9,0.0,0.0,0.0)],
        bearings=[Bearing(5,2,(1.3e6,0.0,0.0,1.4e6,160.0,0.0,0.0,170.0))],
        advanced_bearings=[bearing],
    )


def _ross_rotor(rs, convert_6dof_to_4dof, bearing):
    material=rs.Material(name="B17Steel",rho=7810.0,E=211e9,G_s=81.2e9)
    shaft=rs.ShaftElement(
        L=1.0,idl=0.0,odl=.05,material=material,n=0,
        shear_effects=True,rotary_inertia=True,gyroscopic=True,
    )
    kwargs=dict(
        n=0,kxx=bearing.kxx,kxy=bearing.kxy,kyx=bearing.kyx,kyy=bearing.kyy,
        cxx=bearing.cxx,cxy=bearing.cxy,cyx=bearing.cyx,cyy=bearing.cyy,
        mxx=0.0,myy=0.0,mxy=0.0,myx=0.0,
        speed=list(bearing.speed_rad_s) if bearing.speed_rad_s else None,
        frequency=list(bearing.frequency_rad_s) if bearing.frequency_rad_s else None,
        interpolation=bearing.interpolation,
    )
    adv=rs.BearingElement(**kwargs)
    support=rs.BearingElement(n=1,kxx=1.3e6,kyy=1.4e6,cxx=160.0,cyy=170.0)
    return convert_6dof_to_4dof(rs.Rotor([shaft],bearing_elements=[adv,support]))


def _match_values(actual,expected,rtol=5e-7,atol=2e-5):
    a=list(np.asarray(actual,dtype=np.complex128))
    e=list(np.asarray(expected,dtype=np.complex128))
    assert len(a)==len(e),(len(a),len(e))
    pairs=[]
    remaining=set(range(len(e)))
    for value in a:
        j=min(remaining,key=lambda k:abs(e[k]-value))
        pairs.append(j);remaining.remove(j)
    ordered=np.asarray([e[j] for j in pairs])
    np.testing.assert_allclose(np.asarray(a),ordered,rtol=rtol,atol=atol)
    return pairs


def _mac(a,b):
    a=np.asarray(a,dtype=complex);b=np.asarray(b,dtype=complex)
    den=np.vdot(a,a).real*np.vdot(b,b).real
    return float(abs(np.vdot(a,b))**2/den) if den>0 else 0.0


def _qualify_case(label,bearing,rs,convert):
    model=_model(bearing)
    ross=_ross_rotor(rs,convert,bearing)
    Omega=150.0;omega=70.0
    fixed=run_modal(model,Omega,with_eigenvectors=True,coefficient_policy=FIXED_WHIRL,whirl_frequency_rad_s=omega)
    rfixed=ross.run_modal(Omega,num_modes=16,sparse=False,frequency=omega)
    fixed_pairs=_match_values(fixed.eigenvalues,rfixed.evalues,rtol=3e-6,atol=5e-4)

    matched=run_modal(model,Omega,with_eigenvectors=True,coefficient_policy=MATCHED_WHIRL,whirl_rtol=1e-3,whirl_max_iter=30)
    rmatched=ross.run_modal(Omega,num_modes=16,sparse=False,matched_whirl=True,whirl_rtol=1e-3,whirl_max_iter=30)
    pairs=_match_values(matched.eigenvalues,rmatched.evalues,rtol=3e-4,atol=5e-3)
    rvec=np.asarray(rmatched.evectors,dtype=complex)
    if rvec.shape[0] >= ross.ndof:
        rdisp=rvec[:ross.ndof,:]
        mac=[]
        for i,j in enumerate(pairs):
            if j < rdisp.shape[1]:
                mac.append(_mac(matched.eigenvectors[:,i],rdisp[:,j]))
        if mac:
            assert min(mac)>0.90,(label,mac)

    np.testing.assert_allclose(
        np.sort(np.asarray(matched.metadata["whirl_frequency_rad_s"],dtype=float)),
        np.sort(np.abs(np.asarray(rmatched.wd,dtype=float))),
        rtol=3e-4,atol=5e-3,
    )
    np.testing.assert_allclose(
        np.sort(np.asarray(matched.damping_ratio,dtype=float)),
        np.sort(np.asarray(rmatched.damping_ratio,dtype=float)),
        rtol=2e-3,atol=2e-5,
    )

    speeds=np.array([130.0,150.0,170.0])
    project=RotorProject(label,model)
    case=AnalysisCase("modal_sweep",{
        "speeds_rad_s":speeds.tolist(),"with_eigenvectors":True,"with_kappa":False,
        "coefficient_policy":MATCHED_WHIRL,"whirl_rtol":1e-3,"whirl_max_iter":30,
    },label+" Campbell")
    rs_points=AnalysisService().execute(project,case).result
    rcamp=ross.run_campbell(speeds,frequencies=8,matched_whirl=True,whirl_rtol=1e-3,whirl_max_iter=30)
    for speed,point in zip(speeds,rs_points):
        rpoint=rcamp.modal_results[float(speed)]
        rs_wd=np.sort(np.abs(np.imag(point.eigenvalues)))
        ross_wd=np.sort(np.abs(np.asarray(rpoint.wd,dtype=float)))
        # ROSS Campbell may retain coincident forward/backward branches as
        # duplicate rows. Compare the unique physical frequencies; duplicate
        # multiplicity is a result-container convention, not rotor physics.
        ross_unique=[]
        for value in ross_wd:
            if not ross_unique or abs(float(value)-ross_unique[-1]) > 1e-7*max(1.0,abs(float(value))):
                ross_unique.append(float(value))
        ross_unique=np.asarray(ross_unique,dtype=float)
        assert len(ross_unique)==len(rs_wd),(label,speed,rs_wd,ross_wd)
        np.testing.assert_allclose(rs_wd,ross_unique,rtol=5e-4,atol=8e-3)
    return {
        "case":label,"fixed_modes":len(fixed.eigenvalues),"matched_modes":len(matched.eigenvalues),
        "minimum_inner_mac":min(float(d["last_mac"]) for d in matched.metadata["matched_whirl"]),
        "all_converged":all(bool(d["converged"]) for d in matched.metadata["matched_whirl"]),
    }


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--ross-root",type=Path,required=True)
    args=ap.parse_args()
    head=subprocess.check_output(["git","-C",str(args.ross_root),"rev-parse","HEAD"],text=True).strip()
    if head!=ROSS_SHA:raise SystemExit(f"ROSS authority mismatch: {head}")
    sys.path.insert(0,str(args.ross_root.resolve()))
    import ross as rs
    from ross.utils import convert_6dof_to_4dof

    backend=AdvancedBearingBackend()
    synthetic=_source_bearing()
    plain_map=generate_operating_map(_plain(),(130.0,150.0,170.0),interpolation="linear",backend=backend).to_coefficient_bearing(tag="B17 plain map")
    tpad_map=generate_operating_map(
        _tilting(),(130.0,170.0),(30.0,160.0,320.0),interpolation="linear",backend=backend
    ).to_coefficient_bearing(tag="B17 tpad async map")

    payload={
        "ross_authority":ROSS_SHA,
        "cases":[
            _qualify_case("synthetic_2d",synthetic,rs,convert_6dof_to_4dof),
            _qualify_case("plain_journal_map",plain_map,rs,convert_6dof_to_4dof),
            _qualify_case("tilting_pad_async_map",tpad_map,rs,convert_6dof_to_4dof),
        ],
        "status":"PASS",
    }
    print(json.dumps(payload,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
