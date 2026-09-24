import numpy as np

def _return(x):
    a=np.asarray(x); return float(a) if a.ndim==0 else a

def rpm_to_rad_s(rpm): return _return(np.asarray(rpm,dtype=float)*2*np.pi/60.0)
def rad_s_to_rpm(w): return _return(np.asarray(w,dtype=float)*60.0/(2*np.pi))
def mm_to_m(x): return _return(np.asarray(x,dtype=float)*1e-3)
def m_to_mm(x): return _return(np.asarray(x,dtype=float)*1e3)
def mpa_to_pa(x): return _return(np.asarray(x,dtype=float)*1e6)
def gpa_to_pa(x): return _return(np.asarray(x,dtype=float)*1e9)
def kn_to_n(x): return _return(np.asarray(x,dtype=float)*1e3)
def n_to_kn(x): return _return(np.asarray(x,dtype=float)*1e-3)
def hz_to_rad_s(x): return _return(np.asarray(x,dtype=float)*2*np.pi)
def rad_s_to_hz(x): return _return(np.asarray(x,dtype=float)/(2*np.pi))
def deg_to_rad(x): return _return(np.deg2rad(np.asarray(x,dtype=float)))
def rad_to_deg(x): return _return(np.rad2deg(np.asarray(x,dtype=float)))
