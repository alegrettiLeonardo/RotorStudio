from pathlib import Path
import os, sys, numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'python'/'src'));sys.path.insert(0,str(ROOT))
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,Force,run_runup
from drm_core.units import rpm_to_rad_s
from drm_core.solver.backend import FortranBackend
# Import independent SciPy-oracle helpers from qualification tests.
from python.tests.test_transient_source_oracle_m5 import foundation_model,runup_model,foundation_oracle,runup_oracle

def main():
    out=Path(__file__).resolve().parent
    fm=foundation_model();t,x,f,maxf=foundation_oracle(fm,rpm_to_rad_s(3000),2e-4,601,10)
    dofs=np.array([8,9,16,17],dtype=int)
    np.savez_compressed(out/'time_fdn_source_reference.npz',time=t,response=x[dofs,:],response_dofs=dofs,force=f,max_reduced_frequency_hz=maxf,rotor_speed_rad_s=rpm_to_rad_s(3000),dt=2e-4,npts=601,nr=10,pulse_duration=.025)
    rm=runup_model();alpha=np.array([.20*2*np.pi,8*np.pi,0.]);prod=run_runup(rm,alpha,[0,3.0],nr=4,rtol=2e-7,atol=2e-10,max_points=50000);te=prod.time_s
    x,s,maxf=runup_oracle(rm,alpha,te,4)
    dofs=np.array([24,25],dtype=int)
    np.savez_compressed(out/'runup_source_reference.npz',time=te,response=x[dofs,:],response_dofs=dofs,speed=s,max_reduced_frequency_hz=maxf,alpha=alpha,nr=4,rtol=2e-7,atol=2e-10)
if __name__=='__main__': main()
