from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from scipy.io import loadmat

from drm_core import run_modal
from drm_core.post.whirl import whirl
from validation.equivalence.cases import stationary_model
from validation.equivalence.comparators import match_modes, mac

def isolated_reference_indices(reference, rel_tol):
    r=np.asarray(reference).ravel()
    out=set()
    if len(r)<=1:
        return {0} if len(r)==1 else out
    for j,z in enumerate(r):
        sep=np.abs(r-z)
        sep[j]=np.inf
        rel=float(np.min(sep)/max(1.0,abs(z)))
        if rel>rel_tol:
            out.add(j)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline",required=True)
    ap.add_argument("--isolation-rel",type=float,default=1e-8)
    ap.add_argument("--top",type=int,default=20)
    a=ap.parse_args()

    m=loadmat(Path(a.baseline),squeeze_me=False,struct_as_record=False)
    speeds=np.asarray(m["st_modal_speeds"]).squeeze()
    re=np.asarray(m["st_modal_eig"])
    rv=np.asarray(m["st_modal_vec"])
    rk=np.asarray(m["st_modal_kappa"])
    if re.ndim==1:
        re=re[:,None]

    model=stationary_model()
    rows=[]

    for q,w in enumerate(speeds):
        got=run_modal(model,float(w),with_eigenvectors=True,with_kappa=True)
        ref_eig=re[:,q]
        ref_vec=rv[:,:,q] if rv.ndim==3 else rv
        ref_k=rk[:,:,q] if rk.ndim==3 else rk
        mp=match_modes(got.eigenvalues,ref_eig)
        isolated=isolated_reference_indices(ref_eig,a.isolation_rel)

        for i,j in mp:
            if j not in isolated:
                continue

            mode_mac=mac(got.eigenvectors[:,i],ref_vec[:,j])
            alpha=np.vdot(got.eigenvectors[:,i],ref_vec[:,j])/max(np.vdot(got.eigenvectors[:,i],got.eigenvectors[:,i]).real,np.finfo(float).tiny)
            aligned=alpha*got.eigenvectors[:,i]
            vec_abs=float(np.max(np.abs(aligned-ref_vec[:,j])))
            vec_rel=float(np.linalg.norm(aligned-ref_vec[:,j])/max(np.linalg.norm(ref_vec[:,j]),np.finfo(float).tiny))

            for node in range(got.eigenvectors.shape[0]//2):
                d0=2*node
                d1=d0+1
                ka=float(got.kappa[d0,i])
                kr=float(ref_k[d0,j])
                kd=abs(ka-kr)

                ua=got.eigenvectors[d0,i]
                va=got.eigenvectors[d1,i]
                ur=ref_vec[d0,j]
                vr_=ref_vec[d1,j]

                _,ampa=whirl(np.array([ua]),np.array([va]))
                _,ampr=whirl(np.array([ur]),np.array([vr_]))

                rows.append(dict(
                    kappa_abs=kd,
                    speed=float(w),
                    actual_mode=int(i),
                    ref_mode=int(j),
                    node=int(node+1),
                    actual_kappa=ka,
                    ref_kappa=kr,
                    mac=float(mode_mac),
                    eig_rel=float(abs(got.eigenvalues[i]-ref_eig[j])/max(1.0,abs(ref_eig[j]))),
                    actual_local_amp=float(ampa[0]),
                    ref_local_amp=float(ampr[0]),
                    actual_uv_product=float(abs(ua)*abs(va)),
                    ref_uv_product=float(abs(ur)*abs(vr_)),
                    vector_max_abs_after_scalar=vec_abs,
                    vector_rel_after_scalar=vec_rel,
                ))

    rows.sort(key=lambda x:x["kappa_abs"],reverse=True)
    print("="*120)
    print("G7 KAPPA DIAGNOSTIC — isolated modes only")
    print("="*120)
    print(f"baseline={a.baseline}")
    print(f"isolation_rel={a.isolation_rel:.3e}")
    print(f"observations={len(rows)}")
    print()
    for n,r in enumerate(rows[:a.top],1):
        print(
            f"{n:02d} speed={r['speed']:9.3f} mode={r['actual_mode']:2d}->{r['ref_mode']:2d} "
            f"node={r['node']:2d} dk={r['kappa_abs']:.15e} "
            f"k={r['actual_kappa']:+.15e}/{r['ref_kappa']:+.15e} "
            f"MAC={r['mac']:.15e} eig_rel={r['eig_rel']:.3e}"
        )
        print(
            f"   amp={r['actual_local_amp']:.15e}/{r['ref_local_amp']:.15e} "
            f"|u||v|={r['actual_uv_product']:.15e}/{r['ref_uv_product']:.15e} "
            f"vec_rel_after_scalar={r['vector_rel_after_scalar']:.3e} "
            f"vec_max_abs_after_scalar={r['vector_max_abs_after_scalar']:.3e}"
        )

    if rows:
        worst=rows[0]
        print()
        print("WORST_KAPPA_ABS =",f"{worst['kappa_abs']:.17e}")
        print("WORST_SPEED     =",worst["speed"])
        print("WORST_MODE      =",f"{worst['actual_mode']}->{worst['ref_mode']}")
        print("WORST_NODE      =",worst["node"])
        print("WORST_LOCAL_AMP =",f"{worst['actual_local_amp']:.17e}",f"{worst['ref_local_amp']:.17e}")
        print("WORST_UV_PRODUCT=",f"{worst['actual_uv_product']:.17e}",f"{worst['ref_uv_product']:.17e}")
    print("="*120)

if __name__=="__main__":
    main()
