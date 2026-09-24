from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QSplitter

from drm_core.analysis.coaxial import CoaxialModalResult,CoaxialFrequencyResponseResult
from drm_core.analysis.asymmetric import AsymmetricModalResult,AsymmetricFrequencyResponseResult
from drm_core.post.response import plot_response


class SpecialRotorResultView(QWidget):
    def __init__(self,record,parent=None):
        super().__init__(parent);self.record=record;self.result=record.execution.result
        outer=QVBoxLayout(self);head=QHBoxLayout();title=QLabel(record.execution.case.name or record.execution.case.kind);title.setStyleSheet("font-weight:600;color:#0a4f98;")
        self.stale_label=QLabel("");self.stale_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter);head.addWidget(title,1);head.addWidget(self.stale_label);outer.addLayout(head)
        if isinstance(self.result,(CoaxialModalResult,AsymmetricModalResult)):self._build_modal(outer)
        elif isinstance(self.result,(CoaxialFrequencyResponseResult,AsymmetricFrequencyResponseResult)):self._build_response(outer)
        else:raise TypeError("unsupported special rotor result")
        self.refresh_stale()

    def _build_modal(self,outer):
        split=QSplitter(Qt.Horizontal)
        eig=np.asarray(self.result.eigenvalues)
        table=QTableWidget(len(eig),5);table.setHorizontalHeaderLabels(["#","Real λ","Imag λ","|Im λ| / 2π (Hz)","Stability"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for i,value in enumerate(eig):
            vals=(str(i+1),f"{value.real:.6g}",f"{value.imag:.6g}",f"{abs(value.imag)/(2*np.pi):.6g}","Stable" if value.real<0 else "Unstable" if value.real>0 else "Neutral")
            for j,text in enumerate(vals):table.setItem(i,j,QTableWidgetItem(text))
        split.addWidget(table)
        fig=Figure(figsize=(5,4),tight_layout=True);canvas=FigureCanvasQTAgg(fig);ax=fig.add_subplot(111)
        ax.scatter(eig.real,eig.imag,s=14);ax.axvline(0.0,linewidth=.8);ax.set_xlabel("Real λ (rad/s)");ax.set_ylabel("Imag λ (rad/s)");ax.set_title("Eigenvalue Map");ax.grid(True)
        split.addWidget(canvas);outer.addWidget(split,1)

    def _build_response(self,outer):
        fig=Figure(figsize=(8,6),tight_layout=True);canvas=FigureCanvasQTAgg(fig);axes=[fig.add_subplot(211),fig.add_subplot(212)]
        outnodes=self.record.execution.case.options.get("outnodes",[1.1])
        plot_response(self.result.speeds_rad_s,self.result.response,outnodes,axes=axes)
        axes[0].set_title("Rotor Response")
        outer.addWidget(canvas,1)

    def refresh_stale(self):
        if self.record.stale:
            self.stale_label.setText("⚠ OUTDATED");self.stale_label.setStyleSheet("font-weight:700;color:#a15c00;")
        else:
            self.stale_label.setText("CURRENT");self.stale_label.setStyleSheet("font-weight:600;color:#16723a;")
