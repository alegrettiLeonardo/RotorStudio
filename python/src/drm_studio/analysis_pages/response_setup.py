from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QComboBox, QMessageBox
)

from drm_core import AnalysisCase
from drm_core.units import rpm_to_rad_s


def _grid(start, end, step):
    if end <= start:
        raise ValueError("End value must be greater than start value.")
    if step <= 0:
        raise ValueError("Increment must be positive.")
    count = int(np.floor((end - start) / step + 1e-12)) + 1
    values = start + step * np.arange(count, dtype=float)
    if values[-1] < end - max(1e-12, abs(end) * 1e-12):
        values = np.append(values, end)
    return values


class SynchronousResponseSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Synchronous Response")
        form = QFormLayout(self)
        self.name_field = QLineEdit("Synchronous Response")
        self.start_field = self._rpm(0.0)
        self.end_field = self._rpm(12000.0)
        self.step_field = self._rpm(100.0, minimum=1e-6)
        self.node_field = QSpinBox(); self.node_field.setRange(1, 1000000); self.node_field.setValue(1)
        self.dof_combo = QComboBox()
        for label, dof in (("X translation",1),("Y translation",2),("X rotation",3),("Y rotation",4)):
            self.dof_combo.addItem(label, dof)
        form.addRow("Case name:", self.name_field)
        form.addRow("Start speed:", self.start_field)
        form.addRow("End speed:", self.end_field)
        form.addRow("Speed increment:", self.step_field)
        form.addRow("Output node:", self.node_field)
        form.addRow("Output DOF:", self.dof_combo)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept); buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    @staticmethod
    def _rpm(value, minimum=0.0):
        w=QDoubleSpinBox();w.setRange(minimum,1e8);w.setDecimals(3);w.setSuffix(" rpm");w.setValue(value);return w

    def _accept(self):
        try:_grid(self.start_field.value(),self.end_field.value(),self.step_field.value())
        except ValueError as exc:
            QMessageBox.warning(self,"Invalid response range",str(exc));return
        self.accept()

    def analysis_case(self):
        rpm=_grid(self.start_field.value(),self.end_field.value(),self.step_field.value())
        node=int(self.node_field.value());dof=int(self.dof_combo.currentData())
        return AnalysisCase(
            "frequency_response",
            {"speeds_rad_s":np.asarray(rpm_to_rad_s(rpm),float).tolist()},
            self.name_field.text().strip() or "Synchronous Response",
            {"outnodes":[node+dof/10.0]},
        )


class FrequencyResponseSetupDialog(QDialog):
    def __init__(self, source="auxiliary", parent=None):
        super().__init__(parent)
        self.source=source
        title="Foundation Frequency Response" if source=="foundation" else "Frequency Response"
        self.setWindowTitle(title)
        form=QFormLayout(self)
        self.name_field=QLineEdit(title)
        self.rotor_speed=self._rpm(6000.0)
        self.start_hz=self._hz(0.0)
        self.end_hz=self._hz(1000.0)
        self.step_hz=self._hz(5.0,minimum=1e-9)
        self.direction=QComboBox()
        self.direction.addItem("Forward (+)",1.0);self.direction.addItem("Backward (-)",-1.0)
        self.node_field=QSpinBox();self.node_field.setRange(1,1000000);self.node_field.setValue(1)
        self.dof_combo=QComboBox()
        for label,dof in (("X translation",1),("Y translation",2),("X rotation",3),("Y rotation",4)):
            self.dof_combo.addItem(label,dof)
        form.addRow("Case name:",self.name_field)
        form.addRow("Rotor speed:",self.rotor_speed)
        form.addRow("Start excitation:",self.start_hz)
        form.addRow("End excitation:",self.end_hz)
        form.addRow("Frequency increment:",self.step_hz)
        if source!="foundation":form.addRow("Spinner direction:",self.direction)
        form.addRow("Output node:",self.node_field)
        form.addRow("Output DOF:",self.dof_combo)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept);buttons.rejected.connect(self.reject);form.addRow(buttons)

    @staticmethod
    def _rpm(v):
        w=QDoubleSpinBox();w.setRange(-1e8,1e8);w.setDecimals(3);w.setSuffix(" rpm");w.setValue(v);return w
    @staticmethod
    def _hz(v,minimum=0.0):
        w=QDoubleSpinBox();w.setRange(minimum,1e8);w.setDecimals(6);w.setSuffix(" Hz");w.setValue(v);return w

    def _accept(self):
        try:_grid(self.start_hz.value(),self.end_hz.value(),self.step_hz.value())
        except ValueError as exc:
            QMessageBox.warning(self,"Invalid frequency range",str(exc));return
        self.accept()

    def analysis_case(self):
        hz=_grid(self.start_hz.value(),self.end_hz.value(),self.step_hz.value())
        omega=(2*np.pi*hz).tolist()
        node=int(self.node_field.value());dof=int(self.dof_combo.currentData())
        params={"rotor_speed_rad_s":float(rpm_to_rad_s(self.rotor_speed.value())),"omega_rad_s":omega}
        kind="foundation_frequency_response" if self.source=="foundation" else "auxiliary_frequency_response"
        if self.source!="foundation":params["direction"]=float(self.direction.currentData())
        return AnalysisCase(kind,params,self.name_field.text().strip() or self.windowTitle(),{"outnodes":[node+dof/10.0]})
