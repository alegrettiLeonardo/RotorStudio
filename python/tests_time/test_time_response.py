from dataclasses import replace
import numpy as np
import pytest
from drm_core import run_general_time_response
from drm_core.solver.backend import FortranBackend
from drm_core.solver.ffi import SolverLibraryError
from drm_core.solver.general_time_backend import configure_time
from time_cases import case,NAMES,ROOT
from matrix_probe import matrices

# Frozen from initial evidence (max q error 2.31e-17); translational/rotational units differ.
RTOL=1e-10
ATOL=np.array([1e-12,1e-12,1e-11,1e-11])
def run(m,s,**kw):
    p={k:s[k] for k in ('time_s','force_real','speed','weight','gamma','beta','tol')};p.update(kw)
    return run_general_time_response(m,**p)

@pytest.mark.parametrize('name',NAMES)
def test_ross_time_and_physics(name):
    m,s=case(name);r=run(m,s);ma=matrices(FortranBackend(),m,s)
    with np.load(ROOT/f'validation/ross_parity/time_response/{name}.npz') as g:
        assert np.all(abs(r.displacement-g['q'])<=RTOL*abs(g['q'])+np.tile(ATOL,len(m.nodes))[:,None])
        np.testing.assert_allclose(r.force,g['F'],rtol=2e-12,atol=1e-11)
        np.testing.assert_allclose(r.angular_acceleration_rad_s2,g['alpha'],rtol=2e-12,atol=1e-8)
    for a in (r.displacement,r.velocity,r.acceleration):np.testing.assert_array_equal(a[:,0],0)
    dt=np.diff(r.time_s);q=r.displacement;v=r.velocity;a=r.acceleration;gamma=s['gamma'];beta=s['beta']
    np.testing.assert_allclose(q[:,1:],q[:,:-1]+dt*v[:,:-1]+dt**2*((.5-beta)*a[:,:-1]+beta*a[:,1:]),rtol=1e-12,atol=1e-13)
    np.testing.assert_allclose(v[:,1:],v[:,:-1]+dt*((1-gamma)*a[:,:-1]+gamma*a[:,1:]),rtol=1e-12,atol=1e-12)
    for i in range(1,len(r.time_s)):
        M,C,K=ma['M'][:,:,i],ma['Ceff'][:,:,i],ma['Keff'][:,:,i]
        residual=M@a[:,i]+C@v[:,i]+K@q[:,i]-r.force[:,i]
        assert np.linalg.norm(residual)<s['tol']
        den=np.linalg.norm(M,np.inf)*max(abs(a[:,i]))+np.linalg.norm(C,np.inf)*max(abs(v[:,i]))+np.linalg.norm(K,np.inf)*max(abs(q[:,i]))+max(abs(r.force[:,i]))
        assert max(abs(residual))/(den or 1)<1e-12
    assert np.all(r.absolute_residual[1:]<s['tol']) and np.max(r.iterations)<=50
    if np.any(r.force[:,0]):assert r.residual[0]==1

@pytest.mark.parametrize('variable',[False,True])
def test_dt_convergence(variable):
    m,s=case('harmonic');out=[]
    for nt in (321,641,1281):
        t=np.linspace(0,.04,nt);F=np.zeros((16,nt));F[4]=137*np.sin(317*t)
        out.append(run(m,s,time_s=t,force_real=F,speed=183+900*t/.04 if variable else 183.).displacement)
    a,b,c=out[0],out[1][:,::2],out[2][:,::4]
    assert np.linalg.norm(a-b)/np.linalg.norm(b-c)>2.8
    # Peak and RMS are recorded along with sampled histories; require refinement improvement.
    assert abs(np.max(abs(a))-np.max(abs(c)))>abs(np.max(abs(b))-np.max(abs(c)))
    assert abs(np.sqrt(np.mean(a*a))-np.sqrt(np.mean(c*c)))>abs(np.sqrt(np.mean(b*b))-np.sqrt(np.mean(c*c)))

@pytest.mark.parametrize('key,value',[('time_s',[0,0]),('time_s',[1,0]),('time_s',[0,float('nan')]),('speed',[0,1]),('force_real',[[1,2]]),('gamma',0),('beta',float('nan')),('tol',-1),('weight',1)])
def test_invalid_inputs(key,value):
    m,s=case('harmonic')
    with pytest.raises(ValueError):run(m,s,**{key:value})

