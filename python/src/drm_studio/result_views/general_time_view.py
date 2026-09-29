import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox

def dfft(time,values):
    """One-sided unwindowed amplitude spectrum; never resample a nonuniform grid."""
    t=np.asarray(time);v=np.asarray(values);dt=np.diff(t)
    if len(t)<2 or np.any(dt<=0) or not np.allclose(dt,dt[0],rtol=1e-9,atol=0.0):return None
    amplitude=abs(np.fft.rfft(v))/len(v);amplitude[1:]*=2
    if len(v)%2==0:amplitude[-1]/=2
    return np.fft.rfftfreq(len(v),dt[0]),amplitude

class GeneralTimeResultView(QWidget):
    def __init__(self,record,parent=None):
        super().__init__(parent);self.record=record;self.result=record.execution.result
        layout=QVBoxLayout(self);self.stale_label=QLabel();layout.addWidget(self.stale_label)
        controls=QHBoxLayout();self.output_dof=QComboBox();self.response=QComboBox()
        for j in range(self.result.displacement.shape[0]):self.output_dof.addItem(f'Node {j//4+1}: {("x","y","alpha","beta")[j%4]}')
        self.response.addItems(['displacement','velocity','acceleration']);opts=record.execution.case.options;self.output_dof.setCurrentIndex(opts.get('output_dof',0));self.response.setCurrentText(opts.get('response','displacement'))
        for name,w in [('Response DOF',self.output_dof),('Response',self.response)]:controls.addWidget(QLabel(name));controls.addWidget(w)
        layout.addLayout(controls);self.figure=Figure(figsize=(12,9),tight_layout=True);self.canvas=FigureCanvasQTAgg(self.figure);layout.addWidget(self.canvas,1)
        for w in (self.output_dof,self.response):w.currentIndexChanged.connect(self._draw)
        self._draw();self.refresh_stale()
    def _draw(self):
        r=self.result;dof=self.output_dof.currentIndex();kind=self.response.currentText();value=getattr(r,kind)[dof];t=r.time_s
        self.record.time_selection=dict(output_dof=dof,response=kind)
        unit=('m' if dof%4<2 else 'rad')+{'displacement':'','velocity':'/s','acceleration':'/s²'}[kind]
        self.figure.clear();axes=[self.figure.add_subplot(4,2,i+1) for i in range(7)]
        axes[0].plot(t,value);axes[0].set(title=kind.title(),xlabel='Time (s)',ylabel=unit)
        node=dof//4;axes[1].plot(r.displacement[4*node],r.displacement[4*node+1]);axes[1].set(title='Displacement orbit',xlabel='x (m)',ylabel='y (m)')
        spec=dfft(t,value)
        if spec is None:axes[2].text(.5,.5,'DFFT unavailable: nonuniform time grid',ha='center',transform=axes[2].transAxes)
        else:axes[2].plot(*spec)
        axes[2].set(title='DFFT — unwindowed one-sided amplitude',xlabel='Frequency (Hz)',ylabel=unit)
        axes[3].plot(t,r.rotor_speed_rad_s);axes[3].set(title='Rotor speed',xlabel='Time (s)',ylabel='rad/s')
        axes[4].plot(t,r.force[dof]);axes[4].set(title='Effective force at selected DOF',xlabel='Time (s)',ylabel='N' if dof%4<2 else 'N m')
        axes[5].plot(t[1:],r.absolute_residual[1:]);axes[5].set(title='Equation residual norm (t0 prescribed)',xlabel='Time (s)',ylabel='||F − Ma − Cv − Kq||₂')
        axes[6].step(t,r.iterations,where='post');axes[6].set(title='Newton iterations',xlabel='Time (s)',ylabel='Iterations')
        self.canvas.draw_idle()
    def refresh_stale(self):self.stale_label.setText(('⚠ OUTDATED' if self.record.stale else 'CURRENT')+' — simple Newmark / native Fortran; q0=v0=a0=0')
