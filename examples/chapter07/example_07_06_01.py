from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from drm_core import RotorModel,Node,AsymmetricShaftElement,Disk,Bearing,Force,run_asymmetric_modal,run_asymmetric_frequency_response
from drm_core.units import rpm_to_rad_s

def build(case:int=1,phase:float=0.0):
    E=211e9;rho=7810.;A=.002;Ix=4.2043e-7;Iy=2.4112e-7;rhoA=rho*A;rhoI=rho*(Ix+Iy)/2
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[AsymmetricShaftElement(11,i,i+1,E*Ix,E*Iy,0.,0.,rhoA,rhoI,0.) for i in range(1,7)]
    shaft_od=2*np.sqrt(A/np.pi);disks=[Disk.geometric(3,rho,.07,.28,shaft_od),Disk.geometric(5,rho,.07,.35,shaft_od)]
    damp=0. if case==1 else 5e3;bearings=[Bearing(3,1,(1e6,1e6,damp,damp)),Bearing(3,7,(1e6,1e6,damp,damp))]
    return RotorModel(nodes,shafts,disks,bearings,[Force(1,(3,.001,phase))])

def main(case=1,phase=0.,smoke=False,outdir='example_07_06_01_out'):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);m=build(case,phase)
    rpm=np.arange(0,4500+(100 if smoke else 10),100 if smoke else 10,dtype=float);sp=rpm_to_rad_s(rpm)
    eig=np.column_stack([run_asymmetric_modal(m,w,with_eigenvectors=False).eigenvalues for w in sp]);np.savez(out/'rotating_frame_eigenvalues.npz',rpm=rpm,eigenvalues=eig)
    rrpm=np.arange(10,4500+(50 if smoke else 2),50 if smoke else 2,dtype=float);resp=run_asymmetric_frequency_response(m,rpm_to_rad_s(rrpm)).response
    amps=[]
    for n in (3,4,5):amps.append(np.sqrt(resp[4*n-4,:]**2+resp[4*n-3,:]**2))
    np.savetxt(out/'response_amplitude.csv',np.column_stack([rrpm,*amps]),delimiter=',')
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,ax=plt.subplots()
    for row in range(0,min(16,eig.shape[0]),2):ax.plot(rpm,eig[row,:].imag/(2*np.pi))
    ax.set_xlabel('Rotor spin speed (rev/min)');ax.set_ylabel('Rotating-frame eigenvalue imag/(2pi) (Hz)');ax.grid(True);fig.savefig(out/'rotating_frame_eigs.png',dpi=140);plt.close(fig)
    fig,ax=plt.subplots()
    for a,l in zip(amps,['Left disk','Mid point','Right disk']):ax.semilogy(rrpm,a,label=l)
    ax.set_xlabel('Rotor spin speed (rev/min)');ax.set_ylabel('Response magnitude (m)');ax.grid(True);ax.legend();fig.savefig(out/'response.png',dpi=140);plt.close(fig)
    print(f'Example_07_06_01 case={case} phase={phase} completed: modal_points={len(rpm)} response_points={len(rrpm)}')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case',type=int,choices=[1,2],default=1);p.add_argument('--phase',type=float,default=0.);p.add_argument('--smoke',action='store_true');p.add_argument('--outdir',default='example_07_06_01_out');a=p.parse_args();main(a.case,a.phase,a.smoke,a.outdir)
