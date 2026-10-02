"""Generate B3 axial/torsional authority from frozen real ROSS before native B3 exists."""
from __future__ import annotations
import argparse,importlib,inspect,json,platform,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from validation.b3.authority_common import *
from validation.ross_parity.generate_6dof_global_reference import build_rotor

def phase_normalize(v):
    a=np.asarray(v,dtype=np.complex128).copy()
    for j in range(a.shape[1]):
        n=float(np.linalg.norm(a[:,j]));require(n>np.finfo(float).tiny,"zero family eigenvector")
        a[:,j]/=n;p=int(np.argmax(np.abs(a[:,j])))
        a[:,j]*=np.exp(-1j*np.angle(a[p,j]))
        if a[p,j].real<0:a[:,j]*=-1
    return a

def matrices(rotor,speed):
    w=float(speed)
    return {
        "M":np.asarray(rotor.M(w,w)),
        "K":np.asarray(rotor.K(w,w)),
        "C":np.asarray(rotor.C(w,w)),
        "G":np.asarray(rotor.G()),
        "Ksdt":np.asarray(rotor.Ksdt()),
    }

def family_modal(rotor,speed,family,expected):
    w=float(speed)
    modal=rotor.run_modal(
        speed=w,num_modes=2*rotor.ndof,sparse=False,
        synchronous=False,matched_whirl=False,
    )
    idx=[
        i for i,(shape,wd) in enumerate(zip(modal.shapes,modal.wd,strict=True))
        if shape.mode_type==family and float(wd)>0.0
    ]
    require(len(idx)==int(expected),f"{family}: expected {expected} positive modes, got {len(idx)}")
    sel=np.asarray(idx,dtype=int)
    dofs=family_dofs(rotor.ndof,family)
    ev=np.asarray(modal.evalues)[sel]
    q=np.asarray(modal.evectors[:rotor.ndof,:])[:,sel]
    qr=q[dofs,:]
    mats=matrices(rotor,w)
    sub={k:v[np.ix_(dofs,dofs)] for k,v in mats.items()}
    residual=[]
    for j,lam in enumerate(ev):
        v=qr[:,j]
        R=(lam*lam)*(sub["M"]@v)+lam*((sub["C"]+w*sub["G"])@v)+sub["K"]@v
        scale=(abs(lam)**2*np.linalg.norm(sub["M"])*np.linalg.norm(v)
               +abs(lam)*np.linalg.norm(sub["C"]+w*sub["G"])*np.linalg.norm(v)
               +np.linalg.norm(sub["K"])*np.linalg.norm(v))
        residual.append(float(np.linalg.norm(R)/scale if scale else np.linalg.norm(R)))
    return {
        "evalues":ev,
        "wn":np.asarray(modal.wn)[sel],
        "wd":np.asarray(modal.wd)[sel],
        "damping_ratio":np.asarray(modal.damping_ratio)[sel],
        "log_dec":np.asarray(modal.log_dec)[sel],
        "evectors":qr,
        "evectors_normalized":phase_normalize(qr),
        "residual":np.asarray(residual,float),
        "indices":sel.astype(float),
        "submatrices":sub,
        "fullmatrices":mats,
    }

def source_ranges(rs,ross_root):
    from ross.utils import convert_6dof_to_torsional
    mapping={
      "Rotor.M":rs.Rotor.M,"Rotor.K":rs.Rotor.K,"Rotor.C":rs.Rotor.C,
      "Rotor.G":rs.Rotor.G,"Rotor.Ksdt":rs.Rotor.Ksdt,
      "Rotor.run_modal":rs.Rotor.run_modal,
      "Shape._classify":rs.Shape._classify,
      "convert_6dof_to_torsional":convert_6dof_to_torsional,
    }
    out={}
    for name,obj in mapping.items():
        fn=inspect.unwrap(obj);lines,first=inspect.getsourcelines(fn)
        path=Path(inspect.getsourcefile(fn)).resolve()
        require(path.is_relative_to(ross_root),"B3 source outside frozen ROSS")
        out[name]={"path":path.relative_to(ross_root).as_posix(),"first_line":first,
                   "last_line":first+len(lines)-1,"line_count":len(lines)}
    return out

