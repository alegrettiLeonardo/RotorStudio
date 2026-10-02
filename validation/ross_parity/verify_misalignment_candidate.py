"""Compare C1 misalignment authority candidates under the pre-frozen policy."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]

def group(path:str)->str:
    name=Path(path).stem
    return {
        "time":"time","theta":"theta","omega":"theta","alpha":"theta",
        "base_force":"base_force","misalignment_force":"misalignment_force",
        "total_force":"total_force","q":"displacement","orbit":"orbit",
        "fft_frequency_hz":"fft_frequency","fft_amplitude":"fft_amplitude",
        "rigid_parameters":"rigid_parameters",
    }[name]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reference",required=True)
    ap.add_argument("--candidate",required=True)
    ap.add_argument("--report",required=True)
    args=ap.parse_args()
    ref=Path(args.reference);cand=Path(args.candidate)
    policy=json.loads((ROOT/"validation/c1/TOLERANCE_POLICY.json").read_text())
    ra=sorted(str(p.relative_to(ref)).replace("\\","/") for p in ref.rglob("*.npy"))
    ca=sorted(str(p.relative_to(cand)).replace("\\","/") for p in cand.rglob("*.npy"))
    if ra!=ca:
        raise SystemExit(f"array inventory mismatch: ref-only={sorted(set(ra)-set(ca))}, candidate-only={sorted(set(ca)-set(ra))}")
    rows=[];ok=True
    for rel in ra:
        a=np.load(ref/rel,allow_pickle=False);b=np.load(cand/rel,allow_pickle=False)
        g=group(rel);tol=policy["groups"][g]
        if a.shape!=b.shape:
            passed=False;max_abs=float("inf")
        else:
            finite=np.isfinite(a)&np.isfinite(b)
            nan_equal=np.array_equal(np.isnan(a),np.isnan(b))
            max_abs=float(np.max(np.abs(a[finite]-b[finite]))) if np.any(finite) else 0.0
            passed=nan_equal and np.allclose(a[finite],b[finite],rtol=tol["rtol"],atol=tol["atol"])
        rows.append({"file":rel,"group":g,"max_abs":max_abs,"status":"PASS" if passed else "FAIL"})
        ok &= passed
    for fname in ("cases.json","source_provenance.json"):
        a=json.loads((ref/fname).read_text());b=json.loads((cand/fname).read_text())
        if fname=="source_provenance.json":
            for d in (a,b):
                d.pop("python",None);d.pop("numpy",None)
        same=a==b
        rows.append({"file":fname,"group":"metadata","status":"PASS" if same else "FAIL"})
        ok &= same
    report={"status":"PASS" if ok else "FAIL","array_count":len(ra),"rows":rows}
    Path(args.report).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("C1_AUTHORITY_VERIFY",json.dumps({"status":report["status"],"array_count":len(ra),"max_abs":max((r.get("max_abs",0.0) for r in rows),default=0.0)},sort_keys=True))
    if not ok: raise SystemExit(1)

if __name__=="__main__":
    main()
