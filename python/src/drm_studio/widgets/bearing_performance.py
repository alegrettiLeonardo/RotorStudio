from __future__ import annotations

import numpy as np

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QToolButton, QLabel,
    QGraphicsView, QGraphicsScene, QTabWidget, QPlainTextEdit, QSizePolicy,
    QGroupBox, QFormLayout, QDoubleSpinBox, QPushButton
)

from drm_core import PlainJournalPhysicsBearing, TiltingPadPhysicsBearing
from drm_core.solver.facade import SolverFacade
from drm_studio.docks.bearing_editor import BearingInspectorWidget, _BEARING_NAMES
from drm_studio.resources import studio_icon


class BearingPerformancePage(QWidget):
    """Bearing/seal workspace with explicit native advanced-bearing evaluation.

    Expensive Reynolds/THD/TEHD work is only launched by the Evaluate button;
    selection changes and painting never invoke the physical solver.
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._solver = None
        self._last_payload = None

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
        self.evaluate_button = QPushButton("Evaluate Native Bearing")
        self.evaluate_button.clicked.connect(self._evaluate_advanced)
        self.advanced_status = QLabel("")
        self.advanced_status.setWordWrap(True)
        advanced_form.addRow("Rotor speed Ω:", self.speed_field)
        advanced_form.addRow("Whirl / excitation ω:", self.frequency_field)
        advanced_form.addRow(self.evaluate_button)
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
        self.coefficient_note = QPlainTextEdit()
        self.coefficient_note.setReadOnly(True)
        self.pressure_note = QPlainTextEdit()
        self.pressure_note.setReadOnly(True)
        self.temperature_note = QPlainTextEdit()
        self.temperature_note.setReadOnly(True)
        self.lower_tabs.addTab(self.coefficient_note, "Dynamic Coefficients")
        self.lower_tabs.addTab(self.pressure_note, "Pressure Distribution")
        self.lower_tabs.addTab(self.temperature_note, "Temperature")
        self._clear_field_tabs()
        center_layout.addWidget(self.lower_tabs)
        body.addWidget(center)

        body.setStretchFactor(0, 4)
        body.setStretchFactor(1, 7)
        outer.addWidget(body, 1)

        session.selectionChanged.connect(lambda _: self.refresh())
        session.modelChanged.connect(self.refresh)
        self.refresh()

    def _solver_facade(self):
        if self._solver is None:
            self._solver = SolverFacade()
        return self._solver

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

    def _clear_field_tabs(self):
        self.lower_tabs.setTabEnabled(1, False)
        self.lower_tabs.setTabEnabled(2, False)
        self.pressure_note.setPlainText(
            "Pressure fields are available for qualified native PlainJournal and TiltingPad models "
            "after an explicit Bearing Performance evaluation."
        )
        self.temperature_note.setPlainText(
            "Temperature fields are available for qualified native THD/TEHD models "
            "after an explicit Bearing Performance evaluation."
        )

    def refresh(self):
        kind, bearing = self._selected()
        self.scene.clear()
        self._last_payload = None
        self._clear_field_tabs()
        self.advanced_status.clear()

        if bearing is None:
            self.heading.setText("Bearing / Seal Schematic — select a bearing in Project Explorer")
            self.coefficient_note.setPlainText(
                "Select a legacy or advanced bearing to inspect/evaluate it."
            )
            self.editor.setVisible(True)
            self.advanced_group.setVisible(False)
            return

        if kind == "advanced":
            self.editor.setVisible(False)
            self.advanced_group.setVisible(True)
            family = str(getattr(bearing, "model_family", type(bearing).__name__))
            self.heading.setText(f"{family} — Node {bearing.node}")
            self._draw_advanced_schematic(bearing)
            physical = isinstance(
                bearing, (PlainJournalPhysicsBearing, TiltingPadPhysicsBearing)
            )
            self.evaluate_button.setEnabled(True)
            if physical:
                self.coefficient_note.setPlainText(
                    "Native Fortran fluid-film provider qualified by B12 against "
                    "petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d.\n\n"
                    "Set Ω and ω, then choose Evaluate Native Bearing. "
                    "The solve is explicit; GUI refresh does not run Reynolds/THD/TEHD."
                )
            else:
                self.coefficient_note.setPlainText(
                    "Advanced coefficient/native provider. Set the operating point and "
                    "choose Evaluate Native Bearing to obtain K/C."
                )
            return

        self.editor.setVisible(True)
        self.advanced_group.setVisible(False)
        name = _BEARING_NAMES.get(bearing.bearing_type, f"Type {bearing.bearing_type}")
        self.heading.setText(f"{name} — Node {bearing.node}")
        self._draw_legacy_schematic(bearing)

        if bearing.bearing_type in (3, 4, 5, 6, 20):
            self.coefficient_note.setPlainText(
                "The table shows the persisted qualified constant K/C inputs. "
                "No coefficient identification is performed by the UI."
            )
        elif bearing.bearing_type == 7:
            self.coefficient_note.setPlainText(
                "Hydrodynamic short-width bearing: Stage 1 computes the supported bearing "
                "matrices through the existing qualified Fortran-backed path."
            )
        elif bearing.bearing_type == 8:
            self.coefficient_note.setPlainText(
                "Seal model: only the qualified Stage 1 seal parameters and compatible analyses are exposed."
            )
        else:
            self.coefficient_note.setPlainText(
                "Rigid support boundary condition from the qualified Stage 1 model."
            )

    @staticmethod
    def _matrix_text(name, matrix, units):
        a = np.asarray(matrix, dtype=float)
        return (
            f"{name} [{units}]\n"
            f"  [{a[0,0]: .9e}  {a[0,1]: .9e}]\n"
            f"  [{a[1,0]: .9e}  {a[1,1]: .9e}]"
        )

    @staticmethod
    def _field_text(title, values, units):
        a = np.asarray(values, dtype=float)
        lines = [
            f"{title}",
            f"shape = {a.shape}",
            f"min = {np.min(a):.9e} {units}",
            f"max = {np.max(a):.9e} {units}",
            f"mean = {np.mean(a):.9e} {units}",
        ]
        if a.ndim >= 3:
            axes = tuple(range(1, a.ndim))
            maxima = np.max(a, axis=axes)
            lines.append(
                "per-pad max = [" + ", ".join(f"{x:.9e}" for x in maxima) + f"] {units}"
            )
        return "\n".join(lines)

    def _evaluate_advanced(self):
        kind, bearing = self._selected()
        if kind != "advanced" or bearing is None:
            return
        speed = float(self.speed_field.value())
        frequency = float(self.frequency_field.value())
        self.evaluate_button.setEnabled(False)
        self.advanced_status.setStyleSheet("")
        self.advanced_status.setText("Solving native bearing…")
        try:
            payload = self._solver_facade().advanced_bearing_fields(
                bearing, speed_rad_s=speed, frequency_rad_s=frequency
            )
            self._last_payload = payload
            result = payload["evaluation"]
            details = dict(result.details)
            text = [
                self._matrix_text("K", result.K, "N/m"),
                "",
                self._matrix_text("C", result.C, "N·s/m"),
                "",
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
                ("iterations", "iterations", ""),
            ):
                if key in details:
                    text.append(f"{label} = {details[key]}{unit}")
            if "tilt_angle_rad" in details:
                tilt = np.asarray(details["tilt_angle_rad"], dtype=float)
                text.append(
                    "pad tilt [rad] = [" + ", ".join(f"{x:.9e}" for x in tilt) + "]"
                )
            if "qualification" in details:
                text.append(f"qualification = {details['qualification']}")
                text.append(f"ROSS authority = {details.get('ross_authority_sha', '')}")
            self.coefficient_note.setPlainText("\n".join(text))

            pressure = payload.get("pressure_field_pa")
            temperature = payload.get("temperature_field_k")
            deformation = payload.get("deformation_field_m")
            if pressure is not None:
                self.pressure_note.setPlainText(
                    self._field_text("Native pressure field", pressure, "Pa")
                )
                self.lower_tabs.setTabEnabled(1, True)
            if temperature is not None:
                thermal_text = self._field_text(
                    "Native film temperature field", temperature, "K"
                )
                if deformation is not None:
                    thermal_text += "\n\n" + self._field_text(
                        "Native pad deformation field", deformation, "m"
                    )
                self.temperature_note.setPlainText(thermal_text)
                self.lower_tabs.setTabEnabled(2, True)

            self.advanced_status.setStyleSheet("color:#146b2e;")
            self.advanced_status.setText("Native bearing evaluation completed.")
        except Exception as exc:
            self._last_payload = None
            self.advanced_status.setStyleSheet("color:#a40000;")
            self.advanced_status.setText(str(exc))
            self.session.log("ERROR", f"Bearing Performance: {exc}")
        finally:
            self.evaluate_button.setEnabled(True)

    def _draw_advanced_schematic(self, bearing):
        pen = QPen(QColor("#1e2d39"), 1.5)
        grey = QBrush(QColor("#d7dce1"))
        cx, cy = 210.0, 145.0
        outer, inner = 118.0, 74.0
        self.scene.addEllipse(
            QRectF(cx - outer, cy - outer, 2 * outer, 2 * outer),
            pen,
            QBrush(QColor("#f7f9fb")),
        )
        self.scene.addEllipse(
            QRectF(cx - inner, cy - inner, 2 * inner, 2 * inner), pen, grey
        )

        if isinstance(bearing, TiltingPadPhysicsBearing):
            pivots = np.asarray(bearing.pivot_angle_rad, dtype=float)
            for theta in pivots:
                x1 = cx + 89.0 * np.cos(theta)
                y1 = cy - 89.0 * np.sin(theta)
                x2 = cx + 111.0 * np.cos(theta)
                y2 = cy - 111.0 * np.sin(theta)
                self.scene.addLine(
                    x1, y1, x2, y2, QPen(QColor("#2872b2"), 12)
                )
            label = self.scene.addText("Native Tilting-Pad THD/TEHD")
        elif isinstance(bearing, PlainJournalPhysicsBearing):
            self.scene.addEllipse(
                QRectF(cx - 96, cy - 96, 192, 192),
                QPen(QColor("#2872b2"), 11),
                QBrush(Qt.NoBrush),
            )
            label = self.scene.addText("Native Plain Journal THD/TEHD")
        else:
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                self.scene.addLine(
                    cx + dx * inner,
                    cy + dy * inner,
                    cx + dx * 112,
                    cy + dy * 112,
                    QPen(QColor("#2e6fa6"), 3),
                )
            label = self.scene.addText("Advanced K-C provider")

        label.setDefaultTextColor(QColor("#0a4f98"))
        label.setPos(cx - 95, cy + outer + 14)
        self._draw_axes(cx, cy)

    def _draw_legacy_schematic(self, bearing):
        pen = QPen(QColor("#1e2d39"), 1.5)
        grey = QBrush(QColor("#d7dce1"))
        cx, cy = 210.0, 145.0
        outer, inner = 118.0, 74.0

        self.scene.addEllipse(
            QRectF(cx - outer, cy - outer, 2 * outer, 2 * outer),
            pen,
            QBrush(QColor("#f7f9fb")),
        )
        self.scene.addEllipse(
            QRectF(cx - inner, cy - inner, 2 * inner, 2 * inner), pen, grey
        )

        if bearing.bearing_type == 7:
            self.scene.addEllipse(
                QRectF(cx - 94, cy - 94, 188, 188),
                QPen(QColor("#4b8dc6"), 9),
                QBrush(Qt.NoBrush),
            )
            label = self.scene.addText("Short hydrodynamic bearing")
        elif bearing.bearing_type == 8:
            self.scene.addEllipse(
                QRectF(cx - 98, cy - 98, 196, 196),
                QPen(QColor("#2872b2"), 12),
                QBrush(Qt.NoBrush),
            )
            self.scene.addEllipse(
                QRectF(cx - 88, cy - 88, 176, 176),
                QPen(QColor("#7fb3df"), 5),
                QBrush(Qt.NoBrush),
            )
            label = self.scene.addText("Seal")
        else:
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                self.scene.addLine(
                    cx + dx * inner,
                    cy + dy * inner,
                    cx + dx * 112,
                    cy + dy * 112,
                    QPen(QColor("#2e6fa6"), 3),
                )
            label = self.scene.addText("Support / K-C model")

        label.setDefaultTextColor(QColor("#0a4f98"))
        label.setPos(cx - 82, cy + outer + 14)
        self._draw_axes(cx, cy)

    def _draw_axes(self, cx, cy):
        axis_pen = QPen(QColor("#111111"), 1.2)
        self.scene.addLine(cx - 140, cy, cx + 145, cy, axis_pen)
        self.scene.addLine(cx, cy + 140, cx, cy - 145, axis_pen)
        xlab = self.scene.addText("X")
        xlab.setPos(cx + 147, cy - 12)
        ylab = self.scene.addText("Y")
        ylab.setPos(cx + 5, cy - 163)
        self.scene.setSceneRect(40, -35, 360, 365)
        self.graphics.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
