#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
import numpy as np
from drm_core import Bearing,CoefficientBearing,Node,RotorModel,ShaftElement
from drm_core.analysis.modal import run_modal

ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"

def match_error(a,b):
    remaining=list(np.asarray(b,dtype=complex));errors=[]
    for x in np.asarray(a,dtype=complex):
        j=min(range(len(remaining)),key=lambda k:abs(remaining[k]-x))
        y=remaining.pop(j);errors.append(abs(x-y)/max(1.0,abs(y)))
    return max(errors)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--ross-root",type=Path,required=True);args=ap.parse_args()
    head=subprocess.check_output(["git","-C",str(args.ross_root),"rev-parse","HEAD"],text=True).strip()
    if head!=ROSS_SHA: raise SystemExit(f"ROSS authority mismatch: {head}")
    sys.path.insert(0,str(args.ross_root.resolve()))
    import ross as rs
    from ross.utils import convert_6dof_to_4dof

    bearing=CoefficientBearing(
        node=1,kxx=1.20e6,kxy=2e4,kyx=-3e4,kyy=1.45e6,
        cxx=180.0,cxy=8.0,cyx=-6.0,cyy=210.0,
        mxx=12.0,mxy=0.4,myx=0.4,myy=9.0,
    )
    speed=150.0
    material=rs.Material(name="B19Steel",rho=7810.0,E=211e9,G_s=81.2e9)
    shaft=rs.ShaftElement(L=1.0,idl=0.0,odl=.05,material=material,n=0,shear_effects=True,rotary_inertia=True,gyroscopic=True)
    adv=rs.BearingElement(
        n=0,kxx=bearing.kxx,kxy=bearing.kxy,kyx=bearing.kyx,kyy=bearing.kyy,
        cxx=bearing.cxx,cxy=bearing.cxy,cyx=bearing.cyx,cyy=bearing.cyy,
        mxx=bearing.mxx,mxy=bearing.mxy,myx=bearing.myx,myy=bearing.myy,
    )
    support=rs.BearingElement(n=1,kxx=1.3e6,kyy=1.4e6,cxx=160.0,cyy=170.0)
    rotor=convert_6dof_to_4dof(rs.Rotor([shaft],bearing_elements=[adv,support]))

    model=RotorModel(
        nodes=[Node(1,0.0),Node(2,1.0)],
        shafts=[ShaftElement(2,1,2,.05,0.0,7810.0,211e9,81.2e9,0.0,0.0,0.0)],
        bearings=[Bearing(5,2,(1.3e6,0.0,0.0,1.4e6,160.0,0.0,0.0,170.0))],
        advanced_bearings=[bearing],
    )
    ours=run_modal(model,speed,with_eigenvectors=True)
    ref=rotor.run_modal(speed,num_modes=16,sparse=False)
    err=match_error(ours.eigenvalues,ref.evalues)
    if err>5e-6: raise SystemExit(f"B19 ROSS eigenvalue parity failed: {err}")
    mref=np.asarray(adv.M(speed,speed),dtype=float)[:2,:2]
    np.testing.assert_allclose(mref,[[12.0,.4],[.4,9.0]],rtol=0,atol=1e-14)
    print(json.dumps({"status":"PASS","ross_authority":ROSS_SHA,"max_relative_eigenvalue_error":err,"bearing_mass_matrix_kg":mref.tolist()},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
