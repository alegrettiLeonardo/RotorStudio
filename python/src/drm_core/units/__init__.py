import numpy as np

def _return(x):
    a=np.asarray(x)
    return float(a) if a.ndim==0 else a

def rpm_to_rad_s(rpm): return _return(np.asarray(rpm,dtype=float)*2*np.pi/60.0)
def rad_s_to_rpm(w): return _return(np.asarray(w,dtype=float)*60.0/(2*np.pi))
