from __future__ import annotations

import ctypes as ct
import json
from pathlib import Path

import numpy as np
import pytest

from drm_core.solver.bearings_backend import AdvancedBearingBackend


ROSS_SHA = "6320eab9f890f1b3cc1710d508b446fe063ca68d"
REF_DIR = Path(__file__).resolve().parents[2] / "tests" / "reference" / "ross_6320eab9"

THERMAL = {None: 0, "adiabatic": 1, "full": 2}
DEFORM = {None: 0, "pad_mechanical": 1, "pad_mechanical_thermal": 2}


def _load(name: str):
    meta = json.loads((REF_DIR / f"{name}.json").read_text(encoding="utf-8"))
    fields = np.load(REF_DIR / meta["field_file"])
    return meta, fields


def _ptr(a: np.ndarray):
    return a.ctypes.data_as(ct.POINTER(ct.c_double))


def _iptr(a: np.ndarray):
    return a.ctypes.data_as(ct.POINTER(ct.c_int))


def _scalar(value, default=0.0):
    if value is None:
        return float(default)
    if isinstance(value, (list, tuple)):
        return float(value[0]) if value else float(default)
    return float(value)


def _plain_native(inp: dict):
    backend = AdvancedBearingBackend()
    n = len(inp["pivot_angle"])
    arrays = [
        np.ascontiguousarray(inp[key], dtype=np.float64)
        for key in ("pivot_angle", "pad_arc", "pad_axial_length", "preload", "offset")
    ]
    supply = float(inp["oil_supply_temperature"])
    rcfg = np.ascontiguousarray(
        [
            _scalar(inp["frequency"]),
            float(inp["weight"]),
            float(inp["fxs_load"]),
            float(inp["fys_load"]),
            float(inp["journal_diameter"]),
            float(inp["radial_clearance"]),
            float(inp["viscosity1"]),
            float(inp["viscosity2"]),
            float(inp["temp1"]),
            float(inp["temp2"]),
            float(inp["lube_density"]),
            float(inp["lube_cp"]),
            float(inp["lube_conduct"]),
            float(inp["pad_thickness"]),
            float(inp["pad_conductivity"]),
            float(inp["pad_young"]),
            float(inp["pad_poisson"]),
            float(inp["pad_expansion"]),
            supply,
            float(inp["journal_temperature"]),
            float(inp.get("t_ambient", supply)),
            float(inp["edges_convection"]),
            _scalar(inp["pad_convection"]),
            float(inp["xj"]),
            float(inp["yj"]),
            float(inp["relax_p"]),
            float(inp["relax_t"]),
            1.0e-5,
            1.0e-3,
        ],
        dtype=np.float64,
    )
    icfg = np.ascontiguousarray(
        [
            THERMAL[inp["thermal_type"]],
            DEFORM[inp["deform_type"]],
            int(inp["total_e_x_film"]),
            int(inp["total_e_z_film"]),
            int(inp["total_e_y_pad"]),
            int(inp["total_e_y_film"]),
            120,
            80,
        ],
        dtype=np.int32,
    )
    nx, nz = int(icfg[2]), int(icfg[3])
    nn = (nx + 1) * (nz + 1)
    K = np.empty(4, dtype=np.float64)
    C = np.empty(4, dtype=np.float64)
    summary = np.empty(9, dtype=np.float64)
    pressure = np.empty(n * nn, dtype=np.float64)
    temperature = np.empty(n * nn, dtype=np.float64)
    deformation = np.empty(n * (nx + 1), dtype=np.float64)
    status = backend.lib.rb_plain_journal_multiphysics_fields_pack_c(
        n,
        _ptr(rcfg),
        _iptr(icfg),
        *(_ptr(a) for a in arrays),
        _ptr(K),
        _ptr(C),
        _ptr(summary),
        _ptr(pressure),
        _ptr(temperature),
        _ptr(deformation),
    )
    assert status == 0, f"PlainJournal native B12 solve returned status={status}"
    return {
        "K": K.reshape((2, 2), order="F"),
        "C": C.reshape((2, 2), order="F"),
        "summary": summary,
        "pressure": pressure.reshape((n, nx + 1, nz + 1)),
        "temperature": temperature.reshape((n, nx + 1, nz + 1)),
        "deformation": deformation.reshape((n, nx + 1)),
    }


