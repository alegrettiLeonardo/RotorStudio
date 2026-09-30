"""Independent A8 boundary and geometry gates, using the actual native solver.

No frozen reference is regenerated and no production computation is mocked.
The SVD below is an independent validation oracle, not a production fallback.
"""
from copy import deepcopy
import ctypes as ct
import json
import os
from pathlib import Path

import numpy as np
import pytest

from drm_core import run_clearance, run_forced_response
from drm_core.solver.backend import FortranBackend
from drm_core.solver.ffi import SolverLibraryError, configure_clearance
from test_clearance import args_for, standard_model


def _record(name,payload,tmp_path):
    directory=Path(os.environ.get("A8_QUALIFICATION_EVIDENCE",str(tmp_path)))
    directory.mkdir(parents=True,exist_ok=True)
    (directory/(name+".json")).write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")


def _complex_response(model,result):
    w=result.speed_range_rad_s
    f=np.zeros((4*len(model.nodes),len(w)),dtype=complex)
    for n,u,p in zip(result.unbalance_nodes,result.unbalance_magnitude_kg_m,result.unbalance_phase_rad):
        x=u*w*w*np.exp(1j*p)
        f[4*(n-1)]+=x
        f[4*(n-1)+1]+=-1j*x
    return run_forced_response(model,w,f.real,f.imag,speed=None).displacement


def test_real_a8_orbit_geometry_from_independent_svd(tmp_path):
    _,kwargs=args_for("explicit_20_gmm")
    kwargs["unbalance_phase_rad"]=[0.37]
    model=standard_model()
    result=run_clearance(model,**kwargs)
    q=_complex_response(model,result)
    major=np.empty_like(result.clearance_response_m_pp)
    minor=np.empty_like(major)
    for j,node in enumerate(result.clearance_nodes):
        x=q[4*(node-1)];y=q[4*(node-1)+1]
        for i in range(len(result.speed_range_rad_s)):
            ellipse=np.array([[x[i].real,-x[i].imag],[y[i].real,-y[i].imag]])
            axes=np.linalg.svd(ellipse,compute_uv=False)
            major[j,i],minor[j,i]=axes
    assert np.all(major>=minor) and np.all(minor>=0)
    np.testing.assert_allclose(result.clearance_response_m_pp,
        2*result.scale_factor*major,rtol=5e-12,atol=1e-16)
    for j,(node,theta) in enumerate(zip(result.probe_nodes,result.probe_angles_rad)):
        projection=2*np.abs(q[4*(node-1)]*np.cos(theta)+q[4*(node-1)+1]*np.sin(theta))
        np.testing.assert_allclose(result.probe_response_m_pp[j],projection,rtol=5e-12,atol=1e-16)
    _record("orbit_svd",dict(status="PASS",native_abi="rd_clearance_v1",
        max_pkpk_residual=float(np.max(np.abs(result.clearance_response_m_pp-2*result.scale_factor*major))),
        minimum_minor=float(minor.min()),minimum_major_minus_minor=float((major-minor).min())),tmp_path)


def test_real_complex_unbalance_scaling_before_clearance_normalization():
    _,kwargs=args_for("explicit_20_gmm")
    kwargs["unbalance_phase_rad"]=[0.37]
    model=standard_model()
    a=run_clearance(model,**kwargs);qa=_complex_response(model,a)
    kwargs["unbalance_magnitude_kg_m"]=[80e-6]
    b=run_clearance(model,**kwargs);qb=_complex_response(model,b)
    np.testing.assert_allclose(qb,4*qa,rtol=5e-12,atol=1e-16)
    np.testing.assert_allclose(b.max_probe_amplitude_m_pp,4*a.max_probe_amplitude_m_pp,rtol=5e-12,atol=1e-16)
    np.testing.assert_allclose(b.scale_factor,a.scale_factor/4,rtol=5e-12,atol=1e-14)
    np.testing.assert_allclose(b.clearance_response_m_pp,a.clearance_response_m_pp,rtol=5e-12,atol=1e-16)


def test_operating_amax_excludes_larger_out_of_range_response():
    _,kwargs=args_for("explicit_20_gmm")
    # A deliberately narrow low-speed operating interval makes the larger
    # response outside it observable. Explicit U avoids changing A7 placement.
    kwargs["minimum_allowable_speed_rad_s"]=0.
    kwargs["maximum_continuous_speed_rad_s"]=1.
    result=run_clearance(standard_model(),**kwargs)
    mask=(result.speed_range_rad_s>=0)&(result.speed_range_rad_s<=1)
    assert 0. in result.speed_range_rad_s and 1. in result.speed_range_rad_s
    outside=float(result.probe_response_m_pp[:,~mask].max())
    inside=float(result.probe_response_m_pp[:,mask].max())
    assert outside>inside>0
    assert result.max_probe_amplitude_m_pp==inside
    assert result.scale_factor==result.vibration_limit_m_pp/inside


@pytest.mark.parametrize("rpm",[11999.,12000.,12001.,20000.])
def test_allowable_vibration_exact_formula_on_both_sides_of_12000_rpm(rpm):
    _,kwargs=args_for("explicit_20_gmm")
    nmc=rpm*2*np.pi/60
    kwargs.update(speed_range_rad_s=[0.,.9*nmc,nmc],
        minimum_allowable_speed_rad_s=.9*nmc,maximum_continuous_speed_rad_s=nmc)
    result=run_clearance(standard_model(),**kwargs)
    expected=min(25.4,25.4*np.sqrt(12000/rpm))*1e-6
    np.testing.assert_allclose(result.vibration_limit_m_pp,expected,rtol=2e-12,atol=2e-15)
    if rpm>12000:assert result.vibration_limit_m_pp<25.4e-6


