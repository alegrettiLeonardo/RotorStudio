from __future__ import annotations

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from drm_core import (
    Bearing, CoefficientBearing, Force, Node, PlainJournalPhysicsBearing,
    RotorModel, ShaftElement, TiltingPadPhysicsBearing, generate_operating_map,
)
from drm_core.analysis.transient import run_runup
from drm_core.solver.bearings_backend import AdvancedBearingBackend
from drm_core.solver.ffi import SolverLibraryError


def _shaft():
    E=211e9;G=E/(2*(1+.3));rho=7810.
    return ShaftElement(2,1,2,.025,0.,rho,E,G,0.)


def _base_model():
    return RotorModel(
        nodes=[Node(1,0.0),Node(2,.5)],
        shafts=[_shaft()],
        bearings=[Bearing(3,2,(1.0e7,2.0e7,4.0e5,4.0e5))],
        forces=[Force(1,(2,1.0e-3,0.0))],
    )


def _type5(node,kxx,kxy,kyx,kyy,cxx,cxy,cyx,cyy):
    return Bearing(5,node,(kxx,kxy,kyx,kyy,cxx,cxy,cyx,cyy))


def _constant_advanced(node=1):
    return CoefficientBearing(
        node=node,kxx=1.25e7,kxy=2.5e5,kyx=-1.5e5,kyy=1.65e7,
        cxx=3.2e5,cxy=1.1e4,cyx=-9.0e3,cyy=3.8e5,
    )


def _alpha():
    # Omega(t)=2*a2*t+a1 = 40 + 20*t rad/s on [0,2].
    return np.asarray([10.0,40.0,0.0])


def test_b18_constant_advanced_equals_legacy_type5_runup():
    advanced=_base_model()
    advanced.advanced_bearings=[_constant_advanced(1)]
    b=advanced.advanced_bearings[0]
    legacy=_base_model()
    legacy.bearings=[
        *legacy.bearings,
        _type5(1,b.kxx,b.kxy,b.kyx,b.kyy,b.cxx,b.cxy,b.cyx,b.cyy),
    ]
    kwargs=dict(nr=0,rtol=2e-7,atol=2e-10,h_max=2e-3,max_points=100000)
    ra=run_runup(advanced,_alpha(),[0.0,2.0],**kwargs)
    rl=run_runup(legacy,_alpha(),[0.0,2.0],**kwargs)
    np.testing.assert_allclose(ra.time_s,rl.time_s,rtol=0,atol=2e-13)
    np.testing.assert_allclose(ra.speed_rad_s,rl.speed_rad_s,rtol=0,atol=2e-12)
    np.testing.assert_allclose(ra.response,rl.response,rtol=2e-10,atol=2e-12)
    assert ra.metadata["native_abi"]=="rd_runup_coeffmap_legacy"
    assert ra.metadata["advanced_bearing_scope"]=="FULL_ORDER|SYNCHRONOUS_COEFFICIENT_POLICY|MAP_BASED|NO_TEHD_IN_ODE"


def test_b18_speed_dependent_linear_map_matches_independent_rhs_oracle():
    model=_base_model()
    axis=(30.0,50.0,70.0,90.0)
    b=CoefficientBearing(
        node=1,speed_rad_s=axis,interpolation="linear",
        kxx=tuple(1.1e7+2.0e4*w for w in axis),
        kxy=tuple(2.0e5-100.0*w for w in axis),
        kyx=tuple(-1.0e5+80.0*w for w in axis),
        kyy=tuple(1.5e7+1.0e4*w for w in axis),
        cxx=tuple(2.8e5+100.0*w for w in axis),
        cxy=tuple(8.0e3+10.0*w for w in axis),
        cyx=tuple(-7.0e3+5.0*w for w in axis),
        cyy=tuple(3.4e5+80.0*w for w in axis),
    )
    model.advanced_bearings=[b]
    result=run_runup(model,_alpha(),[0.0,2.0],nr=0,rtol=2e-7,atol=2e-10,h_max=2e-3,max_points=100000)

    # Independent Python/SciPy oracle: use RotorStudio's qualified stationary
    # matrices only for constant rotor/legacy terms; interpolate the B18 map
    # independently inside DOP853.
    from drm_core.solver.backend import FortranBackend
    backend=FortranBackend()
    base=_base_model()
    M,C0,K0,G=backend.assemble_matrices(base,0.0)
    nd=M.shape[0]
    fc=np.zeros(nd,dtype=complex)
    q=1.0e-3
    fc[4*2-4]+=q
    fc[4*2-3]+=-1j*q
    a2,a1,a0=_alpha()
    speed_axis=np.asarray(axis)
    provider=AdvancedBearingBackend()
    def rhs(t,y):
        phi=a2*t*t+a1*t+a0;omega=2*a2*t+a1;dd=2*a2
        ev=provider.evaluate(b,omega,omega)
        K=K0.copy();C=C0+omega*G
        ii=np.array([0,1])
        K[np.ix_(ii,ii)]+=ev.K
        C[np.ix_(ii,ii)]+=ev.C
        forcing=np.real(fc*(omega*omega-1j*dd)*np.exp(1j*phi))
        dy=np.empty_like(y);dy[:nd]=y[nd:]
        dy[nd:]=np.linalg.solve(M,forcing-K@y[:nd]-C@y[nd:])
        return dy
    sol=solve_ivp(rhs,(result.time_s[0],result.time_s[-1]),np.zeros(2*nd),method="DOP853",rtol=2e-10,atol=2e-12,t_eval=result.time_s)
    np.testing.assert_allclose(result.response,sol.y[:nd],rtol=8e-5,atol=2e-9)


