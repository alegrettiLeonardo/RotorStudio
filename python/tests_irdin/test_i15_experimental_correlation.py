from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from drm_core import load_irdin_project
from drm_core.analysis.irdin_lateral import run_irdin_synchronous_sweep
from drm_core.analysis.api541_correlation import (
    ExperimentalLateralDataset,
    assess_lateral_correlation,
    correlate_lateral_dataset,
    load_experimental_lateral_csv,
    modal_assurance_criterion,
    RPM_TO_RAD_S,
)
from validation.irdin.i0_authority import CASE_PATH


def test_i15_csv_import_preserves_complex_amplitude_phase(tmp_path):
    path=tmp_path/"measurement.csv"
    path.write_text(
        "speed_rpm,DE-H_amplitude_um,DE-H_phase_deg,NDE-V_amplitude_um,NDE-V_phase_deg\n"
        "1000,12.5,30,8,-45\n"
        "2000,20,60,10,90\n",
        encoding="utf-8",
    )
    data=load_experimental_lateral_csv(path,measured_critical_speeds_rpm=(1500.0,))
    assert data.channel_names==("DE-H","NDE-V")
    np.testing.assert_allclose(np.abs(data.response_m[:,0]),[12.5e-6,8e-6])
    assert np.angle(data.response_m[0,0])==pytest.approx(np.deg2rad(30.0))
    assert data.measured_critical_speeds_rpm==(1500.0,)


def test_i15_exact_native_dataset_correlates_with_explicit_project_limits():
    p=load_irdin_project(CASE_PATH)
    speed=np.array([500.0,1800.0])
    native=run_irdin_synchronous_sweep(p,speed*RPM_TO_RAD_S)
    names=("DE-H","DE-V","NDE-H","NDE-V")
    data=ExperimentalLateralDataset(speed,names,native.probe_response.copy())
    raw=correlate_lateral_dataset(
        p,data,
        channel_to_probe={"DE-H":1,"DE-V":2,"NDE-H":3,"NDE-V":4},
    )
    assert raw.metadata["status"]=="MODEL_NOT_CORRELATED"
    assert raw.metadata["acceptance_evaluated"] is False
    assessed=assess_lateral_correlation(
        raw,
        amplitude_relative_limit=1e-12,
        phase_deg_limit=1e-9,
    )
    assert assessed.metadata["status"]=="MODEL_CORRELATED_FOR_LATERAL_SCOPE"
    assert assessed.metadata["passed"] is True
    assert all(np.max(np.abs(x.amplitude_delta_m))==pytest.approx(0.0,abs=1e-18) for x in assessed.channels)


def test_i15_perturbed_measurement_fails_declared_acceptance():
    p=load_irdin_project(CASE_PATH)
    speed=np.array([500.0,1800.0])
    native=run_irdin_synchronous_sweep(p,speed*RPM_TO_RAD_S)
    measured=native.probe_response[[0]].copy()*1.25*np.exp(1j*np.deg2rad(20.0))
    data=ExperimentalLateralDataset(speed,("DE-H",),measured)
    result=correlate_lateral_dataset(p,data,channel_to_probe={"DE-H":1})
    assessed=assess_lateral_correlation(
        result,
        amplitude_relative_limit=0.05,
        phase_deg_limit=5.0,
    )
    assert assessed.metadata["status"]=="MODEL_NOT_CORRELATED"
    assert assessed.metadata["passed"] is False


def test_i15_critical_speed_pairing_is_explicit_not_nearest_neighbor_magic():
    p=load_irdin_project(CASE_PATH)
    speed=np.array([500.0])
    native=run_irdin_synchronous_sweep(p,speed*RPM_TO_RAD_S)
    data=ExperimentalLateralDataset(
        speed,("DE-H",),native.probe_response[[0]],
        measured_critical_speeds_rpm=(1000.0,2000.0),
    )
    result=correlate_lateral_dataset(
        p,data,channel_to_probe={"DE-H":1},
        predicted_critical_speeds_rpm=(990.0,2100.0),
        critical_pairs=((0,0),(1,1)),
    )
    assert [x.delta_rpm for x in result.critical_speeds]==[-10.0,100.0]
    assessed=assess_lateral_correlation(
        result,
        amplitude_relative_limit=1e-12,
        phase_deg_limit=1e-9,
        critical_speed_relative_limit=0.06,
    )
    assert assessed.metadata["status"]=="MODEL_CORRELATED_FOR_LATERAL_SCOPE"


def test_i15_mac_identity_and_orthogonality():
    assert modal_assurance_criterion([1,2j],[1,2j])==pytest.approx(1.0)
    assert modal_assurance_criterion([1,0],[0,1])==pytest.approx(0.0)


def test_i15_requires_complete_distinct_probe_mapping():
    p=load_irdin_project(CASE_PATH)
    data=ExperimentalLateralDataset(np.array([1000.0]),("A","B"),np.ones((2,1),complex))
    with pytest.raises(ValueError,match="every experimental channel"):
        correlate_lateral_dataset(p,data,channel_to_probe={"A":1})
    with pytest.raises(ValueError,match="distinct probe"):
        correlate_lateral_dataset(p,data,channel_to_probe={"A":1,"B":1})
