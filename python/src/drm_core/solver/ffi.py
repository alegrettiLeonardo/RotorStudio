from __future__ import annotations
import ctypes as ct
import os
from pathlib import Path

class SolverLibraryError(RuntimeError):
    pass

def _candidate_paths():
    env=os.environ.get("DRMROTOR_LIB")
    if env:
        yield Path(env)
    here=Path(__file__).resolve()
    for p in here.parents:
        yield p/"libdrmrotor.so"
        yield p/"drmrotor.dll"
        yield p/"libdrmrotor.dylib"

def load_library(path=None):
    candidates=[Path(path)] if path else list(_candidate_paths())
    for p in candidates:
        if p.exists():
            return ct.CDLL(str(p))
    raise SolverLibraryError("libdrmrotor not found; set DRMROTOR_LIB to the built shared library")

def configure(lib):
    dptr=ct.POINTER(ct.c_double)
    iptr=ct.POINTER(ct.c_int)

    ver=lib.rd_version
    ver.argtypes=[iptr,iptr,iptr]
    ver.restype=ct.c_int

    f=lib.rd_modal_legacy
    f.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,dptr,dptr]
    f.restype=ct.c_int

    ff=lib.rd_modal_full_legacy
    ff.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,ct.c_int,
                 dptr,dptr,dptr,dptr,dptr]
    ff.restype=ct.c_int

    asm=lib.rd_assemble_legacy
    asm.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_double,
                  dptr,dptr,dptr,dptr,dptr,iptr,dptr]
    asm.restype=ct.c_int

    rsp=lib.rd_frequency_response_legacy
    rsp.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,
                  ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,dptr,dptr]
    rsp.restype=ct.c_int

    crit=lib.rd_critical_speeds_legacy
    crit.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,
                   ct.c_int,ct.c_double,ct.c_int,ct.c_int,ct.c_int,ct.c_double,
                   dptr,dptr,iptr,iptr]
    crit.restype=ct.c_int

    critf=lib.rd_critical_speeds_full_legacy
    critf.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,
                    ct.c_int,ct.c_double,ct.c_int,ct.c_int,ct.c_int,ct.c_double,
                    dptr,dptr,iptr,iptr,dptr,dptr]
    critf.restype=ct.c_int

    se=lib.rd_shaft_element_legacy
    se.argtypes=[ct.c_int,ct.c_double,dptr,dptr,dptr,dptr,dptr]
    se.restype=ct.c_int
    return lib
