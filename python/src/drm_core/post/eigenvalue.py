from __future__ import annotations

import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np


def plot_eigenvalues(speeds_rad_s, eigenvalues, nx=1.5, axes=None):
    speeds = np.asarray(speeds_rad_s, dtype=float)
    eig = np.asarray(eigenvalues, dtype=complex)
    if speeds.ndim != 1 or speeds.size < 2:
        raise ValueError("speeds_rad_s: expected a vector with more than one speed")
    if eig.ndim != 2 or eig.shape[1] != speeds.size:
        raise ValueError("eigenvalues: expected shape (nmode, nspeed)")
    if axes is None:
        _, axes = plt.subplots(1, 2)
    ax_real, ax_imag = axes
    rpm = speeds * 60.0 / (2.0 * np.pi)
    max_rpm = float(np.max(rpm))
    max_hz = abs(float(nx)) * max_rpm / 60.0
    ax_real.plot(rpm, np.sort(eig.real, axis=0).T)
    ax_real.set_xlim(0.0, max_rpm)
    ax_real.set_xlabel("Rotor spin speed (rev/min)")
    ax_real.set_ylabel("Real (eigenvalues)")
    ax_real.grid(True)
    ax_imag.plot(rpm, (np.sort(np.abs(eig.imag), axis=0)/(2*np.pi)).T)
    for order in range(1, int(abs(nx))+1):
        ax_imag.plot(rpm, order*speeds/(2*np.pi), "--")
    ax_imag.set_xlim(0.0, max_rpm)
    ax_imag.set_ylim(-0.05*max_hz, max_hz)
    ax_imag.set_xlabel("Rotor spin speed (rev/min)")
    ax_imag.set_ylabel("Imag (eigenvalues) (Hz)")
    ax_imag.grid(True)
    return ax_real, ax_imag
