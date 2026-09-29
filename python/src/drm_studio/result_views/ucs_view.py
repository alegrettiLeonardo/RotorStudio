import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget
)


class UCSResultView(QWidget):
    """A5 UCS map view; plotting never recomputes solver physics."""

    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.result = record.execution.result
        layout = QVBoxLayout(self)

        self.stale_label = QLabel()
        layout.addWidget(self.stale_label)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Critical intersection"))
        self.intersection = QComboBox()
        nint = len(self.result.intersection_speed_rad_s)
        if nint:
            for i in range(nint):
                mode = int(self.result.intersection_mode_index[i]) + 1
                coeff = str(self.result.intersection_coefficient[i]).upper()
                self.intersection.addItem(
                    f"{i + 1}: branch {mode} / {coeff}",
                    i,
                )
            selected = int(record.execution.case.options.get("intersection_index", 0))
            self.intersection.setCurrentIndex(max(0, min(selected, nint - 1)))
        else:
            self.intersection.addItem("No intersections", -1)
            self.intersection.setEnabled(False)
        controls.addWidget(self.intersection)

        controls.addWidget(QLabel("Speed units"))
        self.speed_units = QComboBox()
        self.speed_units.addItems(["rad/s", "RPM"])
        self.speed_units.setCurrentText(
            str(record.execution.case.options.get("speed_units", "rad/s"))
        )
        controls.addWidget(self.speed_units)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.detail = QLabel()
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)

        self.figure = Figure(figsize=(11, 7), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas, 1)

        self.intersection.currentIndexChanged.connect(self._draw)
        self.speed_units.currentIndexChanged.connect(self._draw)
        self._draw()
        self.refresh_stale()

    def _speed_factor(self):
        return 60.0 / (2.0 * np.pi) if self.speed_units.currentText() == "RPM" else 1.0

    def _draw(self):
        r = self.result
        factor = self._speed_factor()
        unit = self.speed_units.currentText()

        self.figure.clear()
        ax = self.figure.add_subplot(1, 1, 1)
        stiffness = np.asarray(r.stiffness_log_n_m, dtype=float)
        wn = np.asarray(r.natural_frequency_rad_s, dtype=float)

        for branch in range(wn.shape[0]):
            y = wn[branch] * factor
            mask = (stiffness > 0.0) & (y > 0.0) & np.isfinite(y)
            ax.plot(stiffness[mask], y[mask], label=f"Rotor branch {branch + 1}")

        bs = np.asarray(r.bearing_speed_rad_s, dtype=float) * factor
        kxx = np.asarray(r.bearing_kxx_n_m, dtype=float)
        mask = (kxx > 0.0) & (bs > 0.0) & np.isfinite(kxx) & np.isfinite(bs)
        ax.plot(kxx[mask], bs[mask], linestyle="--", label="Bearing Kxx")

        if "kyy" in tuple(r.coefficient_families):
            kyy = np.asarray(r.bearing_kyy_n_m, dtype=float)
            mask = (kyy > 0.0) & (bs > 0.0) & np.isfinite(kyy) & np.isfinite(bs)
            ax.plot(kyy[mask], bs[mask], linestyle="--", label="Bearing Kyy")

        ik = np.asarray(r.intersection_stiffness_n_m, dtype=float)
        isp = np.asarray(r.intersection_speed_rad_s, dtype=float) * factor
        mask = (ik > 0.0) & (isp > 0.0)
        if np.any(mask):
            ax.scatter(ik[mask], isp[mask], marker="o", label="Critical intersections")

        selected = self.intersection.currentData()
        if selected is not None and int(selected) >= 0:
            i = int(selected)
            ax.scatter(
                [float(r.intersection_stiffness_n_m[i])],
                [float(r.intersection_speed_rad_s[i]) * factor],
                marker="x", s=90, linewidths=2.0, label="Selected",
            )
            self.record.ucs_selection = {
                "intersection_index": i,
                "speed_units": unit,
            }
            mode = int(r.intersection_mode_index[i]) + 1
            coeff = str(r.intersection_coefficient[i]).upper()
            critical = np.asarray(r.critical_wn_rad_s, dtype=float)
            modal = critical[:, i] if critical.ndim == 2 and i < critical.shape[1] else np.asarray([])
            preview = ", ".join(f"{x:.6g}" for x in modal[:4])
            self.detail.setText(
                f"Intersection {i + 1}: kcrit={r.intersection_stiffness_n_m[i]:.8g} N/m; "
                f"speedcrit={r.intersection_speed_rad_s[i]:.8g} rad/s "
                f"({r.intersection_speed_rad_s[i] * 60.0 / (2.0 * np.pi):.8g} RPM); "
                f"source={coeff}; rotor branch={mode}. "
                f"Critical modal wn[0:4] rad/s=[{preview}]. "
                f"Map synchronous/Rouch={bool(r.synchronous)}; frozen ROSS critical-point "
                "modal semantics are standard non-Rouch. Mode-shape vectors are not exposed "
                "by rd_ucs_v1 in the declared A5 scope."
            )
        else:
            self.detail.setText(
                "No UCS intersections were found on the declared stiffness and bearing-speed grids."
            )

        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Bearing stiffness [N/m]")
        ax.set_ylabel(f"Critical speed [{unit}]")
        ax.set_title("Undamped Critical Speed Map (UCS)")
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(loc="best")
        self.canvas.draw_idle()

    def refresh_stale(self):
        state = "⚠ OUTDATED" if self.record.stale else "CURRENT"
        mode = "Rouch synchronous map" if self.result.synchronous else "standard undamped map"
        self.stale_label.setText(
            f"{state} — A5 native Fortran UCS / {mode}; temporary bearing damping = 0"
        )
