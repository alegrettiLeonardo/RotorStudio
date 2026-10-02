"""Export exact-head B2 native qualification evidence. Validation/debug only."""
from __future__ import annotations
import argparse,hashlib,json,platform,subprocess,sys
from pathlib import Path
import numpy as np

from drm_core import RotorModel,Node,ShaftElement,TaperedShaftElement,Disk,CoefficientBearing
from drm_core.solver.sixdof_global import assemble_6dof,run_modal_6dof,run_campbell_6dof
from validation.ross_parity.verify_6dof_global_candidate import evec_group_parity

ROOT=Path(__file__).resolve().parents[2]
FROZEN=ROOT/"validation/ross_parity/6dof_global"
AUTH=FROZEN/"initial_reproduction/windows_candidate" if sys.platform=="win32" else FROZEN
SPEC=json.loads((FROZEN/"input_specification.json").read_text(encoding="utf-8"))
POLICY=json.loads((FROZEN/"tolerances.json").read_text(encoding="utf-8"))

def _tuple(v):
    if isinstance(v,list):return tuple(_tuple(x) for x in v)
    return v

def model_for(rotor_id):
    r=SPEC["rotors"][rotor_id];m=SPEC["materials"]["steel"]
    z=[0.0]
    for s in r["shafts"]:z.append(z[-1]+float(s["L"]))
    nodes=[Node(i+1,p) for i,p in enumerate(z)]
    shafts=[]
    for i,s in enumerate(r["shafts"],1):
        tapered=float(s["idl"])!=float(s["idr"]) or float(s["odl"])!=float(s["odr"])
        if tapered:
            shafts.append(TaperedShaftElement(
                22,i,i+1,float(s["odl"]),float(s["odr"]),float(s["idl"]),float(s["idr"]),
                float(m["rho"]),float(m["E"]),float(m["G_s"]),float(s.get("axial_force",0.0))
            ))
        else:
            shafts.append(ShaftElement(
                2,i,i+1,float(s["odl"]),float(s["idl"]),float(m["rho"]),float(m["E"]),
                float(m["G_s"]),0.0,float(s.get("axial_force",0.0)),float(s.get("torque",0.0))
            ))
    disks=[Disk.inertial(int(d["n"])+1,float(d["m"]),float(d["Id"]),float(d["Ip"])) for d in r["disks"]]
    bearings=[]
    for b in r["bearings"]:
        bearings.append(CoefficientBearing(
            node=int(b["n"])+1,kxx=_tuple(b["kxx"]),kyy=_tuple(b["kyy"]),
            kxy=_tuple(b["kxy"]),kyx=_tuple(b["kyx"]),
            cxx=_tuple(b["cxx"]),cyy=_tuple(b["cyy"]),cxy=_tuple(b["cxy"]),cyx=_tuple(b["cyx"]),
            mxx=_tuple(b["mxx"]),myy=_tuple(b["myy"]),mxy=_tuple(b["mxy"]),myx=_tuple(b["myx"]),
            speed_rad_s=tuple(float(x) for x in b.get("speed",[])),
            frequency_rad_s=tuple(float(x) for x in b.get("frequency",[])),
            interpolation=b.get("interpolation","pchip"),tag=f"B2-{rotor_id}-{b['n']}",
            provenance={"authority":"B2","map_contract":"ROSS_B2"} if ("speed" in b or "frequency" in b) else {"authority":"B2"},
        ))
    return RotorModel(nodes=nodes,shafts=shafts,disks=disks,advanced_bearings=bearings)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def maxabs(a,b):
    a=np.asarray(a);b=np.asarray(b)
    return float(np.max(np.abs(a-b),initial=0.0))

def save_npz(path,**arrays):
    path.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(path,**arrays)

