from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QLabel,
    QDoubleSpinBox, QSpinBox, QTabWidget, QHBoxLayout, QStackedWidget,
    QGroupBox, QPushButton, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)

from drm_core.domain.model import ShaftElement
from drm_core.units import m_to_mm, mm_to_m, pa_to_mpa, mpa_to_pa
from drm_core.validation.model import ModelValidationError
from drm_studio.commands.model_commands import SetShaftPropertyCommand
from drm_studio.docks.bearing_editor import BearingInspectorWidget, _schema, _BEARING_NAMES
from drm_studio.docks.disk_editor import DiskInspectorWidget


def _spin(decimals=4, minimum=0.0, maximum=1.0e12):
    widget = QDoubleSpinBox()
    widget.setDecimals(decimals)
    widget.setRange(minimum, maximum)
    widget.setKeyboardTracking(False)
    return widget


class PropertyInspectorDock(QDockWidget):
    """Context-sensitive right inspector.

    Entity selection shows the shaft/disk/bearing inspector.  Result documents
    switch the same dock to Results Properties, matching the Stage 2 mockup.
    """

    exportPlotRequested = Signal()
    exportCsvRequested = Signal()
    reportRequested = Signal()
    rerunRequested = Signal()

    def __init__(self, session, parent=None):
        super().__init__("Element Properties", parent)
        self.setObjectName("ElementPropertiesDock")
        self.setMinimumWidth(330)
        self.session = session
        self._updating = False

        self.stack = QStackedWidget()

        # ---------------- Entity inspector ----------------
        self.tabs = QTabWidget()
        self.shaft_tab = QWidget()
        self.tabs.addTab(self.shaft_tab, "Shaft")

        self.disk_tab = DiskInspectorWidget(session)
        self.tabs.addTab(self.disk_tab, "Disk")

        self.bearing_tab = BearingInspectorWidget(session)
        self.tabs.addTab(self.bearing_tab, "Bearing")

        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        analysis_text = QLabel(
            "Analysis setup is configured through persistent AnalysisCase dialogs."
        )
        analysis_text.setWordWrap(True)
        analysis_layout.addWidget(analysis_text)
        analysis_layout.addStretch(1)
        self.tabs.addTab(analysis_tab, "Analysis Setup")

        form = QFormLayout(self.shaft_tab)
        self.heading = QLabel("No shaft selected")
        self.heading.setObjectName("SectionHeaderTitle")
        form.addRow(self.heading)

        self.type_field = QSpinBox()
        self.type_field.setRange(1, 8)
        self.type_field.setReadOnly(True)
        self.node1_field = QSpinBox()
        self.node1_field.setRange(0, 1000000)
        self.node1_field.setReadOnly(True)
        self.node2_field = QSpinBox()
        self.node2_field.setRange(0, 1000000)
        self.node2_field.setReadOnly(True)
        self.length_field = QLineEdit()
        self.length_field.setReadOnly(True)

        self.do_field = _spin(3)
        self.di_field = _spin(3)
        self.e_field = _spin(3)
        self.g_field = _spin(3)
        self.rho_field = _spin(3)
        self.damping_field = _spin(7)
        self.axial_field = _spin(3, -1.0e12, 1.0e12)
        self.torque_field = _spin(3, -1.0e12, 1.0e12)

        form.addRow("Element Type:", self.type_field)
        form.addRow("Node 1:", self.node1_field)
        form.addRow("Node 2:", self.node2_field)
        form.addRow("Length (L):", self._with_unit(self.length_field, "mm"))
        form.addRow("Outer Diameter (Do):", self._with_unit(self.do_field, "mm"))
        form.addRow("Inner Diameter (Di):", self._with_unit(self.di_field, "mm"))
        form.addRow("Young's Modulus (E):", self._with_unit(self.e_field, "MPa"))
        form.addRow("Shear Modulus (G):", self._with_unit(self.g_field, "MPa"))
        form.addRow("Density (ρ):", self._with_unit(self.rho_field, "kg/m³"))
        form.addRow("Damping Factor (η):", self.damping_field)
        form.addRow("Axial Force:", self._with_unit(self.axial_field, "N"))
        form.addRow("Torque:", self._with_unit(self.torque_field, "N·m"))

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color:#a40000;")
        form.addRow(self.error_label)

        self.stack.addWidget(self.tabs)

        # ---------------- Results Properties ----------------
        self.results_page = QWidget()
        results_layout = QVBoxLayout(self.results_page)
        results_layout.setContentsMargins(8, 8, 8, 8)
        results_layout.setSpacing(8)

        settings_group = QGroupBox("Analysis / Display Settings")
        settings_form = QFormLayout(settings_group)
        self.result_case = QLabel("—")
        self.result_kind = QLabel("—")
        self.result_status = QLabel("—")
        self.result_backend = QLabel("—")
        self.result_hash = QLineEdit()
        self.result_hash.setReadOnly(True)
        settings_form.addRow("Case:", self.result_case)
        settings_form.addRow("Analysis:", self.result_kind)
        settings_form.addRow("Status:", self.result_status)
        settings_form.addRow("Backend:", self.result_backend)
        settings_form.addRow("Result hash:", self.result_hash)
        results_layout.addWidget(settings_group)

        export_group = QGroupBox("Export")
        export_grid = QGridLayout(export_group)
        self.save_plot_button = QPushButton("Save Plot…")
        self.export_data_button = QPushButton("Export Data…")
        self.rerun_button = QPushButton("Rerun Analysis")
        export_grid.addWidget(self.save_plot_button, 0, 0)
        export_grid.addWidget(self.export_data_button, 0, 1)
        export_grid.addWidget(self.rerun_button, 1, 0, 1, 2)
        results_layout.addWidget(export_group)

        reports_group = QGroupBox("Quick Reports")
        reports_layout = QVBoxLayout(reports_group)
        self.quick_report_button = QPushButton("Generate Current Analysis Report")
        reports_layout.addWidget(self.quick_report_button)
        results_layout.addWidget(reports_group)
        results_layout.addStretch(1)

        self.save_plot_button.clicked.connect(self.exportPlotRequested)
        self.export_data_button.clicked.connect(self.exportCsvRequested)
        self.rerun_button.clicked.connect(self.rerunRequested)
        self.quick_report_button.clicked.connect(self.reportRequested)

        self.stack.addWidget(self.results_page)

        # ---------------- Bearing Performance Results ----------------
        self.bearing_results_page = QWidget()
        bearing_results_layout = QVBoxLayout(self.bearing_results_page)
        bearing_results_layout.setContentsMargins(8, 8, 8, 8)
        bearing_results_layout.setSpacing(8)
        self.bearing_results_heading = QLabel("Bearing / Seal")
        self.bearing_results_heading.setObjectName("SectionHeaderTitle")
        bearing_results_layout.addWidget(self.bearing_results_heading)
        self.bearing_results_table = QTableWidget(0, 3)
        self.bearing_results_table.setHorizontalHeaderLabels(["Parameter", "Value", "Units"])
        self.bearing_results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.bearing_results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.bearing_results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.bearing_results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        bearing_results_layout.addWidget(self.bearing_results_table, 1)
        self.bearing_results_note = QLabel(
            "Only qualified Stage 1 bearing/seal inputs and coefficients are displayed. "
            "No pressure or thermal result is fabricated."
        )
        self.bearing_results_note.setWordWrap(True)
        self.bearing_results_note.setStyleSheet("color:#60758a;")
        bearing_results_layout.addWidget(self.bearing_results_note)
        self.stack.addWidget(self.bearing_results_page)

        self.setWidget(self.stack)

        self._edit_map = {
            self.do_field: ("outer_diameter_m", mm_to_m),
            self.di_field: ("inner_diameter_m", mm_to_m),
            self.e_field: ("E_pa", mpa_to_pa),
            self.g_field: ("G_pa", mpa_to_pa),
            self.rho_field: ("rho_kg_m3", float),
            self.damping_field: ("damping_factor", float),
            self.axial_field: ("axial_force_n", float),
            self.torque_field: ("torque_nm", float),
        }
        for field in self._edit_map:
            field.editingFinished.connect(lambda f=field: self._commit_field(f))

        session.selectionChanged.connect(self._selection_changed)
        session.modelChanged.connect(lambda: self.refresh(session.selection))
        self.refresh(None)

    def _with_unit(self, widget, unit):
        host = QWidget()
        layout = QHBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(widget, 1)
        label = QLabel(unit)
        label.setStyleSheet("color:#667788;")
        layout.addWidget(label)
        return host

    def show_entity_context(self):
        self.setWindowTitle("Element Properties")
        self.stack.setCurrentWidget(self.tabs)

    def show_bearing_context(self):
        self.setWindowTitle("Results - Bearing Performance")
        self.stack.setCurrentWidget(self.bearing_results_page)
        ref = self.session.selection
        self.bearing_results_table.setRowCount(0)
        if ref is None or ref.kind != "bearing" or not (0 <= ref.index < len(self.session.project.model.bearings)):
            self.bearing_results_heading.setText("Bearing / Seal — select an item in Project Explorer")
            return
        bearing = self.session.project.model.bearings[ref.index]
        name = _BEARING_NAMES.get(bearing.bearing_type, f"Type {bearing.bearing_type}")
        self.bearing_results_heading.setText(f"{name} — Node {bearing.node}")
        schema = _schema(bearing.bearing_type)
        self.bearing_results_table.setRowCount(len(schema) + 2)
        basic = [("Type", bearing.bearing_type, name), ("Node", bearing.node, "")]
        for row, values in enumerate(basic):
            for col, value in enumerate(values):
                self.bearing_results_table.setItem(row, col, QTableWidgetItem(str(value)))
        props = list(bearing.properties)
        for row, (label, unit, scale) in enumerate(schema, 2):
            value = props[row - 2] if row - 2 < len(props) else 0.0
            shown = float(value) * scale
            self.bearing_results_table.setItem(row, 0, QTableWidgetItem(label))
            self.bearing_results_table.setItem(row, 1, QTableWidgetItem(f"{shown:.8g}"))
            self.bearing_results_table.setItem(row, 2, QTableWidgetItem(unit))

    def show_result_context(self, record):
        if record is None:
            self.show_entity_context()
            return
        self.setWindowTitle("Results Properties")
        self.stack.setCurrentWidget(self.results_page)
        execution = record.execution
        self.result_case.setText(execution.case.name or execution.case.kind)
        self.result_kind.setText(execution.case.kind)
        if record.stale:
            self.result_status.setText("OUTDATED / STALE")
            self.result_status.setProperty("resultStatus", "stale")
        else:
            self.result_status.setText("CURRENT")
            self.result_status.setProperty("resultStatus", "current")
        self.result_status.style().unpolish(self.result_status)
        self.result_status.style().polish(self.result_status)
        self.result_backend.setText(str(execution.build_metadata.get("backend", "—")))
        self.result_hash.setText(str(execution.analysis_hash))

    def _selection_changed(self, ref):
        if ref is not None and ref.kind == "result":
            return
        self.show_entity_context()
        if ref is not None and ref.kind == "bearing":
            self.tabs.setCurrentWidget(self.bearing_tab)
        elif ref is not None and ref.kind == "disk":
            self.tabs.setCurrentWidget(self.disk_tab)
        elif ref is not None and ref.kind == "shaft":
            self.tabs.setCurrentWidget(self.shaft_tab)
        self.refresh(ref)

    def _selected_shaft(self):
        ref = self.session.selection
        if ref is None or ref.kind != "shaft":
            return None, None
        if ref.index < 0 or ref.index >= len(self.session.project.model.shafts):
            return None, None
        shaft = self.session.project.model.shafts[ref.index]
        if not isinstance(shaft, ShaftElement):
            return ref.index, None
        return ref.index, shaft

    def refresh(self, ref):
        self._updating = True
        try:
            idx, shaft = self._selected_shaft()
            enabled = shaft is not None
            self.shaft_tab.setEnabled(enabled)
            self.error_label.setText("")
            if not enabled:
                self.heading.setText("No circular shaft selected")
                return
            self.heading.setText(f"Shaft Element (Element {idx + 1})")
            self.type_field.setValue(shaft.shaft_type)
            self.node1_field.setValue(shaft.node1)
            self.node2_field.setValue(shaft.node2)
            node_z = {n.number: n.z_m for n in self.session.project.model.nodes}
            length = node_z[shaft.node2] - node_z[shaft.node1]
            self.length_field.setText(f"{m_to_mm(length):.3f}")
            self.do_field.setValue(m_to_mm(shaft.outer_diameter_m))
            self.di_field.setValue(m_to_mm(shaft.inner_diameter_m))
            self.e_field.setValue(pa_to_mpa(shaft.E_pa))
            self.g_field.setValue(pa_to_mpa(shaft.G_pa))
            self.rho_field.setValue(shaft.rho_kg_m3)
            self.damping_field.setValue(shaft.damping_factor)
            self.axial_field.setValue(shaft.axial_force_n)
            self.torque_field.setValue(shaft.torque_nm)
        finally:
            self._updating = False

    def _commit_field(self, field):
        if self._updating:
            return
        idx, shaft = self._selected_shaft()
        if shaft is None:
            return
        attr, to_si = self._edit_map[field]
        new_value = to_si(field.value())
        old_value = getattr(shaft, attr)
        if math.isclose(float(new_value), float(old_value), rel_tol=1e-12, abs_tol=1e-15):
            return
        try:
            command = SetShaftPropertyCommand(
                self.session, idx, attr, new_value,
                f"Edit Shaft {idx + 1} {attr}"
            )
            self.session.undo_stack.push(command)
            self.error_label.setText("")
            self.session.log("INFO", f"Shaft {idx + 1}: {attr} updated")
        except (ModelValidationError, ValueError, AttributeError) as exc:
            self.refresh(self.session.selection)
            self.error_label.setText(str(exc))
            self.session.log("ERROR", str(exc))
