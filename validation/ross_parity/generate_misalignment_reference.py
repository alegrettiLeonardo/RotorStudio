"""Generate C1 misalignment authority from the frozen ROSS checkout only."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path
import numpy as np

ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"
ROOT=Path(__file__).resolve().parents[2]

def sha256(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path:Path,value)->None:
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def dfft(x:np.ndarray,dt:float):
    x=np.asarray(x,float)
    amp=np.abs(np.fft.rfft(x))/len(x)
    if len(amp)>1:
        amp[1:]*=2.0
        if len(x)%2==0:
            amp[-1]/=2.0
    return np.fft.rfftfreq(len(x),dt),amp

def build_rotor(rs,spec):
    mat=rs.Material(name="C1Steel",rho=spec["rho_kg_m3"],E=spec["E_pa"],G_s=spec["G_pa"])
    shafts=[
        rs.ShaftElement(
            L=float(L),idl=spec["inner_diameter_m"],odl=spec["outer_diameter_m"],
            material=mat,alpha=0.0,beta=0.0,
            shear_effects=True,rotary_inertia=True,gyroscopic=True,
        )
        for L in spec["lengths_m"]
    ]
    d=spec["disk"]
    disk=rs.DiskElement(n=int(d["node_ross"]),m=d["m_kg"],Id=d["Id_kg_m2"],Ip=d["Ip_kg_m2"])
    bearings=[]
    for b in spec["bearings"]:
        bearings.append(rs.BearingElement(
            n=int(b["node_ross"]),
            kxx=b["kxx_n_m"],kyy=b["kyy_n_m"],kzz=0.0,
            cxx=b["cxx_ns_m"],cyy=b["cyy_ns_m"],czz=0.0,
        ))
    rotor=rs.Rotor(shafts,[disk],bearings)
    if rotor.number_dof!=6:
        raise RuntimeError(f"expected 6 DOF/node from frozen ROSS, got {rotor.number_dof}")
    return rotor

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ross-root",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    ross_root=Path(args.ross_root).resolve()
    sys.path.insert(0,str(ross_root))
    import ross as rs
    from ross.faults.misalignment import MisalignmentFlex,MisalignmentRigid

    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    spec=json.loads((ROOT/"validation/c1/cases.json").read_text(encoding="utf-8"))
    tr=spec["transient"]
    dt=float(tr["dt_s"])
    t=np.arange(tr["time_start_s"],tr["time_stop_s"]+0.25*dt,dt,dtype=float)
    speed=float(tr["speed_rad_s"])
    nodes=[int(x["node_ross"]) for x in tr["unbalance"]]
    mags=[float(x["magnitude_kg_m"]) for x in tr["unbalance"]]
    phases=[float(x["phase_rad"]) for x in tr["unbalance"]]
    obs=int(tr["observation_node_ross"])

    source_files=[
        ross_root/"ross/faults/misalignment.py",
        ross_root/"ross/tests/test_misalignment.py",
        ross_root/"ross/rotor_assembly.py",
        ross_root/"ross/utils.py",
    ]
    provenance={
        "ross_sha":ROSS_SHA,
        "production_solver":"NOT_USED",
        "sources":{str(p.relative_to(ross_root)).replace("\\","/"):sha256(p) for p in source_files},
        "python":sys.version.split()[0],
        "numpy":np.__version__,
    }
    write_json(out/"source_provenance.json",provenance)
    write_json(out/"cases.json",spec)
    (out/".gitattributes").write_text("*.npy binary\n*.npz binary\n",encoding="utf-8")

    summaries=[]
    for case in spec["cases"]:
        rotor=build_rotor(rs,spec["model"])
        base_force,theta,omega,alpha=rotor.unbalance_force_over_time(
            nodes,mags,phases,speed,t,return_all=True
        )
        elem=int(spec["model"]["coupling_element_ross"])
        common=dict(
            rotor=rotor,n=elem,
            input_torque=float(case.get("input_torque_nm",0.0)),
            load_torque=float(case.get("load_torque_nm",0.0)),
        )
        if case["coupling"]=="flex":
            fault=MisalignmentFlex(
                mis_type=case["mis_type"],
                mis_distance_x=float(case["mis_distance_x_m"]),
                mis_distance_y=float(case["mis_distance_y_m"]),
                mis_angle=float(case["mis_angle_rad"]),
                radial_stiffness=float(case["radial_stiffness_n_m"]),
                bending_stiffness=float(case["bending_stiffness_n"]),
                **common,
            )
            result=fault.run(
                nodes,mags,phases,speed,t,method="newmark",
                gamma=tr["gamma"],beta=tr["beta"],tol=tr["tol"],
            )
            rigid=np.full(4,np.nan)
        else:
            fault=MisalignmentRigid(
                mis_distance=float(case["mis_distance_m"]),**common
            )
            result=fault.run(
                nodes,mags,phases,speed,t,
                gamma=tr["gamma"],beta=tr["beta"],tol=tr["tol"],
            )
            rigid=np.asarray([fault.kl1,fault.kl2,fault.kt1,fault.kt2],float)

        q=np.asarray(result.yout,float)
        fmis=np.asarray(fault.forces,float)
        total=np.asarray(base_force,float)+fmis
        ix=rotor.number_dof*obs
        orbit=np.vstack((q[:,ix],q[:,ix+1]))
        freq,amp=dfft(q[:,ix],dt)

        case_dir=out/"cases"/case["id"];case_dir.mkdir(parents=True,exist_ok=True)
        arrays={
            "time":t,"theta":theta,"omega":omega,"alpha":alpha,
            "base_force":base_force,"misalignment_force":fmis,"total_force":total,
            "q":q,"orbit":orbit,"fft_frequency_hz":freq,"fft_amplitude":amp,
            "rigid_parameters":rigid,
        }
        for name,value in arrays.items():
            np.save(case_dir/f"{name}.npy",np.asarray(value),allow_pickle=False)
        summaries.append({
            "id":case["id"],
            "coupling":case["coupling"],
            "mis_type":case.get("mis_type"),
            "ndof":int(rotor.ndof),
            "n_time":int(len(t)),
            "max_abs_misalignment_force":float(np.max(np.abs(fmis))),
            "max_abs_displacement":float(np.max(np.abs(q))),
            "rigid_parameters":rigid.tolist(),
        })

    write_json(out/"case_results.json",summaries)
    hashes={}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name!="SHA256SUMS.json":
            hashes[str(p.relative_to(out)).replace("\\","/")]=sha256(p)
    write_json(out/"SHA256SUMS.json",hashes)
    print("C1_AUTHORITY_GENERATED",json.dumps({"ross_sha":ROSS_SHA,"cases":len(summaries),"arrays":sum(1 for _ in out.rglob("*.npy"))},sort_keys=True))

if __name__=="__main__":
    main()
