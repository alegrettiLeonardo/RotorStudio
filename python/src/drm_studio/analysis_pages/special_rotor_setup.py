from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDoubleSpinBox,
    QComboBox, QCheckBox, QMessageBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel
)
from drm_core import AnalysisCase, RotorDefinition
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
    def __init__(self,family,parent=None,rotor_definitions=()):
        super().__init__(parent);self.family=family
        title="Coaxial Rotor" if family=="coaxial" else "Asymmetric Rotor"
        self.setWindowTitle(title)
        outer=QVBoxLayout(self)
        form=QFormLayout()
        self.name=QLineEdit(title)
        self.analysis=QComboBox();self.analysis.addItem("Modal / eigenvalues","modal");self.analysis.addItem("Synchronous response","response")
        self.speed=_rpm_spin(3000.0);self.start=_rpm_spin(0.0);self.end=_rpm_spin(12000.0);self.step=_rpm_spin(250.0)
        self.vectors=QCheckBox("Compute eigenvectors");self.vectors.setChecked(True)
        self.node=QDoubleSpinBox();self.node.setRange(1.1,1000000.4);self.node.setDecimals(1);self.node.setSingleStep(1.0);self.node.setValue(1.1)
        form.addRow("Case name:",self.name);form.addRow("Analysis:",self.analysis);form.addRow("Modal speed:",self.speed)
        form.addRow("Response start:",self.start);form.addRow("Response end:",self.end);form.addRow("Response increment:",self.step)
        if family=="asymmetric":form.addRow(self.vectors)
        form.addRow("Response output node.dof:",self.node)
        outer.addLayout(form)

        self.rotor_table=None
        if family=="coaxial":
            outer.addWidget(QLabel("Rotor definitions — speed factor may be negative for counter-rotation:"))
            self.rotor_table=QTableWidget(0,3)
            self.rotor_table.setHorizontalHeaderLabels(["Node 1","Node 2","Speed factor"])
            for rotor in rotor_definitions:self._append_rotor(rotor)
            outer.addWidget(self.rotor_table,1)
            buttons_row=QHBoxLayout()
            add=QPushButton("Add rotor");remove=QPushButton("Remove selected")
            add.clicked.connect(lambda:self._append_rotor(RotorDefinition(1,1,1.0)))
            remove.clicked.connect(self._remove_rotors)
            buttons_row.addWidget(add);buttons_row.addWidget(remove);buttons_row.addStretch(1)
            outer.addLayout(buttons_row)

        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self._accept);buttons.rejected.connect(self.reject);outer.addWidget(buttons)
        self.analysis.currentIndexChanged.connect(self._sync);self._sync()

    def _append_rotor(self,rotor):
        row=self.rotor_table.rowCount();self.rotor_table.insertRow(row)
        for col,value in enumerate((rotor.node1,rotor.node2,rotor.speed_factor)):
            self.rotor_table.setItem(row,col,QTableWidgetItem(str(value)))

    def _remove_rotors(self):
        rows=sorted({i.row() for i in self.rotor_table.selectedIndexes()},reverse=True)
        for row in rows:self.rotor_table.removeRow(row)

    def rotor_definitions(self):
        if self.family!="coaxial":return None
        out=[]
        for row in range(self.rotor_table.rowCount()):
            try:
                node1=int(self.rotor_table.item(row,0).text())
                node2=int(self.rotor_table.item(row,1).text())
                factor=float(self.rotor_table.item(row,2).text())
            except (AttributeError,TypeError,ValueError) as exc:
                raise ValueError("Each coaxial rotor row requires integer Node 1/Node 2 and numeric speed factor.") from exc
            out.append(RotorDefinition(node1,node2,factor))
        if not out:raise ValueError("Coaxial analysis requires at least one rotor definition.")
        return out

    def _sync(self):
        modal=self.analysis.currentData()=="modal"
        self.speed.setEnabled(modal);self.vectors.setEnabled(modal and self.family=="asymmetric")
        for w in (self.start,self.end,self.step,self.node):w.setEnabled(not modal)

    def _accept(self):
        try:
            if self.analysis.currentData()=="response":_speed_grid(self.start.value(),self.end.value(),self.step.value())
            if self.family=="coaxial":self.rotor_definitions()
        except ValueError as exc:
            QMessageBox.warning(self,"Invalid analysis definition",str(exc));return
        self.accept()

    def analysis_case(self):
        modal=self.analysis.currentData()=="modal"
        if self.family=="coaxial":
            if modal:return AnalysisCase("coaxial_modal",{"speed_rad_s":float(rpm_to_rad_s(self.speed.value()))},self.name.text().strip() or "Coaxial Modal")
            return AnalysisCase("coaxial_frequency_response",{"speeds_rad_s":_speed_grid(self.start.value(),self.end.value(),self.step.value())},self.name.text().strip() or "Coaxial Response",{"outnodes":[float(self.node.value())]})
        if modal:return AnalysisCase("asymmetric_modal",{"speed_rad_s":float(rpm_to_rad_s(self.speed.value())),"with_eigenvectors":bool(self.vectors.isChecked())},self.name.text().strip() or "Asymmetric Modal")
        return AnalysisCase("asymmetric_frequency_response",{"speeds_rad_s":_speed_grid(self.start.value(),self.end.value(),self.step.value())},self.name.text().strip() or "Asymmetric Response",{"outnodes":[float(self.node.value())]})
