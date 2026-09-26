from __future__ import annotations

import threading
import time

import numpy as np

from drm_core import PlainJournalPhysicsBearing, TiltingPadPhysicsBearing
from drm_core.solver.bearings_backend import (
    AdvancedBearingBackend,
    BearingCancelledError,
)


def _plain(*, expensive=False):
    return PlainJournalPhysicsBearing(
        node=1,
        weight_n=112814.90696191376,
        journal_diameter_m=0.3999992,
        radial_clearance_m=0.000194564,
        oil_viscosity_pa_s=0.01901574061455835,
        pivot_angle_rad=(np.pi / 2.0, 3.0 * np.pi / 2.0),
        pad_arc_rad=(3.07177948351002, 3.07177948351002),
        pad_axial_length_m=(0.263144, 0.263144),
        preload=(0.0, 0.0),
        offset=(0.5, 0.5),
        total_e_x_film=20 if expensive else 8,
        total_e_z_film=10 if expensive else 4,
        total_e_y_pad=6 if expensive else 4,
        total_e_y_film=6 if expensive else 4,
        xj_ratio_initial=0.15,
        yj_ratio_initial=-0.2,
        force_tolerance=5e-3,
        thermal_type="adiabatic" if expensive else None,
        deform_type=None,
        oil_supply_temperature_k=323.0,
        lubricant_density_kg_m3=854.9516,
        lubricant_cp_j_kgk=1951.5015,
        lubricant_conductivity_w_mk=0.15,
        viscosity2_pa_s=0.0077152334111,
        temperature1_k=322.9833333333,
        temperature2_k=352.9833333333,
        relax_temperature=0.35,
        max_iterations=100 if expensive else 60,
        outer_iterations=100 if expensive else 12,
    )


def _tilting():
    return TiltingPadPhysicsBearing(
        node=1,
        weight_n=112814.90696191376,
        journal_diameter_m=0.3999992,
        radial_clearance_m=0.000194564,
        oil_viscosity_pa_s=0.01901574061455835,
        pad_thickness_m=0.149614636,
        pad_density_kg_m3=7835.631544657211,
        pivot_angle_rad=(
            0.9424777960769379,
            2.199114857512855,
            3.4557519189487724,
            4.71238898038469,
            5.969026041820607,
        ),
        pad_arc_rad=(1.0471975511965976,) * 5,
        pad_axial_length_m=(0.263144,) * 5,
        preload=(0.3,) * 5,
        offset=(0.5,) * 5,
        k_rotate_nm_rad=(0.0,) * 5,
        total_e_x_film=8,
        total_e_z_film=4,
        total_e_y_pad=4,
        total_e_y_film=4,
        xj_ratio_initial=0.15,
        yj_ratio_initial=-0.2,
        force_tolerance=5e-3,
    )


def _assert_field_contract(payload, bearing):
    evaluation = payload["evaluation"]
    nx = bearing.total_e_x_film
    nz = bearing.total_e_z_film
    n = len(bearing.pivot_angle_rad)
    assert evaluation.details["qualification"] == "ROSS_PARITY_PASS_B12"
    assert evaluation.details["field_contract"] == "B14-v2"
    assert payload["pressure_field_pa"].shape == (n, nx + 1, nz + 1)
    assert payload["temperature_field_k"].shape == (n, nx + 1, nz + 1)
    assert payload["film_thickness_field_m"].shape == (n, nx + 1, nz + 1)
    assert payload["deformation_field_m"].shape == (n, nx + 1)
    assert payload["theta_rad"].shape == (n, nx + 1)
    assert payload["axial_position_m"].shape == (n, nz + 1)
    np.testing.assert_array_equal(payload["pad_index"], np.arange(1, n + 1))
    assert payload["pad_load_n"].shape == (n,)
    for key in (
        "pressure_field_pa",
        "temperature_field_k",
        "film_thickness_field_m",
        "deformation_field_m",
        "theta_rad",
        "axial_position_m",
        "pad_load_n",
    ):
        assert np.isfinite(payload[key]).all(), key
    assert np.min(payload["film_thickness_field_m"]) > 0.0
    assert np.max(payload["pressure_field_pa"]) > 0.0
    assert np.all(payload["pad_load_n"] >= 0.0)
    assert payload["convergence"]["stage"] == "completed"
    assert payload["convergence"]["percent"] == 100.0


def test_b14_plain_native_full_field_contract_uses_backend_film_thickness():
    bearing = _plain()
    backend = AdvancedBearingBackend()
    payload = backend.evaluate_fields(
        bearing,
        speed_rad_s=94.24777960769379,
        frequency_rad_s=94.24777960769379,
    )
    _assert_field_contract(payload, bearing)

    # Film thickness is a direct native return.  It must have spatial
    # circumferential variation for this eccentric equilibrium and cannot be a
    # GUI-side constant reconstructed from clearance.
    h = payload["film_thickness_field_m"]
    assert float(np.ptp(h)) > 1.0e-8


def test_b14_tilting_pad_native_field_contract_preserves_pad_metadata():
    bearing = _tilting()
    backend = AdvancedBearingBackend()
    payload = backend.evaluate_fields(
        bearing,
        speed_rad_s=94.24777960769379,
        frequency_rad_s=47.123889803846895,
    )
    _assert_field_contract(payload, bearing)
    tilt = np.asarray(payload["evaluation"].details["tilt_angle_rad"], dtype=float)
    assert tilt.shape == (5,)
    assert np.isfinite(tilt).all()


def test_b14_cooperative_native_cancel_returns_no_partial_payload():
    backend = AdvancedBearingBackend()
    bearing = _plain(expensive=True)
    backend.reset_job_control()
    result = {}
    errors = []

    def solve():
        try:
            result["payload"] = backend.evaluate_fields(
                bearing,
                speed_rad_s=94.24777960769379,
                frequency_rad_s=94.24777960769379,
                reset_job_control=False,
            )
        except Exception as exc:  # asserted below
            errors.append(exc)

    thread = threading.Thread(target=solve, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10.0
    seen_running = False
    while time.monotonic() < deadline and thread.is_alive():
        progress = backend.job_progress()
        if progress.stage_code > 0:
            seen_running = True
            backend.request_cancel()
            break
        time.sleep(0.005)

    thread.join(timeout=20.0)
    assert seen_running, "native solve never exposed a cooperative progress stage"
    assert not thread.is_alive(), "native solver did not leave a safe point after cancellation"
    assert "payload" not in result, "cancelled native solve published partial fields"
    assert errors and isinstance(errors[0], BearingCancelledError), errors
    assert backend.job_progress().cancel_requested is True


def test_b14_b12_fields_abi_remains_exported():
    backend = AdvancedBearingBackend()
    for symbol in (
        "rb_plain_journal_multiphysics_fields_pack_c",
        "rb_tilting_pad_multiphysics_fields_pack_c",
        "rb_plain_journal_multiphysics_fields_v2_pack_c",
        "rb_tilting_pad_multiphysics_fields_v2_pack_c",
    ):
        assert hasattr(backend.lib, symbol), symbol
