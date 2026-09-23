from pathlib import Path
import numpy as np
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,run_modal
from drm_core.units import rpm_to_rad_s

def build(ne):
    E=2e11; nu=.27; G=E/(2*(1+nu));rho=7800.;L=1.2/ne
    nodes=[Node(i+1,L*i) for i in range(ne+1)]
    shafts=[ShaftElement(2,i+1,i+2,.08,.03,rho,E,G,0.) for i in range(ne)]
    return RotorModel(nodes,shafts,[Disk.geometric(1+ne//2,rho,.08,.4,.08)],[Bearing(1,1),Bearing(1,ne+1)])
def main(outdir='example_05_08_01_out'):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True); nees=[2,4,6,8,10,12,14,16,18,20,80];vals=[]
    for ne in nees:
        r=run_modal(build(ne),rpm_to_rad_s(5000)); vals.append(np.abs(r.eigenvalues[:16:2])/(2*np.pi))
    vals=np.array(vals).T;np.savetxt(out/'natural_frequencies_hz.csv',vals,delimiter=',')
    err=100*(vals[:,:-1]-vals[:,-1,None])/vals[:,-1,None]
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,ax=plt.subplots();ax.semilogy(nees[:-1],np.abs(err).T);ax.set_xlabel('Number of elements');ax.set_ylabel('Natural frequency error (%)');ax.grid(True);fig.savefig(out/'discretization_error.png',dpi=140);plt.close(fig)
    print('Example_05_08_01 completed');print('80-element first 8 frequencies Hz:', ' '.join(f'{x:.8f}' for x in vals[:,-1]))
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--outdir',default='example_05_08_01_out')
    main(ap.parse_args().outdir)
