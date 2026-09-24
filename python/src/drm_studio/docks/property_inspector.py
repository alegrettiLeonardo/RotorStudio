from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QLabel,
    QDoubleSpinBox, QSpinBox, QTabWidget, QHBoxLayout
)

from drm_core.domain.model import ShaftElement
from drm_core.units import m_to_mm, mm_to_m, pa_to_mpa, mpa_to_pa
from drm_core.validation.model import ModelValidationError
from drm_studio.commands.model_commands import SetShaftPropertyCommand
from drm_studio.docks.bearing_editor import BearingInspectorWidget


def _spin(decimals=4, minimum=0.0, maximum=1.0e12):
    widget = QDoubleSpinBox()
    widget.setDecimals(decimals)
    widget.setRange(minimum, maximum)
    widget.setKeyboardTracking(False)
    return widget


class PropertyInspectorDock(QDockWidget):
    def __init__(self, session, parent=None):
        super().__init__("Element Properties", parent)
        self.setObjectName("ElementPropertiesDock")
        self.session = session
        self._updating = False

        self.tabs = QTabWidget()
        self.shaft_tab = QWidget()
        self.tabs.addTab(self.shaft_tab, "Shaft")

        disk_tab = QWidget()
        disk_layout = QVBoxLayout(disk_tab)
        disk_text = QLabel("Disk editor is integrated in a later Stage 2 vertical slice.")
        disk_text.setWordWrap(True)
        disk_layout.addWidget(disk_text)
        disk_layout.addStretch(1)
        self.tabs.addTab(disk_tab, "Disk")

        self.bearing_tab = BearingInspectorWidget(session)
        self.tabs.addTab(self.bearing_tab, "Bearing")

        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        analysis_text = QLabel("Analysis setup is configured through persistent AnalysisCase dialogs.")
        analysis_text.setWordWrap(True)
        analysis_layout.addWidget(analysis_text)
        analysis_layout.addStretch(1)
        self.tabs.addTab(analysis_tab, "Analysis Setup")

        form = QFormLayout(self.shaft_tab)
        self.heading = QLabel("No shaft selected")
        self.heading.setStyleSheet("font-weight:600;color:#0a4f98;")
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
        self.setWidget(self.tabs)

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

    def _selection_changed(self, ref):
        if ref is not None and ref.kind == "bearing":
            self.tabs.setCurrentWidget(self.bearing_tab)
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
            # Restore the authoritative domain value first, then keep the
            # validation diagnostic visible.  refresh() intentionally clears
            # stale diagnostics during normal selection/model changes.
            self.refresh(self.session.selection)
            self.error_label.setText(str(exc))
            self.session.log("ERROR", str(exc))
