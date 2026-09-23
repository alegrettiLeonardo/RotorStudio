import os,json,subprocess,sys
from pathlib import Path
import numpy as np
from drm_core import RotorModel,Node,ShaftElement,TaperedShaftElement,AsymmetricShaftElement
from drm_core.solver.backend import FortranBackend
from validation.equivalence.element_abi import circular,tapered,asymmetric
def b():return FortranBackend(os.environ['DRMROTOR_LIB'])
def test_element_qualification_abi_circular_matches_global_assembly():
    M,G,K,K1=circular(2,.31,.08,.02,2.1e11,8.1e10,7800.,2.5e4,1.2e3)
    m=RotorModel([Node(1,0),Node(2,.31)],[ShaftElement(2,1,2,.08,.02,7800.,2.1e11,8.1e10,0.,2.5e4,1.2e3)],[],[]);Mg,Cg,Kg,Gg=b().assemble_matrices(m,0.)
    assert np.allclose(M,Mg,rtol=0,atol=1e-12);assert np.allclose(G,Gg,rtol=0,atol=1e-12);assert np.allclose(K,Kg,rtol=2e-13,atol=1e-7)
    md=RotorModel([Node(1,0),Node(2,.31)],[ShaftElement(2,1,2,.08,.02,7800.,2.1e11,8.1e10,1.,2.5e4,1.2e3)],[],[]);_,_,K0,_=b().assemble_matrices(md,0.);_,_,Ksp,_=b().assemble_matrices(md,1.);assert np.allclose(K1,Ksp-K0,rtol=2e-12,atol=1e-6)
def test_element_qualification_abi_tapered_matches_global_assembly():
    M,G,K,K1=tapered(22,.31,.08,.071,.02,.012,2.1e11,8.1e10,7800.,2.5e4)
    m=RotorModel([Node(1,0),Node(2,.31)],[TaperedShaftElement(22,1,2,.08,.071,.02,.012,7800.,2.1e11,8.1e10,2.5e4)],[],[]);Mg,Cg,Kg,Gg=b().assemble_matrices(m,0.)
    assert np.allclose(M,Mg);assert np.allclose(G,Gg);assert np.allclose(K,Kg,rtol=2e-13,atol=1e-7);assert np.allclose(K1,0)
def test_element_qualification_abi_asymmetric_matches_rotating_assembly():
    M,C,K,K2=asymmetric(12,.31,1.25e5,1.05e5,.07,.09,11.5,.0042,0.)
    m=RotorModel([Node(1,0),Node(2,.31)],[AsymmetricShaftElement(12,1,2,1.25e5,1.05e5,.07,.09,11.5,.0042,0.,0.)],[],[]);Mg,C0,C1,K0,K1,K2g=b().asymmetric_assemble(m)
    assert np.allclose(M,Mg);assert np.allclose(C,C1);assert np.allclose(K,K0);assert np.allclose(K2,K2g);assert np.allclose(C0,0);assert np.allclose(K1,0)
def test_formal_equivalence_reports_blocked_without_authority_baseline(tmp_path):
    root=Path(__file__).resolve().parents[2];out=tmp_path/'formal.json';p=subprocess.run([sys.executable,str(root/'validation/equivalence/run_formal_equivalence.py'),'--matlab-baseline',str(tmp_path/'missing.mat'),'--output',str(out)],cwd=root,env=os.environ.copy())
    assert p.returncode==2;data=json.loads(out.read_text());assert data['overall']=='BLOCKED';assert all(v['status']=='BLOCKED' for v in data['gates'].values())
