from __future__ import annotations

import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np


def orbit_xy(mode, node, eigenvalue=None, degrees=341):
    v = np.asarray(mode, dtype=complex)
    if v.ndim != 1:
        raise ValueError("mode: expected a one-dimensional complex vector")
    ix, iy = 4*int(node)-4, 4*int(node)-3
    if ix < 0 or iy >= v.size:
        raise ValueError(f"node={node}: translational DOFs are outside mode length {v.size}")
    theta = np.linspace(0.0, 340.0, int(degrees))*np.pi/180.0
    jot = -1j if eigenvalue is not None and np.imag(eigenvalue) < 0 else 1j
    x = 1e6*np.real(v[ix]*np.exp(jot*theta))
    y = 1e6*np.real(v[iy]*np.exp(jot*theta))
    return x, y


def plot_orbits(mode, output_nodes, title=None, eigenvalue=None, ax=None):
    nodes = [int(n) for n in np.atleast_1d(output_nodes)]
    ax = ax or plt.subplots()[1]
    for node in nodes:
        x, y = orbit_xy(mode, node, eigenvalue=eigenvalue)
        ax.plot(x, y, label=f"Node {node}")
        ax.plot(x[0], y[0], "x")
        ax.plot(x[-1], y[-1], "d")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (µm)")
    ax.set_ylabel("y (µm)")
    if title:
        ax.set_title(title)
    if len(nodes) > 1:
        ax.legend()
    ax.grid(True)
    return ax
