from __future__ import annotations

import ctypes as ct
import os
import sys
from pathlib import Path

from .ffi import SolverLibraryError


_dll_directory_handles = []
_dll_directory_paths = set()


def _prepare_windows_dll_search(library_path: Path) -> None:
    if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
        return
    candidates = [library_path.resolve().parent]
    explicit = os.environ.get("DRMBEARINGS_DLL_DIRS")
    if explicit:
        candidates.extend(Path(p) for p in explicit.split(os.pathsep) if p)
    rotor_dirs = os.environ.get("DRMROTOR_DLL_DIRS")
    if rotor_dirs:
        candidates.extend(Path(p) for p in rotor_dirs.split(os.pathsep) if p)
    candidates.extend(Path(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p)
    for directory in candidates:
        try:
            resolved = directory.resolve()
            is_dir = resolved.is_dir()
        except OSError:
            continue
        key = os.path.normcase(str(resolved))
        if key in _dll_directory_paths or not is_dir:
            continue
        try:
            handle = os.add_dll_directory(str(resolved))
        except OSError:
            continue
        _dll_directory_paths.add(key)
        _dll_directory_handles.append(handle)


def _candidate_paths(rotor_library_path=None):
    env = os.environ.get("DRMBEARINGS_LIB")
    if env:
        yield Path(env)

    rotor_env = rotor_library_path or os.environ.get("DRMROTOR_LIB")
    if rotor_env:
        parent = Path(rotor_env).resolve().parent
        for name in ("libdrmbearings.so", "drmbearings.dll", "libdrmbearings.dll", "libdrmbearings.dylib"):
            yield parent / name

    here = Path(__file__).resolve()
    for p in here.parents:
        yield p / "libdrmbearings.so"
        yield p / "drmbearings.dll"
        yield p / "libdrmbearings.dll"
        yield p / "libdrmbearings.dylib"


def load_bearing_library(path=None, rotor_library_path=None):
    candidates = [Path(path)] if path else list(_candidate_paths(rotor_library_path))
    for candidate in candidates:
        if not candidate.exists():
            continue
        _prepare_windows_dll_search(candidate)
        try:
            return ct.CDLL(str(candidate))
        except OSError as exc:
            raise SolverLibraryError(
                f"found native bearing library at {candidate}, but it could not be loaded "
                f"or one of its dependencies is missing: {exc}"
            ) from exc
    raise SolverLibraryError(
        "libdrmbearings not found; set DRMBEARINGS_LIB or place it beside DRMROTOR_LIB"
    )


def configure_bearing_library(lib):
    dptr = ct.POINTER(ct.c_double)

    lib.rb_interp1_c.argtypes = [
        ct.c_int,
        dptr,
        dptr,
        ct.c_double,
        ct.c_int,
        dptr,
    ]
    lib.rb_interp1_c.restype = ct.c_int

    lib.rb_interp2_c.argtypes = [
        ct.c_int,
        dptr,
        ct.c_int,
        dptr,
        dptr,
        ct.c_double,
        ct.c_double,
        ct.c_int,
        dptr,
    ]
    lib.rb_interp2_c.restype = ct.c_int

    rolling_args = [
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_int,
        ct.c_double,
        ct.c_int,
        ct.c_double,
        dptr,
        dptr,
        dptr,
        dptr,
    ]
    lib.rb_ball_coefficients_c.argtypes = rolling_args
    lib.rb_ball_coefficients_c.restype = ct.c_int
    lib.rb_roller_coefficients_c.argtypes = rolling_args
    lib.rb_roller_coefficients_c.restype = ct.c_int

    lib.rb_cylindrical_coefficients_c.argtypes = [
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
    ]
    lib.rb_cylindrical_coefficients_c.restype = ct.c_int

    lib.rb_sfd_coefficients_c.argtypes = [
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_int,
        ct.c_int,
        dptr,
        dptr,
        dptr,
        dptr,
    ]
    lib.rb_sfd_coefficients_c.restype = ct.c_int

    lib.rb_elliptical_geometry_c.argtypes = [
        ct.c_double,
        ct.c_double,
        dptr,
        dptr,
        dptr,
        dptr,
    ]
    lib.rb_elliptical_geometry_c.restype = ct.c_int

    lib.rb_offset_halves_geometry_c.argtypes = [
        ct.c_double,
        ct.c_double,
        ct.c_double,
        dptr,
        dptr,
        dptr,
        dptr,
    ]
    lib.rb_offset_halves_geometry_c.restype = ct.c_int

    lib.rb_plain_journal_geometry_c.argtypes = [
        ct.c_int,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_int,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
    ]
    lib.rb_plain_journal_geometry_c.restype = ct.c_int

    lib.rb_tilting_pad_prepare_c.argtypes = [
        ct.c_int,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        ct.c_int,
        ct.c_int,
        ct.c_double,
        ct.c_double,
        ct.c_int,
        ct.c_double,
        ct.c_double,
        ct.c_int,
        ct.c_int,
        ct.c_int,
        dptr,
    ]
    lib.rb_tilting_pad_prepare_c.restype = ct.c_int

    lib.rb_reynolds_q4_element_c.argtypes = [
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        dptr,
        dptr,
    ]
    lib.rb_reynolds_q4_element_c.restype = ct.c_int

    lib.rb_pressure_smooth_isoviscous_c.argtypes = [
        ct.c_int,
        ct.c_int,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        dptr,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        dptr,
    ]
    lib.rb_pressure_smooth_isoviscous_c.restype = ct.c_int

    lib.rb_dynamic_reduce_tilts_c.argtypes = [
        ct.c_int,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        ct.c_double,
        dptr,
        ct.c_double,
        ct.c_double,
        dptr,
        dptr,
        dptr,
        dptr,
    ]
    lib.rb_dynamic_reduce_tilts_c.restype = ct.c_int


    lib.rb_plain_journal_isoviscous_c.argtypes = [
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_int,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        ct.c_int,
        ct.c_int,
        ct.c_double,
        ct.c_double,
        ct.c_double,
        ct.c_int,
        ct.c_double,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        dptr,
        ct.POINTER(ct.c_int),
    ]
    lib.rb_plain_journal_isoviscous_c.restype = ct.c_int


    lib.rb_tilting_pad_isoviscous_c.argtypes = [
        ct.c_double, ct.c_double, ct.c_double, ct.c_double, ct.c_double,
        ct.c_double, ct.c_double, ct.c_double, ct.c_double, ct.c_double,
        ct.c_int,
        dptr, dptr, dptr, dptr, dptr, dptr,
        ct.c_int, ct.c_int,
        ct.c_double, ct.c_double, ct.c_double,
        ct.c_int, ct.c_double,
        dptr, dptr, dptr, dptr, dptr, dptr, dptr, dptr,
        ct.POINTER(ct.c_int),
    ]
    lib.rb_tilting_pad_isoviscous_c.restype = ct.c_int


    # Native regular-flooded PlainJournal multiphysics provider:
    # Reynolds + equilibrium + THD + pad deformation/TEHD.
    lib.rb_plain_journal_multiphysics_c.argtypes = (
        [ct.c_double] * 13
        + [ct.c_int, ct.c_int]
        + [ct.c_double] * 10
        + [ct.c_int]
        + [dptr] * 5
        + [ct.c_int] * 4
        + [ct.c_double] * 4
        + [ct.c_int] * 2
        + [ct.c_double] * 2
        + [dptr] * 10
        + [ct.POINTER(ct.c_int)]
    )
    lib.rb_plain_journal_multiphysics_c.restype = ct.c_int

    # Native regular-flooded TiltingPad multiphysics provider.  Rotor spin
    # and whirl/excitation frequency remain independent arguments.
    lib.rb_tilting_pad_multiphysics_c.argtypes = (
        [ct.c_double] * 14
        + [ct.c_int, ct.c_int]
        + [ct.c_double] * 11
        + [ct.c_int]
        + [dptr] * 6
        + [ct.c_int] * 4
        + [ct.c_double] * 4
        + [ct.c_int] * 2
        + [ct.c_double] * 2
        + [dptr] * 11
        + [ct.POINTER(ct.c_int)]
    )
    lib.rb_tilting_pad_multiphysics_c.restype = ct.c_int

    iptr = ct.POINTER(ct.c_int)
    lib.rb_plain_journal_multiphysics_pack_c.argtypes = [
        ct.c_int, dptr, iptr, dptr, dptr, dptr, dptr, dptr, dptr, dptr, dptr
    ]
    lib.rb_plain_journal_multiphysics_pack_c.restype = ct.c_int
    lib.rb_tilting_pad_multiphysics_pack_c.argtypes = [
        ct.c_int, dptr, iptr, dptr, dptr, dptr, dptr, dptr, dptr,
        dptr, dptr, dptr, dptr,
    ]
    lib.rb_tilting_pad_multiphysics_pack_c.restype = ct.c_int
    lib.rb_plain_journal_multiphysics_fields_pack_c.argtypes = [
        ct.c_int, dptr, iptr,
        dptr, dptr, dptr, dptr, dptr,
        dptr, dptr, dptr, dptr, dptr, dptr,
    ]
    lib.rb_plain_journal_multiphysics_fields_pack_c.restype = ct.c_int
    lib.rb_tilting_pad_multiphysics_fields_pack_c.argtypes = [
        ct.c_int, dptr, iptr,
        dptr, dptr, dptr, dptr, dptr, dptr,
        dptr, dptr, dptr, dptr, dptr, dptr, dptr,
    ]
    lib.rb_tilting_pad_multiphysics_fields_pack_c.restype = ct.c_int

    return lib
