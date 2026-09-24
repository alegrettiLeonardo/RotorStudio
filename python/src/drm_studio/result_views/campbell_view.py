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
from drm_core.post.modes import plot_mode_3d
from drm_core.post.orbits import plot_orbits
from drm_core.units import rad_s_to_rpm


def _positive_mode_indices(result: ModalResult):
    eig = np.asarray(result.eigenvalues)
    positive = np.flatnonzero(eig.imag > 1e-10)
    return positive.tolist() if positive.size else list(range(0, len(eig), 2))


class CampbellResultView(QWidget):
    """Mockup-conformant Campbell dashboard over the qualified modal sweep."""

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
        outer.setContentsMargins(3, 3, 3, 3)
        head = QHBoxLayout()
        self.title = QLabel(record.execution.case.name or "Campbell")
        self.title.setObjectName("SectionHeaderTitle")
        self.stale_label = QLabel("")
        self.stale_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        head.addWidget(self.title, 1)
        head.addWidget(self.stale_label)
        outer.addLayout(head)

        # Visual authority pagination: Campbell | Root Locus | Modes | Orbits | FRF | +
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)
        self._build_dashboard_tab()
        self._build_root_locus_tab()
        self._build_mode_tab()
        self._build_orbit_tab()

        frf_placeholder = QLabel(
            "Frequency-response results are opened as their own qualified Result document."
        )
        frf_placeholder.setAlignment(Qt.AlignCenter)
        self.tabs.addTab(frf_placeholder, "FRF")
        self.tabs.setTabEnabled(self.tabs.count() - 1, False)
        plus_placeholder = QWidget()
        self.tabs.addTab(plus_placeholder, "+")
        self.tabs.setTabEnabled(self.tabs.count() - 1, False)

        self.refresh_stale()

    @property
    def speeds_rad_s(self):
        return np.asarray([r.speed_rad_s for r in self.results], dtype=float)

    def _branch_matrix(self, attr):
        rows = [np.asarray(getattr(r, attr)) for r in self.results]
        n = min(x.size for x in rows)
        return np.column_stack([x[:n] for x in rows])

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

    # ------------------------------------------------------------------
    # Campbell dashboard — main plot + root locus + mode shape + orbit +
    # summary table, matching the supplied reference layout.
    # ------------------------------------------------------------------
    def _build_dashboard_tab(self):
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(3)

        self.campbell_figure = Figure(figsize=(9, 4.6), tight_layout=True)
        self.campbell_canvas = FigureCanvasQTAgg(self.campbell_figure)
        layout.addWidget(self.campbell_canvas, 6)

        mini = QSplitter(Qt.Horizontal)
        self.root_preview_figure = Figure(figsize=(3.1, 2.2), tight_layout=True)
        self.root_preview_canvas = FigureCanvasQTAgg(self.root_preview_figure)
        mini.addWidget(self.root_preview_canvas)

        self.mode_preview_figure = Figure(figsize=(3.1, 2.2), tight_layout=True)
        self.mode_preview_canvas = FigureCanvasQTAgg(self.mode_preview_figure)
        mini.addWidget(self.mode_preview_canvas)

        self.orbit_preview_figure = Figure(figsize=(3.1, 2.2), tight_layout=True)
        self.orbit_preview_canvas = FigureCanvasQTAgg(self.orbit_preview_figure)
        mini.addWidget(self.orbit_preview_canvas)
        for i in range(3):
            mini.setStretchFactor(i, 1)
        layout.addWidget(mini, 3)

        self.summary = QTableWidget(0, 5)
        self.summary.setHorizontalHeaderLabels(
            ["Mode", "Critical / Selected Speed (rpm)", "Natural Frequency (Hz)", "Damping Ratio", "Whirl"]
        )
        self.summary.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.summary.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.summary.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.summary.setSelectionMode(QAbstractItemView.SingleSelection)
        self.summary.setMaximumHeight(165)
        layout.addWidget(self.summary, 2)

        self.tabs.addTab(host, "Campbell")
        self._draw_campbell()
        self._draw_root_preview()
        self._populate_summary()
        if self.summary.rowCount():
            self.summary.selectRow(0)
        self.summary.itemSelectionChanged.connect(self._dashboard_selection_changed)
        self._draw_dashboard_mode_orbit()

    def _draw_campbell(self):
        self.campbell_figure.clear()
        ax = self.campbell_figure.add_subplot(111)
        rpm = np.asarray(rad_s_to_rpm(self.speeds_rad_s), dtype=float)
        frequency = self._branch_matrix("natural_frequency_hz")
        positive = [i for i in self._mode_indices if i < frequency.shape[0]]

        for display_mode, idx in enumerate(positive, 1):
            ax.plot(rpm, frequency[idx, :], marker=".", markersize=3, linewidth=1.1)
            if all(r.kappa is not None for r in self.results):
                fw_x, fw_y, bw_x, bw_y = [], [], [], []
                for k, result in enumerate(self.results):
                    label = self._whirl_label(result, idx)
                    if label == "Forward":
                        fw_x.append(rpm[k]); fw_y.append(frequency[idx, k])
                    elif label == "Backward":
                        bw_x.append(rpm[k]); bw_y.append(frequency[idx, k])
                if fw_x:
                    ax.scatter(fw_x, fw_y, marker="o", s=9, label="FW" if display_mode == 1 else None)
                if bw_x:
                    ax.scatter(bw_x, bw_y, marker="x", s=13, label="BW" if display_mode == 1 else None)

        max_order = max(1, int(np.floor(self.nx)))
        for order in range(1, max_order + 1):
            ax.plot(rpm, order * rpm / 60.0, linestyle="--", linewidth=1.0, label=f"{order}X")

        ax.set_title("Campbell Diagram", loc="left", fontsize=10, fontweight="bold")
        ax.set_xlabel("Rotor Speed (rpm)")
        ax.set_ylabel("Natural Frequency (Hz)")
        ax.grid(True, alpha=0.3)
        handles, labels = ax.get_legend_handles_labels()
        unique = {}
        for h, label in zip(handles, labels):
            if label and label not in unique:
                unique[label] = h
        if unique:
            ax.legend(unique.values(), unique.keys(), loc="best", fontsize=8)
        self.campbell_canvas.draw_idle()

    def _draw_root_preview(self):
        self.root_preview_figure.clear()
        ax = self.root_preview_figure.add_subplot(111)
        eig = self._branch_matrix("eigenvalues")
        for idx in self._mode_indices:
            if idx < eig.shape[0]:
                ax.plot(eig[idx, :].real, eig[idx, :].imag, marker=".", markersize=2, linewidth=0.8)
        ax.axvline(0.0, linewidth=0.7, color="black", alpha=0.5)
        ax.set_title("Root Locus", fontsize=9, fontweight="bold", loc="left")
        ax.set_xlabel("Real", fontsize=8)
        ax.set_ylabel("Imag.", fontsize=8)
        ax.grid(True, alpha=0.25)
        ax.tick_params(labelsize=7)
        self.root_preview_canvas.draw_idle()

    def _populate_summary(self):
        # One row per physical mode at the middle sweep speed. This mirrors the
        # mockup's compact mode summary rather than dumping every speed/mode.
        k = len(self.results) // 2
        result = self.results[k]
        rpm = float(rad_s_to_rpm(result.speed_rad_s))
        freq = np.asarray(result.natural_frequency_hz)
        damp = np.asarray(result.damping_ratio)
        rows = []
        for display_mode, idx in enumerate(self._mode_indices, 1):
            if idx >= freq.size:
                continue
            rows.append((display_mode, rpm, float(freq[idx]), float(damp[idx]), self._whirl_label(result, idx), idx, k))
        self.summary.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for col, value in enumerate(values[:5]):
                text = f"{value:.6g}" if isinstance(value, float) else str(value)
                item = QTableWidgetItem(text)
                item.setData(Qt.UserRole, (values[5], values[6]))
                self.summary.setItem(row, col, item)

    def _dashboard_selection_changed(self):
        self._draw_dashboard_mode_orbit()

    def _dashboard_mode_speed(self):
        row = self.summary.currentRow()
        if row < 0 or self.summary.item(row, 0) is None:
            return (self._mode_indices[0] if self._mode_indices else 0), len(self.results)//2
        return self.summary.item(row, 0).data(Qt.UserRole)

    def _draw_dashboard_mode_orbit(self):
        idx, speed_index = self._dashboard_mode_speed()
        result = self.results[int(speed_index)]

        self.mode_preview_figure.clear()
        maxis = self.mode_preview_figure.add_subplot(111, projection="3d")
        self.orbit_preview_figure.clear()
        oaxis = self.orbit_preview_figure.add_subplot(111)

        if result.eigenvectors is None or self.model_snapshot is None:
            maxis.text2D(0.5, 0.5, "Mode unavailable", transform=maxis.transAxes, ha="center")
            maxis.set_axis_off()
            oaxis.text(0.5, 0.5, "Orbit unavailable", ha="center", va="center")
            oaxis.set_axis_off()
        else:
            vector = np.asarray(result.eigenvectors)[:, int(idx)]
            plot_mode_3d(
                self.model_snapshot, vector,
                np.asarray(result.eigenvalues)[int(idx)], ax=maxis,
                orbit_samples=56,
            )
            maxis.set_title(f"Mode Shape — Mode {self._mode_indices.index(int(idx))+1}", fontsize=8)
            preferred = [d.node for d in self.model_snapshot.disks]
            node = preferred[0] if preferred else self.model_snapshot.nodes[len(self.model_snapshot.nodes)//2].number
            plot_orbits(
                vector, [int(node)],
                title=f"Orbit — Node {node}",
                eigenvalue=np.asarray(result.eigenvalues)[int(idx)],
                ax=oaxis,
            )
            oaxis.tick_params(labelsize=7)
            oaxis.title.set_fontsize(8)

        self.mode_preview_canvas.draw_idle()
        self.orbit_preview_canvas.draw_idle()

    # ---------------------------- Full pages ----------------------------
    def _build_root_locus_tab(self):
        host = QWidget()
        layout = QVBoxLayout(host)
        self.root_figure = Figure(figsize=(8, 5), tight_layout=True)
        canvas = FigureCanvasQTAgg(self.root_figure)
        ax = self.root_figure.add_subplot(111)
        eig = self._branch_matrix("eigenvalues")
        for idx in self._mode_indices:
            if idx < eig.shape[0]:
                ax.plot(eig[idx, :].real, eig[idx, :].imag, marker=".", markersize=3)
        ax.axvline(0.0, linewidth=0.8)
        ax.set_title("Root Locus")
        ax.set_xlabel("Real Part (rad/s)")
        ax.set_ylabel("Imaginary Part (rad/s)")
        ax.grid(True, alpha=0.3)
        layout.addWidget(canvas)
        self.tabs.addTab(host, "Root Locus")

    def _build_mode_tab(self):
        host = QWidget()
        outer = QVBoxLayout(host)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Speed:"))
        self.mode_speed_combo = QComboBox()
        for i, result in enumerate(self.results):
            self.mode_speed_combo.addItem(f"{rad_s_to_rpm(result.speed_rad_s):.3f} rpm", i)
        controls.addWidget(self.mode_speed_combo)
        controls.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        for display_mode, idx in enumerate(self._mode_indices, 1):
            self.mode_combo.addItem(f"Mode {display_mode}", idx)
        controls.addWidget(self.mode_combo)
        controls.addStretch(1)
        outer.addLayout(controls)

        self.mode_figure = Figure(figsize=(8, 5), tight_layout=True)
        self.mode_canvas = FigureCanvasQTAgg(self.mode_figure)
        outer.addWidget(self.mode_canvas, 1)
        self.tabs.addTab(host, "Modes")

        self.mode_speed_combo.currentIndexChanged.connect(lambda _: self._draw_full_mode())
        self.mode_combo.currentIndexChanged.connect(lambda _: self._draw_full_mode())
        self._draw_full_mode()

    def _draw_full_mode(self):
        self.mode_figure.clear()
        ax = self.mode_figure.add_subplot(111, projection="3d")
        if self.mode_speed_combo.count() == 0 or self.mode_combo.count() == 0:
            self.mode_canvas.draw_idle(); return
        result = self.results[int(self.mode_speed_combo.currentData())]
        idx = int(self.mode_combo.currentData())
        if result.eigenvectors is None or self.model_snapshot is None:
            ax.text2D(0.5,0.5,"Eigenvectors unavailable",transform=ax.transAxes,ha="center")
            ax.set_axis_off()
        else:
            plot_mode_3d(
                self.model_snapshot,
                np.asarray(result.eigenvectors)[:, idx],
                np.asarray(result.eigenvalues)[idx],
                ax=ax,
            )
        self.mode_canvas.draw_idle()

    def _build_orbit_tab(self):
        host = QWidget()
        outer = QVBoxLayout(host)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Speed:"))
        self.orbit_speed_combo = QComboBox()
        for i, result in enumerate(self.results):
            self.orbit_speed_combo.addItem(f"{rad_s_to_rpm(result.speed_rad_s):.3f} rpm", i)
        controls.addWidget(self.orbit_speed_combo)
        controls.addWidget(QLabel("Mode:"))
        self.orbit_mode_combo = QComboBox()
        for display_mode, idx in enumerate(self._mode_indices, 1):
            self.orbit_mode_combo.addItem(f"Mode {display_mode}", idx)
        controls.addWidget(self.orbit_mode_combo)
        controls.addWidget(QLabel("Node:"))
        self.node_combo = QComboBox()
        if self.model_snapshot is not None:
            preferred = [d.node for d in self.model_snapshot.disks]
            ordered = preferred + [n.number for n in self.model_snapshot.nodes if n.number not in preferred]
            for node in ordered:
                self.node_combo.addItem(f"Node {node}", node)
        controls.addWidget(self.node_combo)
        controls.addStretch(1)
        outer.addLayout(controls)

        self.orbit_figure = Figure(figsize=(7, 5), tight_layout=True)
        self.orbit_canvas = FigureCanvasQTAgg(self.orbit_figure)
        outer.addWidget(self.orbit_canvas, 1)
        self.tabs.addTab(host, "Orbits")

        self.orbit_speed_combo.currentIndexChanged.connect(lambda _: self._draw_full_orbit())
        self.orbit_mode_combo.currentIndexChanged.connect(lambda _: self._draw_full_orbit())
        self.node_combo.currentIndexChanged.connect(lambda _: self._draw_full_orbit())
        self._draw_full_orbit()

    def _draw_full_orbit(self):
        self.orbit_figure.clear()
        ax = self.orbit_figure.add_subplot(111)
        if self.orbit_speed_combo.count() == 0 or self.orbit_mode_combo.count() == 0:
            self.orbit_canvas.draw_idle(); return
        result = self.results[int(self.orbit_speed_combo.currentData())]
        idx = int(self.orbit_mode_combo.currentData())
        node = self.node_combo.currentData()
        if result.eigenvectors is None or node is None:
            ax.text(0.5,0.5,"Orbit unavailable",ha="center",va="center")
            ax.set_axis_off()
        else:
            plot_orbits(
                np.asarray(result.eigenvectors)[:,idx],
                [int(node)],
                title=f"Orbit — Node {node}",
                eigenvalue=np.asarray(result.eigenvalues)[idx],
                ax=ax,
            )
        self.orbit_canvas.draw_idle()

    def refresh_stale(self):
        if self.record.stale:
            self.stale_label.setText("⚠ OUTDATED")
            self.stale_label.setProperty("resultStatus", "stale")
        else:
            self.stale_label.setText("CURRENT")
            self.stale_label.setProperty("resultStatus", "current")
        self.stale_label.style().unpolish(self.stale_label)
        self.stale_label.style().polish(self.stale_label)
