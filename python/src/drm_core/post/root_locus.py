from __future__ import annotations

import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np


def plot_root_locus(speeds_rad_s, eigenvalues, nx=1.5, ax=None):
    speeds = np.asarray(speeds_rad_s, dtype=float)
    eig = np.asarray(eigenvalues, dtype=complex)
    if speeds.ndim != 1 or speeds.size < 2:
        raise ValueError("speeds_rad_s: expected a vector with more than one speed")
    if eig.ndim != 2 or eig.shape[1] != speeds.size:
        raise ValueError("eigenvalues: expected shape (nmode, nspeed)")
    ax = ax or plt.subplots()[1]
    max_axes = abs(float(nx)) * float(np.max(speeds))
    ax.plot(eig.real.T, eig.imag.T)
    ax.plot(eig[:, 0].real, eig[:, 0].imag, "x")
    ax.plot(eig[:, -1].real, eig[:, -1].imag, "d")
    ax.set_xlim(-max_axes, max_axes)
    ax.set_ylim(-max_axes, max_axes)
    ax.set_xlabel("Real (eigenvalues)")
    ax.set_ylabel("Imag (eigenvalues)")
    ax.set_title("Root Locus")
    ax.grid(True)
    return ax
