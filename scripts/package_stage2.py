from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from drm_core import AnalysisCase, RotorProject, save_project
from drm_core.units import rpm_to_rad_s


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_example_model():
    path = ROOT / "examples" / "chapter05" / "example_05_08_01.py"
    spec = importlib.util.spec_from_file_location("stage2_package_example", path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError(f"cannot load example {path}")
    spec.loader.exec_module(module)
    return module.build(6)


def make_smoke_project(path: Path):
    model = load_example_model()
    analyses = [
        AnalysisCase(
            "modal",
            {
                "speed_rad_s": float(rpm_to_rad_s(3210.0)),
                "with_eigenvectors": True,
                "with_kappa": True,
            },
            "Packaged Modal",
        ),
        AnalysisCase(
            "modal_sweep",
            {
                "speeds_rad_s": [float(rpm_to_rad_s(v)) for v in (0.0, 1500.0, 3000.0)],
                "with_eigenvectors": True,
                "with_kappa": True,
            },
            "Packaged Campbell",
            {"nx": 2.0},
        ),
    ]
    save_project(RotorProject("Stage 2 Packaged Smoke", model, analyses), path)


def windows_runtime_dlls():
    roots = []
    explicit = os.environ.get("DRMROTOR_DLL_DIRS", "")
    roots.extend(Path(p) for p in explicit.split(os.pathsep) if p)
    ucrt = os.environ.get("UCRT64_BIN")
    if ucrt:
        roots.append(Path(ucrt))
    patterns = (
        "libgfortran*.dll",
        "libquadmath*.dll",
        "libgcc_s_seh-1.dll",
        "libwinpthread-1.dll",
        "libopenblas*.dll",
        "libblas*.dll",
        "liblapack*.dll",
    )
    found = {}
    for root in roots:
        if not root.is_dir():
            continue
        for pattern in patterns:
            for path in root.glob(pattern):
                found[path.name.lower()] = path
    return list(found.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solver", required=True)
    parser.add_argument("--dist-dir", default="dist/stage2")
    parser.add_argument("--work-dir", default="build-stage2-pyinstaller")
    parser.add_argument("--id", default=os.environ.get("GITHUB_SHA", "local")[:12])
    args = parser.parse_args()

    solver = Path(args.solver).resolve()
    if not solver.is_file():
        raise SystemExit(f"solver library not found: {solver}")

    dist_root = Path(args.dist_dir).resolve()
    work_root = Path(args.work_dir).resolve()
    generated = work_root / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    smoke = generated / "Stage2_Smoke.rds"
    make_smoke_project(smoke)

    pyinstaller = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", "RotorDynamicsStudio",
        "--distpath", str(dist_root),
        "--workpath", str(work_root / "work"),
        "--specpath", str(work_root / "spec"),
        "--paths", str(ROOT / "python" / "src"),
        "--collect-all", "matplotlib",
        "--add-binary", f"{solver}{os.pathsep}.",
        "--add-data", f"{smoke}{os.pathsep}examples",
    ]

    runtime_dlls = windows_runtime_dlls() if os.name == "nt" else []
    for dll in runtime_dlls:
        pyinstaller.extend(["--add-binary", f"{dll}{os.pathsep}."])

    pyinstaller.append(str(ROOT / "scripts" / "rotorstudio_entry.py"))
    subprocess.check_call(pyinstaller, cwd=ROOT)

    app_dir = dist_root / "RotorDynamicsStudio"
    if not app_dir.is_dir():
        raise SystemExit(f"PyInstaller output not found: {app_dir}")

    manifest = {
        "schema_version": 1,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "build_id": args.id,
        "solver_source_name": solver.name,
        "solver_sha256": sha256(solver),
        "windows_runtime_dlls": [p.name for p in runtime_dlls],
        "entry": "RotorDynamicsStudio.exe" if os.name == "nt" else "RotorDynamicsStudio",
        "smoke_project": "examples/Stage2_Smoke.rds",
    }
    (app_dir / "STAGE2_BUILD_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )

    archive_base = dist_root / f"RotorDynamicsStudio-{sys.platform}-{args.id}"
    archive = Path(shutil.make_archive(str(archive_base), "zip", dist_root, "RotorDynamicsStudio"))
    manifest["archive"] = archive.name
    manifest["archive_size"] = archive.stat().st_size
    manifest["archive_sha256"] = sha256(archive)
    report = dist_root / f"PACKAGE_{sys.platform}.json"
    report.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
