import numpy as np
from PySide6.QtWidgets import (QDialog,QDialogButtonBox,QFormLayout,QLineEdit,QLabel,QComboBox,QDoubleSpinBox,QSpinBox,QTableWidget,QTableWidgetItem,QPushButton,QMessageBox)
from drm_core import AnalysisCase

class ForcedResponseSetupDialog(QDialog):
    """Complex-force entry only: scalar or explicit samples; no forcing physics."""
    def __init__(self,model,parent=None):
        super().__init__(parent);self.model=model;self.setWindowTitle('Forced Response');self.resize(850,620)
        form=QFormLayout(self);self.name_field=QLineEdit('Forced Response')
        self.policy=QComboBox();self.policy.addItems(['Synchronous Ω=ω','Fixed rotor speed Ω'])
        self.speed=QDoubleSpinBox();self.speed.setRange(-1e6,1e6);self.speed.setValue(183.);self.speed.setSuffix(' rad/s')
        self.start=QDoubleSpinBox();self.stop=QDoubleSpinBox()
        for x in [self.start,self.stop]:x.setRange(0,1e6);x.setDecimals(4);x.setSuffix(' rad/s')
        self.stop.setValue(600.);self.points=QSpinBox();self.points.setRange(1,10000);self.points.setValue(61)
        self.output_dof=QComboBox()
        for node in model.nodes:
            for dof in ['x','y','alpha','beta']:self.output_dof.addItem(f'Node {node.number}: {dof}')
        for name,w in [('Case',self.name_field),('Speed policy',self.policy),('Rotor speed Ω',self.speed),('Excitation ω start',self.start),('Excitation ω stop',self.stop),('Samples',self.points),('Response DOF',self.output_dof)]:form.addRow(name,w)
        note=QLabel('Forces: x/y in N; moments: alpha/beta in N m. Real = in-phase; imaginary = quadrature. Enter one constant or comma-separated values, one per frequency. Duplicate DOFs add. No automatic unbalance.');note.setWordWrap(True);form.addRow(note)
        self.forces=QTableWidget(0,4);self.forces.setHorizontalHeaderLabels(['Node','DOF / unit','Real samples','Imaginary samples']);self.forces.horizontalHeader().setStretchLastSection(True);form.addRow(self.forces)
        add=QPushButton('Add force / moment');add.clicked.connect(lambda:self.add_force());form.addRow(add)
        remove=QPushButton('Remove selected entry');remove.clicked.connect(lambda:self.forces.removeRow(self.forces.currentRow()));form.addRow(remove)
        self.add_force()
        self.policy.currentIndexChanged.connect(lambda i:self.speed.setEnabled(i==1));self.speed.setEnabled(False)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);form.addRow(buttons)
    def add_force(self,node=None,dof=0,real='1',imag='0'):
        row=self.forces.rowCount();self.forces.insertRow(row);nodes=QComboBox();dofs=QComboBox()
        for n in self.model.nodes:nodes.addItem(str(n.number),n.number)
        if node is not None:nodes.setCurrentIndex(nodes.findData(node))
        dofs.addItems(['x — N','y — N','alpha — N m','beta — N m']);dofs.setCurrentIndex(dof)
        self.forces.setCellWidget(row,0,nodes);self.forces.setCellWidget(row,1,dofs)
        self.forces.setItem(row,2,QTableWidgetItem(str(real)));self.forces.setItem(row,3,QTableWidgetItem(str(imag)))
    def analysis_case(self):
        nf=self.points.value();n=4*len(self.model.nodes)
        if self.stop.value()<self.start.value():raise ValueError('Excitation stop must be at least start; correct the frequency range.')
        if 320*n*nf+160*n*n>512*1024**2:raise ValueError('Sweep exceeds 512 MiB budget; reduce nodes or samples.')
        if not self.forces.rowCount():raise ValueError('Supply at least one force entry; enter zero explicitly for a zero-force test.')
        force=np.zeros((n,nf),complex)
        for row in range(self.forces.rowCount()):
            node=self.forces.cellWidget(row,0).currentData();dof=self.forces.cellWidget(row,1).currentIndex()
            if node is None or dof<0:raise ValueError('Select a valid force node and DOF.')
            components=[]
            for col in (2,3):
                item=self.forces.item(row,col);values=np.array([float(x.strip()) for x in (item.text() if item else '').split(',')])
                if len(values) not in (1,nf) or not np.isfinite(values).all():raise ValueError(f'Force row {row+1}: expected one or {nf} finite samples in N / N m.')
                components.append(values)
            force[4*(node-1)+dof]+=components[0]+1j*components[1]
        if not np.isfinite(force).all():raise ValueError('Summed force is nonfinite; reduce the entered values.')
        p=dict(frequency_rad_s=np.linspace(self.start.value(),self.stop.value(),nf).tolist(),speed=self.speed.value() if self.policy.currentIndex()==1 else None,force_real=force.real.tolist(),force_imag=force.imag.tolist())
        return AnalysisCase('forced_response',p,self.name_field.text().strip() or 'Forced Response',dict(output_dof=max(0,self.output_dof.currentIndex()),response='displacement'))
    def accept(self):
        try:self.analysis_case()
        except (ValueError,TypeError) as exc:QMessageBox.warning(self,'Invalid force spectrum',str(exc));return
        super().accept()
