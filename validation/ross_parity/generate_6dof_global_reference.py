"""Generate B2 6-DOF global/modal/Campbell authority from frozen real ROSS."""
from __future__ import annotations
import argparse,importlib,inspect,json,os,platform,sys,types
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from validation.b2.authority_common import *

def build_rotor(rs,spec,rotor_id):
    r=spec["rotors"][rotor_id]
    mats={}
    for key,m in spec["materials"].items():
        mats[key]=rs.Material(name=m["name"],rho=m["rho"],E=m["E"],G_s=m["G_s"])
    shafts=[rs.ShaftElement(L=s["L"],idl=s["idl"],odl=s["odl"],idr=s["idr"],odr=s["odr"],
        material=mats[s["material"]],n=int(s["n"]),axial_force=s.get("axial_force",0.0),torque=s.get("torque",0.0),
        shear_effects=bool(s.get("shear_effects",True)),rotary_inertia=bool(s.get("rotary_inertia",True)),
        gyroscopic=bool(s.get("gyroscopic",True)),shear_method_calc=s.get("shear_method_calc","cowper")) for s in r["shafts"]]
    disks=[rs.DiskElement(n=int(d["n"]),m=d["m"],Id=d["Id"],Ip=d["Ip"]) for d in r["disks"]]
    bearings=[]
    for b in r["bearings"]:
        kw={k:b[k] for k in ("kxx","cxx","kyy","cyy","kxy","kyx","cxy","cyx","mxx","myy","mxy","myx","kzz","czz","mzz") if k in b}
        if "speed" in b:kw["speed"]=b["speed"]
        if "frequency" in b:kw["frequency"]=b["frequency"]
        kw["interpolation"]=b.get("interpolation","pchip")
        bearings.append(rs.BearingElement(n=int(b["n"]),**kw))
    rotor=rs.Rotor(shaft_elements=shafts,disk_elements=disks,bearing_elements=bearings)
    require(rotor.number_dof==6,f"{rotor_id}: not 6DOF")
    expected=6*(len(shafts)+1);require(rotor.ndof==expected,f"{rotor_id}: ndof {rotor.ndof}!={expected}")
    return rotor

def function_ranges(rs,ross_root):
    mapping={
      "Rotor":(rs.Rotor,["__init__","_check_number_dof","_build_base_matrices","M","K","C","G","Ksdt","A","_index","_eigen","run_modal","run_campbell"]),
      "BearingElement":(rs.BearingElement,["__init__","dof_mapping","M","K","C"]),
      "ShaftElement":(rs.ShaftElement,["__init__","dof_mapping","M","K","G","Kst"]),
      "DiskElement":(rs.DiskElement,["__init__","dof_mapping","M","G","Kdt"]),
      "Material":(rs.Material,["__init__"]),
      "ModalResults":(rs.ModalResults,["__init__","whirl_direction","whirl_values"]),
      "Shape":(rs.Shape,["__init__","_classify","_calculate_orbits"]),
      "Orbit":(rs.Orbit,["__init__"]),
      "CampbellResults":(rs.CampbellResults,["__init__"]),
    }
    out={}
    for clsname,(cls,names) in mapping.items():
        for name in names:
            fn=inspect.unwrap(getattr(cls,name));lines,first=inspect.getsourcelines(fn);path=Path(inspect.getsourcefile(fn)).resolve()
            require(path.is_relative_to(ross_root),"function outside frozen ROSS")
            out[f"{clsname}.{name}"]={"path":path.relative_to(ross_root).as_posix(),"first_line":first,
              "last_line":first+len(lines)-1,"line_count":len(lines)}
    return out

def mac(u,v):
    den=np.vdot(u,u)*np.vdot(v,v)
    return float(abs(np.vdot(u,v))**2/abs(den)) if abs(den)>0 else 0.0

def phase_normalize_columns(vectors):
    value=np.asarray(vectors,dtype=np.complex128)
    out=np.empty_like(value)
    for j in range(value.shape[1]):
        q=value[:,j].copy()
        norm=float(np.linalg.norm(q));require(np.isfinite(norm) and norm>np.finfo(float).tiny,"invalid eigenvector norm")
        q/=norm
        pivot=int(np.argmax(np.abs(q)))
        q*=np.exp(-1j*np.angle(q[pivot]))
        if q[pivot].real<0:q=-q
        out[:,j]=q
    return out