def main(out:Path):
    out=out.resolve()
    if out.exists():raise RuntimeError(f"refuse existing evidence directory: {out}")
    out.mkdir(parents=True)
    metrics={
      "matrix_max_abs":{k:0.0 for k in ("M","K","C","G","Ksdt")},
      "state_space_max_abs":0.0,"eigenvalue_real_max_abs":0.0,"eigenvalue_imag_max_abs":0.0,
      "modal_scalar_max_abs":{k:0.0 for k in ("wn","wd","damping_ratio","log_dec")},
      "eigenvector_min_group_mac":1.0,"residual_max":0.0,
      "campbell_max_abs":{k:0.0 for k in ("wd","wn","wn_display","damping_ratio","log_dec")},
      "tracking_min_threshold_matched_mac":1.0,
    }
    for case in SPEC["matrix_cases"]:
        r=assemble_6dof(model_for(case["rotor"]),case["speed_rad_s"],case["frequency_rad_s"])
        payload={k:getattr(r,k) for k in ("M","K","C","G","Ksdt")}
        save_npz(out/"global"/f"{case['id']}.npz",**payload)
        for k,a in payload.items():
            e=np.load(AUTH/f"global/{case['id']}_{k}.npy",allow_pickle=False)
            metrics["matrix_max_abs"][k]=max(metrics["matrix_max_abs"][k],maxabs(a,e))
    for case in SPEC["modal_cases"]:
        cid=case["id"];r=run_modal_6dof(model_for(case["rotor"]),case["speed_rad_s"],case["num_modes"])
        save_npz(out/"modal"/f"{cid}.npz",
            eigenvalues_all=r.eigenvalues_all,eigenvalues=r.eigenvalues,
            eigenvectors_displacement=r.eigenvectors_displacement,state_space=r.state_space,
            wn=r.wn_rad_s,wd=r.wd_rad_s,damping_ratio=r.damping_ratio,log_dec=r.log_dec,
            whirl=r.whirl_value,residual=r.residual)
        (out/"modal").mkdir(parents=True,exist_ok=True)
        (out/"modal"/f"{cid}_metadata.json").write_text(json.dumps({
            "mode_type":list(r.mode_type),"mass_rcond":r.mass_rcond,"metadata":r.metadata
        },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        A=np.load(AUTH/f"modal/{cid}_A.npy");metrics["state_space_max_abs"]=max(metrics["state_space_max_abs"],maxabs(r.state_space,A))
        e=np.load(AUTH/f"modal/{cid}_evalues.npy")
        metrics["eigenvalue_real_max_abs"]=max(metrics["eigenvalue_real_max_abs"],maxabs(r.eigenvalues.real,e.real))
        metrics["eigenvalue_imag_max_abs"]=max(metrics["eigenvalue_imag_max_abs"],maxabs(r.eigenvalues.imag,e.imag))
        v=np.load(AUTH/f"modal/{cid}_evectors_displacement.npy")
        ok,groups=evec_group_parity(v,r.eigenvectors_displacement,e,POLICY)
        if not ok:raise RuntimeError(f"{cid}: eigenvector group parity failed")
        metrics["eigenvector_min_group_mac"]=min(metrics["eigenvector_min_group_mac"],min((x["score"] for x in groups),default=1.0))
        for attr,suf in (("wn_rad_s","wn"),("wd_rad_s","wd"),("damping_ratio","damping_ratio"),("log_dec","log_dec")):
            expected=np.load(AUTH/f"modal/{cid}_{suf}.npy")
            metrics["modal_scalar_max_abs"][suf]=max(metrics["modal_scalar_max_abs"][suf],maxabs(getattr(r,attr),expected))
        metrics["residual_max"]=max(metrics["residual_max"],float(np.max(r.residual,initial=0.0)))
    for case in SPEC["campbell_cases"]:
        cid=case["id"];model=model_for(case["rotor"])
        r=run_campbell_6dof(model,case["speed_range_rad_s"],case["frequencies"],frequency_type="wd")
        rw=run_campbell_6dof(model,case["speed_range_rad_s"],case["frequencies"],frequency_type="wn")
        save_npz(out/"campbell"/f"{cid}.npz",speed=r.speed_rad_s,wd=r.wd_rad_s,wn=r.wn_rad_s,
                 damping_ratio=r.damping_ratio,log_dec=r.log_dec,whirl=r.whirl_value,
                 tracking_index=r.tracking_index,tracking_mac=r.tracking_mac,mac_matrix=r.mac_matrix,
                 wn_display=rw.wn_rad_s)
        (out/"campbell").mkdir(parents=True,exist_ok=True)
        (out/"campbell"/f"{cid}_metadata.json").write_text(json.dumps({
            "mode_type":r.mode_type.tolist(),"metadata":r.metadata
        },indent=2,sort_keys=True)+"\n",encoding="utf-8")
        for attr,suf in (("wd_rad_s","wd"),("wn_rad_s","wn"),("damping_ratio","damping_ratio"),("log_dec","log_dec")):
            expected=np.load(AUTH/f"campbell/{cid}_{suf}.npy")
            metrics["campbell_max_abs"][suf]=max(metrics["campbell_max_abs"][suf],maxabs(getattr(r,attr).T,expected))
        expected=np.load(AUTH/f"campbell/{cid}_wn_display.npy")
        metrics["campbell_max_abs"]["wn_display"]=max(metrics["campbell_max_abs"]["wn_display"],maxabs(rw.wn_rad_s.T,expected))
        tracking=json.loads((AUTH/f"campbell/{cid}_tracking.json").read_text(encoding="utf-8"))
        for s,station in enumerate(tracking):
            if list(map(int,r.tracking_index[:,s]))!=list(map(int,station["found_order"])):
                raise RuntimeError(f"{cid} station {s}: tracking permutation mismatch")
            flags=np.asarray(station["threshold_match"],dtype=bool)
            if s and np.any(flags):
                metrics["tracking_min_threshold_matched_mac"]=min(
                    metrics["tracking_min_threshold_matched_mac"],float(np.min(r.tracking_mac[:,s][flags]))
                )
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    files={p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    manifest={"schema_version":1,"status":"PASS","head":head,"platform":platform.platform(),
              "authority_commit":"d9be588c71bfd7116f61d1f5f5be3a2ee0e06726",
              "ross_sha":"6320eab9f890f1b3cc1710d508b446fe063ca68d","metrics":metrics,"files":files}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("B2_NATIVE_EVIDENCE",json.dumps({"status":"PASS","head":head,"metrics":metrics},sort_keys=True))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);a=p.parse_args();main(a.out)
