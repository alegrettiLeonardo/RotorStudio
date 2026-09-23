from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,run_campbell,run_critical_speeds
from drm_core.units import rpm_to_rad_s

CASES=np.array([[1e7,1e7,0,0],[1e7,2e7,0,0],[1e7,2e7,6e4,6e4],[1e7,2e7,4e5,4e5],[2e5,4e5,0,0]],float)

def build(lh:int,rh:int)->RotorModel:
    if not (1<=lh<=5 and 1<=rh<=5): raise ValueError('bearing cases must be 1..5')
    E=211e9; G=E/(2*(1+.3)); rho=7810.; od=.025
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i+1,i+2,od,0.,rho,E,G,0.) for i in range(6)]
    disks=[Disk.geometric(7,rho,.04,.250,0.)]
    bearings=[Bearing(3,1,tuple(CASES[lh-1])),Bearing(3,5,tuple(CASES[rh-1]))]
    return RotorModel(nodes,shafts,disks,bearings)

def main(lh:int,rh:int,outdir:str):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True); m=build(lh,rh)
    camp_rpm=np.arange(0.,3200.1,40.)
    camp=run_campbell(m,rpm_to_rad_s(camp_rpm)); np.savez(out/'campbell.npz',speed_rpm=camp_rpm,eigenvalues=camp.eigenvalues)
    direct=run_critical_speeds(m,NX=1,damped_NF=True,number_criticals=10,method='direct')
    iterative=run_critical_speeds(m,NX=1,damped_NF=True,number_criticals=10,max_iterations=20,convergence_tol=1e-6,method='iterative-index')
    seeds_rpm=np.array([300.,400.,2000.,2500.,3000.])
    near=run_critical_speeds(m,NX=1,damped_NF=True,max_iterations=20,convergence_tol=1e-6,method='iterative-nearest',initial_estimates=rpm_to_rad_s(seeds_rpm))
    np.savetxt(out/'critical_direct_rpm.csv',direct.critical_speeds_rad_s*60/(2*np.pi),delimiter=',')
    np.savetxt(out/'critical_iterative_rpm.csv',iterative.critical_speeds_rad_s*60/(2*np.pi),delimiter=',')
    np.savetxt(out/'critical_nearest_rpm.csv',near.critical_speeds_rad_s*60/(2*np.pi),delimiter=',')
    print(f'Example_06_08_01 LH={lh} RH={rh} completed')
    print('direct rpm:', ' '.join(f'{x:.8f}' for x in direct.critical_speeds_rad_s*60/(2*np.pi)))
    print('iterative converged:', bool(np.all(iterative.converged)))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--lh-case',type=int,choices=range(1,6),required=True); ap.add_argument('--rh-case',type=int,choices=range(1,6),required=True); ap.add_argument('--outdir',default='example_06_08_01_out')
    a=ap.parse_args(); main(a.lh_case,a.rh_case,a.outdir)
