import os, numpy as np
from drm_core import RotorModel,Node,Bearing
from drm_core.solver.backend import FortranBackend

def backend(): return FortranBackend(os.environ['DRMROTOR_LIB'])
def model(b): return RotorModel(nodes=[Node(1,0.0)],bearings=[b])

def test_bearing_types_1_and_2_constraints():
    *_,mask1,e1=backend().bearings_matrices(model(Bearing(1,1)),100.0)
    *_,mask2,e2=backend().bearings_matrices(model(Bearing(2,1)),100.0)
    assert mask1.tolist()==[True,True,False,False]
    assert mask2.tolist()==[True,True,True,True]
    assert np.all(e1==0) and np.all(e2==0)

def test_bearing_type3_source_formula():
    b=Bearing(3,1,(11.,22.,3.,4.));M,C,K,mask,e=backend().bearings_matrices(model(b),123.)
    assert np.allclose(M,0); assert not mask.any(); assert e[0]==0
    assert np.array_equal(np.diag(K),[11,22,0,0]);assert np.array_equal(np.diag(C),[3,4,0,0])

def test_bearing_type4_source_formula():
    vals=(11.,22.,33.,44.,1.,2.,3.,4.);M,C,K,_,_=backend().bearings_matrices(model(Bearing(4,1,vals)),50.)
    assert np.allclose(M,0);assert np.array_equal(np.diag(K),vals[:4]);assert np.array_equal(np.diag(C),vals[4:])

def test_bearing_type5_source_formula_cross_coupled():
    vals=(11.,12.,21.,22.,31.,32.,41.,42.);M,C,K,_,_=backend().bearings_matrices(model(Bearing(5,1,vals)),50.)
    assert np.allclose(M,0)
    assert np.array_equal(K[:2,:2],[[11,12],[21,22]])
    assert np.array_equal(C[:2,:2],[[31,32],[41,42]])

def test_bearing_type6_source_formula_full_4x4():
    kval=np.arange(1,17,dtype=float);cval=np.arange(101,117,dtype=float)
    M,C,K,_,_=backend().bearings_matrices(model(Bearing(6,1,tuple(np.r_[kval,cval]))),75.)
    assert np.allclose(M,0)
    assert np.array_equal(K,kval.reshape(4,4))
    assert np.array_equal(C,cval.reshape(4,4))

def _short_oracle(F,D,L,c,eta,speed):
    H=(8*c*c*F/(D*speed*eta*L**3))**2
    roots=np.roots([1,-4,6-(16-np.pi**2)/H,-(4+np.pi**2/H),1])
    admiss=sorted(r.real for r in roots if abs(r.imag)<1e-9 and 0<r.real<1)
    n2=0.5 if not admiss else admiss[0];n=np.sqrt(n2)
    q1=1-n2;q2=1+n2;q3=1+2*n2;p2=np.pi**2;de=(p2*q1+16*n2)**1.5
    a=np.zeros((2,2));b=np.zeros((2,2))
    a[0,0]=4*(p2*(2-n2)+16*n2)/de;a[1,1]=4*(p2*q1*q3+32*n2*q2)/(q1*de)
    a[0,1]=np.pi*(p2*q1**2-16*n**4)/(n*np.sqrt(q1)*de);a[1,0]=-np.pi*(p2*q1*q3+32*n2*q2)/(n*np.sqrt(q1)*de)
    b[0,0]=2*np.pi*np.sqrt(q1)*(p2*q3-16*n2)/(n*de);b[1,1]=2*np.pi*(p2*q1**2+48*n2)/(n*np.sqrt(q1)*de)
    b[0,1]=-8*(p2*q3-16*n2)/de;b[1,0]=b[0,1]
    return n,(F/c)*a,(F/(c*speed))*b

def test_bearing_type7_source_quartic_and_coefficients():
    F,D,L,c,eta,speed=1200.,0.06,0.025,60e-6,0.018,320.
    ecc,K2,C2=_short_oracle(F,D,L,c,eta,speed)
    M,C,K,mask,e=backend().bearings_matrices(model(Bearing(7,1,(F,D,L,c,eta))),speed)
    assert not mask.any();assert np.allclose(M,0)
    assert abs(e[0]-ecc)<=2e-11
    assert np.allclose(K[:2,:2],K2,rtol=2e-10,atol=1e-6)
    assert np.allclose(C[:2,:2],C2,rtol=2e-10,atol=1e-6)

def test_bearing_type7_nonlinear_flag_zeroes_linear_kc_but_keeps_eccentricity():
    F,D,L,c,eta,speed=1200.,0.06,0.025,60e-6,0.018,320.
    ecc,_,_=_short_oracle(F,D,L,c,eta,speed)
    M,C,K,_,e=backend().bearings_matrices(model(Bearing(7,1,(F,D,L,c,eta,1.0))),speed)
    assert np.allclose(M,0);assert np.allclose(C,0);assert np.allclose(K,0);assert abs(e[0]-ecc)<2e-11

def test_bearing_type8_source_formula():
    P,R,L,c,V,fric,speed=2.1e5,0.04,0.08,0.00025,12.0,0.08,450.0
    T=L/V;sigma=fric*L/c;eps=np.pi*sigma*R*P/(6*fric*(1.5+2*sigma))
    mu0=9*sigma/(1.5+2*sigma);mu1=((3+2*sigma)**2*(1.5+2*sigma)-9*sigma)/(1.5+2*sigma)**2
    mu2=(19*sigma+18*sigma**2+8*sigma**3)/(1.5+2*sigma)**3
    J=np.array([[0.,-1.],[1.,0.]]);I=np.eye(2)
    Ko=eps*(mu0-mu2*T*T*speed*speed/4)*I+eps*(mu1*T*speed/2)*J
    Co=eps*mu1*T*I+eps*(mu2*T*T*speed)*J;Mo=eps*mu2*T*T*I
    M,C,K,_,e=backend().bearings_matrices(model(Bearing(8,1,(P,R,L,c,V,fric))),speed)
    assert e[0]==0;assert np.allclose(M[:2,:2],Mo,rtol=1e-13);assert np.allclose(C[:2,:2],Co,rtol=1e-13);assert np.allclose(K[:2,:2],Ko,rtol=1e-13)