def test_mass_policy_and_nonconvergence():
    m,s=case('speed_axis');bs=list(m.advanced_bearings);bs[0]=replace(bs[0],mxx=[0,.1,.2,.3])
    with pytest.raises(ValueError,match='constant bearing mass'):run(replace(m,advanced_bearings=bs),s)
    m,s=case('harmonic')
    with pytest.raises(SolverLibraryError,match='status=40.*iterations=50'):run(m,s,tol=1e-30)
    with pytest.raises(SolverLibraryError,match='No fallback'):configure_time(object())

def test_signed_speed_zero_and_repeat():
    m,s=case('harmonic');r=run(m,s,speed=-183.);rr=run(m,s,speed=-183.)
    np.testing.assert_array_equal(r.displacement,rr.displacement)
    z=run(m,s,force_real=np.zeros((16,81)))
    for x in (z.displacement,z.velocity,z.acceleration):assert not np.any(x)

def test_force_scaling_and_gyro_ksdt_sentinels():
    m,s=case('linear_ramp');r=run(m,s);scaled=run(m,s,force_real=2*np.array(s['force_real']))
    np.testing.assert_allclose(scaled.displacement,2*r.displacement,rtol=1e-10,atol=1e-12)
    ma=matrices(FortranBackend(),m,s)
    # Missing/wrong-sign/double gyroscopic and missing Ksdt terms cannot pass equation residual.
    for factor in (0.,-1.,2.):
        e=[]
        for i in range(1,len(r.time_s)):
            C=ma['C'][:,:,i]+factor*r.rotor_speed_rad_s[i]*ma['G'][:,:,i]
            e.append(np.linalg.norm(ma['M'][:,:,i]@r.acceleration[:,i]+C@r.velocity[:,i]+ma['Keff'][:,:,i]@r.displacement[:,i]-r.force[:,i]))
        assert max(e)>1e-2
    e=[np.linalg.norm(ma['M'][:,:,i]@r.acceleration[:,i]+ma['Ceff'][:,:,i]@r.velocity[:,i]+ma['K'][:,:,i]@r.displacement[:,i]-r.force[:,i]) for i in range(1,len(r.time_s))]
    assert max(e)>1e-2

def test_native_abi_shape_budget_and_mass_guards():
    import ctypes as ct
    from drm_core.solver.general_time_backend import prepare_time
    m,s=case('harmonic');b=FortranBackend();fn=configure_time(b.lib)
    t,omega,F,var,prep=prepare_time(b,m,s['time_s'],s['force_real'],s['speed'],False,.5,.25,1e-6)
    z,sh,di,nodes,coeff,*_=prep;p=b._ptr;n,nt=F.shape
    outputs=[np.zeros_like(F,order='F') for _ in range(3)];alpha=np.zeros(nt);Fe=np.zeros_like(F,order='F');it=np.zeros(nt,dtype=np.int32);res=np.zeros(nt);ar=np.zeros(nt);cond=np.zeros(nt);failed=ct.c_int()
    def call(fd=n,ft=nt,count=nt):
        return fn(len(z),p(z),sh.shape[1],p(sh),di.shape[1],p(di),len(nodes),b._iptr(nodes),count,p(t),p(omega),var,p(coeff),fd,ft,p(F),0,.5,.25,1e-6,*[p(x) for x in outputs],p(alpha),p(Fe),b._iptr(it),p(res),p(ar),p(cond),ct.byref(failed))
    assert call(fd=n-1)==10 and call(ft=nt-1)==10 and call(ft=10001,count=10001)==10
    coeff[0,0,-1]=.1
    assert call()==10

def test_validation_driver_matches_public_abi():
    from probe_time import probe
    m,s=case('nonuniform');r=run(m,s)
    for actual,expected in zip(probe(m,s),(r.displacement,r.velocity,r.acceleration)):
        np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-12)

def test_geometric_disk_matches_inertial_time_response():
    from drm_core import Disk
    m,s=case('linear_ramp');rho,L,od,idd=7810.,.037,.21,.017
    mass=np.pi*rho*L*(od**2-idd**2)/4;Ip=mass*(od**2+idd**2)/8;Id=mass*((od**2+idd**2)/16+L**2/12)
    geom=replace(m,disks=[Disk.geometric(2,rho,L,od,idd)]);inertial=replace(m,disks=[Disk.inertial(2,mass,Id,Ip)])
    g=matrices(FortranBackend(),geom,s);i=matrices(FortranBackend(),inertial,s)
    for k in ('M','G','Ksdt','Kdisk','Ceff','Keff'):np.testing.assert_allclose(g[k],i[k],rtol=2e-12,atol=1e-11)
    np.testing.assert_allclose(run(geom,s).displacement,run(inertial,s).displacement,rtol=1e-10,atol=1e-12)
