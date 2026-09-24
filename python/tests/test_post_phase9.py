import numpy as np
import matplotlib
matplotlib.use("Agg",force=True)
import matplotlib.pyplot as plt

from drm_core.post.fft import fftscale
from drm_core.post.root_locus import plot_root_locus
from drm_core.post.eigenvalue import plot_eigenvalues
from drm_core.post.orbits import orbit_xy,plot_orbits
from drm_core.post.response import plot_response,plot_frf
from drm_core.post.modes import plot_mode
from drm_core.post.exports import export_figure,export_csv,export_npz
from drm_core.domain.model import RotorModel,Node


def test_fftscale_matches_v2_scaling_and_frequency_vector():
    t=np.linspace(0,1,101);y=np.sin(2*np.pi*5*t)[None,:]
    f,hz=fftscale(y,t)
    np.testing.assert_allclose(hz,np.arange(101))
    np.testing.assert_allclose(f,(2/101)*np.fft.fft(y,axis=1))


def test_phase9_plots_and_exports_headless(tmp_path):
    speeds=np.array([0.,10.,20.])
    eig=np.array([[-1+10j,-2+11j,-3+12j],[-1-10j,-2-11j,-3-12j]])
    ax=plot_root_locus(speeds,eig); assert ax.get_title()=="Root Locus"; plt.close(ax.figure)
    a1,a2=plot_eigenvalues(speeds,eig); plt.close(a1.figure)
    mode=np.array([1+0j,1j,0,0, .5+0j,.5j,0,0],complex)
    x,y=orbit_xy(mode,1,1j); assert x.shape==y.shape and x.size==341
    ax=plot_orbits(mode,[1,2],eigenvalue=1j); plt.close(ax.figure)
    rsp=np.vstack([np.ones(3),1j*np.ones(3),np.ones(3),np.ones(3)])
    axes=plot_response(speeds,rsp,[1.1,1.2]); plt.close(axes[0].figure)
    axes=plot_frf(speeds+1,rsp,[1.1]); plt.close(axes[0].figure)
    model=RotorModel(nodes=[Node(1,0.0),Node(2,1.0)])
    ax=plot_mode(model,mode,10j); plt.close(ax.figure)
    fig=plt.figure();plt.plot([0,1],[0,1])
    written=export_figure(fig,tmp_path/"plot")
    assert set(written)=={"png","svg","pdf"} and all(p.is_file() for p in written.values())
    plt.close(fig)
    assert export_csv(tmp_path/"a.csv",[np.arange(3),np.arange(3)**2],header=["x","y"]).is_file()
    assert export_npz(tmp_path/"a.npz",x=np.arange(3)).is_file()
