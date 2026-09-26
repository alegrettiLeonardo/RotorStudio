from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDoubleSpinBox,
    QCheckBox, QComboBox, QSpinBox
)

from drm_core import AnalysisCase
from drm_core.analysis.modal import (
    SYNCHRONOUS_COEFFICIENTS, FIXED_WHIRL, MATCHED_WHIRL,
)
from drm_core.units import rpm_to_rad_s, rad_s_to_rpm


class ModalSetupDialog(QDialog):
    def __init__(self, case: AnalysisCase | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modal / Characteristic Roots")
        form = QFormLayout(self)

        self.name_field = QLineEdit("Modal — Operating Point")
        self.speed_field = QDoubleSpinBox()
        self.speed_field.setRange(-1.0e7, 1.0e7)
        self.speed_field.setDecimals(3)
        self.speed_field.setSuffix(" rpm")
        self.speed_field.setValue(0.0)
        self.vectors_check = QCheckBox("Compute eigenvectors")
        self.vectors_check.setChecked(True)
        self.kappa_check = QCheckBox("Compute whirl / kappa")
        self.kappa_check.setChecked(True)

        self.policy_combo = QComboBox()
        self.policy_combo.addItem("Synchronous coefficients (ω = Ω)", SYNCHRONOUS_COEFFICIENTS)
        self.policy_combo.addItem("Fixed whirl frequency", FIXED_WHIRL)
        self.policy_combo.addItem("Matched whirl (MAC fixed point)", MATCHED_WHIRL)
        self.whirl_field = QDoubleSpinBox()
        self.whirl_field.setRange(0.0, 1.0e8)
        self.whirl_field.setDecimals(6)
        self.whirl_field.setSuffix(" rpm")
        self.whirl_field.setValue(3000.0)
        self.whirl_rtol = QDoubleSpinBox()
        self.whirl_rtol.setRange(1.0e-9, 1.0)
        self.whirl_rtol.setDecimals(7)
        self.whirl_rtol.setValue(1.0e-3)
        self.whirl_max_iter = QSpinBox()
        self.whirl_max_iter.setRange(1, 200)
        self.whirl_max_iter.setValue(15)

        if case is not None and case.kind == "modal":
            self.name_field.setText(case.name or "Modal")
            self.speed_field.setValue(rad_s_to_rpm(case.parameters.get("speed_rad_s", 0.0)))
            self.vectors_check.setChecked(bool(case.parameters.get("with_eigenvectors", True)))
            self.kappa_check.setChecked(bool(case.parameters.get("with_kappa", True)))
            policy=str(case.parameters.get("coefficient_policy", SYNCHRONOUS_COEFFICIENTS)).upper()
            index=self.policy_combo.findData(policy)
            if index >= 0:self.policy_combo.setCurrentIndex(index)
            if case.parameters.get("whirl_frequency_rad_s") is not None:
                self.whirl_field.setValue(rad_s_to_rpm(case.parameters["whirl_frequency_rad_s"]))
            self.whirl_rtol.setValue(float(case.parameters.get("whirl_rtol", 1e-3)))
            self.whirl_max_iter.setValue(int(case.parameters.get("whirl_max_iter", 15)))

        form.addRow("Case name:", self.name_field)
        form.addRow("Rotor speed Ω:", self.speed_field)
        form.addRow("Bearing coefficient policy:", self.policy_combo)
        form.addRow("Fixed whirl ω:", self.whirl_field)
        form.addRow("Matched-whirl relative tolerance:", self.whirl_rtol)
        form.addRow("Matched-whirl max iterations:", self.whirl_max_iter)
        form.addRow(self.vectors_check)
        form.addRow(self.kappa_check)

        self.policy_combo.currentIndexChanged.connect(self._refresh_policy_fields)
        self._refresh_policy_fields()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _refresh_policy_fields(self):
        policy=self.policy_combo.currentData()
        self.whirl_field.setEnabled(policy == FIXED_WHIRL)
        self.whirl_rtol.setEnabled(policy == MATCHED_WHIRL)
        self.whirl_max_iter.setEnabled(policy == MATCHED_WHIRL)

    def analysis_case(self) -> AnalysisCase:
        with_kappa = self.kappa_check.isChecked()
        policy=str(self.policy_combo.currentData())
        params={
            "speed_rad_s": rpm_to_rad_s(self.speed_field.value()),
            "with_eigenvectors": self.vectors_check.isChecked() or with_kappa,
            "with_kappa": with_kappa,
            "coefficient_policy": policy,
        }
        if policy == FIXED_WHIRL:
            params["whirl_frequency_rad_s"]=rpm_to_rad_s(self.whirl_field.value())
        elif policy == MATCHED_WHIRL:
            params["whirl_rtol"]=float(self.whirl_rtol.value())
            params["whirl_max_iter"]=int(self.whirl_max_iter.value())
        return AnalysisCase(
            "modal", params, self.name_field.text().strip() or "Modal"
        )
