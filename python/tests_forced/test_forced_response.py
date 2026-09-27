import numpy as np
import pytest
from forced_cases import case,NAMES,ROOT
from drm_core import AnalysisService,AnalysisCase,RotorProject,save_project,load_project,run_general_frf,run_forced_response
from drm_core.solver.backend import FortranBackend
from drm_core.solver.general_frf_backend import matrices
from drm_core.solver.forced_response_backend import configure_forced_response
from drm_core.solver.ffi import SolverLibraryError

# SI absolute bounds per translation/rotation, fixed after initial evidence.
ATOL={'q':(1e-13,1e-12),'v':(1e-11,1e-10),'a':(1e-8,1e-7)}
def parity(actual,expected,key):
    atol=np.array([ATOL[key][int(i%4>=2)] for i in range(len(actual))])[:,None]
    for part in ('real','imag'):
        a=getattr(actual,part);b=getattr(expected,part)
        assert np.all(abs(a-b)<=atol+1e-10*abs(b)),(key,part,np.max(abs(a-b)))

def run(m,s,F=None,**kw):
    if F is None:F=np.array(s['force_real'])+1j*np.array(s['force_imag'])
    return run_forced_response(m,s['frequencies'],F.real,F.imag,s['speed'],**kw)

@pytest.mark.parametrize('name',NAMES)
def test_ross_a2_direct_physics_persistence(name,tmp_path):
    m,s=case(name);params={k:s[k] for k in ('force_real','force_imag','speed')};params['frequency_rad_s']=s['frequencies']
    c=AnalysisCase('forced_response',params,name);svc=AnalysisService();e=svc.execute(m,c);r=e.result
    h=run_general_frf(m,s['frequencies'],s['speed']);backend=FortranBackend()
    with np.load(ROOT/f'validation/ross_parity/forced/{name}.npz') as g:
        for attr,key,hattr in [('displacement','q','H_disp'),('velocity','v','H_vel'),('acceleration','a','H_acc')]:
            value=getattr(r,attr);parity(value,g[key],key)
            parity(value,np.einsum('ijk,jk->ik',getattr(h,hattr),r.force_complex),key)
        for i,(w,omega) in enumerate(zip(r.frequency_rad_s,r.rotor_speed_rad_s)):
            D=matrices(backend,m,w,omega)['D'];q=r.displacement[:,i];F=r.force_complex[:,i]
            denominator=np.linalg.norm(D,np.inf)*np.linalg.norm(q,np.inf)+np.linalg.norm(F,np.inf)
            residual=np.linalg.norm(D@q-F,np.inf)/denominator
            assert residual<1e-12 and r.residual[i]<1e-12
            assert 1<=r.condition_estimate[i]<1/(len(D)*np.finfo(float).eps)
        np.testing.assert_array_equal(r.velocity,1j*r.frequency_rad_s*r.displacement)
        np.testing.assert_array_equal(r.acceleration,-r.frequency_rad_s**2*r.displacement)
    p=RotorProject(name,m,[c]);save_project(p,tmp_path/'forced.rds');del p
    p=load_project(tmp_path/'forced.rds');again=svc.execute(p,p.analyses[0])
    for attr in ('force_complex','displacement','velocity','acceleration','residual','condition_estimate'):np.testing.assert_array_equal(getattr(r,attr),getattr(again.result,attr))
    assert e.analysis_hash==again.analysis_hash

@pytest.mark.parametrize('name',['single_x','fixed_speed','map_2d','near_resonance'])
def test_linearity_scale_phase_zero(name):
    m,s=case(name);F=np.array(s['force_real'])+1j*np.array(s['force_imag']);F2=np.roll(F,3,axis=0)*(.31-.27j)
    first=run(m,s,F);second=run(m,s,F2);total=run(m,s,F+F2)
    for attr,key in [('displacement','q'),('velocity','v'),('acceleration','a')]:parity(getattr(total,attr),getattr(first,attr)+getattr(second,attr),key)
    for scalar in [-.7+1.3j,np.exp(.731j)]:
        scaled=run(m,s,scalar*F)
        for attr,key in [('displacement','q'),('velocity','v'),('acceleration','a')]:parity(getattr(scaled,attr),scalar*getattr(first,attr),key)
    zero=run(m,s,np.zeros_like(F))
    for attr in ['displacement','velocity','acceleration','residual']:assert not np.any(getattr(zero,attr))

@pytest.mark.parametrize('invalid',['missing','complex_split','shape','nan','inf','frequency','empty','negative','policy','physical','memory'])
def test_fail_closed(invalid):
    m,s=case('fixed_speed');p=dict(frequency_rad_s=s['frequencies'],force_real=s['force_real'],force_imag=s['force_imag'],speed=s['speed'])
    if invalid=='missing':p['force_real']=None
    if invalid=='complex_split':p['force_real']=np.asarray(p['force_real'],complex)+1j
    if invalid=='shape':p['force_real']=[[1.]]
    if invalid in ('nan','inf'):p['force_imag'][0][0]=float(invalid)
    if invalid=='frequency':p['frequency_rad_s']=None
    if invalid=='empty':p['frequency_rad_s']=[]
    if invalid=='negative':p['frequency_rad_s'][0]=-1
    if invalid=='policy':p['free_free']=True
    if invalid=='physical':m.advanced_bearings=[object()]
    if invalid=='memory':
        from drm_core import Node
        m.nodes=[Node(i+1,i*.1) for i in range(128)];p.update(frequency_rad_s=np.arange(10000.),force_real=np.zeros((512,10000)),force_imag=np.zeros((512,10000)))
    with pytest.raises((ValueError,TypeError)):run_forced_response(m,**p)

@pytest.mark.parametrize('supports',[0,1])
@pytest.mark.parametrize('zero',[False,True])
def test_singular_even_zero_force(supports,zero):
    m,s=case('fixed_speed');m.advanced_bearings=m.advanced_bearings[:supports]
    with pytest.raises(SolverLibraryError,match='status=30'):run(m,s,np.zeros_like(s['force_real']) if zero else None)

def test_no_fallback_modes_and_axes():
    with pytest.raises(SolverLibraryError,match='rd_forced_response_v1'):configure_forced_response(object())
    m,s=case('map_2d');np.testing.assert_array_equal(run(m,s).displacement,run(m,s,modes=[0]).displacement)
    normal=run(m,s);swapped=dict(s);swapped['speed']=s['frequencies'][2];swapped['frequencies']=[s['speed']]*len(s['frequencies'])
    assert not np.allclose(normal.displacement,run(m,swapped).displacement,rtol=1e-6,atol=1e-15)
    F=normal.force_complex;assert np.linalg.matrix_rank(F)>1
