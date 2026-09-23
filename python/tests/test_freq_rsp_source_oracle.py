import os, numpy as np, copy
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,Force,BendPoint
from drm_core.solver.backend import FortranBackend

def backend(): return FortranBackend(os.environ['DRMROTOR_LIB'])
def base_model():
    E=2.05e11;G=7.9e10;rho=7850.
    return RotorModel(
        nodes=[Node(1,0),Node(2,.25),Node(3,.55)],
        shafts=[ShaftElement(2,1,2,.05,.01,rho,E,G,1.5e-5),ShaftElement(2,2,3,.045,.008,rho,E,G,1.5e-5)],
        disks=[Disk.geometric(2,rho,.04,.22,.05)],
        bearings=[Bearing(3,1,(8e6,9e6,120.,140.)),Bearing(3,3,(7e6,7.5e6,110.,130.))])

def _expected(model,w):
    b=backend();M,C,K,_=b.assemble_matrices(model,w)
    m0=copy.deepcopy(model);m0.bearings=[]
    _,_,K0,_=b.assemble_matrices(m0,0.)
    nd=4*len(model.nodes);ub=np.zeros(nd,complex);pzt=np.zeros(nd,complex);j=1j
    for f in model.forces:
        vals=f.values
        if f.force_type==1:
            node=int(vals[0]);mag,phase=vals[1],vals[2];q=mag*np.exp(1j*phase);ub[4*node-4]+=q;ub[4*node-3]+=-1j*q
        elif f.force_type==2:
            node=int(vals[0]);mag,phase=vals[1],vals[2];q=mag*np.exp(1j*phase);ub[4*node-2]+=1j*q;ub[4*node-1]+=q
        elif f.force_type==8:
            n1,n2=int(vals[0]),int(vals[1]);mag,phase=vals[2],vals[3];q=mag*np.exp(1j*phase)
            pzt[4*n1-2]+=1j*q;pzt[4*n1-1]+=q;pzt[4*n2-2]-=1j*q;pzt[4*n2-1]-=q
    bend=np.zeros(nd,complex)
    if any(f.force_type==3 for f in model.forces):
        masters=[];xm=[]
        for bp in model.bend:
            masters += [4*bp.node-4,4*bp.node-3]
            xm += [bp.x_m-1j*bp.y_m,bp.y_m+1j*bp.x_m]
        masters=np.array(masters);slaves=np.array([i for i in range(nd) if i not in set(masters)]);xm=np.asarray(xm,complex)
        xs=-np.linalg.solve(K0[np.ix_(slaves,slaves)],K0[np.ix_(slaves,masters)]@xm)
        xb=np.zeros(nd,complex);xb[masters]=xm;xb[slaves]=xs;bend=K0@xb
    force=bend+pzt+ub*w*w
    return np.linalg.solve(-M*w*w+1j*C*w+K,force)

def test_freq_rsp_combined_unbalance_moment_bend_and_pzt_matches_source_equation():
    m=base_model();m.forces=[Force(1,(2,2.2e-4,.37)),Force(2,(2,1.3e-5,-.21)),Force(3,()),Force(8,(1,2,8.5,.12))]
    m.bend=[BendPoint(1,2e-5,-1e-5),BendPoint(3,-1.5e-5,0.5e-5)]
    speeds=np.array([70.,150.,310.]);actual=backend().frequency_response(m,speeds)
    for j,w in enumerate(speeds):
        expected=_expected(m,w)
        assert np.allclose(actual[:,j],expected,rtol=2e-11,atol=2e-12)

def test_freq_rsp_restores_constrained_dofs_as_zero():
    m=base_model();m.bearings=[Bearing(1,1),Bearing(3,3,(7e6,7e6,100.,100.))];m.forces=[Force(1,(2,1e-4,0.))]
    r=backend().frequency_response(m,[120.])[:,0]
    assert r[0]==0 and r[1]==0
    assert np.linalg.norm(r[2:])>0

def test_freq_rsp_unbalance_is_exactly_zero_at_zero_speed_for_constant_bearings():
    m=base_model();m.forces=[Force(1,(2,1e-4,.2)),Force(2,(2,2e-5,.1))]
    r=backend().frequency_response(m,[0.])[:,0]
    assert np.allclose(r,0,atol=0)
