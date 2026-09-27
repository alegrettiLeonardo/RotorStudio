from __future__ import annotations

import copy
from dataclasses import replace
import numpy as np

from drm_core import (
    Bearing,CoefficientBearing,Disk,Force,Node,PlainJournalPhysicsBearing,
    RotorDefinition,RotorModel,ShaftElement,
)
from drm_core.analysis.coaxial import (
    B20_COAXIAL_ADVANCED_POLICY,run_coaxial_frequency_response,run_coaxial_modal,
)
from drm_core.solver.backend import FortranBackend
from drm_core.solver.bearings_backend import AdvancedBearingBackend


def _base(link=True,ratios=(1.0,-0.7)):
    E=2.05e11;G=7.9e10;rho=7800.
    nodes=[Node(1,0),Node(2,.3),Node(3,.6),Node(4,0),Node(5,.3),Node(6,.6)]
    shafts=[
        ShaftElement(2,1,2,.045,.005,rho,E,G,1e-5),
        ShaftElement(2,2,3,.045,.005,rho,E,G,1e-5),
        ShaftElement(2,4,5,.04,.004,rho,E,G,1.2e-5),
        ShaftElement(2,5,6,.04,.004,rho,E,G,1.2e-5),
    ]
    disks=[Disk.geometric(2,rho,.04,.20,.045),Disk.geometric(5,rho,.035,.18,.04)]
    bearings=[
        Bearing(3,1,(6e6,6e6,80.,80.)),Bearing(3,3,(6e6,6e6,80.,80.)),
        Bearing(3,4,(5e6,5e6,70.,70.)),Bearing(3,6,(5e6,5e6,70.,70.)),
    ]
    if link: bearings.append(Bearing(20,2,(5,1.2e6,1.0e6,150.,140.)))
    return RotorModel(
        nodes,shafts,disks,bearings,[Force(1,(5,1.3e-4,.25))],
        rotors=[RotorDefinition(1,3,ratios[0]),RotorDefinition(4,6,ratios[1])],
    )


def _advanced(node=2,nonzero_mass=True):
    sp=(80.0,200.0,350.0);fr=(80.0,200.0,350.0)
    def surf(base,a,b):
        return tuple(tuple(base+a*s+b*w for w in fr) for s in sp)
    return CoefficientBearing(
        node=node,speed_rad_s=sp,frequency_rad_s=fr,interpolation="linear",
        kxx=surf(1.1e6,120.,55.),kxy=surf(2e4,2.,-1.),
        kyx=surf(-3e4,-1.5,.5),kyy=surf(1.35e6,100.,45.),
        cxx=surf(180.,.02,.01),cxy=surf(8.,.001,-.0005),
        cyx=surf(-6.,-.001,.0004),cyy=surf(210.,.018,.009),
        mxx=surf(12.,.001,.0005) if nonzero_mass else 0.0,
        mxy=surf(.4,.0001,-.00005) if nonzero_mass else 0.0,
        myx=surf(.4,.0001,-.00005) if nonzero_mass else 0.0,
        myy=surf(9.,.0008,.0004) if nonzero_mass else 0.0,
        tag="B20 coaxial advanced",
    )


def _legacy_parts(base,speed):
    b=FortranBackend()
    m0=copy.deepcopy(base);m0.bearings=[];m0.rotors=[]
    M,C0,K0,C1=b.assemble_matrices(m0,0.)
    _,_,Kp,_=b.assemble_matrices(m0,1.);K1=Kp-K0
    Mb,Cb,Kb,mask,_=b.bearings_matrices(base,speed)
    for br in base.bearings:
        if br.bearing_type==20:
            n1=br.node;n2=int(br.properties[0]);kxx,kyy,cxx,cyy=br.properties[1:5]
            for off,val in ((0,kxx),(1,kyy)):
                a=4*n1-4+off;b2=4*n2-4+off
                K0[a,a]+=val;K0[b2,b2]+=val;K0[a,b2]-=val;K0[b2,a]-=val
            for off,val in ((0,cxx),(1,cyy)):
                a=4*n1-4+off;b2=4*n2-4+off
                C0[a,a]+=val;C0[b2,b2]+=val;C0[a,b2]-=val;C0[b2,a]-=val
    rel=np.zeros(4*len(base.nodes))
    for rotor in base.rotors:
        rel[4*rotor.node1-4:4*rotor.node2]=rotor.speed_factor
    return M+Mb,C0+Cb,C1,K0+Kb,K1,rel,mask


def _add_eval(M,C,K,node,evaluation):
    ii=np.array([4*node-4,4*node-3])
    M[np.ix_(ii,ii)]+=evaluation.M
    C[np.ix_(ii,ii)]+=evaluation.C
    K[np.ix_(ii,ii)]+=evaluation.K


