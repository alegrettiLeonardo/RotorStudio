from __future__ import annotations
import ast
import pathlib
import numpy as np
import pytest

from drm_core import (
    RotorModel, Node, ShaftElement, TaperedShaftElement, AsymmetricShaftElement,
    Disk, Bearing, Force, AnalysisService, run_assembly, run_modal,
    run_frequency_response, run_critical_speeds,
)
from drm_core.validation.model import validate_model, ModelValidationError
from drm_core.units import rpm_to_rad_s
from drm_core.solver.backend import FortranBackend
from drm_core.solver.ffi import SolverLibraryError


def _model(force=True):
    return RotorModel(
        [Node(1,0.0),Node(2,0.5),Node(3,1.0)],
        [ShaftElement(2,1,2,0.05,0.0,7800,2.1e11,8.0e10),
         ShaftElement(2,2,3,0.05,0.0,7800,2.1e11,8.0e10)],
        [Disk.geometric(2,7800,0.05,0.25,0.05)],
        [Bearing(3,1,(1e6,1e6,0.0,0.0)),Bearing(3,3,(1e6,1e6,0.0,0.0))],
        [Force.unbalance(2,1e-4,0.2)] if force else [],
    )


def test_no_gui_imports():
    root=pathlib.Path(__file__).parents[1]/'src'/'drm_core'
    forbidden={'PySide6','PyQt5','PyQt6','tkinter','wx'}
    for f in root.rglob('*.py'):
        tree=ast.parse(f.read_text())
        for n in ast.walk(tree):
            if isinstance(n,(ast.Import,ast.ImportFrom)):
                names=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else [str(n.module).split('.')[0]]
                assert not forbidden.intersection(names), f'{f} imports GUI library'


def test_units():
    assert abs(rpm_to_rad_s(60)-2*np.pi)<1e-15


def test_validation_messages_and_node_contract():
    m=RotorModel([Node(1,0),Node(2,0)],[ShaftElement(2,1,2,.1,0,7800,2e11,8e10)],[],[])
    with pytest.raises(ModelValidationError,match='Le=0.*expected Le > 0'):
        validate_model(m)
    m2=RotorModel([Node(1,0),Node(3,1)],[ShaftElement(2,1,3,.1,0,7800,2e11,8e10)],[],[])
    with pytest.raises(ModelValidationError,match='sequential node numbers'):
        validate_model(m2)


def test_assembly_mc_gk_invariants():
    r=run_assembly(_model(False),100.0)
    assert r.M.shape==(12,12)
    assert np.all(np.isfinite(r.M)) and np.all(np.diag(r.M)>0)
    assert np.linalg.norm(r.M-r.M.T)/np.linalg.norm(r.M)<1e-13
    assert np.linalg.norm(r.K0-r.K0.T)/np.linalg.norm(r.K0)<1e-13
    den=max(1.0,np.linalg.norm(r.G))
    assert np.linalg.norm(r.G+r.G.T)/den<1e-13
    assert np.all(np.isfinite(r.C)) and np.all(np.isfinite(r.K))
    assert r.metadata['backend'] if 'backend' in r.metadata else True


def test_modal_full_eigenvectors_kappa():
    r=run_modal(_model(False),100.0)
    assert r.eigenvalues.shape==(24,)
    assert r.eigenvectors.shape==(12,24)
    assert r.kappa.shape==(12,24)
    assert np.all(np.isfinite(r.eigenvalues))
    assert np.all(np.isfinite(r.eigenvectors))
    assert np.all(np.isfinite(r.kappa))
    assert r.metadata['solver_version']=='0.3.0'


