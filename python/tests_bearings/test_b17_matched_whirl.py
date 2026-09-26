from __future__ import annotations

import numpy as np

from drm_core import (
    AnalysisCase, AnalysisService, Bearing, CoefficientBearing, Node,
    RotorModel, RotorProject, ShaftElement,
)
from drm_core.analysis.modal import (
    FIXED_WHIRL, MATCHED_WHIRL, SYNCHRONOUS_COEFFICIENTS,
    ModalResult, modal_assurance_criterion, run_modal, track_modal_branches,
)
from drm_core.solver.bearings_backend import AdvancedBearingBackend


def _type5(node, K, C):
    return Bearing(5,node,(
        float(K[0,0]),float(K[0,1]),float(K[1,0]),float(K[1,1]),
        float(C[0,0]),float(C[0,1]),float(C[1,0]),float(C[1,1]),
    ))


def _source_bearing(node=1):
    speed=(50.0,150.0,250.0)
    frequency=(20.0,120.0,320.0)
    def surf(base, a, b):
        return tuple(tuple(base+a*s+b*w for w in frequency) for s in speed)
    return CoefficientBearing(
        node=node,speed_rad_s=speed,frequency_rad_s=frequency,interpolation="linear",
        kxx=surf(1.20e6,250.0,650.0),
        kxy=surf(2.0e4,10.0,-12.0),
        kyx=surf(-3.0e4,-8.0,15.0),
        kyy=surf(1.45e6,180.0,520.0),
        cxx=surf(180.0,0.03,0.10),
        cxy=surf(8.0,0.002,-0.003),
        cyx=surf(-6.0,-0.002,0.004),
        cyy=surf(210.0,0.02,0.08),
    )


def _model():
    shaft=ShaftElement(2,1,2,0.05,0.0,7810.0,211e9,81.2e9,0.0,0.0,0.0)
    return RotorModel(
        nodes=[Node(1,0.0),Node(2,1.0)],
        shafts=[shaft],
        bearings=[Bearing(5,2,(1.3e6,0.0,0.0,1.4e6,160.0,0.0,0.0,170.0))],
        advanced_bearings=[_source_bearing(1)],
    )


def _sorted(values):
    a=np.asarray(values,dtype=np.complex128)
    return a[np.lexsort((np.angle(a),np.abs(a)))]


def test_b17_fixed_whirl_matches_explicit_type5_at_same_omega_and_keeps_gyro_at_Omega():
    model=_model()
    Omega=150.0
    omega=70.0
    fixed=run_modal(
        model,Omega,with_eigenvectors=True,
        coefficient_policy=FIXED_WHIRL,whirl_frequency_rad_s=omega,
    )
    evaluated=AdvancedBearingBackend().evaluate(model.advanced_bearings[0],Omega,omega)
    legacy=RotorModel(
        nodes=model.nodes,shafts=model.shafts,
        bearings=[*model.bearings,_type5(1,evaluated.K,evaluated.C)],
    )
    oracle=run_modal(legacy,Omega,with_eigenvectors=True)
    np.testing.assert_allclose(_sorted(fixed.eigenvalues),_sorted(oracle.eigenvalues),rtol=2e-12,atol=2e-7)
    assert fixed.metadata["coefficient_policy"]==FIXED_WHIRL
    assert fixed.metadata["whirl_frequency_rad_s"]==omega
    # If omega had incorrectly replaced Omega in the gyro term this equality
    # against the explicit type-5 solve at rotor speed Omega would fail.


def test_b17_synchronous_default_remains_omega_equal_Omega():
    model=_model()
    implicit=run_modal(model,140.0,with_eigenvectors=True)
    explicit=run_modal(
        model,140.0,with_eigenvectors=True,
        coefficient_policy=SYNCHRONOUS_COEFFICIENTS,
    )
    np.testing.assert_allclose(implicit.eigenvalues,explicit.eigenvalues,rtol=0,atol=0)
    assert explicit.metadata["whirl_frequency_rad_s"]==140.0


def test_b17_matched_whirl_tracks_modes_by_mac_and_records_diagnostics():
    result=run_modal(
        _model(),150.0,with_eigenvectors=True,
        coefficient_policy=MATCHED_WHIRL,whirl_rtol=2e-4,whirl_max_iter=40,
    )
    diag=result.metadata["matched_whirl"]
    assert len(diag)==len(result.eigenvalues)
    assert len(result.metadata["whirl_frequency_rad_s"])==len(result.eigenvalues)
    for index,item in enumerate(diag):
        assert item["iterations"]>=1
        assert 0.0<=item["last_mac"]<=1.0
        assert item["converged"] is True
        np.testing.assert_allclose(
            item["final_whirl_frequency_rad_s"],
            abs(result.eigenvalues[index].imag),
            rtol=2e-4,atol=1e-8,
        )


def test_b17_mac_and_outer_campbell_tracking_follow_shape_not_frequency_order():
    eye=np.eye(3,dtype=np.complex128)
    previous=ModalResult(
        100.0,np.array([-1+10j,-2+20j,-3+30j]),
        np.array([10,20,30])/(2*np.pi),np.array([.1,.1,.1]),eye,None,None,{}
    )
    permutation=[2,0,1]
    current=ModalResult(
        120.0,np.array([-30+300j,-10+100j,-20+200j]),
        np.array([300,100,200])/(2*np.pi),np.array([.2,.2,.2]),
        eye[:,permutation],None,None,{}
    )
    assert modal_assurance_criterion(eye[:,0],eye[:,0])==1.0
    tracked=track_modal_branches(previous,current)
    np.testing.assert_allclose(tracked.eigenvalues,[-10+100j,-20+200j,-30+300j])
    assert tracked.metadata["campbell_outer_tracking"]["minimum_mac"]==1.0


def test_b17_campbell_runs_inner_matched_whirl_then_outer_mac_tracking():
    project=RotorProject("B17",_model())
    case=AnalysisCase(
        "modal_sweep",
        {
            "speeds_rad_s":[130.0,150.0,170.0],
            "with_eigenvectors":True,
            "with_kappa":False,
            "coefficient_policy":MATCHED_WHIRL,
            "whirl_rtol":5e-4,
            "whirl_max_iter":40,
        },
        "B17 Campbell",
    )
    execution=AnalysisService().execute(project,case)
    assert len(execution.result)==3
    assert all(point.metadata["coefficient_policy"]==MATCHED_WHIRL for point in execution.result)
    assert "campbell_outer_tracking" not in execution.result[0].metadata
    assert all("campbell_outer_tracking" in point.metadata for point in execution.result[1:])
