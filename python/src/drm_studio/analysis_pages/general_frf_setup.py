import numpy as np
from PySide6.QtWidgets import QDialog,QDialogButtonBox,QFormLayout,QLineEdit,QLabel,QComboBox,QDoubleSpinBox,QSpinBox
from drm_core import AnalysisCase

class GeneralFrfSetupDialog(QDialog):
    def __init__(self,model,parent=None):
        super().__init__(parent);self.setWindowTitle('General FRF — Matrix')
        form=QFormLayout(self);self.name_field=QLineEdit('General FRF')
        self.policy=QComboBox();self.policy.addItems(['Synchronous Ω=ω','Fixed rotor speed Ω','Free-free convention: Ω=0, bearings retained'])
        self.speed=QDoubleSpinBox();self.speed.setRange(-1e6,1e6);self.speed.setValue(183.);self.speed.setSuffix(' rad/s')
        self.start=QDoubleSpinBox();self.stop=QDoubleSpinBox()
        for x in [self.start,self.stop]:x.setRange(0,1e6);x.setDecimals(4);x.setSuffix(' rad/s')
        self.stop.setValue(600.);self.points=QSpinBox();self.points.setRange(1,10000);self.points.setValue(61)
        self.input_dof=QComboBox();self.output_dof=QComboBox()
        for n in model.nodes:
            for label in ['x','y','alpha','beta']:
                for combo in [self.input_dof,self.output_dof]:combo.addItem(f'Node {n.number}: {label}')
        self.response=QComboBox();self.response.addItems(['displacement','velocity','acceleration'])
        for name,widget in [('Case',self.name_field),('Speed policy',self.policy),('Rotor speed Ω',self.speed),('Excitation ω start',self.start),('Excitation ω stop',self.stop),('Samples',self.points),('Input DOF',self.input_dof),('Output DOF',self.output_dof),('Response',self.response)]:form.addRow(name,widget)
        note=QLabel('Full-order 4-DOF matrix. Circular type-2 shaft; coefficient-table or constant radial bearings. Direct physical bearing solves are unavailable.');note.setWordWrap(True);form.addRow(note)
        self.policy.currentIndexChanged.connect(lambda i:self.speed.setEnabled(i==1));self.speed.setEnabled(False)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);form.addRow(buttons)
    def analysis_case(self):
        p=dict(frequency_rad_s=np.linspace(self.start.value(),self.stop.value(),self.points.value()).tolist(),speed=self.speed.value() if self.policy.currentIndex()==1 else None,free_free=self.policy.currentIndex()==2)
        return AnalysisCase('general_frf',p,self.name_field.text().strip() or 'General FRF',dict(input_dof=max(0,self.input_dof.currentIndex()),output_dof=max(0,self.output_dof.currentIndex()),response=self.response.currentText()))
