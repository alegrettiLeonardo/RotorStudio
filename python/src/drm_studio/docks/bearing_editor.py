from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView
)

from drm_core.units import m_to_mm, mm_to_m
from drm_core.validation.model import ModelValidationError
from drm_studio.commands.model_commands import EditBearingPropertiesCommand


_BEARING_NAMES = {
    1: "Rigid short / pinned",
    2: "Rigid long / clamped",
    3: "Constant diagonal K/C — translations",
    4: "Constant diagonal K/C — translations + rotations",
    5: "Constant full 2×2 K/C — translations",
    6: "Constant full 4×4 K/C",
    7: "Hydrodynamic short-width bearing",
    8: "Seal",
    20: "Coaxial coupling bearing",
}


def _schema(bearing_type):
    if bearing_type == 3:
        return [("Kxx","N/m",1),("Kyy","N/m",1),("Cxx","N·s/m",1),("Cyy","N·s/m",1)]
    if bearing_type == 4:
        return [
            ("Kxx","N/m",1),("Kyy","N/m",1),("Kθθ","N·m/rad",1),("Kψψ","N·m/rad",1),
            ("Cxx","N·s/m",1),("Cyy","N·s/m",1),("Cθθ","N·m·s/rad",1),("Cψψ","N·m·s/rad",1),
        ]
    if bearing_type == 5:
        return [
            ("Kxx","N/m",1),("Kxy","N/m",1),("Kyx","N/m",1),("Kyy","N/m",1),
            ("Cxx","N·s/m",1),("Cxy","N·s/m",1),("Cyx","N·s/m",1),("Cyy","N·s/m",1),
        ]
    if bearing_type == 6:
        labels=[]
        axes=("x","y","θ","ψ")
        for prefix,unit in (("K","SI stiffness"),("C","SI damping")):
            for i in axes:
                for j in axes:
                    labels.append((f"{prefix}{i}{j}",unit,1))
        return labels
    if bearing_type == 7:
        return [
            ("Static load F","N",1),
            ("Diameter D","mm",1000),
            ("Length L","mm",1000),
            ("Radial clearance c","mm",1000),
            ("Viscosity η","Pa·s",1),
        ]
    if bearing_type == 8:
        return [
            ("Pressure difference P","Pa",1),
            ("Radius R","mm",1000),
            ("Length L","mm",1000),
            ("Radial clearance c","mm",1000),
            ("Average axial velocity V","m/s",1),
            ("Friction coefficient","—",1),
        ]
    if bearing_type == 20:
        return [
            ("Coupled node 2","node",1),
            ("Kxx","N/m",1),("Kyy","N/m",1),("Cxx","N·s/m",1),("Cyy","N·s/m",1),
        ]
    return []


class BearingInspectorWidget(QWidget):
    def __init__(self,session,parent=None):
        super().__init__(parent);self.session=session;self._updating=False
        outer=QVBoxLayout(self)
        form=QFormLayout()
        self.type_label=QLabel("No bearing selected")
        self.node_field=QSpinBox();self.node_field.setRange(0,1000000);self.node_field.setReadOnly(True)
        form.addRow("Bearing type:",self.type_label);form.addRow("Node:",self.node_field)
        outer.addLayout(form)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(["Parameter","Value","Units"])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeToContents)
        outer.addWidget(self.table,1)
        self.error_label=QLabel("");self.error_label.setWordWrap(True);self.error_label.setStyleSheet("color:#a40000;");outer.addWidget(self.error_label)
        self.future_label=QLabel(
            "Tilting-pad, floating-ring, gas, thrust and thermal-bearing solvers are not available in the qualified Stage 1 core."
        );self.future_label.setWordWrap(True);self.future_label.setStyleSheet("color:#667788;");outer.addWidget(self.future_label)
        self.table.cellChanged.connect(self._cell_changed)
        session.selectionChanged.connect(lambda _:self.refresh())
        session.modelChanged.connect(self.refresh)
        self.refresh()

    def _selection(self):
        ref=self.session.selection
        if ref is None or ref.kind!="bearing" or not (0<=ref.index<len(self.session.project.model.bearings)):
            return None,None
        return ref.index,self.session.project.model.bearings[ref.index]

    def refresh(self):
        self._updating=True
        try:
            idx,bearing=self._selection();self.error_label.clear()
            if bearing is None:
                self.setEnabled(False);self.type_label.setText("No bearing selected");self.table.setRowCount(0);return
            self.setEnabled(True);self.type_label.setText(f"{bearing.bearing_type} — {_BEARING_NAMES.get(bearing.bearing_type,'Unknown')}")
            self.node_field.setValue(bearing.node)
            schema=_schema(bearing.bearing_type);values=list(bearing.properties)
            self.table.setRowCount(len(schema))
            for row,(name,unit,scale) in enumerate(schema):
                value=values[row] if row<len(values) else 0.0
                shown=float(value)*scale
                name_item=QTableWidgetItem(name);name_item.setFlags(name_item.flags()&~Qt.ItemIsEditable)
                value_item=QTableWidgetItem(f"{shown:.12g}")
                unit_item=QTableWidgetItem(unit);unit_item.setFlags(unit_item.flags()&~Qt.ItemIsEditable)
                self.table.setItem(row,0,name_item);self.table.setItem(row,1,value_item);self.table.setItem(row,2,unit_item)
        finally:self._updating=False

    def _cell_changed(self,row,column):
        if self._updating or column!=1:return
        idx,bearing=self._selection()
        if bearing is None:return
        schema=_schema(bearing.bearing_type)
        if row>=len(schema):return
        try:value=float(self.table.item(row,1).text())
        except (TypeError,ValueError):
            self.refresh();self.error_label.setText("Value must be numeric.");return
        _,_,scale=schema[row]
        canonical=value/scale
        props=list(bearing.properties)
        while len(props)<len(schema):props.append(0.0)
        if props[row]==canonical:return
        props[row]=canonical
        try:
            cmd=EditBearingPropertiesCommand(self.session,idx,props,f"Edit bearing {idx+1} property {row+1}")
            self.session.undo_stack.push(cmd);self.error_label.clear();self.session.log("INFO",f"Bearing {idx+1} property updated")
        except (ModelValidationError,ValueError) as exc:
            self.refresh();self.error_label.setText(str(exc));self.session.log("ERROR",str(exc))
