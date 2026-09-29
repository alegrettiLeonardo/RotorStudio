import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QComboBox,QHBoxLayout,QLabel,QVBoxLayout,QWidget


_DIR={1:"Forward",2:"Mixed",3:"Backward"}


class Level1ResultView(QWidget):
    """A6 Level 1 Q-logdec view; no solver physics is recalculated."""

    def __init__(self,record,parent=None):
        super().__init__(parent);self.record=record;self.result=record.execution.result
        layout=QVBoxLayout(self)
        self.stale_label=QLabel();layout.addWidget(self.stale_label)
        controls=QHBoxLayout();controls.addWidget(QLabel("Q point"))
        self.point=QComboBox()
        for i,q in enumerate(self.result.cross_coupled_stiffness_n_m):
            self.point.addItem(f"{i+1}: {q:.6g} N/m",i)
        selected=int(record.execution.case.options.get("selected_q_index",0))
        self.point.setCurrentIndex(max(0,min(selected,self.point.count()-1)))
        controls.addWidget(self.point);controls.addStretch(1);layout.addLayout(controls)
        self.detail=QLabel();self.detail.setWordWrap(True);layout.addWidget(self.detail)
        self.figure=Figure(figsize=(11,7),tight_layout=True)
        self.canvas=FigureCanvasQTAgg(self.figure);layout.addWidget(self.canvas,1)
        self.point.currentIndexChanged.connect(self._draw)
        self._draw();self.refresh_stale()

    def _draw(self):
        r=self.result;i=max(0,self.point.currentIndex())
        q=np.asarray(r.cross_coupled_stiffness_n_m,float)
        ld=np.asarray(r.log_dec,float)
        self.figure.clear();ax=self.figure.add_subplot(1,1,1)
        ax.plot(q,ld,marker="o",label="Selected non-backward mode")
        ax.axhline(0.0,linestyle="--",linewidth=1.0,label="Zero log decrement")
        ax.scatter([q[i]],[ld[i]],marker="x",s=90,linewidths=2.0,label="Selected Q")
        ax.set_xlabel("Cross-coupled stiffness Q [N/m]")
        ax.set_ylabel("Logarithmic decrement")
        ax.set_title("Level 1 Stability Analysis")
        ax.grid(True);ax.legend(loc="best")
        mode=int(r.selected_mode_index[i])
        direction=_DIR.get(int(r.mode_direction_code[mode,i]),"Unknown")
        eig=complex(r.eigenvalue_real[mode,i],r.eigenvalue_imag[mode,i])
        self.record.level1_selection={"selected_q_index":i}
        self.detail.setText(
            f"Q={q[i]:.8g} N/m; log dec={ld[i]:.8g}; selected modal index={mode}; "
            f"whirl={direction}; eigenvalue={eig.real:.8g} + j{eig.imag:.8g} rad/s; "
            f"wn={r.natural_frequency_rad_s[mode,i]:.8g} rad/s; "
            f"wd={r.damped_frequency_rad_s[mode,i]:.8g} rad/s. "
            "Selection follows frozen ROSS: first mode that is not Backward; no "
            "branch tracking is applied across Q."
        )
        self.canvas.draw_idle()

    def refresh_stale(self):
        state="⚠ OUTDATED" if self.record.stale else "CURRENT"
        self.stale_label.setText(
            f"{state} — A6 native Level 1 / fixed speed {self.result.rotor_speed_rad_s:.6g} rad/s / "
            f"cross-coupling node {self.result.cross_coupling_node}"
        )
