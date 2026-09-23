from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from drm_core.domain.model import RotorModel
from drm_core.validation.model import validate_model
from drm_core.analysis import run_modal, run_campbell, run_frequency_response, run_critical_speeds
from drm_core.units import rpm_to_rad_s


def _load_model(path: str) -> RotorModel:
    data = json.loads(Path(path).read_text())
    return RotorModel.from_legacy_arrays(
        data.get("node", []), data.get("shaft", []), data.get("disc", []),
        data.get("bearing", []), data.get("force", []), data.get("bend", []),
    )


def _speed_grid(start_rpm: float, stop_rpm: float, step_rpm: float) -> np.ndarray:
    if step_rpm <= 0 or stop_rpm < start_rpm:
        raise SystemExit("expected step-rpm > 0 and stop-rpm >= start-rpm")
    return rpm_to_rad_s(np.arange(start_rpm, stop_rpm + 0.5 * step_rpm, step_rpm, dtype=float))


def main():
    p = argparse.ArgumentParser(prog="drm-cli", description="GUI-independent RotorStudio Stage-1 CLI")
    p.add_argument("--lib", help="path to libdrmrotor.so/drmrotor.dll")
    sp = p.add_subparsers(dest="cmd", required=True)

    v = sp.add_parser("validate")
    v.add_argument("model")

    m = sp.add_parser("modal")
    m.add_argument("model")
    m.add_argument("--speed-rpm", type=float, default=0.0)

    c = sp.add_parser("campbell")
    c.add_argument("model")
    c.add_argument("--start-rpm", type=float, required=True)
    c.add_argument("--stop-rpm", type=float, required=True)
    c.add_argument("--step-rpm", type=float, required=True)

    f = sp.add_parser("frequency-response")
    f.add_argument("model")
    f.add_argument("--start-rpm", type=float, required=True)
    f.add_argument("--stop-rpm", type=float, required=True)
    f.add_argument("--step-rpm", type=float, required=True)
    f.add_argument("--output", help="optional NPZ output")

    cs = sp.add_parser("critical-speeds")
    cs.add_argument("model")
    cs.add_argument("--nx", type=float, default=1.0)
    cs.add_argument("--number", type=int, default=5)
    cs.add_argument("--method", choices=["auto", "direct", "iterative", "iterative-index", "iterative-nearest"], default="auto")
    cs.add_argument("--max-iterations", type=int, default=20)
    cs.add_argument("--tol", type=float, default=1e-6)
    cs.add_argument("--undamped", action="store_true")
    cs.add_argument("--initial-rpm", type=float, nargs="*")

    a = p.parse_args()
    model = _load_model(a.model)
    if a.cmd == "validate":
        validate_model(model)
        print("PASS: model validation")
        return
    if a.cmd == "modal":
        r = run_modal(model, float(rpm_to_rad_s(a.speed_rpm)), a.lib)
        print("# index real_rad_s imag_rad_s natural_frequency_hz damping_ratio")
        for i, (lam, hz, zeta) in enumerate(zip(r.eigenvalues, r.natural_frequency_hz, r.damping_ratio), 1):
            print(f"{i} {lam.real:.12e} {lam.imag:.12e} {hz:.12e} {zeta:.12e}")
        return
    if a.cmd == "campbell":
        speeds = _speed_grid(a.start_rpm, a.stop_rpm, a.step_rpm)
        r = run_campbell(model, speeds, a.lib)
        print(f"PASS: campbell speeds={r.speeds_rad_s.size} modes={r.eigenvalues.shape[0]}")
        return
    if a.cmd == "frequency-response":
        speeds = _speed_grid(a.start_rpm, a.stop_rpm, a.step_rpm)
        r = run_frequency_response(model, speeds, a.lib)
        print(f"PASS: frequency-response speeds={r.speeds_rad_s.size} ndof={r.response.shape[0]} max_abs={np.max(np.abs(r.response)):.12e}")
        if a.output:
            np.savez(a.output, speeds_rad_s=r.speeds_rad_s, response=r.response)
        return
    if a.cmd == "critical-speeds":
        initial = None if not a.initial_rpm else rpm_to_rad_s(np.asarray(a.initial_rpm, dtype=float))
        r = run_critical_speeds(
            model, NX=a.nx, damped_NF=not a.undamped, number_criticals=a.number,
            max_iterations=a.max_iterations, convergence_tol=a.tol, method=a.method,
            initial_estimates=initial, library_path=a.lib,
        )
        print("# index rad_s rpm iterations converged")
        for i, (w, it, ok) in enumerate(zip(r.critical_speeds_rad_s, r.iterations, r.converged), 1):
            print(f"{i} {w:.12e} {w*60/(2*np.pi):.9f} {int(it)} {bool(ok)}")
        return


if __name__ == "__main__":
    main()