def dense_campbell(rotor,speed_range,frequencies,frequency_type="wd"):
    original=rotor.run_modal
    def wrapper(self,speed,**kwargs):
        kwargs["sparse"]=False
        kwargs["synchronous"]=False
        kwargs["matched_whirl"]=False
        return original(speed,**kwargs)
    rotor.run_modal=types.MethodType(wrapper,rotor)
    try:
        return rotor.run_campbell(speed_range=np.asarray(speed_range,float),frequencies=int(frequencies),
                                  frequency_type=frequency_type,torsional_analysis=False,matched_whirl=False)
    finally:
        rotor.run_modal=original

def generate(ross_root:Path,out:Path):
    ross_root=ross_root.resolve();out=out.resolve();frozen=(REPO_ROOT/FROZEN_PATH).resolve()
    require(not out.exists(),"refuse overwrite");require(not out.is_relative_to(frozen),"cannot target frozen authority")
    spec=read_json(REPO_ROOT/INPUT_PATH);validate_spec(spec);check_checkout(ross_root)
    for p in MANDATORY_SOURCES:source_record(ross_root,p,"pre_import")
    require("ross" not in sys.modules,"ROSS imported too early")
    sys.path.insert(0,str(ross_root));rs=importlib.import_module("ross");import scipy
    require(Path(rs.__file__).resolve().is_relative_to(ross_root),"wrong ROSS import")
    out.mkdir(parents=True)
    (out/"input_specification.json").write_bytes((REPO_ROOT/INPUT_PATH).read_bytes())
    (out/"tolerances.json").write_bytes((REPO_ROOT/POLICY_PATH).read_bytes())
    (out/"requirements-freeze.txt").write_bytes(run_bytes([sys.executable,"-m","pip","freeze","--all"]))
    (out/"pip-check.txt").write_bytes(run_bytes([sys.executable,"-m","pip","check"]))
    executed=set(MANDATORY_SOURCES)
    def prof(frame,event,arg):
        if event=="call":
            p=Path(frame.f_code.co_filename)
            if p.is_absolute():
                q=p.resolve()
                if q.is_relative_to(ross_root):executed.add(q.relative_to(ross_root).as_posix())
    arrays=[];cases={};previous=None
    try:
        for case in spec["matrix_cases"]:
            rotor=build_rotor(rs,spec,case["rotor"]);w=float(case["speed_rad_s"]);f=float(case["frequency_rad_s"])
            mats={"M":rotor.M(f,w),"K":rotor.K(f,w),"C":rotor.C(f,w),"G":rotor.G(),"Ksdt":rotor.Ksdt()}
            for name,a in mats.items():arrays.append(save_array(out,f"global/{case['id']}_{name}.npy",a,f"matrix_{name}"))
            cases[case["id"]]={"kind":"global","rotor":case["rotor"],"ndof":rotor.ndof,"speed_rad_s":w,"frequency_rad_s":f}
        for case in spec["modal_cases"]:
            rotor=build_rotor(rs,spec,case["rotor"]);w=float(case["speed_rad_s"]);nm=int(case["num_modes"])
            modal=rotor.run_modal(speed=w,num_modes=nm,sparse=False,synchronous=False,matched_whirl=False)
            f=w;M=rotor.M(f,w);K=rotor.K(f,w);C=rotor.C(f,w);G=rotor.G();A=rotor.A(speed=w,frequency=f,synchronous=False)
            nsel=len(modal.wn);disp=modal.evectors[:rotor.ndof,:nsel]
            vals=modal.evalues[:nsel]
            residuals=[]
            for j,lam in enumerate(vals):
                q=disp[:,j];R=(lam*lam)*(M@q)+lam*((C+w*G)@q)+K@q
                scale=(abs(lam)**2*np.linalg.norm(M)*np.linalg.norm(q)+abs(lam)*np.linalg.norm(C+w*G)*np.linalg.norm(q)+np.linalg.norm(K)*np.linalg.norm(q))
                residuals.append(float(np.linalg.norm(R)/scale if scale else np.linalg.norm(R)))
            payload={"A":A,"evalues_all":modal.evalues,"evalues":vals,"evectors_displacement":disp,
                     "evectors_normalized":phase_normalize_columns(disp),
                     "wn":modal.wn,"wd":modal.wd,"damping_ratio":modal.damping_ratio,"log_dec":modal.log_dec,
                     "whirl":modal.whirl_values(),"residual":np.asarray(residuals)}
            groups={"A":"matrix_A","evalues_all":"modal_eigen","evalues":"modal_eigen",
                    "evectors_displacement":"modal_evec","evectors_normalized":"modal_evec_normalized",
                    "wn":"modal_wn","wd":"modal_wd","damping_ratio":"modal_damping","log_dec":"modal_logdec",
                    "whirl":"modal_whirl","residual":"modal_residual"}
            for name,a in payload.items():
                group=groups[name]
                arrays.append(save_array(out,f"modal/{case['id']}_{name}.npy",a,group,allow_nan=(group=="modal_whirl")))
            write_json(out/f"modal/{case['id']}_mode_types.json",[s.mode_type for s in modal.shapes[:nsel]])
            cases[case["id"]]={"kind":"modal","rotor":case["rotor"],"ndof":rotor.ndof,"speed_rad_s":w,"num_modes":nm,"selected_modes":nsel}
        for case in spec["campbell_cases"]:
            rotor=build_rotor(rs,spec,case["rotor"]);speeds=np.asarray(case["speed_range_rad_s"],float);freqs=int(case["frequencies"])
            camp=dense_campbell(rotor,speeds,freqs,"wd")
            camp_wn=dense_campbell(rotor,speeds,freqs,"wn")
            wn_tracked=np.vstack([camp.modal_results[float(w)].wn[:freqs] for w in speeds])
            payload={"speed":speeds,"wd":camp.wd,"wn":wn_tracked,"wn_display":camp_wn.wd,
                     "log_dec":camp.log_dec,"damping_ratio":camp.damping_ratio,"whirl":camp.whirl_values}
            group_map={"speed":"campbell_speed","wd":"campbell_wd","wn":"campbell_wn","wn_display":"campbell_wn",
                       "log_dec":"campbell_log_dec","damping_ratio":"campbell_damping_ratio","whirl":"campbell_whirl"}
            for name,a in payload.items():
                group=group_map[name]
                arrays.append(save_array(out,f"campbell/{case['id']}_{name}.npy",a,group,allow_nan=(group=="campbell_whirl")))
            track=[];types_out=[];previous_tracked=None;mode_order=np.arange(freqs+2,dtype=int);threshold=0.9
            for i,w in enumerate(speeds):
                tracked=camp.modal_results[float(w)]
                raw=rotor.run_modal(speed=float(w),num_modes=2*(freqs+2),sparse=False,synchronous=False,matched_whirl=False)
                n=freqs+2;raw_v=raw.evectors[:,:n]
                if i==0:
                    decision=np.eye(n,dtype=float);found_order=mode_order.copy()
                    modes_not_found=np.asarray([],dtype=int);missing_modes=[];threshold_match=np.ones(n,dtype=bool)
                else:
                    decision=np.array([[mac(previous_tracked[:,ii],raw_v[:,jj]) for jj in range(n)] for ii in range(n)],float)
                    mask=decision>threshold
                    found_order=np.where(mask.any(axis=1),np.argmax(decision*mask,axis=1),-1)
                    modes_not_found=np.where(found_order==-1)[0]
                    missing_modes=sorted(set(mode_order.tolist())-set(found_order.tolist()))
                    if len(modes_not_found):
                        found_order[modes_not_found]=missing_modes[:len(modes_not_found)]
                    threshold_match=mask.any(axis=1)
                require(sorted(int(x) for x in found_order)==mode_order.tolist(),f"{case['id']} station {i}: tracking is not a permutation")
                # Prove the independently reconstructed ROSS decision produced the stored tracked object.
                require(np.allclose(tracked.evalues[:n],raw.evalues[found_order],rtol=2e-12,atol=2e-9),
                        f"{case['id']} station {i}: reconstructed found_order differs from ROSS")
                tracked_v=tracked.evectors[:,:n]
                selected=np.asarray([decision[row,found_order[row]] for row in range(n)],float)
                if i>0:
                    require(np.all(selected[threshold_match]>threshold),f"{case['id']} station {i}: threshold match contract failed")
                arrays.append(save_array(out,f"campbell/{case['id']}_station{i}_decision_mac.npy",decision,"campbell_tracking_mac"))
                arrays.append(save_array(out,f"campbell/{case['id']}_station{i}_found_order.npy",found_order.astype(float),"campbell_tracking_assignment"))
                arrays.append(save_array(out,f"campbell/{case['id']}_station{i}_selected_mac.npy",selected,"campbell_tracking_selected_mac"))
                types_out.append([s.mode_type for s in tracked.shapes[:freqs]])
                track.append({"speed":float(w),"found_order":[int(x) for x in found_order],
                              "modes_not_found":[int(x) for x in modes_not_found],
                              "missing_modes":[int(x) for x in missing_modes],
                              "threshold_match":[bool(x) for x in threshold_match],
                              "assignment_mac":[float(x) for x in selected]})
                previous_tracked=tracked_v
            write_json(out/f"campbell/{case['id']}_mode_types.json",types_out);write_json(out/f"campbell/{case['id']}_tracking.json",track)
            cases[case["id"]]={"kind":"campbell","rotor":case["rotor"],"ndof":rotor.ndof,"frequencies":freqs,
                               "speed_range_rad_s":speeds.tolist(),"num_modes":2*(freqs+2),"evec_size":freqs+2,
                               "tracking_threshold":threshold}
    finally:
        sys.setprofile(previous)
    # Freeze gates required by the declared B2 scope.
    observed_types=set()
    nonlateral_nan_ok=True
    for p in sorted((out/"modal").glob("*_mode_types.json")):
        mode_types=read_json(p);observed_types.update(mode_types)
        whirl=np.load(p.with_name(p.name.replace("_mode_types.json","_whirl.npy")),allow_pickle=False)
        for kind,value in zip(mode_types,whirl,strict=True):
            if kind!="Lateral":
                nonlateral_nan_ok &= bool(np.isnan(value))
    require({"Lateral","Axial","Torsional"}.issubset(observed_types),
            f"authority must expose Lateral/Axial/Torsional, observed={sorted(observed_types)}")
    require(nonlateral_nan_ok,"non-lateral ROSS whirl values must remain NaN")
    crossing=False
    for p in sorted((out/"campbell").glob("*_tracking.json")):
        for station in read_json(p)[1:]:
            assignment=station["found_order"]
            if assignment!=list(range(len(assignment))):
                crossing=True
    require(crossing,"authority requires at least one non-identity MAC tracking sentinel")
    ranges=function_ranges(rs,ross_root);modules={}
    byfile={}
    for name,module in sorted(sys.modules.items()):
        if name=="ross" or name.startswith("ross."):
            fn=getattr(module,"__file__",None)
            if fn:
                p=Path(inspect.getsourcefile(module) or fn).resolve()
                if p.is_relative_to(ross_root):
                    rel=p.relative_to(ross_root).as_posix();byfile.setdefault(rel,[]).append(name)
    srcs=set(MANDATORY_SOURCES)|executed|set(byfile)|{"pyproject.toml","requirements.txt","ross/available_materials.toml"}
    prov=[source_record(ross_root,p,"executed" if p in executed else "imported_or_required",byfile.get(p,[])) for p in sorted(srcs)]
    write_json(out/"cases.json",cases);write_json(out/"source_ranges.json",ranges);write_json(out/"source_provenance.json",prov)
    authority={"schema_version":1,"ross_sha":ROSS_SHA,"generator_head":head(REPO_ROOT),"generated_utc":datetime.now(timezone.utc).isoformat(),
      "platform":platform.platform(),"python":sys.version,"numpy":np.__version__,"scipy":scipy.__version__,
      "input_sha256":file_hash(REPO_ROOT/INPUT_PATH),"policy_sha256":file_hash(REPO_ROOT/POLICY_PATH),
      "case_counts":{"global":11,"modal":8,"campbell":4},"arrays":arrays,"source_file_count":len(prov),"function_ranges":ranges,
      "scope":"B2 frozen ROSS global 6DOF + dense modal + standard Campbell authority"}
    metadata_files={p.relative_to(out).as_posix():file_hash(p) for p in sorted(out.rglob("*"))
                    if p.is_file() and p.suffix!=".npy" and p.name!="authority.json"}
    authority["metadata_files"]=metadata_files
    authority["data_bundle_sha256"]=sha256(canonical_bytes({"cases":cases,"arrays":arrays,"metadata_files":metadata_files}))
    write_json(out/"authority.json",authority)
    print("B2_AUTHORITY_CANDIDATE",json.dumps({"status":"PASS","arrays":len(arrays),"cases":len(cases),"data_bundle_sha256":authority["data_bundle_sha256"]},sort_keys=True))
    return authority

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--ross-root",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();generate(a.ross_root,a.out)
