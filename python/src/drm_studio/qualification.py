from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QTimer

from drm_core import AnalysisCase
from drm_core.units import rpm_to_rad_s
from drm_studio.main_window import MainWindow
from drm_studio.result_views.io import export_view_plot_bundle


class PackagedQualification(QObject):
    """Drive the frozen GUI through a real modal → Campbell → reopen → modal smoke.

    No mock backend is used.  The normal MainWindow/SolverJobManager/AnalysisService
    path remains active and therefore reaches the packaged Fortran library.
    """

    def __init__(self, app, window: MainWindow, output_dir, project_path):
        super().__init__(window)
        self.app = app
        self.window = window
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.project_path = Path(project_path)
        self.stage = "initial"
        self.records = []
        self._connect_window(window)

    def _connect_window(self, window):
        window.session.resultAdded.connect(self._result_added)
        window.jobs.failed.connect(self._failed)
        window.jobs.cancelled.connect(
            lambda case, reason: self._abort(f"unexpected cancellation: {case.name or case.kind}: {reason}")
        )

    def start(self):
        try:
            self.window.open_project(self.project_path)
            self.window.show()
            self.stage = "modal_first"
            self._run_case("modal")
        except Exception as exc:
            self._abort(f"startup/open failed: {type(exc).__name__}: {exc}")

    def _case(self, kind):
        for case in self.window.session.project.analyses:
            if case.kind == kind:
                return case
        if kind == "modal":
            return AnalysisCase(
                "modal",
                {
                    "speed_rad_s": float(rpm_to_rad_s(3210.0)),
                    "with_eigenvectors": True,
                    "with_kappa": True,
                },
                "Packaged Modal",
            )
        if kind == "modal_sweep":
            return AnalysisCase(
                "modal_sweep",
                {
                    "speeds_rad_s": [
                        float(rpm_to_rad_s(v)) for v in (0.0, 1500.0, 3000.0)
                    ],
                    "with_eigenvectors": True,
                    "with_kappa": True,
                },
                "Packaged Campbell",
                {"nx": 2.0},
            )
        raise ValueError(kind)

    def _run_case(self, kind):
        if not self.window.run_analysis(self._case(kind)):
            raise RuntimeError(f"UI rejected qualification analysis {kind!r}")

    def _result_added(self, record):
        self.records.append(record)
        QTimer.singleShot(0, lambda r=record: self._after_result(r))

    def _after_result(self, record):
        try:
            backend = record.execution.build_metadata.get("backend")
            if backend != "Fortran2018/ctypes":
                raise RuntimeError(f"unexpected backend {backend!r}")

            if self.stage == "modal_first":
                self.stage = "campbell"
                self._run_case("modal_sweep")
                return

            if self.stage == "campbell":
                view = self.window._result_tabs.get(record.key)
                if view is None:
                    raise RuntimeError("Campbell result view was not created")
                exports = export_view_plot_bundle(
                    view, self.output_dir / "packaged_campbell"
                )
                for path in exports.values():
                    if not path.exists() or path.stat().st_size == 0:
                        raise RuntimeError(f"empty plot export: {path}")

                saved = self.output_dir / "packaged_saved_project.rds"
                self.window.save_project(saved)
                if not saved.exists() or saved.stat().st_size == 0:
                    raise RuntimeError("project save produced no file")

                self.window.close()
                self.window = MainWindow()
                self._connect_window(self.window)
                self.window.open_project(saved)
                self.window.show()
                self.stage = "modal_reopened"
                self._run_case("modal")
                return

            if self.stage == "modal_reopened":
                screenshot = self.output_dir / "packaged_reopened_modal.png"
                self.window.grab().save(str(screenshot))
                if not screenshot.exists() or screenshot.stat().st_size == 0:
                    raise RuntimeError("packaged screenshot was not produced")
                payload = {
                    "status": "PASS",
                    "backend": "Fortran2018/ctypes",
                    "steps": [
                        "launch",
                        "open packaged example",
                        "real modal",
                        "real Campbell",
                        "export PNG/SVG/PDF",
                        "save project",
                        "close window",
                        "reopen saved project",
                        "real modal recompute",
                    ],
                    "result_count": len(self.records),
                    "saved_project": str(self.output_dir / "packaged_saved_project.rds"),
                    "screenshot": str(screenshot),
                }
                (self.output_dir / "PACKAGED_SMOKE.json").write_text(
                    json.dumps(payload, indent=2, sort_keys=True)
                )
                self.window.close()
                self.app.exit(0)
        except Exception as exc:
            self._abort(f"{type(exc).__name__}: {exc}")

    def _failed(self, failure):
        self._abort(
            f"solver failure {failure.exception_type}: {failure.message}; "
            f"guidance={failure.guidance}"
        )

    def _abort(self, message):
        payload = {"status": "FAIL", "message": message, "stage": self.stage}
        (self.output_dir / "PACKAGED_SMOKE.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True)
        )
        try:
            self.window.close()
        finally:
            self.app.exit(2)
