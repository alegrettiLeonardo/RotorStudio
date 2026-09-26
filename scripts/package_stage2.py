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


def linux_runtime_libraries(solver):
    try:
        output = subprocess.check_output(["ldd", str(solver)], text=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    wanted = ("gfortran", "quadmath", "blas", "lapack", "openblas")
    found = {}
    for line in output.splitlines():
        if "=>" not in line:
            continue
        name, rest = line.split("=>", 1)
        token = rest.strip().split()[0] if rest.strip() else ""
        path = Path(token)
        if path.is_file() and any(key in name.lower() for key in wanted):
            found[path.name] = path
    return list(found.values())


def windows_runtime_dlls():
    roots = []
    for variable in ("DRMROTOR_DLL_DIRS", "DRMBEARINGS_DLL_DIRS"):
        explicit = os.environ.get(variable, "")
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
    parser.add_argument("--solver", required=True, help="Qualified libdrmrotor shared library")
    parser.add_argument(
        "--bearing-solver",
        help="Qualified libdrmbearings shared library. Required for the advanced-bearing runtime.",
    )
    parser.add_argument("--dist-dir", default="dist/stage2")
    parser.add_argument("--work-dir", default="build-stage2-pyinstaller")
    parser.add_argument("--id", default=os.environ.get("GITHUB_SHA", "local")[:12])
    args = parser.parse_args()

    solver = Path(args.solver).resolve()
    if not solver.is_file():
        raise SystemExit(f"solver library not found: {solver}")
    bearing_solver = Path(args.bearing_solver).resolve() if args.bearing_solver else None
    if bearing_solver is not None and not bearing_solver.is_file():
        raise SystemExit(f"bearing solver library not found: {bearing_solver}")

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
        "--collect-all", "qtawesome",
        "--add-binary", f"{solver}{os.pathsep}.",
        "--add-data", f"{smoke}{os.pathsep}examples",
    ]
    if bearing_solver is not None:
        pyinstaller.extend(["--add-binary", f"{bearing_solver}{os.pathsep}."])

    runtime_dlls = windows_runtime_dlls() if os.name == "nt" else []
    runtime_shared = []
    if os.name != "nt":
        runtime_shared.extend(linux_runtime_libraries(solver))
        if bearing_solver is not None:
            runtime_shared.extend(linux_runtime_libraries(bearing_solver))

    # Do not add the same BLAS/Fortran runtime twice when both native
    # libraries resolve to the same dependency.
    dependencies = {}
    for dependency in [*runtime_dlls, *runtime_shared]:
        dependencies[str(dependency.resolve())] = dependency
    for dependency in dependencies.values():
        pyinstaller.extend(["--add-binary", f"{dependency}{os.pathsep}."])

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
        "bearing_solver_source_name": bearing_solver.name if bearing_solver else None,
        "bearing_solver_sha256": sha256(bearing_solver) if bearing_solver else None,
        "advanced_bearing_runtime": "BUNDLED" if bearing_solver else "NOT_BUNDLED",
        "windows_runtime_dlls": [p.name for p in runtime_dlls],
        "linux_runtime_libraries": [p.name for p in runtime_shared],
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