def test_b18_map_coverage_and_reduced_order_fail_closed():
    model=_base_model()
    model.advanced_bearings=[CoefficientBearing(
        node=1,speed_rad_s=(45.0,70.0),interpolation="linear",
        kxx=(1e7,1.1e7),kyy=(1.2e7,1.3e7),cxx=(3e5,3.1e5),cyy=(3.2e5,3.3e5),
    )]
    with pytest.raises(SolverLibraryError,match="coverage"):
        run_runup(model,_alpha(),[0.0,2.0],nr=0)
    with pytest.raises(SolverLibraryError,match="reduced-order path is not qualified"):
        run_runup(model,_alpha(),[0.5,1.0],nr=4)


def test_b18_rejects_direct_physics_and_async_2d_map():
    model=_base_model()
    model.advanced_bearings=[_plain()]
    with pytest.raises(SolverLibraryError,match="does not execute physical Reynolds/THD/TEHD"):
        run_runup(model,_alpha(),[0.0,1.0],nr=0)
    model.advanced_bearings=[CoefficientBearing(
        node=1,speed_rad_s=(30.0,90.0),frequency_rad_s=(30.0,90.0),
        kxx=((1e7,1e7),(1e7,1e7)),kyy=1.2e7,cxx=3e5,cyy=3.2e5,
        interpolation="linear",
    )]
    with pytest.raises(SolverLibraryError,match="synchronous 1-D map"):
        run_runup(model,_alpha(),[0.0,1.0],nr=0)


def _plain():
    return PlainJournalPhysicsBearing(
        node=1,weight_n=112814.90696191376,journal_diameter_m=0.3999992,
        radial_clearance_m=0.000194564,oil_viscosity_pa_s=0.01901574061455835,
        pivot_angle_rad=(np.pi/2,3*np.pi/2),pad_arc_rad=(3.07177948351002,)*2,
        pad_axial_length_m=(0.263144,)*2,preload=(0.0,0.0),offset=(0.5,0.5),
        total_e_x_film=8,total_e_z_film=4,total_e_y_pad=4,total_e_y_film=4,
        xj_ratio_initial=.15,yj_ratio_initial=-.2,force_tolerance=5e-3,outer_iterations=8,
    )


def _tilting():
    return TiltingPadPhysicsBearing(
        node=1,weight_n=112814.90696191376,journal_diameter_m=0.3999992,
        radial_clearance_m=0.000194564,oil_viscosity_pa_s=0.01901574061455835,
        pad_thickness_m=0.149614636,pad_density_kg_m3=7835.631544657211,
        pivot_angle_rad=(0.9424777960769379,2.199114857512855,3.4557519189487724,4.71238898038469,5.969026041820607),
        pad_arc_rad=(1.0471975511965976,)*5,pad_axial_length_m=(0.263144,)*5,
        preload=(0.3,)*5,offset=(0.5,)*5,k_rotate_nm_rad=(0.0,)*5,
        total_e_x_film=8,total_e_z_film=4,total_e_y_pad=4,total_e_y_film=4,
        xj_ratio_initial=.15,yj_ratio_initial=-.2,force_tolerance=5e-3,outer_iterations=8,
    )


@pytest.mark.parametrize("factory",[_plain,_tilting])
def test_b18_b16_synchronous_physical_maps_run_without_physical_provider_in_ode(factory):
    provider=AdvancedBearingBackend()
    axis=(30.0,50.0,70.0,90.0)
    operating=generate_operating_map(factory(),axis,interpolation="linear",backend=provider)
    mapped=operating.to_coefficient_bearing(tag="B18 synchronous physical map")
    model=_base_model();model.advanced_bearings=[mapped]
    result=run_runup(model,_alpha(),[0.0,2.0],nr=0,rtol=1e-5,atol=1e-8,h_max=5e-3,max_points=100000)
    assert result.metadata["map_points"]==len(axis)
    assert result.metadata["advanced_bearing_scope"].endswith("NO_TEHD_IN_ODE")
    assert np.isfinite(result.response).all()


def test_b18_time_step_and_map_resolution_convergence():
    fine_axis=tuple(np.linspace(30.0,90.0,13))
    coarse_axis=tuple(np.linspace(30.0,90.0,5))
    def bearing(axis):
        return CoefficientBearing(
            node=1,speed_rad_s=axis,interpolation="linear",
            kxx=tuple(1e7+3e4*w+25*w*w for w in axis),
            kyy=tuple(1.3e7+2e4*w+15*w*w for w in axis),
            cxx=tuple(3e5+60*w for w in axis),cyy=tuple(3.4e5+40*w for w in axis),
        )
    def run(axis,h):
        m=_base_model();m.advanced_bearings=[bearing(axis)]
        return run_runup(m,_alpha(),[0.0,2.0],nr=0,rtol=2e-6,atol=2e-9,h_max=h,max_points=150000)
    coarse=run(coarse_axis,4e-3);fine=run(fine_axis,2e-3);finer=run(fine_axis,1e-3)
    # Compare final state; refinement in time must collapse, and the map
    # refinement effect remains bounded for this smooth synthetic surface.
    assert np.linalg.norm(finer.response[:,-1]-fine.response[:,-1]) < 5e-4*max(1e-12,np.linalg.norm(finer.response[:,-1]))
    assert np.linalg.norm(fine.response[:,-1]-coarse.response[:,-1]) < 2e-2*max(1e-12,np.linalg.norm(fine.response[:,-1]))
