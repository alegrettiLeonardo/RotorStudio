from __future__ import annotations

import argparse
import copy
import importlib.util
from pathlib import Path

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from drm_core import AnalysisCase, AnalysisService, RotorProject, Force, Bearing
from drm_core.units import rpm_to_rad_s
from drm_studio.application.session import EntityRef, ProjectSession
from drm_studio.main_window import MainWindow


def load_example():
    root = Path(__file__).resolve().parents[1]
    path = root / "examples" / "chapter05" / "example_05_08_01.py"
    spec = importlib.util.spec_from_file_location("example_05_08_01_capture", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def capture(window, app, path):
    window.show()
    app.processEvents()
    window.model_page.view.fit_view()
    app.processEvents()
    assert window.grab().save(str(path))
    assert path.exists() and path.stat().st_size > 0


def show_real_result(window, project, case):
    execution = AnalysisService().execute(project, case)
    assert execution.build_metadata["backend"] == "Fortran2018/ctypes"
    record = window.session.add_result(execution, model_snapshot=copy.deepcopy(project.model))
    window._show_result(record)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="validation/reports/stage2_screenshots")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    QCoreApplication.setOrganizationName("RotorStudio-CI")
    QCoreApplication.setApplicationName("Rotor Dynamics Studio Capture")
    app = QApplication.instance() or QApplication([])

    example = load_example()

    # Mockup 1 — real Rotor Model application shell.
    model = example.build(6)
    project = RotorProject("Example_05_08_01", model)
    session = ProjectSession(project)
    window = MainWindow(session=session)
    session.set_selection(EntityRef("shaft", 2))
    capture(window, app, outdir / "rotor_model.png")
    window.close()

    # Mockup 3 — real Campbell result workspace from the qualified Fortran solver.
    model = example.build(6)
    campbell = AnalysisCase(
        "modal_sweep",
        {
            "speeds_rad_s": [float(rpm_to_rad_s(v)) for v in (0.0, 1500.0, 3000.0, 4500.0)],
            "with_eigenvectors": True,
            "with_kappa": True,
        },
        "Campbell — Screenshot",
        {"nx": 2.0},
    )
    project = RotorProject("Campbell Screenshot", model, [campbell])
    window = MainWindow(session=ProjectSession(project))
    show_real_result(window, project, campbell)
    capture(window, app, outdir / "campbell_results.png")
    window.close()

    # Mockup 2 boundary — actual Stage 1 short hydrodynamic bearing editor only.
    model = example.build(6)
    model.bearings[0] = Bearing(7, model.bearings[0].node, (1234.5, 0.053217, 0.017413, 0.000123, 0.0321))
    project = RotorProject("Bearing Seal Editor", model)
    session = ProjectSession(project)
    window = MainWindow(session=session)
    session.set_selection(EntityRef("bearing", 0))
    window._open_bearing_performance()
    capture(window, app, outdir / "bearing_seal_editor.png")
    window.close()

    # Real modal workspace with the Stage 2.1 orbit-rich 3-D mode shape.
    model = example.build(6)
    modal = AnalysisCase(
        "modal",
        {
            "speed_rad_s": float(rpm_to_rad_s(4000.0)),
            "with_eigenvectors": True,
            "with_kappa": True,
        },
        "Mode Shape 3D — Screenshot",
    )
    project = RotorProject("Mode Shape 3D Screenshot", model, [modal])
    window = MainWindow(session=ProjectSession(project))
    show_real_result(window, project, modal)
    capture(window, app, outdir / "mode_shape_3d.png")
    window.close()

    # Real synchronous response workspace.
    model = example.build(6)
    model.forces = [Force(1, (3, 2.321e-4, 0.217))]
    frf = AnalysisCase(
        "frequency_response",
        {"speeds_rad_s": [float(rpm_to_rad_s(v)) for v in np.linspace(100.0, 4500.0, 31)]},
        "Synchronous Response — Screenshot",
        {"outnodes": [3.1]},
    )
    project = RotorProject("Frequency Response Screenshot", model, [frf])
    window = MainWindow(session=ProjectSession(project))
    show_real_result(window, project, frf)
    capture(window, app, outdir / "frequency_response.png")
    window.close()

    # Real run-up/transient result workspace.
    model = example.build(6)
    model.forces = [Force(1, (3, 1.234e-4, 0.0))]
    runup = AnalysisCase(
        "runup",
        {
            "alpha": [0.20 * 2.0 * np.pi, 8.0 * np.pi, 0.0],
            "tspan": [0.0, 0.25],
            "nr": 4,
            "rtol": 1.0e-5,
            "atol": 1.0e-8,
            "max_points": 20000,
        },
        "Run-up — Screenshot",
        {"outnode": 3.1},
    )
    project = RotorProject("Run-up Screenshot", model, [runup])
    window = MainWindow(session=ProjectSession(project))
    show_real_result(window, project, runup)
    capture(window, app, outdir / "runup_transient.png")
    window.close()

    for name in (
        "rotor_model.png", "campbell_results.png", "bearing_seal_editor.png",
        "mode_shape_3d.png", "frequency_response.png", "runup_transient.png",
    ):
        print(outdir / name)


if __name__ == "__main__":
    main()
