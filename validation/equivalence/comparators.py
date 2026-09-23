from __future__ import annotations
import numpy as np

def rel_fro(a,b):
    a=np.asarray(a);b=np.asarray(b);return float(np.linalg.norm(a-b)/max(np.linalg.norm(b),np.finfo(float).tiny))
def rel_scalar(a,b): return float(abs(a-b)/max(1.0,abs(b)))
def match_modes(actual,reference):
    actual=np.asarray(actual).ravel();reference=np.asarray(reference).ravel();unused=set(range(len(reference)));mapping=[]
    for i,a in enumerate(actual):
        j=min(unused,key=lambda k:abs(a-reference[k]));mapping.append((i,j));unused.remove(j)
    return mapping
def eigenvalue_max_rel(actual,reference,mapping=None):
    a=np.asarray(actual).ravel();r=np.asarray(reference).ravel();mapping=mapping or match_modes(a,r)
    return max((rel_scalar(a[i],r[j]) for i,j in mapping),default=0.0)
def mac(phi_a,phi_b):
    a=np.asarray(phi_a).reshape(-1);b=np.asarray(phi_b).reshape(-1);den=np.vdot(a,a).real*np.vdot(b,b).real
    return 0.0 if den<=0 else float(abs(np.vdot(a,b))**2/den)
def mac_min(vec_a,vec_b,mapping):
    A=np.asarray(vec_a);B=np.asarray(vec_b);return min((mac(A[:,i],B[:,j]) for i,j in mapping),default=1.0)
def complex_response_rel(actual,reference): return rel_fro(actual,reference)
def max_abs(actual,reference): return float(np.max(np.abs(np.asarray(actual)-np.asarray(reference))))
