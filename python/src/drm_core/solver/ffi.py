from __future__ import annotations

import ctypes as ct
import os
import sys
from pathlib import Path


class SolverLibraryError(RuntimeError):
    pass


_dll_directory_handles = []
_dll_directory_paths = set()


def _candidate_paths():
    env = os.environ.get("DRMROTOR_LIB")
    if env:
        yield Path(env)

    here = Path(__file__).resolve()
    for p in here.parents:
        yield p / "libdrmrotor.so"
        yield p / "drmrotor.dll"
        yield p / "libdrmrotor.dll"
        yield p / "libdrmrotor.dylib"


def _prepare_windows_dll_search(library_path: Path) -> None:
    """Register dependency search directories for ctypes on modern Windows.

    Python 3.8+ does not rely on PATH alone for dependent DLL resolution in
    ctypes.  Keep AddDllDirectory handles alive for the process lifetime.
    """

    if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
        return

    candidates = [library_path.resolve().parent]

    explicit = os.environ.get("DRMROTOR_DLL_DIRS")
    if explicit:
        candidates.extend(Path(p) for p in explicit.split(os.pathsep) if p)

    path_env = os.environ.get("PATH", "")
    candidates.extend(Path(p) for p in path_env.split(os.pathsep) if p)

    for directory in candidates:
        try:
            resolved = directory.resolve()
            is_dir = resolved.is_dir()
        except OSError:
            # PATH on managed/corporate Windows machines may contain locations
            # that exist but cannot be stat'ed by the current user.  A single
            # inaccessible entry must not prevent registration of valid solver
            # dependency directories such as MSYS2 UCRT64.
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


def load_library(path=None):
    candidates = [Path(path)] if path else list(_candidate_paths())

    for p in candidates:
        if not p.exists():
            continue

        _prepare_windows_dll_search(p)

        try:
            return ct.CDLL(str(p))
        except OSError as exc:
            raise SolverLibraryError(
                f"found solver library at {p}, but Windows could not load it "
                f"or one of its dependencies: {exc}. "
                "Set DRMROTOR_DLL_DIRS to dependency directories if needed."
            ) from exc

    raise SolverLibraryError(
        "libdrmrotor not found; set DRMROTOR_LIB to the built shared library"
    )


def configure(lib):
    dptr=ct.POINTER(ct.c_double); iptr=ct.POINTER(ct.c_int)
    lib.rd_modal_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,dptr,dptr];lib.rd_modal_legacy.restype=ct.c_int
    lib.rd_modal_legacy_vectors.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,dptr,dptr,dptr,dptr,dptr];lib.rd_modal_legacy_vectors.restype=ct.c_int
    lib.rd_assemble_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,dptr,dptr,dptr,dptr];lib.rd_assemble_legacy.restype=ct.c_int
    lib.rd_bearings_legacy.argtypes=[ct.c_int,ct.c_int,dptr,ct.c_double,dptr,dptr,dptr,iptr,dptr];lib.rd_bearings_legacy.restype=ct.c_int
    lib.rd_freq_rsp_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,dptr,dptr];lib.rd_freq_rsp_legacy.restype=ct.c_int
    lib.rd_freq_aux_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,dptr,ct.c_double,dptr,dptr];lib.rd_freq_aux_legacy.restype=ct.c_int
    lib.rd_freq_fdn_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,dptr,dptr,dptr];lib.rd_freq_fdn_legacy.restype=ct.c_int
    lib.rd_crit_spd_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,ct.c_int,ct.c_int,ct.c_double,dptr];lib.rd_crit_spd_legacy.restype=ct.c_int
    lib.rd_crit_spd_legacy_ex.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,ct.c_int,ct.c_int,ct.c_double,ct.c_int,dptr,ct.c_int,dptr,iptr,iptr];lib.rd_crit_spd_legacy_ex.restype=ct.c_int
    lib.rd_coax_modal_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,dptr,dptr,dptr,dptr];lib.rd_coax_modal_legacy.restype=ct.c_int
    lib.rd_coax_freq_rsp_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,dptr,dptr];lib.rd_coax_freq_rsp_legacy.restype=ct.c_int
    lib.rd_asym_assemble_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,dptr,dptr,dptr,dptr,dptr,dptr];lib.rd_asym_assemble_legacy.restype=ct.c_int
    lib.rd_bearasym_legacy.argtypes=[ct.c_int,ct.c_int,dptr,dptr,dptr,dptr,iptr];lib.rd_bearasym_legacy.restype=ct.c_int
    lib.rd_asym_modal_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,ct.c_int,dptr,dptr,dptr,dptr];lib.rd_asym_modal_legacy.restype=ct.c_int
    lib.rd_asym_freq_rsp_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,dptr];lib.rd_asym_freq_rsp_legacy.restype=ct.c_int
    lib.rd_time_fdn_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,dptr,ct.c_double,ct.c_double,ct.c_int,ct.c_int,ct.c_double,ct.c_double,ct.c_double,ct.c_double,dptr,dptr,dptr,iptr,dptr,iptr,iptr];lib.rd_time_fdn_legacy.restype=ct.c_int
    lib.rd_runup_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,dptr,ct.c_double,ct.c_double,ct.c_int,ct.c_double,ct.c_double,ct.c_double,ct.c_double,ct.c_int,dptr,dptr,dptr,iptr,iptr,dptr,iptr,iptr];lib.rd_runup_legacy.restype=ct.c_int
    return lib