def _tilting_native(inp: dict, whirl_rad_s: float):
    backend = AdvancedBearingBackend()
    n = len(inp["pivot_angle"])
    arrays = [
        np.ascontiguousarray(inp[key], dtype=np.float64)
        for key in (
            "pivot_angle",
            "pad_arc",
            "pad_axial_length",
            "preload",
            "offset",
            "k_rotate",
        )
    ]
    supply = float(inp["oil_supply_temperature"])
    rcfg = np.ascontiguousarray(
        [
            _scalar(inp["frequency"]),
            float(whirl_rad_s),
            float(inp["weight"]),
            float(inp["fxs_load"]),
            float(inp["fys_load"]),
            float(inp["journal_diameter"]),
            float(inp["radial_clearance"]),
            float(inp["viscosity1"]),
            float(inp["viscosity2"]),
            float(inp["temp1"]),
            float(inp["temp2"]),
            float(inp["lube_density"]),
            float(inp["lube_cp"]),
            float(inp["lube_conduct"]),
            float(inp["pad_thickness"]),
            float(inp["pad_density"]),
            float(inp["pad_conductivity"]),
            float(inp["pad_young"]),
            float(inp["pad_poisson"]),
            float(inp["pad_expansion"]),
            supply,
            float(inp["journal_temperature"]),
            float(inp.get("t_ambient", supply)),
            float(inp["edges_convection"]),
            _scalar(inp["pad_convection"]),
            float(inp["xj"]),
            float(inp["yj"]),
            float(inp["relax_p"]),
            float(inp["relax_t"]),
            1.0e-5,
            1.0e-3,
        ],
        dtype=np.float64,
    )
    icfg = np.ascontiguousarray(
        [
            THERMAL[inp["thermal_type"]],
            DEFORM[inp["deform_type"]],
            int(inp["total_e_x_film"]),
            int(inp["total_e_z_film"]),
            int(inp["total_e_y_pad"]),
            int(inp["total_e_y_film"]),
            120,
            80,
        ],
        dtype=np.int32,
    )
    nx, nz = int(icfg[2]), int(icfg[3])
    nn = (nx + 1) * (nz + 1)
    tilt = np.empty(n, dtype=np.float64)
    K = np.empty(4, dtype=np.float64)
    C = np.empty(4, dtype=np.float64)
    summary = np.empty(9, dtype=np.float64)
    pressure = np.empty(n * nn, dtype=np.float64)
    temperature = np.empty(n * nn, dtype=np.float64)
    deformation = np.empty(n * (nx + 1), dtype=np.float64)
    status = backend.lib.rb_tilting_pad_multiphysics_fields_pack_c(
        n,
        _ptr(rcfg),
        _iptr(icfg),
        *(_ptr(a) for a in arrays),
        _ptr(tilt),
        _ptr(K),
        _ptr(C),
        _ptr(summary),
        _ptr(pressure),
        _ptr(temperature),
        _ptr(deformation),
    )
    assert status == 0, f"TiltingPad native B12 solve returned status={status}"
    return {
        "K": K.reshape((2, 2), order="F"),
        "C": C.reshape((2, 2), order="F"),
        "tilt": tilt,
        "summary": summary,
        "pressure": pressure.reshape((n, nx + 1, nz + 1)),
        "temperature": temperature.reshape((n, nx + 1, nz + 1)),
        "deformation": deformation.reshape((n, nx + 1)),
    }


def _relative_l2(actual, expected):
    a = np.asarray(actual, dtype=float)
    e = np.asarray(expected, dtype=float)
    denom = max(float(np.linalg.norm(e.ravel())), np.finfo(float).tiny)
    return float(np.linalg.norm((a - e).ravel()) / denom)


def _assert_scalar_and_matrices(native, golden, *, thermal=False, deformation=False):
    o = golden["outputs"]
    s = native["summary"]
    np.testing.assert_allclose(s[0], o["xj_ratio"], rtol=0.0, atol=1.0e-5)
    np.testing.assert_allclose(s[1], o["yj_ratio"], rtol=0.0, atol=1.0e-5)
    np.testing.assert_allclose(s[4], o["p_max_pa"], rtol=1.0e-4, atol=1.0)
    np.testing.assert_allclose(native["K"], o["K_n_m"], rtol=1.0e-3, atol=1.0)
    np.testing.assert_allclose(native["C"], o["C_n_s_m"], rtol=1.0e-3, atol=1.0)
    if thermal:
        np.testing.assert_allclose(s[5], o["t_max_k"], rtol=1.0e-4, atol=1.0e-3)
        np.testing.assert_allclose(s[6], o["t_out_bulk_k"], rtol=1.0e-4, atol=1.0e-3)
    if deformation:
        np.testing.assert_allclose(
            s[7], o["deformation_max_m"], rtol=1.0e-3, atol=1.0e-10
        )


def test_b12_reference_authority_is_frozen():
    manifest = json.loads((REF_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["ross_commit"] == ROSS_SHA
    assert set(manifest["cases"]) == {
        "plain_journal_isoviscous",
        "plain_journal_tehd",
        "tilting_pad_synchronous_thd",
        "tilting_pad_asynchronous",
    }


def test_b12_plain_journal_isoviscous_parity():
    golden, fields = _load("plain_journal_isoviscous")
    native = _plain_native(golden["inputs"])
    _assert_scalar_and_matrices(native, golden)
    assert _relative_l2(native["pressure"], fields["pressure_field_pa"]) <= 1.0e-2


def test_b12_plain_journal_tehd_parity():
    golden, fields = _load("plain_journal_tehd")
    native = _plain_native(golden["inputs"])
    _assert_scalar_and_matrices(native, golden, thermal=True, deformation=True)
    assert _relative_l2(native["pressure"], fields["pressure_field_pa"]) <= 1.0e-2
    assert _relative_l2(native["temperature"], fields["temperature_field_k"]) <= 1.0e-3


def test_b12_tilting_pad_synchronous_thd_parity():
    golden, fields = _load("tilting_pad_synchronous_thd")
    native = _tilting_native(golden["inputs"], golden["case"]["whirl_rad_s"])
    _assert_scalar_and_matrices(native, golden, thermal=True)
    np.testing.assert_allclose(
        native["tilt"], golden["outputs"]["tilt_angle_rad"], rtol=1.0e-3, atol=1.0e-8
    )
    assert _relative_l2(native["pressure"], fields["pressure_field_pa"]) <= 1.0e-2
    assert _relative_l2(native["temperature"], fields["temperature_field_k"]) <= 1.0e-3


def test_b12_tilting_pad_asynchronous_omega_sweep_parity():
    golden, _fields = _load("tilting_pad_asynchronous")
    native_k = []
    native_c = []
    for point in golden["points"]:
        native = _tilting_native(point["inputs"], point["case"]["whirl_rad_s"])
        _assert_scalar_and_matrices(native, point)
        native_k.append(native["K"])
        native_c.append(native["C"])

    # Explicitly guard against an implementation that collapses omega to Omega.
    assert not np.allclose(native_k[0], native_k[-1], rtol=1.0e-6, atol=1.0)
    assert not np.allclose(native_c[0], native_c[-1], rtol=1.0e-6, atol=1.0)
