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
    lib.rd_runup_coeffmap_legacy.argtypes=[
        ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,
        ct.c_int,dptr,ct.c_int,iptr,ct.c_int,dptr,dptr,dptr,ct.c_int,
        dptr,ct.c_double,ct.c_double,ct.c_double,ct.c_double,ct.c_double,ct.c_double,
        ct.c_int,dptr,dptr,dptr,iptr,iptr,iptr,iptr
    ]
    lib.rd_runup_coeffmap_legacy.restype=ct.c_int
    return lib


def configure_static(lib):
    """Additive ABI: old libraries remain usable for legacy analyses only."""
    try:
        fn=lib.rd_static_v1
    except AttributeError as exc:
        raise SolverLibraryError(
            'Static: native rd_static_v1 is unavailable; expected an A1-capable drmrotor library. '
            'Rebuild/install the qualified native library; no Python fallback is available.'
        ) from exc
    dptr=ct.POINTER(ct.c_double)
    fn.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr]+[dptr]*8
    fn.restype=ct.c_int
    return fn

def configure_general_frf(lib):
    import ctypes as ct
    try:
        frf=lib.rd_frf_general_v1;matrix=lib.rd_dynamic_stiffness_v1
    except AttributeError as exc:
        raise SolverLibraryError('General FRF requires rd_frf_general_v1 and rd_dynamic_stiffness_v1; rebuild the native solver. No fallback is available.') from exc
    I=ct.c_int;D=ct.c_double;P=ct.POINTER(D);IP=ct.POINTER(I)
    frf.argtypes=[I,P,I,P,I,P,I,IP,I,P,I,D,P]+[P]*7;frf.restype=I
    matrix.argtypes=[I,P,I,P,I,P,I,IP,P,D,D]+[P]*9;matrix.restype=I
    return frf,matrix


def configure_ucs(lib):
    """A5 versioned UCS ABI. No legacy ABI is modified."""
    try:
        required=lib.rd_ucs_required_v1
        map_fn=lib.rd_ucs_map_v1
        matrix_fn=lib.rd_ucs_matrix_v1
        full_fn=lib.rd_ucs_v1
    except AttributeError as exc:
        raise SolverLibraryError(
            "UCS requires rd_ucs_required_v1/rd_ucs_map_v1/rd_ucs_matrix_v1/rd_ucs_v1; "
            "rebuild the A5 native solver. No Python physics fallback is available."
        ) from exc
    I=ct.c_int;D=ct.c_double;P=ct.POINTER(D);IP=ct.POINTER(I)
    required.argtypes=[I,I,I,I,IP,IP,IP];required.restype=I
    map_fn.argtypes=[I,P,I,P,I,P,I,IP,D,D,I,I,I,I,P,P];map_fn.restype=I
    matrix_fn.argtypes=[I,P,I,P,I,P,I,IP,D,I,P,P,P,P];matrix_fn.restype=I
    full_fn.argtypes=[
        I,P,I,P,I,P,I,IP,D,D,I,I,I,I,P,P,P,I,I,I,
        P,P,IP,P,P,IP,IP,P,P,P,P,P,P
    ];full_fn.restype=I
    return required,map_fn,matrix_fn,full_fn
