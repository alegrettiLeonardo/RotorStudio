from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox
)

from drm_core import Bearing
from drm_core.validation.model import ModelValidationError
from drm_studio.commands import EditBearingCommand


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
        labels=[];axes=("x","y","θ","ψ")
        for prefix,unit in (("K","SI stiffness"),("C","SI damping")):
            for i in axes:
                for j in axes:labels.append((prefix+i+j,unit,1))
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


def _default_properties(bearing_type, model, node):
    if bearing_type in (1,2):return ()
    if bearing_type==3:return (1.0e6,1.0e6,0.0,0.0)
    if bearing_type==4:return (1.0e6,1.0e6,0.0,0.0,0.0,0.0,0.0,0.0)
    if bearing_type==5:return (1.0e6,0.0,0.0,1.0e6,0.0,0.0,0.0,0.0)
    if bearing_type==6:
        k=[0.0]*16;c=[0.0]*16
        for i in range(4):k[4*i+i]=1.0e6
        return tuple(k+c)
    if bearing_type==7:return (1000.0,0.05,0.025,5.0e-5,0.02)
    if bearing_type==8:return (0.0,0.025,0.025,5.0e-5,1.0,0.01)
    if bearing_type==20:
        other=next((n.number for n in model.nodes if n.number!=node),node)
        return (float(other),1.0e6,1.0e6,0.0,0.0)
    raise ValueError("unsupported bearing type")


class BearingInspectorWidget(QWidget):
    def __init__(self,session,parent=None):
        super().__init__(parent);self.session=session;self._updating=False
        outer=QVBoxLayout(self)
        form=QFormLayout()
        self.type_combo=QComboBox()
        for t in (1,2,3,4,5,6,7,8,20):self.type_combo.addItem(str(t)+" — "+_BEARING_NAMES[t],t)
        self.node_field=QSpinBox();self.node_field.setRange(1,1000000);self.node_field.setKeyboardTracking(False)
        form.addRow("Bearing / seal type:",self.type_combo);form.addRow("Node:",self.node_field)
        outer.addLayout(form)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(["Parameter","Value","Units"])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeToContents)
        outer.addWidget(self.table,1)
        self.error_label=QLabel("");self.error_label.setWordWrap(True);self.error_label.setStyleSheet("color:#a40000;");outer.addWidget(self.error_label)
        self.future_label=QLabel(
            "NOT AVAILABLE / FUTURE: tilting-pad, floating-ring, gas, thrust and thermal-bearing solvers. "
            "This editor exposes only Stage 1 bearing types 1–8 and coaxial coupling type 20."
        );self.future_label.setWordWrap(True);self.future_label.setStyleSheet("color:#667788;");outer.addWidget(self.future_label)
        self.table.cellChanged.connect(self._cell_changed)
        self.type_combo.currentIndexChanged.connect(self._type_changed)
        self.node_field.editingFinished.connect(self._node_changed)
        session.selectionChanged.connect(lambda _:self.refresh())
        session.modelChanged.connect(self.refresh)
        self.refresh()

    def _selection(self):
        ref=self.session.selection
        if ref is None or ref.kind!="bearing" or not (0<=ref.index<len(self.session.project.model.bearings)):return None,None
        return ref.index,self.session.project.model.bearings[ref.index]

    def refresh(self):
        self._updating=True
        try:
            idx,bearing=self._selection();self.error_label.clear()
            if bearing is None:
                self.setEnabled(False);self.table.setRowCount(0);return
            self.setEnabled(True)
            pos=self.type_combo.findData(bearing.bearing_type)
            if pos>=0:self.type_combo.setCurrentIndex(pos)
            self.node_field.setValue(bearing.node)
            schema=_schema(bearing.bearing_type);values=list(bearing.properties)
            self.table.setRowCount(len(schema))
            for row,(name,unit,scale) in enumerate(schema):
                value=values[row] if row<len(values) else 0.0;shown=float(value)*scale
                name_item=QTableWidgetItem(name);name_item.setFlags(name_item.flags()&~Qt.ItemIsEditable)
                value_item=QTableWidgetItem(f"{shown:.12g}")
                unit_item=QTableWidgetItem(unit);unit_item.setFlags(unit_item.flags()&~Qt.ItemIsEditable)
                self.table.setItem(row,0,name_item);self.table.setItem(row,1,value_item);self.table.setItem(row,2,unit_item)
        finally:self._updating=False

    def _commit(self,new_bearing,text):
        idx,old=self._selection()
        if old is None:return
        try:
            self.session.undo_stack.push(EditBearingCommand(self.session,idx,new_bearing,text))
            self.error_label.clear();self.session.log("INFO",text)
        except (ModelValidationError,ValueError) as exc:
            self.refresh();self.error_label.setText(str(exc));self.session.log("ERROR",str(exc))

    def _type_changed(self):
        if self._updating:return
        idx,bearing=self._selection()
        if bearing is None:return
        t=int(self.type_combo.currentData())
        if t==bearing.bearing_type:return
        self._commit(Bearing(t,bearing.node,_default_properties(t,self.session.project.model,bearing.node)),f"Change bearing {idx+1} type to {t}")

    def _node_changed(self):
        if self._updating:return
        idx,bearing=self._selection()
        if bearing is None:return
        node=int(self.node_field.value())
        if node==bearing.node:return
        self._commit(Bearing(bearing.bearing_type,node,bearing.properties),f"Move bearing {idx+1} to node {node}")

    def _cell_changed(self,row,column):
        if self._updating or column!=1:return
        idx,bearing=self._selection()
        if bearing is None:return
        schema=_schema(bearing.bearing_type)
        if row>=len(schema):return
        try:value=float(self.table.item(row,1).text())
        except (TypeError,ValueError):
            self.refresh();self.error_label.setText("Value must be numeric.");return
        _,_,scale=schema[row];canonical=value/scale
        props=list(bearing.properties)
        while len(props)<len(schema):props.append(0.0)
        if props[row]==canonical:return
        props[row]=canonical
        self._commit(Bearing(bearing.bearing_type,bearing.node,tuple(props)),f"Edit bearing {idx+1} property {row+1}")
