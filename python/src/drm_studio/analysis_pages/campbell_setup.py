from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDoubleSpinBox,
    QCheckBox, QMessageBox, QComboBox, QSpinBox
)

from drm_core import AnalysisCase
from drm_core.analysis.modal import (
    SYNCHRONOUS_COEFFICIENTS, FIXED_WHIRL, MATCHED_WHIRL,
)
from drm_core.units import rpm_to_rad_s, rad_s_to_rpm


class CampbellSetupDialog(QDialog):
    """Campbell setup with B17 bearing coefficient policies."""

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

        self.policy_combo=QComboBox()
        self.policy_combo.addItem("Synchronous coefficients (ω = Ω)",SYNCHRONOUS_COEFFICIENTS)
        self.policy_combo.addItem("Fixed whirl frequency",FIXED_WHIRL)
        self.policy_combo.addItem("Matched whirl (MAC fixed point)",MATCHED_WHIRL)
        self.whirl_field=self._rpm_spin(3000.0)
        self.whirl_rtol=QDoubleSpinBox()
        self.whirl_rtol.setRange(1e-9,1.0);self.whirl_rtol.setDecimals(7);self.whirl_rtol.setValue(1e-3)
        self.whirl_max_iter=QSpinBox()
        self.whirl_max_iter.setRange(1,200);self.whirl_max_iter.setValue(15)

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
            policy=str(case.parameters.get("coefficient_policy",SYNCHRONOUS_COEFFICIENTS)).upper()
            index=self.policy_combo.findData(policy)
            if index>=0:self.policy_combo.setCurrentIndex(index)
            if case.parameters.get("whirl_frequency_rad_s") is not None:
                self.whirl_field.setValue(rad_s_to_rpm(case.parameters["whirl_frequency_rad_s"]))
            self.whirl_rtol.setValue(float(case.parameters.get("whirl_rtol",1e-3)))
            self.whirl_max_iter.setValue(int(case.parameters.get("whirl_max_iter",15)))

        form.addRow("Case name:", self.name_field)
        form.addRow("Start speed:", self.start_field)
        form.addRow("End speed:", self.end_field)
        form.addRow("Speed increment:", self.step_field)
        form.addRow("Excitation-line range:", self.nx_field)
        form.addRow("Bearing coefficient policy:",self.policy_combo)
        form.addRow("Fixed whirl ω:",self.whirl_field)
        form.addRow("Matched-whirl relative tolerance:",self.whirl_rtol)
        form.addRow("Matched-whirl max iterations:",self.whirl_max_iter)
        form.addRow(self.vectors_check)
        form.addRow(self.kappa_check)
        self.policy_combo.currentIndexChanged.connect(self._refresh_policy_fields)
        self._refresh_policy_fields()

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

    def _refresh_policy_fields(self):
        policy=self.policy_combo.currentData()
        self.whirl_field.setEnabled(policy==FIXED_WHIRL)
        self.whirl_rtol.setEnabled(policy==MATCHED_WHIRL)
        self.whirl_max_iter.setEnabled(policy==MATCHED_WHIRL)

    def _accept_if_valid(self):
        if self.end_field.value() <= self.start_field.value():
            QMessageBox.warning(self, "Invalid Campbell range", "End speed must be greater than start speed.")
            return
        if self.step_field.value() <= 0.0:
            QMessageBox.warning(self, "Invalid Campbell range", "Speed increment must be positive.")
            return
        self.accept()

    def analysis_case(self) -> AnalysisCase:
        start = self.start_field.value();end = self.end_field.value();step = self.step_field.value()
        count = int(np.floor((end - start) / step + 1e-12)) + 1
        rpm = start + step * np.arange(count, dtype=float)
        if rpm[-1] < end - max(1e-9, abs(end) * 1e-12):
            rpm = np.append(rpm, end)
        with_kappa = self.kappa_check.isChecked()
        policy=str(self.policy_combo.currentData())
        params={
            "speeds_rad_s": np.asarray(rpm_to_rad_s(rpm), dtype=float).tolist(),
            "with_eigenvectors": self.vectors_check.isChecked() or with_kappa,
            "with_kappa": with_kappa,
            "coefficient_policy":policy,
        }
        if policy==FIXED_WHIRL:
            params["whirl_frequency_rad_s"]=rpm_to_rad_s(self.whirl_field.value())
        elif policy==MATCHED_WHIRL:
            params["whirl_rtol"]=float(self.whirl_rtol.value())
            params["whirl_max_iter"]=int(self.whirl_max_iter.value())
        return AnalysisCase(
            "modal_sweep",params,self.name_field.text().strip() or "Campbell",
            {"nx": float(self.nx_field.value())},
        )
