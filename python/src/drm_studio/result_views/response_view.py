from __future__ import annotations

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from drm_core.analysis.frequency_response import FrequencyResponseResult
from drm_core.post.response import plot_response, plot_frf
from drm_core.post.exports import export_figure


class FrequencyResponseResultView(QWidget):
    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record=record
        self.result=record.execution.result
        if not isinstance(self.result,FrequencyResponseResult):
            raise TypeError("FrequencyResponseResultView requires FrequencyResponseResult")
        self.outnodes=record.execution.case.options.get("outnodes",[1.1])
        outer=QVBoxLayout(self)
        head=QHBoxLayout()
        title=QLabel(record.execution.case.name or record.execution.case.kind)
        title.setStyleSheet("font-weight:600;color:#0a4f98;")
        self.stale_label=QLabel("");self.stale_label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        head.addWidget(title,1);head.addWidget(self.stale_label);outer.addLayout(head)

        self.figure=Figure(figsize=(8,6),tight_layout=True)
        self.canvas=FigureCanvasQTAgg(self.figure);outer.addWidget(self.canvas,1)
        self._draw()
        self.refresh_stale()

    def _draw(self):
        self.figure.clear()
        axes=[self.figure.add_subplot(211),self.figure.add_subplot(212)]
        kind=self.record.execution.case.kind
        if kind=="frequency_response":
            plot_response(self.result.speeds_rad_s,self.result.response,self.outnodes,axes=axes)
            axes[0].set_title("Synchronous Response")
        else:
            plot_frf(self.result.speeds_rad_s,self.result.response,self.outnodes,axes=axes)
            axes[0].set_title("Frequency Response Function")
        self.canvas.draw_idle()

    def save_figure(self,path):
        export_figure(self.figure,path)

    def refresh_stale(self):
        if self.record.stale:
            self.stale_label.setText("⚠ OUTDATED")
            self.stale_label.setStyleSheet("font-weight:700;color:#a15c00;")
        else:
            self.stale_label.setText("CURRENT")
            self.stale_label.setStyleSheet("font-weight:600;color:#16723a;")
