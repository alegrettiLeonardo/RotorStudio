"""I18 native API 541 torsional matrices and free-mode analysis."""
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
from .ffi import SolverLibraryError, load_library


@dataclass(frozen=True)
class API541TorsionalModalResult:
    M: np.ndarray
    C: np.ndarray
    K: np.ndarray
    frequency_rad_s: np.ndarray
    frequency_hz: np.ndarray
    modes: np.ndarray
    metadata: dict


def run_api541_torsional_modes(
    model: API541TorsionalModel,
    *,
    library_path: str | Path | None = None,
) -> API541TorsionalModalResult:
    contract = validate_api541_torsional_model(model)
    n = len(model.stations)
    inertia = np.ascontiguousarray(
        [float(x.polar_inertia_kgm2) for x in model.stations],
        dtype=np.float64,
    )
    stiffness = np.ascontiguousarray(
        [float(x.stiffness_nm_rad) for x in model.connections],
        dtype=np.float64,
    )
    damping = np.ascontiguousarray(
        [float(x.damping_nms_rad) for x in model.connections],
        dtype=np.float64,
    )

    lib = load_library(library_path)
    try:
        fn = lib.rd_api541_torsional_modes_v1
    except AttributeError as exc:
        raise SolverLibraryError(
            "I18 requires rd_api541_torsional_modes_v1; rebuild the native solver. "
            "No Python torsional-eigenvalue fallback is available."
        ) from exc

    I = ct.c_int
    D = ct.c_double
    P = ct.POINTER(D)
    fn.argtypes = [I, P, P, P, P, P, P, I, I, P, P, I, I]
    fn.restype = I

    matrices = [
        np.full((n, n), np.nan, dtype=np.float64, order="F")
        for _ in range(3)
    ]
    freq = np.full(n, np.nan, dtype=np.float64)
    modes = np.full((n, n), np.nan, dtype=np.float64, order="F")

    ptr = lambda a: a.ctypes.data_as(P)
    status = int(
        fn(
            n,
            ptr(inertia),
            ptr(stiffness),
            ptr(damping),
            ptr(matrices[0]),
            ptr(matrices[1]),
            ptr(matrices[2]),
            n,
            n * n,
            ptr(freq),
            ptr(modes),
            n,
            n * n,
        )
    )
    if status:
        raise SolverLibraryError(f"I18 torsional native solver returned status={status}")
    if not all(np.isfinite(x).all() for x in [*matrices, freq, modes]):
        raise SolverLibraryError("I18 torsional native solver returned NaN/Inf")
    if np.any(freq < 0.0):
        raise SolverLibraryError("I18 torsional native solver returned negative frequencies")

    return API541TorsionalModalResult(
        M=matrices[0],
        C=matrices[1],
        K=matrices[2],
        frequency_rad_s=freq,
        frequency_hz=freq / (2.0 * math.pi),
        modes=modes,
        metadata={
            **contract,
            "status": "PASS_I18_NATIVE_TORSIONAL_MODAL",
            "native_solver": "rd_api541_torsional_modes_v1",
            "rigid_body_mode_retained": True,
            "forced_response_qualified": False,
            "transient_response_qualified": False,
        },
    )


__all__ = ["API541TorsionalModalResult", "run_api541_torsional_modes"]
