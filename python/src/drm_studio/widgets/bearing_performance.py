from __future__ import annotations

import json
import numpy as np

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QToolButton, QLabel,
    QGraphicsView, QGraphicsScene, QTabWidget, QPlainTextEdit,
    QGroupBox, QFormLayout, QDoubleSpinBox, QPushButton, QProgressBar,
    QComboBox,
)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from drm_core import PlainJournalPhysicsBearing, TiltingPadPhysicsBearing
from drm_core.domain.bearings import advanced_bearing_to_dict
from drm_studio.docks.bearing_editor import BearingInspectorWidget, _BEARING_NAMES
from drm_studio.jobs import BearingJobManager, JobState
from drm_studio.resources import studio_icon


class _FieldCanvas(QWidget):
    def __init__(self, mode: str, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.figure = Figure(figsize=(5.2, 3.1), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.pad = QComboBox()
        self.pad.currentIndexChanged.connect(self._redraw)
        self._payload = None
        self._key = None
        self._title = ""
        self._units = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        if mode == "contour":
            row = QHBoxLayout()
            row.addWidget(QLabel("Pad:"))
            row.addWidget(self.pad)
            row.addStretch(1)
            layout.addLayout(row)
        else:
            self.pad.hide()
        layout.addWidget(self.canvas, 1)
        self.clear("No solved field available.")

    def clear(self, message="No solved field available."):
        self._payload = None
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        self.canvas.draw_idle()

    def set_payload(self, payload, key: str, title: str, units: str):
        self._payload = payload
        self._key = key
        self._title = title
        self._units = units
        if self.mode == "contour":
            n = int(np.asarray(payload[key]).shape[0])
            self.pad.blockSignals(True)
            self.pad.clear()
            for i in range(n):
                self.pad.addItem(str(i + 1))
            self.pad.blockSignals(False)
        self._redraw()

    def _redraw(self):
        if not self._payload or self._key not in self._payload:
            return
        values = self._payload.get(self._key)
        if values is None:
            self.clear()
            return
        a = np.asarray(values, dtype=float)
        self.figure.clear()
        if self.mode == "contour":
            pad = max(0, min(self.pad.currentIndex(), a.shape[0] - 1))
            theta = np.asarray(self._payload["theta_rad"], dtype=float)[pad]
            axial = np.asarray(self._payload["axial_position_m"], dtype=float)[pad]
            ax = self.figure.add_subplot(111)
            mesh = ax.pcolormesh(
                axial * 1.0e3,
                np.rad2deg(theta),
                a[pad],
                shading="auto",
            )
            self.figure.colorbar(mesh, ax=ax, label=self._units)
            ax.set_xlabel("Axial position z [mm]")
            ax.set_ylabel("Circumferential angle θ [deg]")
            ax.set_title(f"{self._title} — pad {pad + 1}")
        elif self.mode == "deformation":
            theta = np.asarray(self._payload["theta_rad"], dtype=float)
            ax = self.figure.add_subplot(111)
            for p in range(a.shape[0]):
                ax.plot(np.rad2deg(theta[p]), a[p] * 1.0e6, label=f"Pad {p + 1}")
            ax.set_xlabel("Circumferential angle θ [deg]")
            ax.set_ylabel("Pad deformation [µm]")
            ax.set_title(self._title)
            ax.legend(loc="best")
            ax.grid(True)
        elif self.mode == "pads":
            loads = np.asarray(self._payload.get("pad_load_n"), dtype=float)
            evaluation = self._payload["evaluation"]
            tilt = np.asarray(evaluation.details.get("tilt_angle_rad", []), dtype=float)
            x = np.arange(1, len(loads) + 1)
            ax1 = self.figure.add_subplot(211)
            ax1.bar(x, loads)
            ax1.set_ylabel("Load [N]")
            ax1.set_title("Pad hydrodynamic load")
            ax1.grid(True, axis="y")
            ax2 = self.figure.add_subplot(212)
            if tilt.size:
                ax2.plot(np.arange(1, len(tilt) + 1), tilt, marker="o")
            ax2.set_xlabel("Pad")
            ax2.set_ylabel("Tilt [rad]")
            ax2.set_title("Pad tilt")
            ax2.grid(True)
        self.canvas.draw_idle()


class BearingPerformancePage(QWidget):
    """B14 Bearing Performance: explicit asynchronous native solve + real fields."""

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._last_payload = None
        self._active_request_id = None
        self._active_selection_key = None
        self.jobs = BearingJobManager(self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)

        nav = QHBoxLayout()
        nav.setSpacing(4)
        specs = [
            ("Rigid / K-C", "bearing", True),
            ("Short Hydro", "bearing", True),
            ("Seal", "seal", True),
            ("Tilting-Pad", "bearing", True),
            ("Floating-Ring", "bearing", False),
            ("Gas Bearing", "bearing", False),
            ("Thrust", "bearing", False),
        ]
        self.nav_buttons = {}
        for text, icon_name, enabled in specs:
            b = QToolButton()
            b.setText(text)
            b.setIcon(studio_icon(icon_name))
            b.setIconSize(QSize(24, 24))
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setMinimumWidth(82)
            b.setMinimumHeight(56)
            b.setEnabled(enabled)
            if not enabled:
                b.setToolTip("NOT AVAILABLE / FUTURE — no qualified solver for this family.")
            nav.addWidget(b)
            self.nav_buttons[text] = b
        nav.addStretch(1)
        outer.addLayout(nav)

        body = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        self.editor = BearingInspectorWidget(session)
        self.editor.setMinimumWidth(330)
        left_layout.addWidget(self.editor, 1)

        self.advanced_group = QGroupBox("Native Advanced Bearing Operating Point")
        advanced_form = QFormLayout(self.advanced_group)
        self.speed_field = QDoubleSpinBox()
        self.speed_field.setDecimals(8)
        self.speed_field.setRange(1.0e-9, 1.0e7)
        self.speed_field.setValue(94.24777960769379)
        self.speed_field.setSuffix(" rad/s")
        self.frequency_field = QDoubleSpinBox()
        self.frequency_field.setDecimals(8)
        self.frequency_field.setRange(1.0e-9, 1.0e7)
        self.frequency_field.setValue(94.24777960769379)
        self.frequency_field.setSuffix(" rad/s")
        controls = QWidget()
        crow = QHBoxLayout(controls)
        crow.setContentsMargins(0, 0, 0, 0)
        self.evaluate_button = QPushButton("Evaluate Native Bearing")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.evaluate_button.clicked.connect(self._evaluate_advanced)
        self.cancel_button.clicked.connect(lambda: self.jobs.cancel())
        crow.addWidget(self.evaluate_button)
        crow.addWidget(self.cancel_button)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setFormat("Idle")
        self.advanced_status = QLabel("")
        self.advanced_status.setWordWrap(True)
        advanced_form.addRow("Rotor speed Ω:", self.speed_field)
        advanced_form.addRow("Whirl / excitation ω:", self.frequency_field)
        advanced_form.addRow(controls)
        advanced_form.addRow(self.progress)
        advanced_form.addRow(self.advanced_status)
        self.advanced_group.setVisible(False)
        left_layout.addWidget(self.advanced_group)
        body.addWidget(left)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(3, 3, 3, 3)
        self.heading = QLabel("Bearing / Seal Schematic")
        self.heading.setObjectName("SectionHeaderTitle")
        center_layout.addWidget(self.heading)

        self.scene = QGraphicsScene(self)
        self.graphics = QGraphicsView(self.scene)
        self.graphics.setBackgroundBrush(QBrush(QColor("white")))
        center_layout.addWidget(self.graphics, 1)

        self.lower_tabs = QTabWidget()
        self.summary_note = QPlainTextEdit()
        self.summary_note.setReadOnly(True)
        self.coefficient_note = QPlainTextEdit()
        self.coefficient_note.setReadOnly(True)
        self.pressure_plot = _FieldCanvas("contour")
        self.temperature_plot = _FieldCanvas("contour")
        self.film_plot = _FieldCanvas("contour")
        self.deformation_plot = _FieldCanvas("deformation")
        self.pads_plot = _FieldCanvas("pads")
        self.convergence_note = QPlainTextEdit()
        self.convergence_note.setReadOnly(True)
        self.lower_tabs.addTab(self.summary_note, "Summary")
        self.lower_tabs.addTab(self.coefficient_note, "Dynamic Coefficients")
        self.lower_tabs.addTab(self.pressure_plot, "Pressure")
        self.lower_tabs.addTab(self.temperature_plot, "Temperature")
        self.lower_tabs.addTab(self.film_plot, "Film Thickness")
        self.lower_tabs.addTab(self.deformation_plot, "Deformation")
        self.lower_tabs.addTab(self.pads_plot, "Pads")
        self.lower_tabs.addTab(self.convergence_note, "Convergence")
        self._clear_field_tabs()
        center_layout.addWidget(self.lower_tabs)
        body.addWidget(center)

        body.setStretchFactor(0, 4)
        body.setStretchFactor(1, 7)
        outer.addWidget(body, 1)

        self.jobs.stateChanged.connect(self._job_state)
        self.jobs.progress.connect(self._job_progress)
        self.jobs.completed.connect(self._job_completed)
        self.jobs.cancelled.connect(self._job_cancelled)
        self.jobs.failed.connect(self._job_failed)
        session.selectionChanged.connect(lambda _: self.refresh())
        session.modelChanged.connect(self.refresh)
        self.refresh()

    def _selected(self):
        ref = self.session.selection
        model = self.session.project.model
        if ref is None:
            return None, None
        if ref.kind == "bearing" and 0 <= ref.index < len(model.bearings):
            return "legacy", model.bearings[ref.index]
        if ref.kind == "advanced_bearing" and 0 <= ref.index < len(model.advanced_bearings):
            return "advanced", model.advanced_bearings[ref.index]
        return None, None

    @staticmethod
    def _selection_key(bearing):
        return json.dumps(
            advanced_bearing_to_dict(bearing),
            sort_keys=True,
            separators=(",", ":"),
            default=list,
        )

    def _clear_field_tabs(self):
        for index in range(2, 8):
            self.lower_tabs.setTabEnabled(index, False)
        self.pressure_plot.clear("Pressure available after explicit native field solve.")
        self.temperature_plot.clear("Temperature available after explicit THD/TEHD solve.")
        self.film_plot.clear("Film thickness is returned by the native backend.")
        self.deformation_plot.clear("Deformation available after qualified deformation solve.")
        self.pads_plot.clear("Pad tilt/load available after native solve.")
        self.convergence_note.setPlainText("No active or completed native solve.")

    def refresh(self):
        kind, bearing = self._selected()
        self.scene.clear()
        self._last_payload = None
        self._clear_field_tabs()
        self.advanced_status.clear()

        if bearing is None:
            self.heading.setText("Bearing / Seal Schematic — select a bearing in Project Explorer")
            self.summary_note.setPlainText("Select a legacy or advanced bearing.")
            self.coefficient_note.setPlainText("")
            self.editor.setVisible(True)
            self.advanced_group.setVisible(False)
            return

        if kind == "advanced":
            self.editor.setVisible(False)
            self.advanced_group.setVisible(True)
            family = str(getattr(bearing, "model_family", type(bearing).__name__))
            self.heading.setText(f"{family} — Node {bearing.node}")
            self._draw_advanced_schematic(bearing)
            physical = isinstance(bearing, (PlainJournalPhysicsBearing, TiltingPadPhysicsBearing))
            self.evaluate_button.setEnabled(self.jobs.active is None)
            self.summary_note.setPlainText(
                f"{family} at node {bearing.node}.\n"
                "Evaluation is explicit and asynchronous; selection/painting never starts Reynolds/THD/TEHD."
            )
            if physical:
                self.coefficient_note.setPlainText(
                    "B12 coefficient physics authority: petrobras/ross@"
                    "6320eab9f890f1b3cc1710d508b446fe063ca68d.\n"
                    "B14 adds job control and field transport only; it does not change B12 equations."
                )
            else:
                self.coefficient_note.setPlainText(
                    "Advanced coefficient provider. Evaluate to inspect K/C/M at the requested operating point."
                )
            return

        self.editor.setVisible(True)
        self.advanced_group.setVisible(False)
        name = _BEARING_NAMES.get(bearing.bearing_type, f"Type {bearing.bearing_type}")
        self.heading.setText(f"{name} — Node {bearing.node}")
        self._draw_legacy_schematic(bearing)
        self.summary_note.setPlainText("Qualified legacy bearing path; B14 native fields are not applicable.")
        self.coefficient_note.setPlainText("Legacy persisted bearing properties are unchanged.")

    @staticmethod
    def _matrix_text(name, matrix, units):
        a = np.asarray(matrix, dtype=float)
        return (
            f"{name} [{units}]\n"
            f"  [{a[0,0]: .9e}  {a[0,1]: .9e}]\n"
            f"  [{a[1,0]: .9e}  {a[1,1]: .9e}]"
        )

    def _evaluate_advanced(self):
        kind, bearing = self._selected()
        if kind != "advanced" or bearing is None or self.jobs.active is not None:
            return
        speed = float(self.speed_field.value())
        frequency = float(self.frequency_field.value())
        key = self._selection_key(bearing)
        runnable = self.jobs.submit(bearing, speed, frequency, key)
        self._active_request_id = runnable.request.request_id
        self._active_selection_key = key
        self.evaluate_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setValue(0)
        self.progress.setFormat("Queued")
        self.advanced_status.setStyleSheet("")
        self.advanced_status.setText("Queued native bearing solve…")

    def _job_state(self, state, request):
        if request.request_id != self._active_request_id:
            return
        self.cancel_button.setEnabled(state in (JobState.QUEUED.value, JobState.RUNNING.value, JobState.CANCEL_REQUESTED.value))
        if state == JobState.RUNNING.value:
            self.progress.setFormat("Running — %p%")
            self.advanced_status.setText("Native Reynolds/THD/TEHD worker is running; UI remains responsive.")
        elif state == JobState.CANCEL_REQUESTED.value:
            self.progress.setFormat("Cancel requested — %p%")
            self.advanced_status.setText("Cancellation requested; waiting for the next native safe point.")

    def _job_progress(self, request, progress):
        if request.request_id != self._active_request_id:
            return
        self.progress.setValue(int(round(progress.percent * 10.0)))
        self.progress.setFormat(
            f"{progress.stage}: {progress.iteration}/{progress.max_iterations} — %p%"
        )
        self.convergence_note.setPlainText(
            f"stage = {progress.stage}\n"
            f"iteration = {progress.iteration}\n"
            f"max iterations = {progress.max_iterations}\n"
            f"completed cases = {progress.completed_cases}\n"
            f"total cases = {progress.total_cases}\n"
            f"cancel requested = {progress.cancel_requested}\n"
            f"percent = {progress.percent:.2f}"
        )
        self.lower_tabs.setTabEnabled(7, True)

    def _selection_still_matches(self, request):
        kind, bearing = self._selected()
        return (
            kind == "advanced"
            and bearing is not None
            and request.selection_key == self._selection_key(bearing)
            and request.request_id == self._active_request_id
        )

    def _job_completed(self, outcome):
        request = outcome.request
        self.evaluate_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if not self._selection_still_matches(request):
            self.session.log(
                "INFO",
                f"Bearing Performance request {request.request_id} completed but was not published because selection changed.",
            )
            return
        self._last_payload = outcome.payload
        self._render_payload(outcome.payload, request.speed_rad_s, request.frequency_rad_s)
        self.progress.setValue(1000)
        self.progress.setFormat("Completed")
        self.advanced_status.setStyleSheet("color:#146b2e;")
        self.advanced_status.setText("Native bearing evaluation completed.")
        self.session.log("INFO", f"Bearing Performance request {request.request_id}: COMPLETED")

    def _job_cancelled(self, request, reason):
        if request.request_id != self._active_request_id:
            return
        self._last_payload = None
        self.evaluate_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setFormat("Cancelled")
        self.advanced_status.setStyleSheet("color:#8a5a00;")
        self.advanced_status.setText(reason)
        self.session.log("INFO", f"Bearing Performance request {request.request_id}: CANCELLED — {reason}")

    def _job_failed(self, failure):
        request = failure.request
        if request.request_id != self._active_request_id:
            return
        self._last_payload = None
        self.evaluate_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setFormat("Failed")
        self.advanced_status.setStyleSheet("color:#a40000;")
        self.advanced_status.setText(f"{failure.exception_type}: {failure.message}")
        self.session.log("ERROR", f"Bearing Performance: {failure.exception_type}: {failure.message}")
        for line in failure.traceback.rstrip().splitlines():
            self.session.log("ERROR", line)

    def _render_payload(self, payload, speed, frequency):
        result = payload["evaluation"]
        details = dict(result.details)
        summary = [
            f"family = {result.model_family}",
            f"Ω = {speed:.9g} rad/s",
            f"ω = {frequency:.9g} rad/s",
        ]
        for key, label, unit in (
            ("xj_ratio", "xj/Cb", ""),
            ("yj_ratio", "yj/Cb", ""),
            ("eccentricity_ratio", "eccentricity ratio", ""),
            ("p_max_pa", "pmax", " Pa"),
            ("t_max_k", "Tmax", " K"),
            ("t_out_k", "Tout", " K"),
            ("deformation_max_m", "max deformation", " m"),
            ("iterations", "journal iterations", ""),
        ):
            if key in details:
                summary.append(f"{label} = {details[key]}{unit}")
        summary.append(f"qualification = {details.get('qualification', 'n/a')}")
        summary.append(f"ROSS authority = {details.get('ross_authority_sha', 'n/a')}")
        self.summary_note.setPlainText("\n".join(summary))
        self.coefficient_note.setPlainText(
            self._matrix_text("K", result.K, "N/m")
            + "\n\n" + self._matrix_text("C", result.C, "N·s/m")
            + "\n\n" + self._matrix_text("M", result.M, "kg")
        )

        fields = (
            (2, self.pressure_plot, "pressure_field_pa", "Pressure", "Pa"),
            (3, self.temperature_plot, "temperature_field_k", "Film temperature", "K"),
            (4, self.film_plot, "film_thickness_field_m", "Film thickness", "m"),
            (5, self.deformation_plot, "deformation_field_m", "Pad deformation", "m"),
        )
        for tab, widget, key, title, unit in fields:
            available = payload.get(key) is not None
            self.lower_tabs.setTabEnabled(tab, available)
            if available:
                widget.set_payload(payload, key, title, unit)
        pads_available = payload.get("pad_load_n") is not None
        self.lower_tabs.setTabEnabled(6, pads_available)
        if pads_available:
            self.pads_plot.set_payload(payload, "pad_load_n", "Pads", "N")
        convergence = payload.get("convergence")
        self.lower_tabs.setTabEnabled(7, convergence is not None)
        if convergence:
            self.convergence_note.setPlainText(
                "\n".join(f"{key} = {value}" for key, value in convergence.items())
            )

    def shutdown(self, timeout_ms=5000):
        return self.jobs.shutdown(timeout_ms)

    def _draw_advanced_schematic(self, bearing):
        pen = QPen(QColor("#1e2d39"), 1.5)
        grey = QBrush(QColor("#d7dce1"))
        cx, cy = 210.0, 145.0
        outer, inner = 118.0, 74.0
        self.scene.addEllipse(QRectF(cx-outer, cy-outer, 2*outer, 2*outer), pen, QBrush(QColor("#f7f9fb")))
        self.scene.addEllipse(QRectF(cx-inner, cy-inner, 2*inner, 2*inner), pen, grey)
        if isinstance(bearing, TiltingPadPhysicsBearing):
            for theta in np.asarray(bearing.pivot_angle_rad, dtype=float):
                x1, y1 = cx + 89*np.cos(theta), cy - 89*np.sin(theta)
                x2, y2 = cx + 111*np.cos(theta), cy - 111*np.sin(theta)
                self.scene.addLine(x1, y1, x2, y2, QPen(QColor("#2872b2"), 12))
            label = self.scene.addText("Native Tilting-Pad THD/TEHD")
        elif isinstance(bearing, PlainJournalPhysicsBearing):
            self.scene.addEllipse(QRectF(cx-96, cy-96, 192, 192), QPen(QColor("#2872b2"), 11), QBrush(Qt.NoBrush))
            label = self.scene.addText("Native Plain Journal THD/TEHD")
        else:
            for dx, dy in ((0,-1),(1,0),(0,1),(-1,0)):
                self.scene.addLine(cx+dx*inner, cy+dy*inner, cx+dx*112, cy+dy*112, QPen(QColor("#2e6fa6"), 3))
            label = self.scene.addText("Advanced K-C provider")
        label.setDefaultTextColor(QColor("#0a4f98"))
        label.setPos(cx-95, cy+outer+14)
        self._draw_axes(cx, cy)

    def _draw_legacy_schematic(self, bearing):
        pen = QPen(QColor("#1e2d39"), 1.5)
        grey = QBrush(QColor("#d7dce1"))
        cx, cy = 210.0, 145.0
        outer, inner = 118.0, 74.0
        self.scene.addEllipse(QRectF(cx-outer, cy-outer, 2*outer, 2*outer), pen, QBrush(QColor("#f7f9fb")))
        self.scene.addEllipse(QRectF(cx-inner, cy-inner, 2*inner, 2*inner), pen, grey)
        if bearing.bearing_type == 7:
            self.scene.addEllipse(QRectF(cx-94, cy-94, 188, 188), QPen(QColor("#4b8dc6"), 9), QBrush(Qt.NoBrush))
            label = self.scene.addText("Short hydrodynamic bearing")
        elif bearing.bearing_type == 8:
            self.scene.addEllipse(QRectF(cx-98, cy-98, 196, 196), QPen(QColor("#2872b2"), 12), QBrush(Qt.NoBrush))
            self.scene.addEllipse(QRectF(cx-88, cy-88, 176, 176), QPen(QColor("#7fb3df"), 5), QBrush(Qt.NoBrush))
            label = self.scene.addText("Seal")
        else:
            for dx, dy in ((0,-1),(1,0),(0,1),(-1,0)):
                self.scene.addLine(cx+dx*inner, cy+dy*inner, cx+dx*112, cy+dy*112, QPen(QColor("#2e6fa6"), 3))
            label = self.scene.addText("Support / K-C model")
        label.setDefaultTextColor(QColor("#0a4f98"))
        label.setPos(cx-82, cy+outer+14)
        self._draw_axes(cx, cy)

    def _draw_axes(self, cx, cy):
        axis_pen = QPen(QColor("#111111"), 1.2)
        self.scene.addLine(cx-140, cy, cx+145, cy, axis_pen)
        self.scene.addLine(cx, cy+140, cx, cy-145, axis_pen)
        xlab = self.scene.addText("X"); xlab.setPos(cx+147, cy-12)
        ylab = self.scene.addText("Y"); ylab.setPos(cx+5, cy-163)
        self.scene.setSceneRect(40, -35, 360, 365)
        self.graphics.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
