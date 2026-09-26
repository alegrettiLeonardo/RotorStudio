from __future__ import annotations

import json
import numpy as np
from pathlib import Path

from PySide6.QtCore import QObject, QTimer

from drm_core import (
    AnalysisCase, BallBearing, Bearing, Node, PlainJournalPhysicsBearing,
    RotorModel, ShaftElement,
)
from drm_core.solver.facade import SolverFacade
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
        self.bearing_smoke = None
        self.fluidfilm_smoke = None
        self.b13_crud_smoke = None
        self._connect_window(window)

    def _connect_window(self, window):
        window.session.resultAdded.connect(self._result_added)
        window.jobs.failed.connect(self._failed)
        window.jobs.cancelled.connect(
            lambda case, reason: self._abort(f"unexpected cancellation: {case.name or case.kind}: {reason}")
        )

    def start(self):
        try:
            # B13 qualification starts with the real PySide6 engineering
            # editor/command/persistence chain. Reading or editing these
            # entities does not run Reynolds/THD/TEHD.
            from .b13_qualification import run_b13_frozen_crud_smoke
            self.b13_crud_smoke = run_b13_frozen_crud_smoke(
                self.window, self.output_dir
            )

            # Prove that the separately packaged advanced-bearing library can
            # be loaded from a clean frozen extraction before any rotor solve.
            bearing = BallBearing(
                node=1,
                n_balls=8,
                d_balls_m=0.03,
                static_load_n=500.0,
                alpha_rad=0.5235987755982988,
            )
            evaluated = SolverFacade().advanced_bearing(
                bearing, speed_rad_s=100.0
            )
            kxx = float(evaluated.K[0, 0])
            if abs(kxx - 4.64168838e7) > 1e-7 * 4.64168838e7:
                raise RuntimeError(
                    f"packaged advanced-bearing oracle mismatch: Kxx={kxx}"
                )
            self.bearing_smoke = {
                "family": evaluated.model_family,
                "kxx_n_m": kxx,
                "status": "PASS",
            }

            # Promotion smoke: prove the B12-qualified native PlainJournal can
            # cross the normal advanced-bearing -> type-5 adapter -> rotor
            # assembly path in the clean frozen application.  This does not
            # alter the historical type 1-8 / 20 implementation.
            fluid = PlainJournalPhysicsBearing(
                node=1,
                weight_n=112814.90696191376,
                journal_diameter_m=0.3999992,
                radial_clearance_m=0.000194564,
                oil_viscosity_pa_s=0.01901574061455835,
                pivot_angle_rad=(1.5707963267948966, 4.71238898038469),
                pad_arc_rad=(3.07177948351002, 3.07177948351002),
                pad_axial_length_m=(0.263144, 0.263144),
                preload=(0.0, 0.0),
                offset=(0.5, 0.5),
                total_e_x_film=20,
                total_e_z_film=10,
                xj_ratio_initial=0.15,
                yj_ratio_initial=-0.2,
                force_tolerance=5e-3,
            )
            speed = 94.24777960769379
            fluid_eval = SolverFacade().advanced_bearing(
                fluid, speed_rad_s=speed, frequency_rad_s=speed
            )
            if fluid_eval.details.get("qualification") != "ROSS_PARITY_PASS_B12":
                raise RuntimeError(
                    f"packaged native fluid-film qualification missing: {fluid_eval.details}"
                )
            model = RotorModel(
                nodes=[Node(1, 0.0), Node(2, 1.0)],
                shafts=[
                    ShaftElement(
                        2, 1, 2, 0.05, 0.0, 7810.0, 211e9, 81.2e9,
                        0.0, 0.0, 0.0
                    )
                ],
                bearings=[
                    Bearing(
                        5, 2,
                        (1.5e6, 0.0, 0.0, 1.5e6, 150.0, 0.0, 0.0, 150.0),
                    )
                ],
                advanced_bearings=[fluid],
            )
            assembled = SolverFacade().assemble(model, speed)
            if not all(np.isfinite(matrix).all() for matrix in assembled):
                raise RuntimeError("packaged native fluid-film rotor assembly is non-finite")
            self.fluidfilm_smoke = {
                "family": fluid_eval.model_family,
                "qualification": fluid_eval.details["qualification"],
                "ross_authority_sha": fluid_eval.details["ross_authority_sha"],
                "rotor_assembly": "PASS",
                "status": "PASS",
            }

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
                        "B13 advanced-bearing GUI CRUD + save/reopen",
                        "native advanced-bearing load/oracle",
                        "real modal",
                        "real Campbell",
                        "export PNG/SVG/PDF",
                        "save project",
                        "close window",
                        "reopen saved project",
                        "real modal recompute",
                    ],
                    "result_count": len(self.records),
                    "advanced_bearing": self.bearing_smoke,
                    "b13_advanced_bearing_crud": self.b13_crud_smoke,
                    "native_fluidfilm_bearing": self.fluidfilm_smoke,
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
