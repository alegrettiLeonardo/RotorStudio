import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox

def orbit_xy(result,node,frequency_index,phase):
    """Node is zero-based; Re(q exp(j theta)), x horizontal and y vertical."""
    q=result.displacement[4*node:4*node+2,frequency_index]
    return np.real(q[:,None]*np.exp(1j*np.asarray(phase))[None,:])

class ForcedResponseResultView(QWidget):
    def __init__(self,record,parent=None):
        super().__init__(parent);self.record=record;self.result=record.execution.result
        layout=QVBoxLayout(self);self.stale_label=QLabel();layout.addWidget(self.stale_label)
        controls=QHBoxLayout();self.output_dof=QComboBox();self.response=QComboBox();self.frequency=QComboBox()
        for j in range(self.result.displacement.shape[0]):self.output_dof.addItem(f'Node {j//4+1}: {("x","y","alpha","beta")[j%4]}')
        self.response.addItems(['displacement','velocity','acceleration'])
        for w in self.result.frequency_rad_s:self.frequency.addItem(f'{w:.6g} rad/s')
        opts=record.execution.case.options;self.output_dof.setCurrentIndex(opts.get('output_dof',0));self.response.setCurrentText(opts.get('response','displacement'))
        for label,combo in [('Response DOF',self.output_dof),('Response',self.response),('Orbit frequency',self.frequency)]:controls.addWidget(QLabel(label));controls.addWidget(combo)
        layout.addLayout(controls);self.figure=Figure(figsize=(10,7),tight_layout=True);self.canvas=FigureCanvasQTAgg(self.figure);layout.addWidget(self.canvas,1)
        for combo in [self.output_dof,self.response,self.frequency]:combo.currentIndexChanged.connect(self._draw)
        self._draw();self.refresh_stale()
    def _draw(self):
        out=self.output_dof.currentIndex();kind=self.response.currentText();index=self.frequency.currentIndex()
        self.record.forced_selection=dict(output_dof=out,response=kind,frequency_index=index)
        value=getattr(self.result,kind)[out];w=self.result.frequency_rad_s
        unit=('m' if out%4<2 else 'rad')+{'displacement':'','velocity':'/s','acceleration':'/s²'}[kind]
        self.figure.clear();a=self.figure.add_subplot(221);b=self.figure.add_subplot(223);c=self.figure.add_subplot(222,projection='polar');d=self.figure.add_subplot(224)
        a.plot(w,abs(value));a.set(title=f'{kind.title()} amplitude',ylabel=unit,xlabel='Excitation ω (rad/s)')
        b.plot(w,np.angle(value));b.set(ylabel='Phase (rad)',xlabel='Excitation ω (rad/s)')
        c.plot(np.angle(value),abs(value));c.set_title('Polar response')
        xy=orbit_xy(self.result,out//4,index,np.linspace(0,2*np.pi,241));d.plot(*xy);d.set(title=f'Node {out//4+1} displacement orbit — {w[index]:.5g} rad/s',xlabel='x (m)',ylabel='y (m)');d.set_aspect('equal',adjustable='datalim')
        self.canvas.draw_idle()
    def refresh_stale(self):self.stale_label.setText(('⚠ OUTDATED' if self.record.stale else 'CURRENT')+' — '+self.result.coefficient_policy)
