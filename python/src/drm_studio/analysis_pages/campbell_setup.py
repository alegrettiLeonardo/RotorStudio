from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDoubleSpinBox,
    QCheckBox, QMessageBox
)

from drm_core import AnalysisCase
from drm_core.units import rpm_to_rad_s, rad_s_to_rpm


class CampbellSetupDialog(QDialog):
    """Configure the existing Stage 1 modal_sweep contract.

    Display-only Campbell options live in AnalysisCase.options so they are
    never forwarded to run_modal/SolverFacade.
    """

    def __init__(self, case: AnalysisCase | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Campbell Diagram")
        form = QFormLayout(self)

        self.name_field = QLineEdit("Campbell — Operating Range")
        self.start_field = self._rpm_spin(0.0)
        self.end_field = self._rpm_spin(12000.0)
        self.step_field = self._rpm_spin(250.0, minimum=1e-6)
        self.nx_field = QDoubleSpinBox()
        self.nx_field.setRange(0.25, 12.0)
        self.nx_field.setDecimals(2)
        self.nx_field.setValue(2.0)
        self.nx_field.setSuffix(" X")
        self.vectors_check = QCheckBox("Compute eigenvectors for Modes/Orbits")
        self.vectors_check.setChecked(True)
        self.kappa_check = QCheckBox("Compute whirl / kappa")
        self.kappa_check.setChecked(True)

        if case is not None and case.kind == "modal_sweep":
            self.name_field.setText(case.name or "Campbell")
            speeds = np.asarray(case.parameters.get("speeds_rad_s", []), dtype=float)
            if speeds.size:
                rpm = np.asarray(rad_s_to_rpm(speeds), dtype=float)
                self.start_field.setValue(float(rpm[0]))
                self.end_field.setValue(float(rpm[-1]))
                if rpm.size > 1:
                    self.step_field.setValue(float(np.median(np.diff(rpm))))
            self.vectors_check.setChecked(bool(case.parameters.get("with_eigenvectors", True)))
            self.kappa_check.setChecked(bool(case.parameters.get("with_kappa", True)))
            self.nx_field.setValue(float(case.options.get("nx", 2.0)))

        form.addRow("Case name:", self.name_field)
        form.addRow("Start speed:", self.start_field)
        form.addRow("End speed:", self.end_field)
        form.addRow("Speed increment:", self.step_field)
        form.addRow("Excitation-line range:", self.nx_field)
        form.addRow(self.vectors_check)
        form.addRow(self.kappa_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    @staticmethod
    def _rpm_spin(value, minimum=0.0):
        spin = QDoubleSpinBox()
        spin.setRange(minimum, 1.0e8)
        spin.setDecimals(3)
        spin.setSuffix(" rpm")
        spin.setValue(value)
        return spin

    def _accept_if_valid(self):
        if self.end_field.value() <= self.start_field.value():
            QMessageBox.warning(self, "Invalid Campbell range", "End speed must be greater than start speed.")
            return
        if self.step_field.value() <= 0.0:
            QMessageBox.warning(self, "Invalid Campbell range", "Speed increment must be positive.")
            return
        self.accept()

    def analysis_case(self) -> AnalysisCase:
        start = self.start_field.value()
        end = self.end_field.value()
        step = self.step_field.value()
        # Include end point when it lies on the requested grid, without
        # accumulating repeated floating-point additions.
        count = int(np.floor((end - start) / step + 1e-12)) + 1
        rpm = start + step * np.arange(count, dtype=float)
        if rpm[-1] < end - max(1e-9, abs(end) * 1e-12):
            rpm = np.append(rpm, end)
        with_kappa = self.kappa_check.isChecked()
        return AnalysisCase(
            "modal_sweep",
            {
                "speeds_rad_s": np.asarray(rpm_to_rad_s(rpm), dtype=float).tolist(),
                "with_eigenvectors": self.vectors_check.isChecked() or with_kappa,
                "with_kappa": with_kappa,
            },
            self.name_field.text().strip() or "Campbell",
            {"nx": float(self.nx_field.value())},
        )
