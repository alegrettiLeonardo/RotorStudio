from __future__ import annotations
import ctypes as ct, os
from pathlib import Path
class SolverLibraryError(RuntimeError): pass

def _candidate_paths():
    env=os.environ.get("DRMROTOR_LIB")
    if env: yield Path(env)
    here=Path(__file__).resolve()
    for p in here.parents:
        yield p/"libdrmrotor.so"; yield p/"drmrotor.dll"; yield p/"libdrmrotor.dylib"

def load_library(path=None):
    candidates=[Path(path)] if path else list(_candidate_paths())
    for p in candidates:
        if p.exists(): return ct.CDLL(str(p))
    raise SolverLibraryError("libdrmrotor not found; set DRMROTOR_LIB to the built shared library")

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
