from __future__ import annotations
import numpy as np

def fftscale(response, time):
    """Legacy-equivalent scaled FFT from Rotor_Software_v2/fftscale.m."""
    t=np.asarray(time,dtype=float)
    if t.ndim!=1: raise ValueError("time must be a vector")
    if t.size<2: raise ValueError("time must contain at least two samples")
    y=np.asarray(response)
    if y.ndim==1: y=y.reshape(1,-1)
    if y.ndim!=2 or y.shape[1]!=t.size:
        raise ValueError(f"response has {y.shape[-1] if y.ndim else 1} samples; expected {t.size} from time")
    tmin=float(np.min(t));tmax=float(np.max(t));dt=(tmax-tmin)/(t.size-1)
    tref=tmin+np.arange(t.size)*dt
    if np.max(np.abs(t-tref))>1e-10*abs(tmax): raise ValueError("time vector does not have equal increments")
    return (2.0/t.size)*np.fft.fft(y,axis=1),np.arange(t.size,dtype=float)/(tmax-tmin)
