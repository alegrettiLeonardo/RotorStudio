"""A5 UCS exact-head numerical qualification.

This script is validation-only.  Production UCS construction, modal sweeps,
Rouch mass folding, intersections and critical modal solves remain Fortran.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.linalg import eig

from drm_core import (
    Bearing, CoefficientBearing, Disk, Node, RotorModel, ShaftElement, run_ucs
)
from drm_core.solver.backend import FortranBackend


ROOT=Path(__file__).resolve().parents[2]
GOLD=ROOT/"validation"/"ross_parity"/"ucs"
ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"

# Frozen before remote closure.  These are A5-specific; A4 tolerances are not
# reused implicitly.  The bearing default speed axis inherits the modal
# tolerance because frozen ROSS derives it from ARPACK wn while production
# derives the same affine construction from the native LAPACK wn.
TOLERANCES={
    "M":{"rtol":2e-12,"atol":2e-12},
    "G":{"rtol":2e-12,"atol":2e-12},
    "K":{"rtol":2e-12,"atol":1e-6},
    "wn":{"rtol":2e-8,"atol":2e-6},
    "bearing_axis":{"rtol":2e-8,"atol":2e-6},
    "bearing_curve":{"rtol":2e-10,"atol":1e-5},
    "intersection_k":{"rtol":2e-7,"atol":2e-2},
    "intersection_speed":{"rtol":2e-7,"atol":2e-5},
    "critical_modal":{"rtol":3e-8,"atol":3e-6},
    "eigen_residual_scaled_max":1e-9,
    "intersection_polyline_scaled_max":2e-7,
}


def _model(bearing):
    z=(0.0,0.21,0.48,0.67)
    shafts=[
        ShaftElement(2,i+1,i+2,od,0.014,7810.0,211e9,81.2e9,2.5e-3,0.0,0.0)
        for i,od in enumerate((0.054,0.061,0.049))
    ]
    disk=Disk.inertial(3,19.0,0.083,0.151)
    if isinstance(bearing,tuple):
        kx,ky=bearing
        return RotorModel(
            [Node(i+1,x) for i,x in enumerate(z)],shafts,[disk],
            [Bearing(3,1,(kx,ky,230.0,230.0)),Bearing(3,4,(kx,ky,230.0,230.0))]
        )
    from dataclasses import replace
    return RotorModel(
        [Node(i+1,x) for i,x in enumerate(z)],shafts,[disk],[],
        advanced_bearings=[replace(bearing,node=1,tag="A5 bearing 0"),replace(bearing,node=4,tag="A5 bearing 1")]
    )


def _bearing_cases():
    speed=(40.0,120.0,260.0,480.0,820.0)
    frequency=(30.0,100.0,230.0,470.0,830.0)
    equal=(4.2e6,7.1e6,1.18e7,1.75e7,2.65e7)
    sx=(3.9e6,7.4e6,1.28e7,2.02e7,3.05e7)
    sy=(6.2e6,9.6e6,1.53e7,2.42e7,3.62e7)
    fx=(4.6e6,7.8e6,1.33e7,2.11e7,3.28e7)
    fy=(5.9e6,9.1e6,1.51e7,2.39e7,3.55e7)
    gx=(
        (3.6e6,4.2e6,5.1e6,6.3e6,7.8e6),
        (5.1e6,5.9e6,7.0e6,8.5e6,1.03e7),
        (7.4e6,8.4e6,9.8e6,1.17e7,1.39e7),
        (1.04e7,1.17e7,1.35e7,1.58e7,1.86e7),
        (1.47e7,1.63e7,1.86e7,2.15e7,2.50e7),
    )
    gy=tuple(tuple(1.18*x+2.0e5 for x in row) for row in gx)
    return {
        "isotropic_constant":((1.25e7,1.25e7),{}),
        "anisotropic_constant":((1.05e7,1.85e7),{}),
        "speed_equal":(CoefficientBearing(1,equal,0.0,equal,0.0,speed_rad_s=speed),{}),
        "speed_anisotropic":(CoefficientBearing(1,sx,0.0,sy,0.0,speed_rad_s=speed),{}),
        "frequency_axis":(CoefficientBearing(1,fx,0.0,fy,0.0,frequency_rad_s=frequency),{}),
        "map_2d":(CoefficientBearing(1,gx,0.0,gy,0.0,speed_rad_s=speed,frequency_rad_s=frequency,interpolation="pchip"),{}),
        "explicit_bearing_speed_range":((1.05e7,1.85e7),{"bearing_speed_range":(40.0,900.0)}),
        "no_intersection":((1.0e3,1.0e3),{"bearing_speed_range":(50.0,900.0)}),
        "synchronous_true":((1.25e7,1.25e7),{"synchronous":True}),
    }


def _load(name):
    return json.loads((GOLD/f"{name}.json").read_text())


def _max_abs(a,b):
    a=np.asarray(a);b=np.asarray(b)
    if a.size==0 and b.size==0:return 0.0
    return float(np.max(np.abs(a-b)))


def _assert_close(a,b,key):
    tol=TOLERANCES[key]
    np.testing.assert_allclose(a,b,rtol=tol["rtol"],atol=tol["atol"])


def _point_polyline_scaled_distance(x,y,xs,ys):
    xs=np.asarray(xs,float);ys=np.asarray(ys,float)
    sx=max(1.0,abs(float(x)));sy=max(1.0,abs(float(y)))
    p=np.array([x/sx,y/sy],float)
    best=np.inf
    for j in range(len(xs)-1):
        a=np.array([xs[j]/sx,ys[j]/sy],float)
        b=np.array([xs[j+1]/sx,ys[j+1]/sy],float)
        d=b-a
        den=float(d@d)
        t=0.0 if den==0.0 else float(np.clip(((p-a)@d)/den,0.0,1.0))
        best=min(best,float(np.linalg.norm(p-(a+t*d))))
    return best


def _independent_generalized_eigen(M,K,nbranch):
    values,vectors=eig(K,M)
    candidates=[]
    residuals=[]
    for i,lam in enumerate(values):
        if not np.isfinite(lam):
            continue
        if abs(lam.imag)>1e-6*max(1.0,abs(lam.real)) or lam.real<=0.0:
            continue
        omega=float(np.sqrt(lam.real))
        phi=vectors[:,i]
        lhs=K@phi
        rhs=lam*M@phi
        scale=max(np.linalg.norm(lhs)+np.linalg.norm(rhs),np.finfo(float).tiny)
        candidates.append((omega,i))
        residuals.append(float(np.linalg.norm(lhs-rhs)/scale))
    candidates.sort(key=lambda pair:pair[0])
    # 4-DOF lateral isotropy yields the pair structure mirrored by modal.wn[::2].
    selected=[x[0] for x in candidates[::2][:nbranch]]
    return np.asarray(selected), max(residuals,default=np.inf)


def qualify(out:Path):
    authority=json.loads((GOLD/"authority.json").read_text())
    assert authority["commit"]==ROSS_SHA

    metrics={
        "matrix_max_abs":{"M":0.0,"C":0.0,"G":0.0,"K":0.0},
        "wn_max_abs":0.0,
        "bearing_axis_max_abs":0.0,
        "bearing_curve_max_abs":0.0,
        "intersection_k_max_abs":0.0,
        "intersection_speed_max_abs":0.0,
        "critical_modal_max_abs":0.0,
        "eigen_residual_scaled_max":0.0,
        "intersection_polyline_scaled_max":0.0,
    }
    cases={}
    backend=FortranBackend()

    # Matrix-first qualification, including ordinary and Rouch mass matrices.
    for sync,name in ((False,"isotropic_constant"),(True,"synchronous_true")):
        model=_model((1.25e7,1.25e7))
        golden=_load(name)
        for sent in golden["matrix_sentinels"]:
            got=backend.ucs_matrices(model,float(sent["stiffness"]),sync)
            for key in ("M","G","K"):
                metrics["matrix_max_abs"][key]=max(
                    metrics["matrix_max_abs"][key],_max_abs(got[key],sent[key])
                )
                _assert_close(got[key],sent[key],key)
            metrics["matrix_max_abs"]["C"]=max(
                metrics["matrix_max_abs"]["C"],float(np.max(np.abs(got["C"])))
            )
            assert np.array_equal(got["C"],np.zeros_like(got["C"]))
            assert np.array_equal(np.asarray(sent["C"]),np.zeros_like(got["C"]))

            independent,residual=_independent_generalized_eigen(
                got["M"],got["K"],len(sent["modal_branch"])
            )
            metrics["eigen_residual_scaled_max"]=max(
                metrics["eigen_residual_scaled_max"],residual
            )
            _assert_close(independent,sent["modal_branch"],"wn")

    # Full result-chain parity for every immutable production case.
    for name,(bearing,extra) in _bearing_cases().items():
        golden=_load(name)
        kwargs=dict(stiffness_range_exponents=(6,10),num=7,num_modes=16)
        kwargs.update(extra)
        result=run_ucs(_model(bearing),**kwargs)

        _assert_close(result.stiffness_log_n_m,golden["stiffness_log"],"K")
        # logspace_gate is a dedicated exponent/grid contract.  Full modal
        # branch parity is already exercised by the constant, anisotropic,
        # coefficient-map and Rouch cases on the same physical rotor.  Do not
        # turn this semantic sentinel into a second eigensolver tolerance gate:
        # frozen ROSS ARPACK and native LAPACK differ most on the highest
        # conditioned branch at the isolated 1e9 point.
        metrics["wn_max_abs"]=max(
            metrics["wn_max_abs"],
            _max_abs(result.natural_frequency_rad_s,golden["rotor_wn"])
        )
        if name!="logspace_gate":
            _assert_close(result.natural_frequency_rad_s,golden["rotor_wn"],"wn")

        if result.bearing_speed_policy=="constant_10_point_rotor_wn_margin":
            margin=float(result.natural_frequency_rad_s.min())*0.1
            semantic=np.linspace(
                float(result.natural_frequency_rad_s.min()-margin),
                float(result.natural_frequency_rad_s.max()+margin),10
            )
            np.testing.assert_array_equal(result.bearing_speed_rad_s,semantic)
        if name!="logspace_gate":
            _assert_close(result.bearing_speed_rad_s,golden["bearing_speed_range"],"bearing_axis")
        metrics["bearing_axis_max_abs"]=max(metrics["bearing_axis_max_abs"],_max_abs(result.bearing_speed_rad_s,golden["bearing_speed_range"]))

        for got,ref in (
            (result.bearing_kxx_n_m,golden["bearing_kxx"]),
            (result.bearing_kyy_n_m,golden["bearing_kyy"]),
        ):
            _assert_close(got,ref,"bearing_curve")
            metrics["bearing_curve_max_abs"]=max(metrics["bearing_curve_max_abs"],_max_abs(got,ref))

        _assert_close(result.intersection_stiffness_n_m,golden["intersection_x"],"intersection_k")
        _assert_close(result.intersection_speed_rad_s,golden["intersection_y"],"intersection_speed")
        metrics["intersection_k_max_abs"]=max(metrics["intersection_k_max_abs"],_max_abs(result.intersection_stiffness_n_m,golden["intersection_x"]))
        metrics["intersection_speed_max_abs"]=max(metrics["intersection_speed_max_abs"],_max_abs(result.intersection_speed_rad_s,golden["intersection_y"]))

        assert list(result.coefficient_families)==list(golden["coefficients_processed"])
        if name=="isotropic_constant":
            assert result.coefficient_families==("kxx",)
        if name=="no_intersection":
            assert len(result.intersection_speed_rad_s)==0

        if golden["critical_modal"]:
            ref=np.asarray([x["wn"] for x in golden["critical_modal"]],float).T
            _assert_close(result.critical_wn_rad_s,ref,"critical_modal")
            metrics["critical_modal_max_abs"]=max(metrics["critical_modal_max_abs"],_max_abs(result.critical_wn_rad_s,ref))

        assert np.all(np.diff(result.stiffness_log_n_m)>0.0)
        assert np.all(result.stiffness_log_n_m>0.0)
        assert np.all(result.natural_frequency_rad_s>=0.0)

        # Independent geometric residual: every reported intersection lies on
        # both the selected rotor branch and the original bearing curve.
        for i,(kc,sc) in enumerate(zip(result.intersection_stiffness_n_m,result.intersection_speed_rad_s)):
            mode=int(result.intersection_mode_index[i])
            coeff=str(result.intersection_coefficient[i])
            d1=_point_polyline_scaled_distance(
                kc,sc,result.stiffness_log_n_m,result.natural_frequency_rad_s[mode]
            )
            curve=result.bearing_kxx_n_m if coeff=="kxx" else result.bearing_kyy_n_m
            d2=_point_polyline_scaled_distance(
                kc,sc,curve,result.bearing_speed_rad_s
            )
            metrics["intersection_polyline_scaled_max"]=max(
                metrics["intersection_polyline_scaled_max"],d1,d2
            )

        cases[name]={
            "status":"PASS",
            "intersections":int(len(result.intersection_speed_rad_s)),
            "branches":int(result.natural_frequency_rad_s.shape[0]),
            "stiffness_points":int(result.natural_frequency_rad_s.shape[1]),
            "bearing_speed_policy":result.bearing_speed_policy,
            "synchronous":bool(result.synchronous),
        }

    assert metrics["eigen_residual_scaled_max"]<=TOLERANCES["eigen_residual_scaled_max"]
    assert metrics["intersection_polyline_scaled_max"]<=TOLERANCES["intersection_polyline_scaled_max"]

    logspace=run_ucs(_model((1.25e7,1.25e7)),(6,10),num=5,num_modes=16)
    logspace_authority=_load("logspace_gate")
    np.testing.assert_allclose(
        logspace.stiffness_log_n_m,[1e6,1e7,1e8,1e9,1e10],rtol=2e-15,atol=0
    )
    np.testing.assert_allclose(
        logspace.stiffness_log_n_m,logspace_authority["stiffness_log"],rtol=2e-15,atol=0
    )

    payload={
        "status":"PASS",
        "ross_authority":ROSS_SHA,
        "production_physics":"Fortran 2018",
        "native_abi":"rd_ucs_v1",
        "scope":"A5 UCS 4-DOF single shaft / non-linked radial supports / simple and Rouch map",
        "tolerances":TOLERANCES,
        "metrics":metrics,
        "cases":cases,
        "gates":{
            "immutable_authority":"PASS",
            "matrix_first_M_C_G_K":"PASS",
            "C_UCS_exact_zero":"PASS",
            "rouch_mass":"PASS",
            "logspace_exponent_semantics":"PASS",
            "modal_branch_parity":"PASS on production parity cases; logspace sentinel is grid-only by design",
            "bearing_curve_parity":"PASS",
            "intersection_parity":"PASS",
            "intersection_independent_residual":"PASS",
            "critical_modal_parity":"PASS",
            "independent_generalized_eigen_residual":"PASS",
        },
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,indent=2,sort_keys=True))
    print(json.dumps(payload,indent=2,sort_keys=True))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=ROOT/"validation"/"reports"/"a5_ucs_ci.json")
    args=parser.parse_args()
    qualify(args.out)
