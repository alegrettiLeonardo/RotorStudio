"""Materialize real input histories; all response physics is native Fortran."""
import numpy as np
from PySide6.QtWidgets import (QDialog,QDialogButtonBox,QFormLayout,QLineEdit,QLabel,QComboBox,QDoubleSpinBox,QSpinBox,QTableWidget,QTableWidgetItem,QPushButton,QMessageBox,QCheckBox,QFileDialog)
from drm_core import AnalysisCase

class GeneralTimeSetupDialog(QDialog):
    def __init__(self,model,parent=None):
        super().__init__(parent);self.model=model;self.setWindowTitle('General Time Response F(t)');self.resize(960,720)
        form=QFormLayout(self);self.name_field=QLineEdit('General Time Response');form.addRow('Case',self.name_field)
        self.start=QDoubleSpinBox();self.stop=QDoubleSpinBox()
        for x in (self.start,self.stop):x.setRange(0,1e6);x.setDecimals(8);x.setSuffix(' s')
        self.stop.setValue(.04);self.points=QSpinBox();self.points.setRange(2,10000);self.points.setValue(81)
        self.time_values=QLineEdit();self.time_values.setPlaceholderText('Optional explicit time samples (s), comma-separated; overrides uniform grid')
        self.speed_values=QLineEdit('183');self.speed_values.setPlaceholderText('One constant or one Ω value per time sample, rad/s')
        self.gamma=QLineEdit('0.5');self.beta=QLineEdit('0.25');self.tol=QLineEdit('1e-6');self.weight=QCheckBox('Include gravity: g = -9.8065 m/s² in y')
        self.output_dof=QComboBox()
        for node in model.nodes:
            for dof in ('x','y','alpha','beta'):self.output_dof.addItem(f'Node {node.number}: {dof}')
        for label,w in [('Uniform start',self.start),('Uniform stop',self.stop),('Samples',self.points),('Explicit time grid',self.time_values),('Rotor speed Ω(t)',self.speed_values),('Newmark gamma',self.gamma),('Newmark beta',self.beta),('Absolute residual tolerance',self.tol),('Weight',self.weight),('Response DOF',self.output_dof)]:form.addRow(label,w)
        note=QLabel('SI input: x/y forces in N; alpha/beta moments in N m. Constant: value. Sine: amplitude, angular frequency (rad/s), phase (rad). Pulse: amplitude, start (s), end (s), inclusive. Samples: one value per time. Duplicate DOFs add. Initial q/v/a = 0; no static initialization.');note.setWordWrap(True);form.addRow(note)
        self.forces=QTableWidget(0,4);self.forces.setHorizontalHeaderLabels(['Node','DOF / unit','Input form','Parameters / explicit samples']);self.forces.horizontalHeader().setStretchLastSection(True);form.addRow(self.forces)
        add=QPushButton('Add force / moment');add.clicked.connect(lambda:self.add_force());form.addRow(add)
        remove=QPushButton('Remove selected entry');remove.clicked.connect(lambda:self.forces.removeRow(self.forces.currentRow()));form.addRow(remove)
        imp=QPushButton('Import CSV: time_s, speed_rad_s, F0 … F(ndof-1), SI');imp.clicked.connect(self._import_csv);form.addRow(imp)
        self.add_force()
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);form.addRow(buttons)
    @staticmethod
    def numbers(text):
        a=np.array([float(x.strip()) for x in text.split(',')]);
        if not np.isfinite(a).all():raise ValueError('All input samples must be finite.')
        return a
    def add_force(self,node=None,dof=0,kind='Constant',values='1'):
        row=self.forces.rowCount();self.forces.insertRow(row);nodes=QComboBox();dofs=QComboBox();shape=QComboBox()
        for n in self.model.nodes:nodes.addItem(str(n.number),n.number)
        if node is not None:nodes.setCurrentIndex(nodes.findData(node))
        dofs.addItems(['x — N','y — N','alpha — N m','beta — N m']);dofs.setCurrentIndex(dof)
        shape.addItems(['Constant','Sine','Pulse','Samples']);shape.setCurrentText(kind)
        for i,w in enumerate((nodes,dofs,shape)):self.forces.setCellWidget(row,i,w)
        self.forces.setItem(row,3,QTableWidgetItem(str(values)))
    def import_csv(self,path):
        expected=['time_s','speed_rad_s']+[f'F{i}' for i in range(4*len(self.model.nodes))]
        a=np.genfromtxt(path,delimiter=',',names=True)
        if list(a.dtype.names or [])!=expected or a.ndim!=1 or not 2<=len(a)<=10000:raise ValueError('CSV must have 2..10000 rows and exactly these SI columns: '+','.join(expected))
        data=np.column_stack([a[k] for k in expected])
        if not np.isfinite(data).all() or np.any(np.diff(data[:,0])<=0):raise ValueError('CSV requires finite values and strictly increasing time.')
        fmt=lambda x:','.join(format(float(v),'.17g') for v in x)
        self.time_values.setText(fmt(data[:,0]));self.speed_values.setText(fmt(data[:,1]));self.forces.setRowCount(0)
        for dof in range(data.shape[1]-2):
            if np.any(data[:,dof+2]):self.add_force(dof//4+1,dof%4,'Samples',fmt(data[:,dof+2]))
        if not self.forces.rowCount():self.add_force(values='0')
    def _import_csv(self):
        path,_=QFileDialog.getOpenFileName(self,'Import explicit SI history','','CSV (*.csv)')
        if path:
            try:self.import_csv(path)
            except (ValueError,OSError) as exc:QMessageBox.warning(self,'Invalid time history',str(exc))
    def analysis_case(self):
        t=self.numbers(self.time_values.text()) if self.time_values.text().strip() else np.linspace(self.start.value(),self.stop.value(),self.points.value())
        nt=len(t);n=4*len(self.model.nodes)
        if not 2<=nt<=10000 or np.any(np.diff(t)<=0):raise ValueError('Time must contain 2..10000 strictly increasing finite seconds.')
        if not 8<=n<=512 or 320*n*nt+240*n*n>512*1024**2:raise ValueError('Numerical budget exceeds 512 MiB or node limit; reduce nodes/samples.')
        speed=self.numbers(self.speed_values.text())
        if len(speed) not in (1,nt):raise ValueError(f'Speed requires 1 or {nt} values in rad/s.')
        gamma,beta,tol=map(float,(self.gamma.text(),self.beta.text(),self.tol.text()))
        if not all(np.isfinite(x) and x>0 for x in (gamma,beta,tol)):raise ValueError('gamma, beta, tol must be finite and positive.')
        if not self.forces.rowCount():raise ValueError('Enter at least one explicit force, including zero if intended.')
        F=np.zeros((n,nt))
        for row in range(self.forces.rowCount()):
            node=self.forces.cellWidget(row,0).currentData();dof=self.forces.cellWidget(row,1).currentIndex();kind=self.forces.cellWidget(row,2).currentText();item=self.forces.item(row,3)
            x=self.numbers(item.text() if item else '')
            if node is None or dof<0:raise ValueError('Select force node and DOF.')
            count={'Constant':1,'Sine':3,'Pulse':3,'Samples':nt}[kind]
            if len(x)!=count:raise ValueError(f'Row {row+1}: {kind} requires {count} values.')
            if kind=='Sine':f=x[0]*np.sin(x[1]*t+x[2])
            elif kind=='Pulse':
                if x[2]<x[1]:raise ValueError('Pulse end must not precede start.')
                f=np.where((t>=x[1])&(t<=x[2]),x[0],0.)
            else:f=x
            F[4*(node-1)+dof]+=f
        if not np.isfinite(F).all():raise ValueError('Summed force is nonfinite; reduce inputs.')
        return AnalysisCase('general_time_response',dict(time_s=t.tolist(),speed=float(speed[0]) if len(speed)==1 else speed.tolist(),force_real=F.tolist(),gamma=gamma,beta=beta,tol=tol,weight=self.weight.isChecked()),self.name_field.text().strip() or 'General Time Response',dict(output_dof=max(0,self.output_dof.currentIndex()),response='displacement'))
    def accept(self):
        try:self.analysis_case()
        except (ValueError,TypeError) as exc:QMessageBox.warning(self,'Invalid time response input',str(exc));return
        super().accept()
