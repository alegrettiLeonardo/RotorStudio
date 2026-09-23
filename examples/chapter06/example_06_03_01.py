from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,Force,run_campbell,run_frequency_response
from drm_core.units import rpm_to_rad_s


def build(case:int)->RotorModel:
    if case not in (1,2): raise ValueError('case must be 1 or 2')
    E=211e9; G=81.2e9; rho=7810.; shaft_od=.05
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i+1,i+2,shaft_od,0.,rho,E,G,0.) for i in range(6)]
    disks=[Disk.geometric(3,rho,.07,.28,shaft_od),Disk.geometric(5,rho,.07,.35,shaft_od)]
    props=(1e6,1e6,100.,100.) if case==1 else (1e6,.8e6,10.,10.)
    bearings=[Bearing(3,1,props),Bearing(3,7,props)]
    return RotorModel(nodes,shafts,disks,bearings,[Force.unbalance(3,.001,0.)])


def main(case:int,outdir:str):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True)
    model=build(case)
    camp_rpm=np.arange(0.,4500.1,100.)
    camp=run_campbell(model,rpm_to_rad_s(camp_rpm))
    np.savez(out/'campbell.npz',speed_rpm=camp_rpm,eigenvalues=camp.eigenvalues,kappa=camp.kappa)
    rsp_rpm=np.arange(10.,4500.1,10.)
    rsp=run_frequency_response(model,rpm_to_rad_s(rsp_rpm))
    np.savez(out/'frequency_response.npz',speed_rpm=rsp_rpm,response=rsp.response)
    probe=np.array([496.,1346.,2596.]) if case==1 else np.array([751.,800.,2320.])
    pr=run_frequency_response(model,rpm_to_rad_s(probe))
    np.savez(out/'orbit_probe_response.npz',speed_rpm=probe,response=pr.response)
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig,ax=plt.subplots();
    ax.plot(rsp_rpm,np.abs(rsp.response[8,:]),label='node 3 x')
    ax.plot(rsp_rpm,np.abs(rsp.response[16,:]),label='node 5 x')
    ax.set_xlabel('Rotor speed (rev/min)'); ax.set_ylabel('Response amplitude (m)'); ax.grid(True); ax.legend()
    fig.savefig(out/'response_nodes_3_5.png',dpi=140); plt.close(fig)
    print(f'Example_06_03_01 case={case} completed; max_abs={np.max(np.abs(rsp.response)):.12e}')

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--case',type=int,choices=[1,2],required=True); ap.add_argument('--outdir',default='example_06_03_01_out')
    a=ap.parse_args(); main(a.case,a.outdir)
