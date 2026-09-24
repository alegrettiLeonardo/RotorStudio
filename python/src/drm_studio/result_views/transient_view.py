from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTabWidget

from drm_core.analysis.transient import TransientResult
from drm_core.post.phase9 import fft_scale
from drm_core.post.response import _decode_outnode
from drm_core.units import rad_s_to_rpm


class TransientResultView(QWidget):
    def __init__(self,record,parent=None):
        super().__init__(parent)
        self.record=record;self.result=record.execution.result
        if not isinstance(self.result,TransientResult):raise TypeError("TransientResultView requires TransientResult")
        self.outnode=float(record.execution.case.options.get("outnode",1.1))
        self.dof_index=_decode_outnode(self.outnode)[2]
        outer=QVBoxLayout(self)
        head=QHBoxLayout();title=QLabel(record.execution.case.name or record.execution.case.kind);title.setStyleSheet("font-weight:600;color:#0a4f98;")
        self.stale_label=QLabel("");self.stale_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter);head.addWidget(title,1);head.addWidget(self.stale_label);outer.addLayout(head)
        self.tabs=QTabWidget();outer.addWidget(self.tabs,1)
        self._build_time();self._build_fft();self.refresh_stale()

    def _build_time(self):
        host=QWidget();layout=QVBoxLayout(host);self.time_figure=Figure(figsize=(8,5),tight_layout=True);fig=self.time_figure;canvas=FigureCanvasQTAgg(fig)
        if self.result.speed_rad_s is None and self.result.forcing is None:
            ax=fig.add_subplot(111);ax.plot(self.result.time_s,self.result.response[self.dof_index,:]);ax.set_xlabel("Time (s)");ax.set_ylabel("Response");ax.grid(True)
        else:
            ax=fig.add_subplot(211);ax.plot(self.result.time_s,self.result.response[self.dof_index,:]);ax.set_ylabel("Response");ax.grid(True)
            bx=fig.add_subplot(212)
            if self.result.speed_rad_s is not None:
                bx.plot(self.result.time_s,rad_s_to_rpm(self.result.speed_rad_s));bx.set_ylabel("Rotor Speed (rpm)")
            elif self.result.forcing is not None:
                bx.plot(self.result.time_s,self.result.forcing);bx.set_ylabel("Foundation excitation")
            bx.set_xlabel("Time (s)");bx.grid(True)
        layout.addWidget(canvas);self.tabs.addTab(host,"Time Response")

    def _build_fft(self):
        host=QWidget();layout=QVBoxLayout(host);self.fft_figure=Figure(figsize=(8,5),tight_layout=True);fig=self.fft_figure;canvas=FigureCanvasQTAgg(fig);ax=fig.add_subplot(111)
        try:
            fft=fft_scale(self.result.response[self.dof_index,:],self.result.time_s)
            n=max(1,len(fft.frequency_hz)//2)
            ax.plot(fft.frequency_hz[:n],np.abs(fft.spectrum[0,:n]));ax.set_xlabel("Frequency (Hz)");ax.set_ylabel("Scaled FFT magnitude");ax.grid(True)
        except ValueError as exc:
            ax.text(.5,.5,f"FFT unavailable: {exc}",ha="center",va="center",transform=ax.transAxes);ax.set_axis_off()
        layout.addWidget(canvas);self.tabs.addTab(host,"FFT")

    def refresh_stale(self):
        if self.record.stale:
            self.stale_label.setText("⚠ OUTDATED");self.stale_label.setStyleSheet("font-weight:700;color:#a15c00;")
        else:
            self.stale_label.setText("CURRENT");self.stale_label.setStyleSheet("font-weight:600;color:#16723a;")
