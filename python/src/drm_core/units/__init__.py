import numpy as np

def _return(x):
    a=np.asarray(x)
    return float(a) if a.ndim==0 else a

def rpm_to_rad_s(rpm): return _return(np.asarray(rpm,dtype=float)*2*np.pi/60.0)
def rad_s_to_rpm(w): return _return(np.asarray(w,dtype=float)*60.0/(2*np.pi))

# Stage 2 display-unit adapters.  Canonical domain/SolverFacade values remain SI.
# These helpers deliberately live in drm_core so UI widgets never scatter
# conversion constants through presentation code.
def mm_to_m(mm): return _return(np.asarray(mm,dtype=float)*1.0e-3)
def m_to_mm(m): return _return(np.asarray(m,dtype=float)*1.0e3)
def mpa_to_pa(mpa): return _return(np.asarray(mpa,dtype=float)*1.0e6)
def pa_to_mpa(pa): return _return(np.asarray(pa,dtype=float)*1.0e-6)
