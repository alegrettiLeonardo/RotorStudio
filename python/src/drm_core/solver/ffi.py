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
    dptr=ct.POINTER(ct.c_double)
    lib.rd_modal_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,dptr,dptr];lib.rd_modal_legacy.restype=ct.c_int
    lib.rd_assemble_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,dptr,dptr,dptr,dptr];lib.rd_assemble_legacy.restype=ct.c_int
    lib.rd_freq_rsp_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,dptr,dptr];lib.rd_freq_rsp_legacy.restype=ct.c_int
    lib.rd_crit_spd_legacy.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,ct.c_int,ct.c_int,ct.c_double,dptr];lib.rd_crit_spd_legacy.restype=ct.c_int
    return lib
