from __future__ import annotations

from pathlib import Path
import numpy as np


FIGURE_FORMATS=("png","svg","pdf")
NUMERIC_FORMATS=("csv","npz")


def export_figure(fig, base_path, formats=FIGURE_FORMATS, **savefig_kwargs):
    base=Path(base_path);base.parent.mkdir(parents=True,exist_ok=True)
    written={}
    for fmt in formats:
        fmt=fmt.lower()
        if fmt not in FIGURE_FORMATS: raise ValueError(f"unsupported figure format {fmt!r}; expected {FIGURE_FORMATS}")
        path=base.with_suffix("."+fmt);fig.savefig(path,format=fmt,**savefig_kwargs);written[fmt]=path
    return written


def export_npz(path, **arrays):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    np.savez(p,**arrays);return p


def export_csv(path, columns, header=None):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    arrays=[np.asarray(x) for x in columns]
    if not arrays or any(a.ndim!=1 for a in arrays): raise ValueError("columns: expected one or more 1-D arrays")
    n=arrays[0].size
    if any(a.size!=n for a in arrays): raise ValueError("columns: all arrays must have equal length")
    data=np.column_stack(arrays)
    if np.iscomplexobj(data):
        raise ValueError("CSV export does not silently flatten complex values; export real/imag or magnitude/phase explicitly")
    np.savetxt(p,data,delimiter=",",header="" if header is None else ",".join(header),comments="")
    return p
