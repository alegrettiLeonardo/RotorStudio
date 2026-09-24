from pathlib import Path
import numpy as np
import pytest
from drm_core import RotorModel,Node,ShaftElement,Bearing,Seal,RotorProject,AnalysisCase,analysis_hash,save_project,load_project,fft_scale,plot_root_locus,export_bundle
from drm_core.validation.contracts import bearing_kc_matrices,validate_bearing_contract
def demo():
    return RotorModel([Node(1,0),Node(2,.25)],[ShaftElement(2,1,2,.05,0,7810,211e9,81.2e9)],[],[Bearing(3,1,(1e6,1e6,100,100)),Bearing(3,2,(1e6,1e6,100,100))])
def test_project_roundtrip_and_hash(tmp_path):
    m=demo();c=AnalysisCase("modal",{"speed_rad_s":100.0},"m100",{"precision":"double"});p=RotorProject("demo",m,[c])
    assert analysis_hash(m,c,{"build":"Release"})==analysis_hash(m,c,{"build":"Release"})
    q=load_project(save_project(p,tmp_path/"p.json"));assert q.model.model_hash()==m.model_hash();assert q.analyses[0].canonical_dict()==c.canonical_dict()
def test_seal_and_kc_contract():
    b=Seal(1,1e5,.05,.02,1e-4,5,.01).as_bearing();validate_bearing_contract(b);assert b.bearing_type==8
    K,C=bearing_kc_matrices(Bearing(5,1,(10,2,3,20,1,.2,.3,2)));assert np.allclose(K[:2,:2],[[10,2],[3,20]]) and np.allclose(C[:2,:2],[[1,.2],[.3,2]])
def test_fft_v2_scaling_and_exports(tmp_path):
    t=np.linspace(0,1,101);r=np.sin(2*np.pi*5*t)[None,:];o=fft_scale(r,t);assert np.allclose(o.spectrum,(2/101)*np.fft.fft(r,axis=1))
    sp=np.array([0.,10.,20.]);ev=np.array([[-1+5j,-1+6j,-1+7j],[-1-5j,-1-6j,-1-7j]]);fig=plot_root_locus(sp,ev).figure
    m=export_bundle(tmp_path,{"root":fig},{"speed":sp},{"scope":"test"});assert all((tmp_path/f"root.{x}").is_file() for x in ("png","svg","pdf"));assert (tmp_path/"data.npz").is_file() and (tmp_path/"data.csv").is_file()
