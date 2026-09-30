"""Internal B1 element interface: type checks, buffers and versioned native ABI.

All element physics is Fortran. This module does not import ROSS, use linear
algebra to construct matrices, or fall back if the native kernel fails.
SI inputs; node order (x,y,z,alpha,beta,theta). Not a global 6-DOF rotor API.
"""
from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass
import math
from numbers import Integral, Real
from pathlib import Path

import numpy as np

from .ffi import SolverLibraryError, load_library

NODE_DOF_ORDER = ("x", "y", "z", "alpha", "beta", "theta")
STATUS_NAMES = {
    0: "SUCCESS", 10: "INVALID_INPUT", 11: "INVALID_FLAG_OR_ENUM",
    12: "INVALID_DIMENSION", 13: "INSUFFICIENT_CAPACITY", 14: "NONFINITE_RESULT",
}


class SixDofInputError(ValueError):
    def __init__(self, status: int, context: str):
        self.status = status
        super().__init__(f"B1 {STATUS_NAMES.get(status, 'UNKNOWN_STATUS')} ({status}): {context}")


class SixDofComputationError(RuntimeError):
    def __init__(self, status: int, context: str):
        self.status = status
        super().__init__(f"B1 {STATUS_NAMES.get(status, 'UNKNOWN_STATUS')} ({status}): {context}. No Python fallback was used.")


@dataclass(frozen=True)
class ShaftMatrices:
    M: np.ndarray
    K: np.ndarray
    G: np.ndarray
    Kst: np.ndarray


@dataclass(frozen=True)
class DiskMatrices:
    M: np.ndarray
    G: np.ndarray
    Kdt: np.ndarray


def _real(name: str, value: Real) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise SixDofInputError(10, f"{name}={value!r}; expected a finite real SI scalar, not a vector, string, boolean or complex value")
    try:
        result = float(value)
    except (ValueError, OverflowError) as error:
        raise SixDofInputError(10, f"{name} cannot be represented as float64") from error
    if not math.isfinite(result):
        raise SixDofInputError(10, f"{name}={value!r}; expected a finite real SI scalar")
    return result


def _flag(name: str, value: bool | int) -> int:
    if not isinstance(value, (bool, np.bool_, Integral)) or value not in (0, 1):
        raise SixDofInputError(11, f"{name}={value!r}; expected bool or integer 0/1")
    return int(value)


def _functions(library_path: str | Path | None = None):
    lib = load_library(library_path)
    try:
        shaft = lib.rd_shaft_6dof_matrices_v1
        disk = lib.rd_disk_6dof_matrices_v1
    except AttributeError as error:
        raise SolverLibraryError("B1 requires rd_shaft_6dof_matrices_v1 and rd_disk_6dof_matrices_v1. Build/install the B1 native library; no fallback is available.") from error
    D, I, P = ct.c_double, ct.c_int, ct.POINTER(ct.c_double)
    shaft.argtypes = [D]*10 + [I]*4 + [P, I, I]*4
    disk.argtypes = [D]*3 + [P, I, I]*3
    shaft.restype = I
    disk.restype = I
    return lib, shaft, disk


def _buffers(n: int, count: int):
    # NaNs make incomplete writes observable; they are never returned on failure.
    arrays = [np.full((n, n), np.nan, dtype=np.float64, order="F") for _ in range(count)]
    args = []
    for array in arrays:
        args.extend([array.ctypes.data_as(ct.POINTER(ct.c_double)), n, array.size])
    return arrays, args


def _status(status: int, context: str) -> None:
    if status in (10, 11, 12, 13):
        raise SixDofInputError(status, context)
    if status:
        raise SixDofComputationError(status, context)


def shaft_matrices(*, L: Real, idl: Real, odl: Real, idr: Real, odr: Real,
                   rho: Real, E: Real, G_s: Real, axial_force: Real = 0.0,
                   torque: Real = 0.0, shear_effects: bool | int = True,
                   rotary_inertia: bool | int = True, gyroscopic: bool | int = True,
                   shear_method: str = "cowper", library_path: str | Path | None = None) -> ShaftMatrices:
    values = {"L": L, "idl": idl, "odl": odl, "idr": idr, "odr": odr,
              "rho": rho, "E": E, "G_s": G_s, "axial_force": axial_force, "torque": torque}
    scalars = [_real(name, value) for name, value in values.items()]
    flags = [_flag("shear_effects", shear_effects), _flag("rotary_inertia", rotary_inertia), _flag("gyroscopic", gyroscopic)]
    if not isinstance(shear_method, str) or shear_method.lower() not in ("cowper", "hutchinson"):
        raise SixDofInputError(11, f"shear_method={shear_method!r}; expected cowper or hutchinson")
    method = {"cowper": 1, "hutchinson": 2}[shear_method.lower()]
    lib, fn, _ = _functions(library_path)
    arrays, args = _buffers(12, 4)
    result = int(fn(*scalars, *flags, method, *args))
    _status(result, f"shaft inputs={values!r}; require L,rho,E,G_s>0 and 0<=inner<outer at both ends")
    if not all(np.isfinite(a).all() for a in arrays):
        raise SixDofComputationError(14, "native shaft reported success but an output is nonfinite")
    return ShaftMatrices(*arrays)


def disk_matrices(*, m: Real, Id: Real, Ip: Real,
                  library_path: str | Path | None = None) -> DiskMatrices:
    values = {"m": m, "Id": Id, "Ip": Ip}
    scalars = [_real(name, value) for name, value in values.items()]
    lib, _, fn = _functions(library_path)
    arrays, args = _buffers(6, 3)
    result = int(fn(*scalars, *args))
    _status(result, f"disk inputs={values!r}; require m,Id,Ip>0 for the declared nondegenerate rigid-disk scope")
    if not all(np.isfinite(a).all() for a in arrays):
        raise SixDofComputationError(14, "native disk reported success but an output is nonfinite")
    return DiskMatrices(*arrays)
