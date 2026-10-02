"""I19 API 541 torsional harmonic-response orchestration.

All dynamic solves stay in rd_api541_torsional_response_v1. Python resolves the
explicit I17 excitation references, sums torques sharing one frequency and
reports modal/excitation separation. No API 541 separation percentage is
invented: PASS/FAIL exists only when the caller supplies a project criterion.
"""
from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np

from drm_core.analysis.api541_torsional_contract import (
    API541TorsionalModel,
    validate_api541_torsional_model,
)
from drm_core.solver.api541_torsional_native import (
    API541TorsionalModalResult,
    run_api541_torsional_modes,
)
from drm_core.solver.ffi import SolverLibraryError, load_library


@dataclass(frozen=True)
class API541TorsionalSeparationCheck:
    mode_index: int
    natural_frequency_rad_s: float
    natural_frequency_hz: float
    excitation_frequency_rad_s: float
    excitation_frequency_hz: float
    separation_fraction: float
    required_fraction: float | None
    passed: bool | None


@dataclass(frozen=True)
class API541TorsionalResponseResult:
    modal: API541TorsionalModalResult
    excitation_frequency_rad_s: np.ndarray
    torque_input: np.ndarray
    angle_response_rad: np.ndarray
    connection_torque_nm: np.ndarray
    separation_checks: tuple[API541TorsionalSeparationCheck, ...]
    metadata: dict


def _frequency_rad_s(model: API541TorsionalModel, excitation) -> float:
    if excitation.order is not None:
        return (
            float(excitation.order)
            * float(model.operating_speed_rpm)
            * 2.0
            * math.pi
            / 60.0
        )
    return float(excitation.frequency_hz) * 2.0 * math.pi


def _group_forces(model: API541TorsionalModel) -> tuple[np.ndarray, np.ndarray]:
    frequencies: list[float] = []
    columns: list[np.ndarray] = []
    n = len(model.stations)
    for excitation in model.excitations:
        omega = _frequency_rad_s(model, excitation)
        value = float(excitation.torque_nm) * np.exp(1j * float(excitation.phase_rad))
        target = None
        for i, existing in enumerate(frequencies):
            if math.isclose(omega, existing, rel_tol=1e-12, abs_tol=1e-12):
                target = i
                break
        if target is None:
            frequencies.append(omega)
            columns.append(np.zeros(n, dtype=np.complex128))
            target = len(columns) - 1
        columns[target][int(excitation.station)] += value
    order = np.argsort(np.asarray(frequencies), kind="stable")
    freq = np.asarray([frequencies[i] for i in order], dtype=np.float64)
    force = np.asfortranarray(np.column_stack([columns[i] for i in order]))
    return freq, force


def _native_response(
    model: API541TorsionalModel,
    omega: np.ndarray,
    force: np.ndarray,
    *,
    library_path: str | Path | None,
) -> tuple[np.ndarray, np.ndarray]:
    n = len(model.stations)
    nf = len(omega)
    inertia = np.ascontiguousarray(
        [float(x.polar_inertia_kgm2) for x in model.stations], dtype=np.float64
    )
    stiffness = np.ascontiguousarray(
        [float(x.stiffness_nm_rad) for x in model.connections], dtype=np.float64
    )
    damping = np.ascontiguousarray(
        [float(x.damping_nms_rad) for x in model.connections], dtype=np.float64
    )
    fr = np.asfortranarray(np.asarray(force.real, dtype=np.float64))
    fi = np.asfortranarray(np.asarray(force.imag, dtype=np.float64))
    if fr.shape != (n, nf):
        raise ValueError("I19 force matrix shape mismatch")

    lib = load_library(library_path)
    try:
        fn = lib.rd_api541_torsional_response_v1
    except AttributeError as exc:
        raise SolverLibraryError(
            "I19 requires rd_api541_torsional_response_v1; rebuild the native solver. "
            "No Python torsional-response fallback is available."
        ) from exc

    I = ct.c_int
    D = ct.c_double
    P = ct.POINTER(D)
    fn.argtypes = [I, P, P, P, I, P, P, P, I, I, P, P, P, P, I, I]
    fn.restype = I
    qr = np.full((n, nf), np.nan, dtype=np.float64, order="F")
    qi = np.full_like(qr, np.nan, order="F")
    tr = np.full((n - 1, nf), np.nan, dtype=np.float64, order="F")
    ti = np.full_like(tr, np.nan, order="F")
    ptr = lambda a: a.ctypes.data_as(P)

    status = int(
        fn(
            n,
            ptr(inertia),
            ptr(stiffness),
            ptr(damping),
            nf,
            ptr(np.ascontiguousarray(omega, dtype=np.float64)),
            ptr(fr),
            ptr(fi),
            n,
            n * nf,
            ptr(qr),
            ptr(qi),
            ptr(tr),
            ptr(ti),
            n - 1,
            (n - 1) * nf,
        )
    )
    if status:
        raise SolverLibraryError(f"I19 torsional response returned status={status}")
    if not all(np.isfinite(x).all() for x in (qr, qi, tr, ti)):
        raise SolverLibraryError("I19 torsional response returned NaN/Inf")
    return qr + 1j * qi, tr + 1j * ti


def run_api541_torsional_response(
    model: API541TorsionalModel,
    *,
    required_separation_fraction: float | None = None,
    library_path: str | Path | None = None,
) -> API541TorsionalResponseResult:
    contract = validate_api541_torsional_model(model)
    if required_separation_fraction is not None:
        required = float(required_separation_fraction)
        if not math.isfinite(required) or required < 0.0:
            raise ValueError("required_separation_fraction must be finite and >= 0")
    else:
        required = None

    modal = run_api541_torsional_modes(model, library_path=library_path)
    omega, force = _group_forces(model)
    response, connection_torque = _native_response(
        model, omega, force, library_path=library_path
    )

    checks = []
    scale = max(1.0, float(np.max(modal.frequency_rad_s)))
    rigid_tol = 1024.0 * np.finfo(float).eps * scale
    for mode_index, natural in enumerate(modal.frequency_rad_s):
        natural = float(natural)
        if natural <= rigid_tol:
            continue
        for excitation in omega:
            excitation = float(excitation)
            separation = abs(natural - excitation) / excitation
            passed = None if required is None else bool(separation >= required)
            checks.append(
                API541TorsionalSeparationCheck(
                    mode_index=mode_index,
                    natural_frequency_rad_s=natural,
                    natural_frequency_hz=natural / (2.0 * math.pi),
                    excitation_frequency_rad_s=excitation,
                    excitation_frequency_hz=excitation / (2.0 * math.pi),
                    separation_fraction=float(separation),
                    required_fraction=required,
                    passed=passed,
                )
            )

    return API541TorsionalResponseResult(
        modal=modal,
        excitation_frequency_rad_s=omega,
        torque_input=force,
        angle_response_rad=response,
        connection_torque_nm=connection_torque,
        separation_checks=tuple(checks),
        metadata={
            **contract,
            "status": "PASS_I19_NATIVE_TORSIONAL_HARMONIC_RESPONSE",
            "native_solver": "rd_api541_torsional_response_v1",
            "required_separation_fraction": required,
            "separation_acceptance_evaluated": required is not None,
            "stress_fatigue_qualified": False,
            "transient_response_qualified": False,
            "whole_api541_compliance_claim": False,
        },
    )


__all__ = [
    "API541TorsionalSeparationCheck",
    "API541TorsionalResponseResult",
    "run_api541_torsional_response",
]