def test_tapered_element_and_stationary_assembly():
    b=FortranBackend()
    t=TaperedShaftElement(22,1,2,0.055,0.045,0.010,0.008,7800,2.1e11,8.0e10,0.0)
    M,G,K,K1=b.shaft_element_matrices(t,0.5)
    assert np.linalg.norm(M-M.T)/np.linalg.norm(M)<1e-13
    assert np.linalg.norm(K-K.T)/np.linalg.norm(K)<1e-13
    assert np.linalg.norm(G+G.T)/max(1,np.linalg.norm(G))<1e-13
    assert np.linalg.norm(K1)==0
    m=RotorModel([Node(1,0),Node(2,.5)],[t],[],[Bearing(3,1,(1e6,1e6,0,0)),Bearing(3,2,(1e6,1e6,0,0))])
    a=run_assembly(m,50.0)
    assert np.all(np.isfinite(a.M))


def test_asymmetric_element_preserves_legacy_defect_gate():
    b=FortranBackend()
    a=AsymmetricShaftElement(12,1,2,2e5,1.8e5,0.05,0.06,25.0,0.02,0.001,0.0)
    M,G,K,C=b.shaft_element_matrices(a,0.4)
    assert np.all(np.isfinite(M)) and np.all(np.isfinite(K))
    assert np.linalg.norm(M-M.T)/np.linalg.norm(M)<1e-13
    bad=AsymmetricShaftElement(12,1,2,2e5,1.8e5,0.05,0.06,25.0,0.02,0.001,100.0)
    with pytest.raises(SolverLibraryError,match='status=40'):
        b.shaft_element_matrices(bad,0.4)


def test_frequency_response_fortran_path():
    r=run_frequency_response(_model(True),np.array([50.0,100.0,150.0]))
    assert r.response.shape==(12,3)
    assert np.all(np.isfinite(r.response))
    assert np.max(np.abs(r.response))>0
    assert r.metadata['legacy_function']=='freq_rsp.m'


def test_critical_speed_direct_and_iterative_agree():
    m=_model(False)
    d=run_critical_speeds(m,number_criticals=3,method='direct')
    it=run_critical_speeds(m,number_criticals=3,method='iterative-index')
    assert np.all(d.converged) and np.all(it.converged)
    assert d.mode_shapes.shape==(12,3)
    assert it.mode_shapes.shape==(12,3)
    rel=np.abs(it.critical_speeds_rad_s-d.critical_speeds_rad_s)/np.maximum(1,np.abs(d.critical_speeds_rad_s))
    assert np.max(rel)<1e-7
    near=run_critical_speeds(m,method='iterative-nearest',initial_estimates=d.critical_speeds_rad_s)
    assert np.all(near.converged)
    rel2=np.abs(near.critical_speeds_rad_s-d.critical_speeds_rad_s)/np.maximum(1,np.abs(d.critical_speeds_rad_s))
    assert np.max(rel2)<1e-7


def test_hydrodynamic_and_seal_bearing_paths():
    b=FortranBackend()
    # V2 type 7: F,D,L,c,eta. Non-zero speed is required by source equations.
    m7=RotorModel([Node(1,0),Node(2,.5)],[ShaftElement(2,1,2,.05,0,7800,2.1e11,8e10)],[],
                  [Bearing(7,1,(1000.0,0.05,0.02,50e-6,0.02)),Bearing(3,2,(1e6,1e6,0,0))])
    a7=run_assembly(m7,200.0)
    assert 0<a7.bearing_eccentricity[0]<1
    m8=RotorModel([Node(1,0),Node(2,.5)],[ShaftElement(2,1,2,.05,0,7800,2.1e11,8e10)],[],
                  [Bearing(8,1,(2e5,0.025,0.02,50e-6,10.0,0.02)),Bearing(3,2,(1e6,1e6,0,0))])
    a8=run_assembly(m8,200.0)
    assert np.linalg.norm(a8.M)>0 and np.linalg.norm(a8.C0)>0 and np.linalg.norm(a8.K0)>0


def test_analysis_service_uses_same_fortran_core():
    svc=AnalysisService()
    assert svc.modal(_model(False),80.0).metadata['solver_version']=='0.3.0'
    assert svc.frequency_response(_model(True),[80.0]).response.shape==(12,1)
