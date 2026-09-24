from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import (
    QDialog,QDialogButtonBox,QFormLayout,QLineEdit,QDoubleSpinBox,QComboBox,QCheckBox,QMessageBox
)
from drm_core import AnalysisCase
from drm_core.units import rpm_to_rad_s


def _rpm_spin(value=0.0):
    w=QDoubleSpinBox();w.setRange(-1e8,1e8);w.setDecimals(3);w.setSuffix(" rpm");w.setValue(value);return w


def _speed_grid(start,end,step):
    if end<=start:raise ValueError("End speed must be greater than start speed.")
    if step<=0:raise ValueError("Speed increment must be positive.")
    n=int(np.floor((end-start)/step+1e-12))+1
    x=start+step*np.arange(n,dtype=float)
    if x[-1]<end-max(1e-9,abs(end)*1e-12):x=np.append(x,end)
    return np.asarray(rpm_to_rad_s(x),float).tolist()


class SpecialRotorSetupDialog(QDialog):
    def __init__(self,family,parent=None):
        super().__init__(parent);self.family=family
        title="Coaxial Rotor" if family=="coaxial" else "Asymmetric Rotor"
        self.setWindowTitle(title)
        form=QFormLayout(self)
        self.name=QLineEdit(title)
        self.analysis=QComboBox();self.analysis.addItem("Modal / eigenvalues","modal");self.analysis.addItem("Synchronous response","response")
        self.speed=_rpm_spin(3000.0);self.start=_rpm_spin(0.0);self.end=_rpm_spin(12000.0);self.step=_rpm_spin(250.0)
        self.vectors=QCheckBox("Compute eigenvectors");self.vectors.setChecked(True)
        self.node=QDoubleSpinBox();self.node.setRange(1.1,1000000.4);self.node.setDecimals(1);self.node.setSingleStep(1.0);self.node.setValue(1.1)
        form.addRow("Case name:",self.name);form.addRow("Analysis:",self.analysis);form.addRow("Modal speed:",self.speed)
        form.addRow("Response start:",self.start);form.addRow("Response end:",self.end);form.addRow("Response increment:",self.step)
        if family=="asymmetric":form.addRow(self.vectors)
        form.addRow("Response output node.dof:",self.node)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self._accept);buttons.rejected.connect(self.reject);form.addRow(buttons)
        self.analysis.currentIndexChanged.connect(self._sync);self._sync()

    def _sync(self):
        modal=self.analysis.currentData()=="modal"
        self.speed.setEnabled(modal);self.vectors.setEnabled(modal and self.family=="asymmetric")
        for w in (self.start,self.end,self.step,self.node):w.setEnabled(not modal)

    def _accept(self):
        if self.analysis.currentData()=="response":
            try:_speed_grid(self.start.value(),self.end.value(),self.step.value())
            except ValueError as exc:QMessageBox.warning(self,"Invalid speed range",str(exc));return
        self.accept()

    def analysis_case(self):
        modal=self.analysis.currentData()=="modal"
        if self.family=="coaxial":
            if modal:return AnalysisCase("coaxial_modal",{"speed_rad_s":float(rpm_to_rad_s(self.speed.value()))},self.name.text().strip() or "Coaxial Modal")
            return AnalysisCase("coaxial_frequency_response",{"speeds_rad_s":_speed_grid(self.start.value(),self.end.value(),self.step.value())},self.name.text().strip() or "Coaxial Response",{"outnodes":[float(self.node.value())]})
        if modal:return AnalysisCase("asymmetric_modal",{"speed_rad_s":float(rpm_to_rad_s(self.speed.value())),"with_eigenvectors":bool(self.vectors.isChecked())},self.name.text().strip() or "Asymmetric Modal")
        return AnalysisCase("asymmetric_frequency_response",{"speeds_rad_s":_speed_grid(self.start.value(),self.end.value(),self.step.value())},self.name.text().strip() or "Asymmetric Response",{"outnodes":[float(self.node.value())]})
