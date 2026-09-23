from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,Force,RotorDefinition,run_coaxial_modal,run_coaxial_frequency_response
from drm_core.units import rpm_to_rad_s
from drm_core.post.whirl import whirl

def build(case:int=1):
    E=2.07e11;nu=.3;G=E/(2*(1+nu));rho=8300.;df=0.
    z=[0,.076,.159,.254,.324,.406,.457,.508,.152,.203,.279,.356,.406]
    nodes=[Node(i+1,v) for i,v in enumerate(z)]
    shafts=[]
    for a,b in zip(range(1,8),range(2,9)):shafts.append(ShaftElement(2,a,b,.030,0.,rho,E,G,df))
    for a,b in zip(range(9,13),range(10,14)):shafts.append(ShaftElement(2,a,b,.060,.050,rho,E,G,df))
    disks=[Disk.inertial(2,10.5,.043,.086),Disk.inertial(7,7.,.034,.068),Disk.inertial(10,7.,.021,.042),Disk.inertial(12,3.5,.013,.026)]
    bearings=[Bearing(3,1,(26e6,52e6,20.,20.)),Bearing(3,8,(18e6,36e6,20.,20.)),Bearing(3,9,(18e6,36e6,20.,20.)),Bearing(20,6,(13,9e6,9e6,20.,20.))]
    rotors=[RotorDefinition(1,8,1.),RotorDefinition(9,13,1.5)]
    force=[Force(1,(2 if case==1 else 10,1e-4,0.))]
    return RotorModel(nodes,shafts,disks,bearings,force,rotors=rotors)

def main(case=1,smoke=False,outdir='example_06_06_01_out'):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);m=build(case)
    rpm=np.arange(0,15000+(1000 if smoke else 100),1000 if smoke else 100,dtype=float);sp=rpm_to_rad_s(rpm)
    eig=np.column_stack([run_coaxial_modal(m,w).eigenvalues for w in sp]);np.savez(out/'campbell_data.npz',rpm=rpm,eigenvalues=eig)
    rrpm=np.arange(10,15000+(500 if smoke else 10),500 if smoke else 10,dtype=float);rsp=run_coaxial_frequency_response(m,rpm_to_rad_s(rrpm)).response
    output=[2,10,12,7];amps=[]
    for n in output:
        _,amp=whirl(rsp[4*n-4,:],rsp[4*n-3,:]);amps.append(amp)
    np.savetxt(out/'response_amplitude.csv',np.column_stack([rrpm,*amps]),delimiter=',')
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,ax=plt.subplots()
    for row in range(0,min(16,eig.shape[0]),2):ax.plot(rpm,np.abs(eig[row,:].imag)/(2*np.pi))
    ax.plot(rpm,rpm/60,'--');ax.plot(rpm,1.5*rpm/60,'-.');ax.set_xlabel('Low speed rotor (rev/min)');ax.set_ylabel('Natural frequency (Hz)');ax.grid(True);fig.savefig(out/'campbell.png',dpi=140);plt.close(fig)
    fig,ax=plt.subplots()
    for amp,label in zip(amps,['Disk 1','Disk 2','Disk 3','Disk 4']):ax.semilogy(rrpm,amp,label=label)
    ax.set_xlabel('Low speed rotor (rev/min)');ax.set_ylabel('Response (m)');ax.grid(True);ax.legend();fig.savefig(out/'response.png',dpi=140);plt.close(fig)
    print(f'Example_06_06_01 case={case} completed: modal_points={len(rpm)} response_points={len(rrpm)}')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case',type=int,choices=[1,2],default=1);p.add_argument('--smoke',action='store_true');p.add_argument('--outdir',default='example_06_06_01_out');a=p.parse_args();main(a.case,a.smoke,a.outdir)
