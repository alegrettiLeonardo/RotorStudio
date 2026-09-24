from __future__ import annotations

import numpy as np

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QSplitter, QComboBox, QAbstractItemView, QHeaderView
)

from drm_core.analysis.modal import ModalResult
from drm_core.post.modes import plot_mode
from drm_core.post.orbits import plot_orbits
from drm_core.units import rad_s_to_rpm


class ModalResultView(QWidget):
    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.result = record.execution.result
        if not isinstance(self.result, ModalResult):
            raise TypeError("ModalResultView requires a ModalResult")
        self.model_snapshot = record.model_snapshot
        self._mode_indices = self._physical_mode_indices()
        self._build_ui()
        self.refresh_stale()
        if self._mode_indices:
            self.table.selectRow(0)

    def _physical_mode_indices(self):
        eig = np.asarray(self.result.eigenvalues)
        positive = np.flatnonzero(eig.imag > 1e-10)
        if positive.size:
            return positive.tolist()
        return list(range(0, len(eig), 2))

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        head = QHBoxLayout()
        case_name = self.record.execution.case.name or "Modal"
        rpm = rad_s_to_rpm(self.result.speed_rad_s)
        self.title = QLabel(f"{case_name} — {rpm:.3f} rpm")
        self.title.setStyleSheet("font-weight:600;color:#0a4f98;")
        self.stale_label = QLabel("")
        self.stale_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        head.addWidget(self.title, 1)
        head.addWidget(self.stale_label)
        outer.addLayout(head)

        splitter = QSplitter(Qt.Vertical)
        upper = QSplitter(Qt.Horizontal)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Mode", "Natural Frequency (Hz)", "Damping Ratio", "Whirl"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._populate_table()
        upper.addWidget(self.table)

        plots = QSplitter(Qt.Horizontal)
        self.mode_figure = Figure(figsize=(5.0, 3.2), tight_layout=True)
        self.mode_canvas = FigureCanvasQTAgg(self.mode_figure)
        self.orbit_figure = Figure(figsize=(4.0, 3.2), tight_layout=True)
        self.orbit_canvas = FigureCanvasQTAgg(self.orbit_figure)
        plots.addWidget(self.mode_canvas)
        plots.addWidget(self.orbit_canvas)
        upper.addWidget(plots)
        upper.setStretchFactor(0, 1)
        upper.setStretchFactor(1, 2)

        splitter.addWidget(upper)

        node_bar = QWidget()
        node_layout = QHBoxLayout(node_bar)
        node_layout.setContentsMargins(4, 1, 4, 1)
        node_layout.addWidget(QLabel("Orbit output node:"))
        self.node_combo = QComboBox()
        if self.model_snapshot is not None:
            preferred = [d.node for d in self.model_snapshot.disks]
            ordered = preferred + [
                n.number for n in self.model_snapshot.nodes if n.number not in preferred
            ]
            for node in ordered:
                self.node_combo.addItem(f"Node {node}", node)
        node_layout.addWidget(self.node_combo)
        node_layout.addStretch(1)
        splitter.addWidget(node_bar)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        outer.addWidget(splitter, 1)

        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.node_combo.currentIndexChanged.connect(lambda _: self._update_plots())

    def _whirl_label(self, mode_index):
        kappa = self.result.kappa
        if kappa is None:
            return "—"
        values = np.asarray(kappa)[:, mode_index]
        values = values[np.isfinite(values)]
        if not values.size:
            return "—"
        score = float(np.mean(values))
        if score > 0.05:
            return "Forward"
        if score < -0.05:
            return "Backward"
        return "Mixed"

    def _populate_table(self):
        freq = np.asarray(self.result.natural_frequency_hz)
        damp = np.asarray(self.result.damping_ratio)
        self.table.setRowCount(len(self._mode_indices))
        for row, idx in enumerate(self._mode_indices):
            values = (
                str(row + 1),
                f"{float(freq[idx]):.6g}",
                f"{float(damp[idx]):.6g}",
                self._whirl_label(idx),
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, idx)
                self.table.setItem(row, col, item)

    def _selection_changed(self):
        self._update_plots()

    def selected_mode_index(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._mode_indices):
            return None
        return self._mode_indices[row]

    def _update_plots(self):
        idx = self.selected_mode_index()
        self.mode_figure.clear()
        self.orbit_figure.clear()
        if idx is None:
            self.mode_canvas.draw_idle()
            self.orbit_canvas.draw_idle()
            return

        vectors = self.result.eigenvectors
        if vectors is None or self.model_snapshot is None:
            ax = self.mode_figure.add_subplot(111)
            ax.text(0.5, 0.5, "Eigenvectors were not requested", ha="center", va="center")
            ax.set_axis_off()
        else:
            ax = self.mode_figure.add_subplot(111, projection="3d")
            plot_mode(
                self.model_snapshot,
                np.asarray(vectors)[:, idx],
                np.asarray(self.result.eigenvalues)[idx],
                ax=ax,
            )
            ax.set_title(f"Mode {self._mode_indices.index(idx) + 1}")

        orbit_ax = self.orbit_figure.add_subplot(111)
        node = self.node_combo.currentData()
        if vectors is None or node is None:
            orbit_ax.text(0.5, 0.5, "Orbit unavailable", ha="center", va="center")
            orbit_ax.set_axis_off()
        else:
            plot_orbits(
                np.asarray(vectors)[:, idx],
                [int(node)],
                title=f"Orbit — Node {node}",
                eigenvalue=np.asarray(self.result.eigenvalues)[idx],
                ax=orbit_ax,
            )
        self.mode_canvas.draw_idle()
        self.orbit_canvas.draw_idle()

    def refresh_stale(self):
        if self.record.stale:
            self.stale_label.setText("⚠ OUTDATED")
            self.stale_label.setStyleSheet("font-weight:700;color:#a15c00;")
        else:
            self.stale_label.setText("CURRENT")
            self.stale_label.setStyleSheet("font-weight:600;color:#16723a;")
