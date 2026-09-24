from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QComboBox
)

from drm_core import AnalysisCase
from drm_core.units import rpm_to_rad_s


class FoundationTimeSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Foundation Time Response")
        form=QFormLayout(self)
        self.name_field=QLineEdit("Foundation Time Response")
        self.speed_field=QDoubleSpinBox();self.speed_field.setRange(-1e8,1e8);self.speed_field.setDecimals(3);self.speed_field.setSuffix(" rpm")
        self.dt_field=QDoubleSpinBox();self.dt_field.setRange(1e-9,1e3);self.dt_field.setDecimals(9);self.dt_field.setValue(1e-4);self.dt_field.setSuffix(" s")
        self.npts_field=QSpinBox();self.npts_field.setRange(2,2000000);self.npts_field.setValue(2001)
        self.nr_field=QSpinBox();self.nr_field.setRange(0,100000);self.nr_field.setValue(0)
        self.rtol_field=QDoubleSpinBox();self.rtol_field.setRange(1e-12,1.0);self.rtol_field.setDecimals(10);self.rtol_field.setValue(1e-3)
        self.atol_field=QDoubleSpinBox();self.atol_field.setRange(1e-15,1.0);self.atol_field.setDecimals(12);self.atol_field.setValue(1e-6)
        self.node_field=QSpinBox();self.node_field.setRange(1,1000000);self.node_field.setValue(1)
        self.dof_combo=QComboBox()
        for label,dof in (("X translation",1),("Y translation",2),("X rotation",3),("Y rotation",4)):
            self.dof_combo.addItem(label,dof)
        form.addRow("Case name:",self.name_field);form.addRow("Rotor speed:",self.speed_field)
        form.addRow("Output time step:",self.dt_field);form.addRow("Number of output points:",self.npts_field)
        form.addRow("Reduced DOFs (0 = full):",self.nr_field);form.addRow("Relative tolerance:",self.rtol_field);form.addRow("Absolute tolerance:",self.atol_field)
        form.addRow("Output node:",self.node_field);form.addRow("Output DOF:",self.dof_combo)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);form.addRow(buttons)

    def analysis_case(self):
        node=int(self.node_field.value());dof=int(self.dof_combo.currentData())
        return AnalysisCase(
            "foundation_time_response",
            {
                "rotor_speed_rad_s":float(rpm_to_rad_s(self.speed_field.value())),
                "dt":float(self.dt_field.value()),
                "npts":int(self.npts_field.value()),
                "nr":int(self.nr_field.value()),
                "rtol":float(self.rtol_field.value()),
                "atol":float(self.atol_field.value()),
            },
            self.name_field.text().strip() or "Foundation Time Response",
            {"outnode":node+dof/10.0},
        )


class RunupSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run-up / Run-down")
        form=QFormLayout(self)
        self.name_field=QLineEdit("Run-up / Run-down")
        self.a2=QDoubleSpinBox();self.a2.setRange(-1e12,1e12);self.a2.setDecimals(9)
        self.a1=QDoubleSpinBox();self.a1.setRange(-1e12,1e12);self.a1.setDecimals(9)
        self.a0=QDoubleSpinBox();self.a0.setRange(-1e12,1e12);self.a0.setDecimals(9)
        self.t0=QDoubleSpinBox();self.t0.setRange(-1e6,1e6);self.t0.setDecimals(6)
        self.tf=QDoubleSpinBox();self.tf.setRange(-1e6,1e6);self.tf.setDecimals(6);self.tf.setValue(10.0)
        self.nr=QSpinBox();self.nr.setRange(0,100000)
        self.rtol=QDoubleSpinBox();self.rtol.setRange(1e-12,1.0);self.rtol.setDecimals(10);self.rtol.setValue(1e-3)
        self.atol=QDoubleSpinBox();self.atol.setRange(1e-15,1.0);self.atol.setDecimals(12);self.atol.setValue(1e-6)
        self.node=QSpinBox();self.node.setRange(1,1000000);self.node.setValue(1)
        self.dof=QComboBox()
        for label,n in (("X translation",1),("Y translation",2),("X rotation",3),("Y rotation",4)):self.dof.addItem(label,n)
        form.addRow("Case name:",self.name_field)
        form.addRow("alpha[0] (t² coefficient):",self.a2);form.addRow("alpha[1] (t coefficient):",self.a1);form.addRow("alpha[2] (constant):",self.a0)
        form.addRow("Start time:",self.t0);form.addRow("End time:",self.tf);form.addRow("Reduced DOFs (0 = full):",self.nr)
        form.addRow("Relative tolerance:",self.rtol);form.addRow("Absolute tolerance:",self.atol);form.addRow("Output node:",self.node);form.addRow("Output DOF:",self.dof)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);form.addRow(buttons)

    def analysis_case(self):
        node=int(self.node.value());dof=int(self.dof.currentData())
        return AnalysisCase(
            "runup",
            {
                "alpha":[float(self.a2.value()),float(self.a1.value()),float(self.a0.value())],
                "tspan":[float(self.t0.value()),float(self.tf.value())],
                "nr":int(self.nr.value()),"rtol":float(self.rtol.value()),"atol":float(self.atol.value()),
            },
            self.name_field.text().strip() or "Run-up / Run-down",
            {"outnode":node+dof/10.0},
        )