def test_none_cap_is_really_uncapped_and_explicit_mode_metadata_is_absent():
    _,kwargs=args_for("explicit_20_gmm")
    kwargs["unbalance_magnitude_kg_m"]=[1e-10]
    result=run_clearance(standard_model(),**kwargs)
    assert result.scale_factor_cap is None and result.scale_factor>6
    assert result.scale_factor==result.vibration_limit_m_pp/result.max_probe_amplitude_m_pp
    assert result.mode is None and result.mode_index is None and result.mode_frequency_rad_s is None
    kwargs["scale_factor_cap"]=6.
    capped=run_clearance(standard_model(),**kwargs)
    assert capped.scale_factor==6.
    np.testing.assert_array_equal(capped.probe_response_m_pp,result.probe_response_m_pp)


def test_strict_75_percent_boundary_is_exercised_through_real_fortran(tmp_path):
    _,kwargs=args_for("explicit_20_gmm")
    kwargs.update(clearance_nodes=list(range(1,8)),radial_clearance_m=[100e-6]*7,
                  clearance_tags=[f"boundary-{n}" for n in range(1,8)])
    model=standard_model();chosen=None
    # Select an exactly representable binary equality, not an allclose band.
    # No physical output or acceptance tolerance is modified to manufacture it.
    for cap in (None,.7,.9,1.3):
        kwargs["scale_factor_cap"]=cap
        initial=run_clearance(model,**kwargs)
        for row,target in enumerate(initial.max_clearance_response_m_pp):
            center=np.float64(target/1.5)
            for direction in (0.,np.inf):
                radial=center
                for _ in range(8):
                    if .75*(2*radial)==target:
                        chosen=(deepcopy(kwargs),initial,row,radial);break
                    radial=np.nextafter(radial,direction)
                if chosen is not None:break
            if chosen is not None:break
        if chosen is not None:break
    assert chosen is not None,"unable to construct an exact floating-point boundary sentinel"
    kwargs,initial,row,radial=chosen
    kwargs["radial_clearance_m"][row]=float(radial)
    equal=run_clearance(model,**kwargs)
    target=equal.max_clearance_response_m_pp[row]
    np.testing.assert_array_equal(equal.clearance_response_m_pp,initial.clearance_response_m_pp)
    assert target==equal.clearance_limit_m[row]
    assert not equal.passed[row]
    decisions={"equal":bool(equal.passed[row])}
    for label,direction,want in (("below_clearance",0.,False),("above_clearance",np.inf,True)):
        neighbor=np.nextafter(radial,direction)
        for _ in range(8):
            if .75*(2*neighbor)!=target:break
            neighbor=np.nextafter(neighbor,direction)
        assert .75*(2*neighbor)!=target
        kwargs["radial_clearance_m"][row]=float(neighbor)
        result=run_clearance(model,**kwargs)
        assert bool(result.passed[row]) is want
        decisions[label]=bool(result.passed[row])
    _record("strict_75_percent",dict(status="PASS",node=int(equal.clearance_nodes[row]),
        max_response_m_pp=float(target),limit_m=float(equal.clearance_limit_m[row]),
        exact_equality=True,decisions=decisions),tmp_path)


def test_zero_probe_response_fails_closed_in_the_actual_solver():
    _,kwargs=args_for("explicit_20_gmm")
    kwargs["unbalance_magnitude_kg_m"]=[0.]
    with pytest.raises(SolverLibraryError,match="status=20"):
        run_clearance(standard_model(),**kwargs)


@pytest.mark.parametrize("field,value",[
    ("speed_range_rad_s",[0.,np.nan]),
    ("speed_range_rad_s",[0.,np.inf]),
    ("probe_angles_rad",[np.nan,0.]),
    ("probe_angles_rad",[0.,np.inf]),
    ("radial_clearance_m",[1e-4,np.nan,1e-4]),
    ("radial_clearance_m",[1e-4,np.inf,1e-4]),
    ("unbalance_magnitude_kg_m",[np.nan]),
    ("unbalance_phase_rad",[np.inf]),
    ("scale_factor_cap",np.nan),
    ("scale_factor_cap",np.inf),
    ("minimum_allowable_speed_rad_s",np.nan),
    ("maximum_continuous_speed_rad_s",np.inf),
])
def test_nonfinite_inputs_fail_closed(field,value):
    _,kwargs=args_for("explicit_20_gmm")
    kwargs[field]=value
    with pytest.raises(ValueError):run_clearance(standard_model(),**kwargs)


@pytest.mark.parametrize("dims",[
    (1,10,1,1),(129,10,1,1),(7,0,1,1),(7,10001,1,1),
    (7,10,0,1),(7,10,29,1),(7,10,1,0),(7,10,1,29),
])
def test_actual_native_size_query_rejects_out_of_scope_extents(dims):
    required,_=configure_clearance(FortranBackend().lib)
    maximum=ct.c_int(-123)
    assert required(*dims,ct.byref(maximum))==10
    assert maximum.value==0


def test_actual_native_size_query_returns_caller_capacity():
    required,_=configure_clearance(FortranBackend().lib)
    maximum=ct.c_int(-123)
    assert required(7,53,2,3,ct.byref(maximum))==0
    assert maximum.value==7
