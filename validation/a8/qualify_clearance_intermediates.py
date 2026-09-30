"""Read-only response-first A8 audit against the actual frozen ROSS checkout.

A8 calls the already-qualified A3 Fortran response internally. Its v1 ABI does
not export that internal complex array. This audit compares the shared A3
native response to ROSS before checking native A8 probe/orbit/scalar outputs.
The independent SVD is validation-only; no Python solver is added to production.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
PARITY=ROOT/"validation"/"ross_parity"
ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"
sys.path.insert(0,str(ROOT/"python"/"src"))
sys.path.insert(0,str(ROOT/"python"/"tests_clearance"))
sys.path.insert(0,str(PARITY))


def git(root,*args):
    return subprocess.check_output(["git",*args],cwd=root,text=True).strip()


def audit(ross_root:Path,out:Path):
    import numpy as np
    import scipy
    import ross as rs
    from ross import results as ross_results
    from ross.utils import convert_6dof_to_4dof
    from drm_core import run_clearance,run_forced_response
    from test_clearance import CASES,TOL,args_for,standard_model,map2d_model
    from generate_clearance_reference import base_rotor,probes

    ross_root=ross_root.resolve();out=out.resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    report={"status":"FAIL","head_sha":git(ROOT,"rev-parse","HEAD"),
            "ross_sha":ROSS_SHA,"python":sys.version,"numpy":np.__version__,
            "scipy":scipy.__version__,"cases":{},"tolerances":deepcopy(TOL)}
    arrays={}
    try:
        assert git(ross_root,"rev-parse","HEAD")==ROSS_SHA
        assert Path(rs.__file__).resolve().is_relative_to(ross_root)
        subprocess.run(["git","diff","--exit-code","HEAD","--"],cwd=ross_root,check=True)
        manifest=json.loads((PARITY/"clearance"/"authority.json").read_text())
        assert manifest["commit"]==ROSS_SHA
        for relative,digest in manifest["source_sha256"].items():
            assert hashlib.sha256((ross_root/relative).read_bytes()).hexdigest()==digest,relative
        for relative,digest in manifest["golden_sha256"].items():
            assert hashlib.sha256((PARITY/"clearance"/relative).read_bytes()).hexdigest()==digest,relative
        report["source_sha256"]=manifest["source_sha256"]
        report["source_mapping"]={}
        methods={
            "Rotor.run_clearance_analysis":rs.Rotor.run_clearance_analysis,
            "Rotor.api617_unbalance":rs.Rotor.api617_unbalance,
            "Rotor.run_unbalance_response":rs.Rotor.run_unbalance_response,
            "Rotor.run_forced_response":rs.Rotor.run_forced_response,
            "ForcedResponseResults.data_magnitude":ross_results.ForcedResponseResults.data_magnitude,
            "Orbit.__init__":ross_results.Orbit.__init__,
            "Orbit.calculate_amplitude":ross_results.Orbit.calculate_amplitude,
            "ClearanceResults.passed":ross_results.ClearanceResults.passed.fget,
            "ClearanceResults.speed_at_max_response":ross_results.ClearanceResults.speed_at_max_response.fget,
        }
        for label,method in methods.items():
            method=inspect.unwrap(method)
            lines,start=inspect.getsourcelines(method)
            filename=Path(inspect.getsourcefile(method)).resolve()
            report["source_mapping"][label]={"file":str(filename.relative_to(ross_root)),
                "start_line":start,"end_line":start+len(lines)-1}
        library=Path(os.environ["DRMROTOR_LIB"]).resolve()
        report["native_library_sha256"]=hashlib.sha256(library.read_bytes()).hexdigest()
        report["native_boundary"]={"clearance_abi":"rd_clearance_v1",
            "complex_response":"shared native A3 used internally by A8; not an A8 ABI output",
            "orbit_minor":"independent SVD validation oracle, not a production output"}

        for name in CASES:
            frozen,kwargs=args_for(name)
            model=map2d_model() if name=="map_2d" else standard_model()
            canonical=deepcopy(model.canonical_dict());model_hash=model.model_hash()
            native=run_clearance(model,**kwargs)
            rotor=convert_6dof_to_4dof(base_rotor(rs,np,map_backed=name=="map_2d"))
            spec=frozen["input"]
            explicit=spec["explicit_unbalance"]
            ross_args=dict(speed_range=spec["speed_range_rad_s"],
                minimum_allowable_speed=spec["minimum_allowable_speed_rad_s"],
                maximum_continuous_speed=spec["maximum_continuous_speed_rad_s"],
                probes=probes(rs,np),mode=spec["mode"],
                scale_factor_cap=spec["scale_factor_cap"],num_modes=spec["num_modes"])
            if explicit is not None:
                ross_args.update(node=explicit["node"],unbalance_magnitude=explicit["magnitude"],
                                 unbalance_phase=explicit["phase"])
            reference=rotor.run_clearance_analysis(**ross_args)
            metrics={}

            def close(label,got,want,tolerance):
                a=np.asarray(got);b=np.asarray(want)
                assert a.shape==b.shape,(name,label,a.shape,b.shape)
                np.testing.assert_allclose(a,b,equal_nan=False,err_msg=name+":"+label,**tolerance)
                metrics[label]=float(np.max(np.abs(a-b))) if a.size else 0.

            close("speed_rad_s",native.speed_range_rad_s,reference.speed_range,TOL["speed"])
            np.testing.assert_array_equal(native.unbalance_nodes-1,reference.unbalance_node)
            close("unbalance_kg_m",native.unbalance_magnitude_kg_m,reference.unbalance_magnitude,TOL["unbalance"])
            p=np.asarray(reference.unbalance_phase,float)
            close("relative_phase_rad",np.mod(native.unbalance_phase_rad-native.unbalance_phase_rad[0],2*np.pi),
                  np.mod(p-p[0],2*np.pi),dict(rtol=0,atol=2e-10))
            phase=0. if explicit is not None else float(native.unbalance_phase_rad[0]-p[0])
            if explicit is not None:
                close("explicit_phase_rad",native.unbalance_phase_rad,p,dict(rtol=0,atol=2e-10))
                assert native.mode is None and native.mode_index is None and native.mode_frequency_rad_s is None
            else:
                assert native.mode==reference.mode and native.mode_index==reference.mode_index
                close("mode_frequency_rad_s",native.mode_frequency_rad_s,reference.mode_frequency,dict(rtol=3e-8,atol=3e-7))
            w=native.speed_range_rad_s
            force=np.zeros((4*len(model.nodes),len(w)),dtype=complex)
            for node,u,angle in zip(native.unbalance_nodes,native.unbalance_magnitude_kg_m,native.unbalance_phase_rad):
                fx=u*w*w*np.exp(1j*angle)
                force[4*(node-1)]+=fx;force[4*(node-1)+1]+=-1j*fx
            q=run_forced_response(model,w,force.real,force.imag,speed=None).displacement
            rq=rotor.run_unbalance_response(reference.unbalance_node,reference.unbalance_magnitude,
                                            reference.unbalance_phase,reference.speed_range).forced_resp
            assert rotor.number_dof==4 and q.shape==rq.shape
            aligned=rq*np.exp(1j*phase)
            xy=np.array([4*n+k for n in range(len(model.nodes)) for k in (0,1)])
            # Gate real and imaginary displacement before any absolute value,
            # projection, orbit semi-axis, normalization or clearance decision.
            close("complex_xy_real_m",q[xy].real,aligned[xy].real,TOL["response"])
            close("complex_xy_imag_m",q[xy].imag,aligned[xy].imag,TOL["response"])

            np.testing.assert_array_equal(native.probe_nodes-1,reference.probe_nodes)
            close("probe_angles_rad",native.probe_angles_rad,reference.probe_angles,dict(rtol=0,atol=2e-15))
            close("probe_pkpk_m",native.probe_response_m_pp,reference.probe_response,TOL["response"])
            mask=(w>=native.minimum_allowable_speed_rad_s)&(w<=native.maximum_continuous_speed_rad_s)
            assert native.minimum_allowable_speed_rad_s in w and native.maximum_continuous_speed_rad_s in w
            assert native.max_probe_amplitude_m_pp==float(native.probe_response_m_pp[:,mask].max())
            close("Amax_m",native.max_probe_amplitude_m_pp,reference.max_probe_amplitude,TOL["scalar"])
            close("Avl_m",native.vibration_limit_m_pp,reference.vibration_limit,dict(rtol=2e-12,atol=2e-15))
            close("Scc",native.scale_factor,reference.scale_factor,TOL["scale"])
            if native.scale_factor_cap is None:
                assert native.scale_factor==native.vibration_limit_m_pp/native.max_probe_amplitude_m_pp
            else:assert native.scale_factor<=native.scale_factor_cap

            np.testing.assert_array_equal(native.clearance_nodes-1,reference.clearance_nodes)
            close("diametral_clearance_m",native.diametral_clearance_m,reference.diametral_clearance,dict(rtol=2e-12,atol=2e-15))
            major=np.empty_like(native.clearance_response_m_pp);minor=np.empty_like(major)
            rmajor=np.empty_like(major);rminor=np.empty_like(major)
            for j,node in enumerate(native.clearance_nodes):
                dof=4*(node-1)
                for i in range(len(w)):
                    x,y=q[dof,i],q[dof+1,i]
                    major[j,i],minor[j,i]=np.linalg.svd(
                        np.array([[x.real,-x.imag],[y.real,-y.imag]]),compute_uv=False)
                    orbit=ross_results.Orbit(node=int(node-1),node_pos=float(rotor.nodes_pos[node-1]),
                        ru_e=rq[dof,i],rv_e=rq[dof+1,i])
                    rmajor[j,i]=orbit.major_axis;rminor[j,i]=orbit.minor_axis
            assert np.all(major>=minor) and np.all(minor>=0)
            close("orbit_major_m",major,rmajor,TOL["response"])
            close("orbit_minor_m",minor,rminor,TOL["response"])
            close("native_orbit_pkpk_identity_m",native.clearance_response_m_pp,
                  2*native.scale_factor*major,dict(rtol=5e-12,atol=1e-16))
            close("clearance_pkpk_m",native.clearance_response_m_pp,reference.clearance_response,TOL["response"])
            close("max_clearance_pkpk_m",native.max_clearance_response_m_pp,reference.max_clearance_response,TOL["response"])
            close("clearance_limit_m",native.clearance_limit_m,reference.clearance_limit,dict(rtol=2e-12,atol=2e-15))
            np.testing.assert_array_equal(native.passed,reference.passed)
            observable=np.asarray(reference.max_clearance_response)>1e-12
            close("observable_speed_at_max_rad_s",native.speed_at_max_response_rad_s[observable],
                  np.asarray(reference.speed_at_max_response)[observable],TOL["speed"])
            assert np.all(native.max_clearance_response_m_pp[~observable]<1e-12)
            assert model.canonical_dict()==canonical and model.model_hash()==model_hash
            report["cases"][name]={"status":"PASS","maximum_absolute_differences":metrics,
                "global_phase_alignment_rad":phase,"speed_points":len(w),
                "probe_shape":list(native.probe_response_m_pp.shape),
                "clearance_shape":list(native.clearance_response_m_pp.shape),
                "nonobservable_argmax_nodes":native.clearance_nodes[~observable].tolist(),
                "model_hash_unchanged":True}
            data={"speed":w,"force":force,"native_q_xy":q[xy],"ross_q_xy":rq[xy],
                "ross_aligned_q_xy":aligned[xy],"probe_native":native.probe_response_m_pp,
                "probe_ross":reference.probe_response,"major_svd":major,"minor_svd":minor,
                "major_ross":rmajor,"minor_ross":rminor,"clearance_native":native.clearance_response_m_pp,
                "clearance_ross":reference.clearance_response}
            arrays.update({name+"__"+key:np.asarray(value) for key,value in data.items()})
        subprocess.run(["git","diff","--exit-code","HEAD","--","validation/ross_parity"],cwd=ROOT,check=True)
        report["status"]="PASS"
    except Exception as exc:
        report["error"]=f"{type(exc).__name__}: {exc}"
        raise
    finally:
        archive=out.with_suffix(".npz")
        np.savez_compressed(archive,**arrays)
        report["numeric_archive"]=archive.name
        report["numeric_archive_sha256"]=hashlib.sha256(archive.read_bytes()).hexdigest()
        out.write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
        print(json.dumps(report,indent=2,sort_keys=True))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--ross-root",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    audit(args.ross_root,args.out)