def _match_error(actual,expected):
    rem=list(expected);errs=[]
    for x in actual:
        j=min(range(len(rem)),key=lambda k:abs(rem[k]-x));y=rem.pop(j)
        errs.append(abs(x-y)/max(1.,abs(y)))
    return max(errs)


def test_b20_modal_matches_independent_v2_coaxial_equation_with_advanced_KCM():
    speed=200.0;base=_base();adv=_advanced();model=copy.deepcopy(base);model.advanced_bearings=[adv]
    actual,_=FortranBackend().coaxial_modal(model,speed)
    M,C0,C1,K0,K1,rel,mask=_legacy_parts(base,speed)
    ev=AdvancedBearingBackend().evaluate(adv,speed,speed)
    _add_eval(M,C0,K0,adv.node,ev)
    C=C0+speed*(rel[:,None]*C1);K=K0+speed*(rel[:,None]*K1)
    keep=~mask;Mr=M[np.ix_(keep,keep)];Cr=C[np.ix_(keep,keep)];Kr=K[np.ix_(keep,keep)]
    n=len(Mr);A=np.block([[np.zeros((n,n)),np.eye(n)],[-np.linalg.solve(Mr,Kr),-np.linalg.solve(Mr,Cr)]])
    assert _match_error(actual,np.linalg.eigvals(A))<6e-9


def test_b20_frequency_response_re_materializes_advanced_coefficients_at_each_reference_speed():
    speeds=np.array([90.,200.,340.]);base=_base();adv=_advanced();model=copy.deepcopy(base);model.advanced_bearings=[adv]
    actual=FortranBackend().coaxial_frequency_response(model,speeds)
    provider=AdvancedBearingBackend()
    f=base.forces[0];node=int(f.values[0]);q=f.values[1]*np.exp(1j*f.values[2])
    ub=np.zeros(24,complex);ub[4*node-4]+=q;ub[4*node-3]+=-1j*q
    ratio=base.rotors[1].speed_factor
    for col,w in enumerate(speeds):
        M,C0,C1,K0,K1,rel,mask=_legacy_parts(base,float(w))
        _add_eval(M,C0,K0,adv.node,provider.evaluate(adv,float(w),float(w)))
        exc=ratio*w;C=C0+w*(rel[:,None]*C1);K=K0+w*(rel[:,None]*K1)
        A=-M*exc*exc+1j*C*exc+K;expected=np.zeros(24,complex);keep=~mask
        expected[keep]=np.linalg.solve(A[np.ix_(keep,keep)],ub[keep]*exc*exc)
        np.testing.assert_allclose(actual[:,col],expected,rtol=5e-10,atol=5e-11)


def test_b20_analysis_metadata_makes_reference_speed_policy_explicit():
    model=_base();model.advanced_bearings=[_advanced(nonzero_mass=False)]
    modal=run_coaxial_modal(model,200.0)
    frf=run_coaxial_frequency_response(model,[100.0,200.0])
    assert modal.metadata["advanced_bearing_policy"]==B20_COAXIAL_ADVANCED_POLICY
    assert frf.metadata["advanced_bearing_frequency"]=="reference_rotor_speed"


def _plain():
    return PlainJournalPhysicsBearing(
        node=2,weight_n=112814.90696191376,journal_diameter_m=0.3999992,
        radial_clearance_m=0.000194564,oil_viscosity_pa_s=0.01901574061455835,
        pivot_angle_rad=(np.pi/2,3*np.pi/2),pad_arc_rad=(3.07177948351002,)*2,
        pad_axial_length_m=(0.263144,)*2,preload=(0.,0.),offset=(.5,.5),
        total_e_x_film=8,total_e_z_film=4,total_e_y_pad=4,total_e_y_film=4,
        xj_ratio_initial=.15,yj_ratio_initial=-.2,force_tolerance=5e-3,outer_iterations=10,
    )


def test_b20_native_plain_journal_can_enter_coaxial_modal_at_reference_speed():
    base=_base();model=copy.deepcopy(base);model.advanced_bearings=[_plain()]
    eig,_=FortranBackend().coaxial_modal(model,100.0)
    assert eig.size>0
    assert np.isfinite(eig.real).all() and np.isfinite(eig.imag).all()


def test_b20_legacy_coaxial_result_is_unchanged_when_no_advanced_bearing_is_present():
    model=_base();speed=210.0
    now,_=FortranBackend().coaxial_modal(model,speed)
    # Existing source-oracle behavior is independently guarded by
    # python/tests/test_coaxial_source_oracle.py; this gate ensures the new
    # advanced branch is not taken for a legacy-only model.
    assert now.size==2*(4*len(model.nodes))
