from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QComboBox,
    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)

from drm_core.analysis.modal import ModalResult
from drm_core.post.modes import plot_mode
from drm_core.post.orbits import plot_orbits
from drm_core.units import rad_s_to_rpm


def _positive_mode_indices(result: ModalResult):
    eig = np.asarray(result.eigenvalues)
    positive = np.flatnonzero(eig.imag > 1e-10)
    return positive.tolist() if positive.size else list(range(0, len(eig), 2))


class CampbellResultView(QWidget):
    """Result workspace for the qualified Stage 1 modal_sweep result list."""

    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.results = list(record.execution.result)
        if not self.results or not all(isinstance(r, ModalResult) for r in self.results):
            raise TypeError("CampbellResultView requires a non-empty list of ModalResult")
        self.model_snapshot = record.model_snapshot
        self.nx = float(record.execution.case.options.get("nx", 2.0))
        self._mode_indices = _positive_mode_indices(self.results[0])

        outer = QVBoxLayout(self)
        head = QHBoxLayout()
        self.title = QLabel(record.execution.case.name or "Campbell")
        self.title.setStyleSheet("font-weight:600;color:#0a4f98;")
        self.stale_label = QLabel("")
        self.stale_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        head.addWidget(self.title, 1)
        head.addWidget(self.stale_label)
        outer.addLayout(head)

        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)
        self._build_campbell_tab()
        self._build_root_locus_tab()
        self._build_modes_tab()
        self.refresh_stale()

    @property
    def speeds_rad_s(self):
        return np.asarray([r.speed_rad_s for r in self.results], dtype=float)

    def _branch_matrix(self, attr):
        rows = [np.asarray(getattr(r, attr)) for r in self.results]
        n = min(x.size for x in rows)
        return np.column_stack([x[:n] for x in rows])

    def _build_campbell_tab(self):
        host = QWidget()
        layout = QVBoxLayout(host)
        self.campbell_figure = Figure(figsize=(8, 5), tight_layout=True)
        self.campbell_canvas = FigureCanvasQTAgg(self.campbell_figure)
        layout.addWidget(self.campbell_canvas, 1)

        self.summary = QTableWidget(0, 4)
        self.summary.setHorizontalHeaderLabels(["Speed (rpm)", "Mode", "Frequency (Hz)", "Whirl"])
        self.summary.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.summary.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.summary.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.summary.setMaximumHeight(180)
        layout.addWidget(self.summary)
        self.tabs.addTab(host, "Campbell")
        self._draw_campbell()
        self._populate_summary()

    def _whirl_label(self, result, idx):
        if result.kappa is None:
            return "—"
        values = np.asarray(result.kappa)[:, idx]
        values = values[np.isfinite(values)]
        if not values.size:
            return "—"
        score = float(np.mean(values))
        if score > 0.05:
            return "Forward"
        if score < -0.05:
            return "Backward"
        return "Mixed"

    def _draw_campbell(self):
        ax = self.campbell_figure.add_subplot(111)
        rpm = np.asarray(rad_s_to_rpm(self.speeds_rad_s), dtype=float)
        frequency = self._branch_matrix("natural_frequency_hz")
        positive = [i for i in self._mode_indices if i < frequency.shape[0]]

        for display_mode, idx in enumerate(positive, 1):
            line = ax.plot(rpm, frequency[idx, :], marker=".", markersize=3, linewidth=1)[0]
            if all(r.kappa is not None for r in self.results):
                fw_x, fw_y, bw_x, bw_y = [], [], [], []
                for k, result in enumerate(self.results):
                    label = self._whirl_label(result, idx)
                    target = (fw_x, fw_y) if label == "Forward" else (bw_x, bw_y) if label == "Backward" else None
                    if target is not None:
                        target[0].append(rpm[k]); target[1].append(frequency[idx, k])
                if fw_x:
                    ax.scatter(fw_x, fw_y, marker="o", s=8, label="FW" if display_mode == 1 else None)
                if bw_x:
                    ax.scatter(bw_x, bw_y, marker="x", s=12, label="BW" if display_mode == 1 else None)

        max_order = max(1, int(np.floor(self.nx)))
        for order in range(1, max_order + 1):
            excitation_hz = order * rpm / 60.0
            ax.plot(rpm, excitation_hz, linestyle="--", linewidth=1, label=f"{order}X")

        ax.set_title("Campbell Diagram")
        ax.set_xlabel("Rotor Speed (rpm)")
        ax.set_ylabel("Natural Frequency (Hz)")
        ax.grid(True)
        handles, labels = ax.get_legend_handles_labels()
        # Avoid a giant branch legend; only excitation/FW/BW labels are present.
        if labels:
            unique = {}
            for h, label in zip(handles, labels):
                if label and label not in unique:
                    unique[label] = h
            ax.legend(unique.values(), unique.keys(), loc="best")
        self.campbell_canvas.draw_idle()

    def _populate_summary(self):
        rows = []
        for k, result in enumerate(self.results):
            rpm = float(rad_s_to_rpm(result.speed_rad_s))
            for display_mode, idx in enumerate(self._mode_indices, 1):
                if idx >= len(result.natural_frequency_hz):
                    continue
                rows.append((
                    rpm, display_mode,
                    float(result.natural_frequency_hz[idx]),
                    self._whirl_label(result, idx),
                ))
        self.summary.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                text = f"{value:.6g}" if isinstance(value, float) else str(value)
                self.summary.setItem(row, col, QTableWidgetItem(text))

    def _build_root_locus_tab(self):
        host = QWidget()
        layout = QVBoxLayout(host)
        fig = Figure(figsize=(8, 5), tight_layout=True)
        canvas = FigureCanvasQTAgg(fig)
        ax = fig.add_subplot(111)
        eig = self._branch_matrix("eigenvalues")
        for idx in self._mode_indices:
            if idx < eig.shape[0]:
                ax.plot(eig[idx, :].real, eig[idx, :].imag, marker=".", markersize=3)
        ax.axvline(0.0, linewidth=0.8)
        ax.set_title("Root Locus")
        ax.set_xlabel("Real Part (rad/s)")
        ax.set_ylabel("Imaginary Part (rad/s)")
        ax.grid(True)
        layout.addWidget(canvas)
        self.tabs.addTab(host, "Root Locus")

    def _build_modes_tab(self):
        host = QWidget()
        outer = QVBoxLayout(host)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        for i, result in enumerate(self.results):
            self.speed_combo.addItem(f"{rad_s_to_rpm(result.speed_rad_s):.3f} rpm", i)
        controls.addWidget(self.speed_combo)
        controls.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        for display_mode, idx in enumerate(self._mode_indices, 1):
            self.mode_combo.addItem(f"Mode {display_mode}", idx)
        controls.addWidget(self.mode_combo)
        controls.addWidget(QLabel("Orbit node:"))
        self.node_combo = QComboBox()
        if self.model_snapshot is not None:
            preferred = [d.node for d in self.model_snapshot.disks]
            ordered = preferred + [n.number for n in self.model_snapshot.nodes if n.number not in preferred]
            for node in ordered:
                self.node_combo.addItem(f"Node {node}", node)
        controls.addWidget(self.node_combo)
        controls.addStretch(1)
        outer.addLayout(controls)

        split = QSplitter(Qt.Horizontal)
        self.mode_figure = Figure(figsize=(5, 4), tight_layout=True)
        self.mode_canvas = FigureCanvasQTAgg(self.mode_figure)
        self.orbit_figure = Figure(figsize=(4, 4), tight_layout=True)
        self.orbit_canvas = FigureCanvasQTAgg(self.orbit_figure)
        split.addWidget(self.mode_canvas)
        split.addWidget(self.orbit_canvas)
        outer.addWidget(split, 1)
        self.tabs.addTab(host, "Modes / Orbits")

        self.speed_combo.currentIndexChanged.connect(lambda _: self._draw_mode_orbit())
        self.mode_combo.currentIndexChanged.connect(lambda _: self._draw_mode_orbit())
        self.node_combo.currentIndexChanged.connect(lambda _: self._draw_mode_orbit())
        self._draw_mode_orbit()

    def _draw_mode_orbit(self):
        self.mode_figure.clear()
        self.orbit_figure.clear()
        if self.speed_combo.count() == 0 or self.mode_combo.count() == 0:
            return
        result = self.results[int(self.speed_combo.currentData())]
        idx = int(self.mode_combo.currentData())
        mode_ax = self.mode_figure.add_subplot(111, projection="3d")
        orbit_ax = self.orbit_figure.add_subplot(111)
        if result.eigenvectors is None or self.model_snapshot is None:
            mode_ax.text2D(0.5, 0.5, "Eigenvectors unavailable", transform=mode_ax.transAxes, ha="center")
            mode_ax.set_axis_off()
            orbit_ax.text(0.5, 0.5, "Orbit unavailable", ha="center", va="center")
            orbit_ax.set_axis_off()
        else:
            vector = np.asarray(result.eigenvectors)[:, idx]
            plot_mode(self.model_snapshot, vector, np.asarray(result.eigenvalues)[idx], ax=mode_ax)
            mode_ax.set_title(self.mode_combo.currentText())
            node = self.node_combo.currentData()
            if node is not None:
                plot_orbits(
                    vector, [int(node)],
                    title=f"Orbit — Node {node}",
                    eigenvalue=np.asarray(result.eigenvalues)[idx],
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
