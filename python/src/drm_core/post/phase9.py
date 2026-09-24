from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

from .fft import fftscale
from .root_locus import plot_root_locus
from .eigenvalue import plot_eigenvalues
from .modes import plot_mode as _plot_mode
from .orbits import plot_orbits as _plot_orbits
from .response import plot_response as _plot_response, plot_frf as _plot_frf
from .exports import export_figure, export_npz


@dataclass(frozen=True)
class FFTResult:
    frequency_hz: np.ndarray
    spectrum: np.ndarray


def fft_scale(response, time_s):
    spectrum, frequency_hz = fftscale(response, time_s)
    return FFTResult(frequency_hz, spectrum)


def plot_eigenvalue_traces(speeds_rad_s, eigenvalues, nx=1.5):
    fig, axes = plt.subplots(1, 2)
    plot_eigenvalues(speeds_rad_s, eigenvalues, nx=nx, axes=axes)
    fig.tight_layout()
    return fig


def plot_mode(model, mode, eigenvalue=None):
    return _plot_mode(model, mode, eigenvalue=eigenvalue).figure


def plot_orbits(mode, nodes, title=None, eigenvalue=None):
    return _plot_orbits(mode, nodes, title=title, eigenvalue=eigenvalue).figure


def plot_response(speeds_rad_s, response, outnodes=(1.1,)):
    axes = _plot_response(speeds_rad_s, response, outnodes)
    axes[0].figure.tight_layout()
    return axes[0].figure


def plot_frf(omega_rad_s, response, outnodes=(1.1,)):
    axes = _plot_frf(omega_rad_s, response, outnodes)
    axes[0].figure.tight_layout()
    return axes[0].figure


def export_csv(path, **arrays):
    """Export one-dimensional result arrays without discarding phase."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    cols = {}
    for name, value in arrays.items():
        a = np.asarray(value)
        if a.ndim == 0:
            a = a.reshape(1)
        if a.ndim != 1:
            continue
        if np.iscomplexobj(a):
            cols[name + "_real"] = a.real
            cols[name + "_imag"] = a.imag
        else:
            cols[name] = a
    if not cols:
        raise ValueError("arrays: no one-dimensional columns available for CSV export")
    lengths = {len(v) for v in cols.values()}
    if len(lengths) != 1:
        raise ValueError(f"arrays: CSV columns have unequal lengths {sorted(lengths)}")
    keys = list(cols)
    np.savetxt(
        p,
        np.column_stack([cols[k] for k in keys]),
        delimiter=",",
        header=",".join(keys),
        comments="",
    )
    return p


def export_bundle(outdir, figures=None, arrays=None, metadata=None):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"figures": {}, "data": {}, "metadata": metadata or {}}
    for name, fig in (figures or {}).items():
        manifest["figures"][name] = [
            p.name for p in export_figure(fig, out / name).values()
        ]
    if arrays:
        manifest["data"]["npz"] = export_npz(out / "data.npz", **arrays).name
        manifest["data"]["csv"] = export_csv(out / "data.csv", **arrays).name
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


__all__ = [
    "FFTResult", "fft_scale", "plot_root_locus", "plot_eigenvalue_traces",
    "plot_mode", "plot_orbits", "plot_response", "plot_frf",
    "export_figure", "export_csv", "export_npz", "export_bundle",
]
