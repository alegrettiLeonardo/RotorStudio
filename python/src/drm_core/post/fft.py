from __future__ import annotations

import numpy as np


def fftscale(response, time):
    """V2-compatible scaled DFT.

    Returns the complete FFT spectrum and the legacy frequency vector in Hz.
    Scaling follows Rotor_Software_v2/fftscale.m exactly: 2/npts.
    """
    y = np.asarray(response)
    t = np.asarray(time, dtype=float)
    if t.ndim != 1:
        raise ValueError("time: received non-vector input; expected a 1-D vector")
    if t.size < 2:
        raise ValueError("time: received fewer than 2 points; expected at least 2")
    if y.ndim == 1:
        y = y[None, :]
    if y.ndim != 2:
        raise ValueError("response: expected shape (ndof, npts)")
    if y.shape[1] != t.size:
        raise ValueError(
            f"response: received npts={y.shape[1]}, time has npts={t.size}; expected equal lengths"
        )
    tmin = float(np.min(t)); tmax = float(np.max(t))
    span = tmax - tmin
    if span <= 0:
        raise ValueError(f"time: received span={span}; expected Tmax > Tmin")
    dt = span / (t.size - 1)
    reconstructed = tmin + np.arange(t.size) * dt
    tol = 1e-10 * max(abs(tmax), 1.0)
    if np.max(np.abs(t - reconstructed)) > tol:
        raise ValueError("time: increments are not equally spaced within the V2 tolerance")
    fft_out = (2.0 / t.size) * np.fft.fft(y, axis=1)
    frequency_hz = (1.0 / span) * np.arange(t.size)
    return fft_out, frequency_hz
