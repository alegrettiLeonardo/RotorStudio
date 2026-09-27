import numpy as np
import pytest
from cases import case,ROOT,NAMES
from drm_core import AnalysisService,AnalysisCase,RotorProject,save_project,load_project
from drm_core.solver.backend import FortranBackend
from drm_core.solver.general_frf_backend import matrices
from drm_core.solver.ffi import configure_general_frf,SolverLibraryError

@pytest.mark.parametrize('name',NAMES)
def test_full_complex_parity_and_residual(name,tmp_path):
    m,s=case(name);params=dict(frequency_rad_s=s['frequencies'],speed=s['speed'],free_free=s['free_free'])
    c=AnalysisCase('general_frf',params,name);service=AnalysisService();e=service.execute(m,c);v=e.result
    with np.load(ROOT/f'validation/ross_parity/frf/{name}.npz') as r:
        for key,atol in [('H_disp',1e-13),('H_vel',1e-10),('H_acc',1e-7)]:
            a=getattr(v,key)
            for part in ('real','imag'):np.testing.assert_allclose(getattr(a,part),getattr(r[key],part),rtol=1e-9,atol=atol)
        for i,(w,omega) in enumerate(zip(v.frequency_rad_s,v.rotor_speed_rad_s)):
            native=matrices(FortranBackend(),m,w,omega)
            for key,a in native.items():np.testing.assert_allclose(a,r[key][:,:,i],rtol=2e-12,atol=1e-7 if key in ('D','K','Kb') else 1e-11)
            D=native['D'];H=v.H_disp[:,:,i];I=np.eye(len(D))
            residual=np.linalg.norm(D@H-I,np.inf)/(np.linalg.norm(D,np.inf)*np.linalg.norm(H,np.inf)+1)
            assert residual<1e-12 and v.residual[i]<1e-12
            np.testing.assert_allclose(v.H_vel[:,:,i],1j*w*H,rtol=1e-14,atol=1e-16)
            np.testing.assert_allclose(v.H_acc[:,:,i],-w*w*H,rtol=1e-14,atol=1e-16)
    p=RotorProject(name,m,[c]);save_project(p,tmp_path/'frf.rds');del p
    p=load_project(tmp_path/'frf.rds');again=service.execute(p,p.analyses[0])
    for key in ('H_disp','H_vel','H_acc'):np.testing.assert_array_equal(getattr(v,key),getattr(again.result,key))
    assert e.analysis_hash==again.analysis_hash

def test_native_symbol_required():
    with pytest.raises(SolverLibraryError,match='rd_frf_general_v1'):configure_general_frf(object())

@pytest.mark.parametrize('frequencies',[[],[float('nan')],[-1.],np.zeros(10001),np.zeros((2,2))])
def test_invalid_frequency(frequencies):
    m,_=case('fixed_speed')
    with pytest.raises(ValueError):AnalysisService().execute(m,AnalysisCase('general_frf',dict(frequency_rad_s=frequencies)))

def test_no_support_zero_frequency_fail_closed():
    m,_=case('fixed_speed');m.advanced_bearings=[]
    with pytest.raises(SolverLibraryError,match='status=30'):AnalysisService().execute(m,AnalysisCase('general_frf',dict(frequency_rad_s=[0.])))

def test_policy_modes_axes():
    m,s=case('map_2d');backend=FortranBackend()
    a=matrices(backend,m,117.,183.);b=matrices(backend,m,183.,117.)
    assert not np.allclose(a['Kb'],b['Kb'],rtol=1e-6)
    svc=AnalysisService();params=dict(frequency_rad_s=[43.,117.,650.],speed=183.)
    normal=svc.execute(m,AnalysisCase('general_frf',params)).result
    modes=svc.execute(m,AnalysisCase('general_frf',dict(params,modes=[0]))).result
    np.testing.assert_array_equal(normal.H_disp,modes.H_disp)
    assert normal.metadata['bearing_evaluation'][-1][0]['status']=='extrapolated'
    assert normal.metadata['bearing_evaluation'][0][0]['status']=='interpolated'
    free=svc.execute(m,AnalysisCase('general_frf',dict(params,free_free=True))).result
    zero=svc.execute(m,AnalysisCase('general_frf',dict(params,speed=0.))).result
    np.testing.assert_array_equal(free.H_disp,zero.H_disp)
    assert not np.allclose(free.H_disp,normal.H_disp,rtol=1e-6,atol=1e-15)

@pytest.mark.parametrize('kind',['memory','nonfinite_geometry','preload','physical_bearing','rigid','linked'])
def test_scope_and_memory_fail_closed(kind):
    from dataclasses import replace
    from drm_core.domain.model import Bearing
    m,_=case('fixed_speed');freq=[43.]
    if kind=='memory':
        from drm_core.domain.model import Node
        m.nodes=[Node(i+1,i*.1) for i in range(128)];freq=np.zeros(10000)
    elif kind=='nonfinite_geometry':m.shafts[0]=replace(m.shafts[0],outer_diameter_m=float('inf'))
    elif kind=='preload':m.shafts[0]=replace(m.shafts[0],axial_force_n=1.)
    elif kind=='physical_bearing':m.advanced_bearings=[object()]
    elif kind=='rigid':m.bearings=[Bearing(1,1)]
    elif kind=='linked':m.bearings=[Bearing(20,1,(4,1e6,1e6,0.,0.))]
    with pytest.raises((ValueError,SolverLibraryError)):AnalysisService().execute(m,AnalysisCase('general_frf',dict(frequency_rad_s=freq)))

def test_constant_legacy_paths_match_coefficient_tables():
    from drm_core.domain.model import Bearing
    m,s=case('cross_coupled');legacy=case('cross_coupled')[0];legacy.advanced_bearings=[]
    for b in m.advanced_bearings:legacy.bearings.append(Bearing(5,b.node,(b.kxx,b.kxy,b.kyx,b.kyy,b.cxx,b.cxy,b.cyx,b.cyy)))
    c=AnalysisCase('general_frf',dict(frequency_rad_s=[43.,117.],speed=183.))
    np.testing.assert_array_equal(AnalysisService().execute(m,c).result.H_disp,AnalysisService().execute(legacy,c).result.H_disp)

def test_near_resonance_using_frozen_primitive_matrices():
    from scipy.linalg import eigh
    m,_=case('synchronous')
    with np.load(ROOT/'validation/ross_parity/frf/synchronous.npz') as r:
        M,C,G,K=[r[k][:,:,0] for k in ['M','C','G','K']]
        natural=float(np.sqrt(eigh(K,M,eigvals_only=True)[0]))
        frequencies=natural*np.array([.999,1.,1.001])
        result=AnalysisService().execute(m,AnalysisCase('general_frf',dict(frequency_rad_s=frequencies,speed=183.))).result
        for i,w in enumerate(frequencies):
            D=K-w*w*M+1j*w*(C+183.*G)
            reference=np.linalg.solve(D,np.eye(len(D))) # independent validation only
            np.testing.assert_allclose(result.H_disp[:,:,i],reference,rtol=1e-9,atol=1e-13)
            assert result.residual[i]<1e-12

@pytest.mark.parametrize('supports',[0,1])
def test_rigid_body_numerical_singularity(supports):
    m,_=case('fixed_speed');m.advanced_bearings=m.advanced_bearings[:supports]
    with pytest.raises(SolverLibraryError,match='status=30'):
        AnalysisService().execute(m,AnalysisCase('general_frf',dict(frequency_rad_s=[0.])))
