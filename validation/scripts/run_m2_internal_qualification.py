from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from drm_core import (
    RotorModel, Node, ShaftElement, TaperedShaftElement, Disk, Bearing, Force,
    run_assembly, run_modal, run_frequency_response, run_critical_speeds,
)
from drm_core.solver.backend import FortranBackend

OUT=Path(__file__).resolve().parents[1]/'reports'/'M2_INTERNAL_METRICS.json'

def rel(a,b):
    den=np.linalg.norm(b)
    return float(np.linalg.norm(a-b)/(den if den else 1.0))

def model(force=False):
    return RotorModel(
        [Node(1,0.0),Node(2,0.5),Node(3,1.0)],
        [ShaftElement(2,1,2,0.05,0.0,7800,2.1e11,8.0e10),
         ShaftElement(2,2,3,0.05,0.0,7800,2.1e11,8.0e10)],
        [Disk.geometric(2,7800,0.05,0.25,0.05)],
        [Bearing(3,1,(1e6,1e6,0.0,0.0)),Bearing(3,3,(1e6,1e6,0.0,0.0))],
        [Force.unbalance(2,1e-4,0.2)] if force else [],
    )

b=FortranBackend()
metrics={'solver_version':b.version(),'matlab_equivalence':'BLOCKED_NOT_MEASURED'}
# A tapered constant section must reduce to the circular source formulas when axial force is zero.
taper={}
for base in range(1,9):
    c=ShaftElement(base,1,2,.05,.01,7800,2.1e11,8.0e10,0.0,0.0,0.0)
    t=TaperedShaftElement(base+20,1,2,.05,.05,.01,.01,7800,2.1e11,8.0e10,0.0)
    cm,cg,ck,ca=b.shaft_element_matrices(c,.4)
    tm,tg,tk,ta=b.shaft_element_matrices(t,.4)
    taper[str(base+20)]={'M_rel':rel(tm,cm),'G_rel':rel(tg,cg),'K_rel':rel(tk,ck),'K1_norm':float(np.linalg.norm(ta))}
metrics['taper_constant_section_vs_circular_axial0']=taper
m=model(False)
a=run_assembly(m,100.0)
metrics['global_invariants']={
    'M_sym_rel':rel(a.M,a.M.T),
    'K0_sym_rel':rel(a.K0,a.K0.T),
    'G_skew_rel':float(np.linalg.norm(a.G+a.G.T)/max(1.0,np.linalg.norm(a.G))),
    'min_diag_M':float(np.min(np.diag(a.M))),
    'finite_MCK':bool(np.all(np.isfinite(a.M)) and np.all(np.isfinite(a.C)) and np.all(np.isfinite(a.K))),
}
r=run_modal(m,100.0)
metrics['modal_smoke']={'n_eigenvalues':int(r.eigenvalues.size),'max_abs_eigenvalue':float(np.max(np.abs(r.eigenvalues))),'finite':bool(np.all(np.isfinite(r.eigenvalues)))}
f=run_frequency_response(model(True),[50.0,100.0,150.0])
metrics['freq_rsp_smoke']={'shape':list(f.response.shape),'max_abs_response':float(np.max(np.abs(f.response))),'finite':bool(np.all(np.isfinite(f.response)))}
d=run_critical_speeds(m,number_criticals=3,method='direct')
i=run_critical_speeds(m,number_criticals=3,method='iterative-index')
n=run_critical_speeds(m,method='iterative-nearest',initial_estimates=d.critical_speeds_rad_s)
metrics['critical_speed_internal_consistency']={
    'direct_rad_s':d.critical_speeds_rad_s.tolist(),
    'iterative_index_rad_s':i.critical_speeds_rad_s.tolist(),
    'iterative_nearest_rad_s':n.critical_speeds_rad_s.tolist(),
    'max_rel_direct_vs_iterative_index':float(np.max(np.abs(i.critical_speeds_rad_s-d.critical_speeds_rad_s)/np.maximum(1,np.abs(d.critical_speeds_rad_s)))),
    'max_rel_direct_vs_iterative_nearest':float(np.max(np.abs(n.critical_speeds_rad_s-d.critical_speeds_rad_s)/np.maximum(1,np.abs(d.critical_speeds_rad_s)))),
    'iterative_index_iterations':i.iterations.tolist(),
    'all_converged':bool(np.all(i.converged) and np.all(n.converged)),
}
OUT.write_text(json.dumps(metrics,indent=2,sort_keys=True)+'\n')
print(OUT)
print(json.dumps(metrics,indent=2,sort_keys=True))
