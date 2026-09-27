import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox

class GeneralFrfResultView(QWidget):
    """Selected transfer function display; H is exclusively the native result."""
    def __init__(self,record,parent=None):
        super().__init__(parent);self.record=record;self.result=record.execution.result
        layout=QVBoxLayout(self);self.stale_label=QLabel();layout.addWidget(self.stale_label)
        controls=QHBoxLayout();self.input_dof=QComboBox();self.output_dof=QComboBox();self.response=QComboBox()
        for j in range(self.result.H_disp.shape[0]):
            text=f'Node {j//4+1}: {("x","y","alpha","beta")[j%4]}'
            self.input_dof.addItem(text);self.output_dof.addItem(text)
        self.response.addItems(['displacement','velocity','acceleration'])
        opts=record.execution.case.options
        self.input_dof.setCurrentIndex(opts.get('input_dof',0));self.output_dof.setCurrentIndex(opts.get('output_dof',0));self.response.setCurrentText(opts.get('response','displacement'))
        for label,combo in [('Input',self.input_dof),('Output',self.output_dof),('Response',self.response)]:controls.addWidget(QLabel(label));controls.addWidget(combo)
        layout.addLayout(controls);self.figure=Figure(figsize=(10,6),tight_layout=True);self.canvas=FigureCanvasQTAgg(self.figure);layout.addWidget(self.canvas,1)
        for combo in [self.input_dof,self.output_dof,self.response]:combo.currentIndexChanged.connect(self._draw)
        self._draw();self.refresh_stale()
    def _draw(self):
        inp=self.input_dof.currentIndex();out=self.output_dof.currentIndex();kind=self.response.currentText()
        self.record.frf_selection=dict(input_dof=inp,output_dof=out,response=kind)
        array=getattr(self.result,{'displacement':'H_disp','velocity':'H_vel','acceleration':'H_acc'}[kind]);h=array[out,inp,:];w=self.result.frequency_rad_s
        output_unit='m' if out%4<2 else 'rad';input_unit='N' if inp%4<2 else 'N m'
        if kind=='velocity':output_unit+='/s'
        if kind=='acceleration':output_unit+='/s²'
        self.figure.clear();a=self.figure.add_subplot(221);b=self.figure.add_subplot(223);c=self.figure.add_subplot(122,projection='polar')
        a.plot(w,abs(h));a.set(title=f'{kind.title()} FRF',ylabel=f'{output_unit} / ({input_unit})',xlabel='Excitation ω (rad/s)')
        b.plot(w,np.angle(h));b.set(ylabel='Phase (rad)',xlabel='Excitation ω (rad/s)')
        c.plot(np.angle(h),abs(h));c.set_title('Polar response')
        self.canvas.draw_idle()
    def refresh_stale(self):self.stale_label.setText(('⚠ OUTDATED' if self.record.stale else 'CURRENT')+' — '+self.result.metadata['omega_policy'])
