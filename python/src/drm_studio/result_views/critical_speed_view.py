from __future__ import annotations

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)

from drm_core.analysis.critical_speed import CriticalSpeedResult
from drm_core.units import rad_s_to_rpm


class CriticalSpeedResultView(QWidget):
    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.result = record.execution.result
        if not isinstance(self.result, CriticalSpeedResult):
            raise TypeError("CriticalSpeedResultView requires CriticalSpeedResult")

        outer = QVBoxLayout(self)
        head = QHBoxLayout()
        title = QLabel(record.execution.case.name or "Critical Speeds")
        title.setStyleSheet("font-weight:600;color:#0a4f98;")
        self.stale_label = QLabel("")
        self.stale_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        head.addWidget(title, 1)
        head.addWidget(self.stale_label)
        outer.addLayout(head)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["#", "Critical Speed (rpm)", "Critical Speed (rad/s)", "Iterations", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        outer.addWidget(self.table, 1)
        self._populate()
        self.refresh_stale()

    def _populate(self):
        critical = np.asarray(self.result.critical_speeds_rad_s, dtype=float)
        iterations = None if self.result.iterations is None else np.asarray(self.result.iterations)
        converged = None if self.result.converged is None else np.asarray(self.result.converged, dtype=bool)
        self.table.setRowCount(len(critical))
        for i, value in enumerate(critical):
            status = "—" if converged is None else ("Converged" if bool(converged[i]) else "Not converged")
            it = "—" if iterations is None else str(int(iterations[i]))
            values = (
                str(i + 1),
                f"{float(rad_s_to_rpm(value)):.6g}",
                f"{float(value):.6g}",
                it,
                status,
            )
            for col, text in enumerate(values):
                self.table.setItem(i, col, QTableWidgetItem(text))

    def refresh_stale(self):
        if self.record.stale:
            self.stale_label.setText("⚠ OUTDATED")
            self.stale_label.setStyleSheet("font-weight:700;color:#a15c00;")
        else:
            self.stale_label.setText("CURRENT")
            self.stale_label.setStyleSheet("font-weight:600;color:#16723a;")