def generate(ross_root:Path,out:Path):
    ross_root=ross_root.resolve();out=out.resolve()
    frozen=(REPO_ROOT/FROZEN_PATH).resolve()
    require(not out.exists(),"refuse overwrite")
    require(not out.is_relative_to(frozen),"cannot generate into frozen authority")
    spec=read_json(REPO_ROOT/INPUT_PATH);validate_spec(spec)
    policy=read_json(REPO_ROOT/POLICY_PATH)
    require(policy["fixed_before_native"] is True,"B3 tolerance policy not frozen")
    rotor_spec=read_json(REPO_ROOT/ROTOR_SPEC_PATH)
    check_checkout(ross_root)
    for p in MANDATORY_SOURCES:source_record(ross_root,p,"pre_import")
    require("ross" not in sys.modules,"ROSS imported too early")
    sys.path.insert(0,str(ross_root));rs=importlib.import_module("ross")
    from ross.utils import convert_6dof_to_torsional
    require(Path(rs.__file__).resolve().is_relative_to(ross_root),"wrong ROSS import")
    out.mkdir(parents=True)
    (out/"cases.json").write_bytes((REPO_ROOT/INPUT_PATH).read_bytes())
    (out/"tolerances.json").write_bytes((REPO_ROOT/POLICY_PATH).read_bytes())
    (out/"rotor_specification.json").write_bytes((REPO_ROOT/ROTOR_SPEC_PATH).read_bytes())
    (out/"requirements-freeze.txt").write_bytes(run_bytes([sys.executable,"-m","pip","freeze","--all"]))
    (out/"pip-check.txt").write_bytes(run_bytes([sys.executable,"-m","pip","check"]))

    arrays=[];case_meta={};max_decouple=0.0
    for case in spec["modal_cases"]:
        cid=case["id"];family=case["family"];w=float(case["speed_rad_s"])
        rotor=build_rotor(rs,rotor_spec,case["rotor"])
        result=family_modal(rotor,w,family,case["expected_modes"])
        dofs=family_dofs(rotor.ndof,family)
        ratios={}
        for name,A in result["fullmatrices"].items():
            ratio=decoupling_ratio(A,dofs);ratios[name]=ratio;max_decouple=max(max_decouple,ratio)
            require(ratio<=policy["decoupling"]["relative_frobenius_max"],
                    f"{cid} {name}: {family} subspace coupled, ratio={ratio}")
            arrays.append(save_array(out,f"modal/{cid}_{name}.npy",result["submatrices"][name],f"{family.lower()}_matrix_{name}"))
        for name,group in [
            ("evalues","modal_eigen"),("wn","modal_wn"),("wd","modal_wd"),
            ("damping_ratio","modal_damping"),("log_dec","modal_logdec"),
            ("evectors","modal_evec"),("evectors_normalized","modal_evec_normalized"),
            ("residual","modal_residual"),("indices","modal_indices"),
        ]:
            arrays.append(save_array(out,f"modal/{cid}_{name}.npy",result[name],f"{family.lower()}_{group}"))
        require(float(np.max(result["residual"],initial=0.0))<=policy["modal"]["residual_max"],
                f"{cid}: reduced second-order residual failed")
        cross={}
        if family=="Torsional":
            converted=convert_6dof_to_torsional(rotor)
            for name in ("M","K","C","G","Ksdt"):
                if name=="M":A=np.asarray(converted.M(w,w))
                elif name=="K":A=np.asarray(converted.K(w,w))
                elif name=="C":A=np.asarray(converted.C(w,w))
                elif name=="G":A=np.asarray(converted.G())
                else:A=np.asarray(converted.Ksdt())
                ref=result["submatrices"][name]
                require(A.shape==ref.shape,f"{cid}: converted torsional {name} shape mismatch")
                p=policy["matrix"][name]
                require(np.allclose(A,ref,rtol=p["rtol"],atol=p["atol"]),f"{cid}: ROSS torsional conversion {name} mismatch")
                cross[name]=float(np.max(np.abs(A-ref),initial=0.0))
        case_meta[cid]={"kind":"modal","family":family,"rotor":case["rotor"],"speed_rad_s":w,
                        "mode_count":int(case["expected_modes"]),"family_dofs":dofs.tolist(),
                        "decoupling_ratio":ratios,"torsional_conversion_max_abs":cross}

    for case in spec["sweep_cases"]:
        cid=case["id"];family=case["family"];speeds=np.asarray(case["speed_range_rad_s"],float)
        rotor=build_rotor(rs,rotor_spec,case["rotor"]);rows=[]
        for w in speeds:
            rows.append(family_modal(rotor,float(w),family,case["expected_modes"]))
        for name,group in [("wn","sweep_wn"),("wd","sweep_wd"),("damping_ratio","sweep_damping"),("log_dec","sweep_logdec")]:
            a=np.vstack([r[name] for r in rows])
            arrays.append(save_array(out,f"sweep/{cid}_{name}.npy",a,f"{family.lower()}_{group}"))
            if name in ("wn","wd"):
                drift=float(np.max(np.abs(a-a[0:1,:]),initial=0.0))
                require(drift<=policy["sweep"]["speed_invariance_abs_rad_s"],
                        f"{cid}: {family} {name} unexpectedly speed dependent: {drift}")
        arrays.append(save_array(out,f"sweep/{cid}_speed.npy",speeds,f"{family.lower()}_sweep_speed"))
        case_meta[cid]={"kind":"sweep","family":family,"rotor":case["rotor"],
                        "speed_range_rad_s":speeds.tolist(),"mode_count":int(case["expected_modes"])}

    ranges=source_ranges(rs,ross_root)
    prov=[source_record(ross_root,p,"required") for p in MANDATORY_SOURCES]
    write_json(out/"case_results.json",case_meta)
    write_json(out/"source_ranges.json",ranges)
    write_json(out/"source_provenance.json",prov)
    authority={
      "schema_version":1,"ross_sha":ROSS_SHA,"generator_head":head(REPO_ROOT),
      "generated_utc":datetime.now(timezone.utc).isoformat(),"platform":platform.platform(),
      "python":sys.version,"numpy":np.__version__,
      "case_counts":{"modal":6,"sweep":2},"arrays":arrays,
      "input_sha256":file_hash(REPO_ROOT/INPUT_PATH),
      "policy_sha256":file_hash(REPO_ROOT/POLICY_PATH),
      "rotor_spec_sha256":file_hash(REPO_ROOT/ROTOR_SPEC_PATH),
      "max_decoupling_ratio":max_decouple,
      "scope":"B3 dedicated axial/torsional modal families and speed sweeps from qualified 6DOF platform",
    }
    meta={p.relative_to(out).as_posix():file_hash(p) for p in sorted(out.rglob("*"))
          if p.is_file() and p.suffix!=".npy" and p.name!="authority.json"}
    authority["metadata_files"]=meta
    authority["data_bundle_sha256"]=sha256(canonical_bytes({"arrays":arrays,"metadata_files":meta,"cases":case_meta}))
    write_json(out/"authority.json",authority)
    print("B3_AUTHORITY_CANDIDATE",json.dumps({"status":"PASS","arrays":len(arrays),
          "data_bundle_sha256":authority["data_bundle_sha256"],
          "max_decoupling_ratio":max_decouple},sort_keys=True))
    return authority

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--ross-root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();generate(a.ross_root,a.out)
