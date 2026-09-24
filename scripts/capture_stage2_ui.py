from __future__ import annotations

import argparse
import copy
import importlib.util
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from drm_core import AnalysisCase, AnalysisService, RotorProject
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
    model = example.build(6)
    case = AnalysisCase(
        "modal",
        {
            "speed_rad_s": rpm_to_rad_s(5000.0),
            "with_eigenvectors": True,
            "with_kappa": True,
        },
        "Example_05_08_01 — Modal",
    )
    project = RotorProject("Example_05_08_01", model, [case])
    session = ProjectSession(project)
    window = MainWindow(session=session)
    window.show()
    session.set_selection(EntityRef("shaft", 2))
    window.model_page.view.fit_view()
    app.processEvents()
    assert window.grab().save(str(outdir / "rotor_model.png"))

    execution = AnalysisService().execute(project, case)
    record = session.add_result(execution, model_snapshot=copy.deepcopy(model))
    window._show_result(record)
    app.processEvents()
    assert window.grab().save(str(outdir / "modal_results.png"))

    print(outdir / "rotor_model.png")
    print(outdir / "modal_results.png")
    window.close()


if __name__ == "__main__":
    main()
