import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QLabel,QVBoxLayout,QWidget


class API617UnbalanceResultView(QWidget):
    """A7 API 617 placement view; no physics is recalculated."""

    def __init__(self,record,parent=None):
        super().__init__(parent);self.record=record;self.result=record.execution.result
        layout=QVBoxLayout(self)
        self.stale_label=QLabel();layout.addWidget(self.stale_label)
        self.detail=QLabel();self.detail.setWordWrap(True);layout.addWidget(self.detail)
        self.figure=Figure(figsize=(11,7),tight_layout=True)
        self.canvas=FigureCanvasQTAgg(self.figure);layout.addWidget(self.canvas,1)
        self._draw();self.refresh_stale()

    def _draw(self):
        r=self.result
        node_axis=np.arange(1,len(r.mode_major_axis)+1,dtype=int)
        amp=np.asarray(r.mode_major_axis,float)
        scale=float(np.max(amp)) if amp.size else 1.0
        normalized=amp/scale if scale>0 else amp

        self.figure.clear();ax=self.figure.add_subplot(1,1,1)
        ax.plot(node_axis,normalized,marker="o",label="Selected mode |major axis|")
        for j,node in enumerate(np.asarray(r.nodes,dtype=int)):
            ax.axvline(node,linestyle="--",linewidth=1.0)
            ax.scatter([node],[normalized[node-1]],marker="x",s=90,linewidths=2.0)
        ax.set_xlabel("RotorStudio node [one-based]")
        ax.set_ylabel("Normalized orbit major-axis amplitude")
        ax.set_title("API 617 Unbalance Placement")
        ax.grid(True);ax.legend(loc="best")

        rpm=r.maximum_continuous_speed_rad_s*60.0/(2*np.pi)
        rows=[]
        for node,mag,phase,load in zip(
            r.nodes,r.unbalance_magnitude_kg_m,r.unbalance_phase_rad,r.static_load_kg
        ):
            rows.append(
                f"node {int(node)}: Ua={float(mag):.8g} kg·m, "
                f"phase={np.degrees(float(phase)):.6g}°, W={float(load):.8g} kg"
            )
        self.detail.setText(
            f"Nmc={r.maximum_continuous_speed_rad_s:.8g} rad/s "
            f"({rpm:.8g} rpm); requested forward mode={r.requested_forward_mode+1}; "
            f"raw modal index={r.mode_index}; wd={r.mode_frequency_rad_s:.8g} rad/s. "
            + " | ".join(rows)
        )
        self.canvas.draw_idle()

    def refresh_stale(self):
        state="⚠ OUTDATED" if self.record.stale else "CURRENT"
        self.stale_label.setText(
            f"{state} — A7 native API 617 unbalance placement / "
            f"ROSS {self.result.metadata.get('ross_authority','unknown')}"
        )
