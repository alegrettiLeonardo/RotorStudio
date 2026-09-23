from pathlib import Path
import numpy as np
from drm_core import run_foundation_time_response,run_runup
from drm_core.units import rpm_to_rad_s
from python.tests.test_transient_source_oracle_m5 import foundation_model,runup_model
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'validation'/'baseline'/'transient'

def test_frozen_source_reference_time_fdn():
    ref=np.load(BASE/'time_fdn_source_reference.npz')
    r=run_foundation_time_response(foundation_model(),float(ref['rotor_speed_rad_s']),float(ref['dt']),int(ref['npts']),nr=int(ref['nr']),rtol=2e-7,atol=2e-10)
    assert np.array_equal(r.time_s,ref['time'])
    assert np.allclose(r.forcing,ref['force'],rtol=0,atol=2e-15)
    dofs=np.asarray(ref['response_dofs'],dtype=int);assert np.allclose(r.response[dofs,:],ref['response'],rtol=3e-5,atol=4e-9)
    assert abs(r.metadata['max_reduced_frequency_hz']-float(ref['max_reduced_frequency_hz']))/float(ref['max_reduced_frequency_hz'])<3e-10

def test_frozen_source_reference_runup():
    ref=np.load(BASE/'runup_source_reference.npz');alpha=np.asarray(ref['alpha'],float)
    r=run_runup(runup_model(),alpha,[float(ref['time'][0]),float(ref['time'][-1])],nr=int(ref['nr']),rtol=float(ref['rtol']),atol=float(ref['atol']),max_points=50000)
    assert np.allclose(r.time_s,ref['time'],rtol=0,atol=5e-13)
    assert np.allclose(r.speed_rad_s,ref['speed'],rtol=0,atol=1e-12)
    dofs=np.asarray(ref['response_dofs'],dtype=int);assert np.allclose(r.response[dofs,:],ref['response'],rtol=5e-5,atol=5e-9)
    assert abs(r.metadata['max_reduced_frequency_hz']-float(ref['max_reduced_frequency_hz']))/float(ref['max_reduced_frequency_hz'])<3e-10
