import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import QComboBox,QHBoxLayout,QLabel,QVBoxLayout,QWidget


class ClearanceResultView(QWidget):
    """A8 close-clearance workspace; it only presents native result arrays."""

    def __init__(self,record,parent=None):
        super().__init__(parent);self.record=record;self.result=record.execution.result
        layout=QVBoxLayout(self)
        self.stale_label=QLabel();layout.addWidget(self.stale_label)
        controls=QHBoxLayout();controls.addWidget(QLabel("Clearance location"))
        self.location=QComboBox()
        for i,(tag,node) in enumerate(zip(self.result.clearance_tags,self.result.clearance_nodes)):
            self.location.addItem(f"{tag} — node {int(node)}",i)
        selected=int(record.execution.case.options.get("selected_clearance_index",0))
        self.location.setCurrentIndex(max(0,min(selected,self.location.count()-1)))
        controls.addWidget(self.location);controls.addStretch(1);layout.addLayout(controls)
        self.detail=QLabel();self.detail.setWordWrap(True);layout.addWidget(self.detail)
        self.figure=Figure(figsize=(11,7),tight_layout=True)
        self.canvas=FigureCanvasQTAgg(self.figure);layout.addWidget(self.canvas,1)
        self.location.currentIndexChanged.connect(self._draw)
        self._draw();self.refresh_stale()

    def _draw(self):
        r=self.result;i=max(0,self.location.currentIndex())
        speed=np.asarray(r.speed_range_rad_s,float)
        rpm=speed*60/(2*np.pi)
        response=np.asarray(r.clearance_response_m_pp[i],float)*1e6
        limit=float(r.clearance_limit_m[i])*1e6

        self.figure.clear();ax=self.figure.add_subplot(1,1,1)
        ax.plot(rpm,response,label=f"{r.clearance_tags[i]} scaled pk-pk")
        ax.axhline(limit,linestyle="--",linewidth=1.2,label="75% diametral clearance")
        j=int(np.argmax(response))
        ax.scatter([rpm[j]],[response[j]],marker="x",s=90,linewidths=2.0,label="Maximum")
        ax.axvspan(
            r.minimum_allowable_speed_rad_s*60/(2*np.pi),
            r.maximum_continuous_speed_rad_s*60/(2*np.pi),
            alpha=.08,label="Nma–Nmc operating range"
        )
        ax.set_xlabel("Rotor speed [rpm]");ax.set_ylabel("Amplitude [µm peak-to-peak]")
        ax.set_title("API 617 Close-Clearance Analysis");ax.grid(True);ax.legend(loc="best")

        status="PASS" if bool(r.passed[i]) else "EXCEEDED"
        self.record.clearance_selection={"selected_clearance_index":i}
        cap="none" if r.scale_factor_cap is None else f"{r.scale_factor_cap:.6g}"
        self.detail.setText(
            f"{status} — {r.clearance_tags[i]}, node {int(r.clearance_nodes[i])}, "
            f"radial clearance={0.5*r.diametral_clearance_m[i]*1e6:.6g} µm, "
            f"diametral={r.diametral_clearance_m[i]*1e6:.6g} µm, "
            f"75% limit={limit:.6g} µm pk-pk, "
            f"max scaled response={r.max_clearance_response_m_pp[i]*1e6:.6g} µm pk-pk "
            f"at {r.speed_at_max_response_rad_s[i]*60/(2*np.pi):.6g} rpm. "
            f"Avl={r.vibration_limit_m_pp*1e6:.6g} µm pk-pk; "
            f"Amax={r.max_probe_amplitude_m_pp*1e6:.6g} µm pk-pk; "
            f"Scc={r.scale_factor:.8g}; cap={cap}."
        )
        self.canvas.draw_idle()

    def refresh_stale(self):
        state="⚠ OUTDATED" if self.record.stale else "CURRENT"
        overall="PASS" if bool(np.all(self.result.passed)) else "EXCEEDED"
        self.stale_label.setText(
            f"{state} — A8 native close-clearance / overall {overall} / "
            f"ROSS {self.result.metadata.get('ross_authority','unknown')}"
        )
