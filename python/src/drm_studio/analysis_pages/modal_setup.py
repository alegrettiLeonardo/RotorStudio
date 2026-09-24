from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDoubleSpinBox, QCheckBox
)

from drm_core import AnalysisCase
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

        if case is not None and case.kind == "modal":
            self.name_field.setText(case.name or "Modal")
            self.speed_field.setValue(rad_s_to_rpm(case.parameters.get("speed_rad_s", 0.0)))
            self.vectors_check.setChecked(bool(case.parameters.get("with_eigenvectors", True)))
            self.kappa_check.setChecked(bool(case.parameters.get("with_kappa", True)))

        form.addRow("Case name:", self.name_field)
        form.addRow("Rotor speed:", self.speed_field)
        form.addRow(self.vectors_check)
        form.addRow(self.kappa_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def analysis_case(self) -> AnalysisCase:
        with_kappa = self.kappa_check.isChecked()
        return AnalysisCase(
            "modal",
            {
                "speed_rad_s": rpm_to_rad_s(self.speed_field.value()),
                "with_eigenvectors": self.vectors_check.isChecked() or with_kappa,
                "with_kappa": with_kappa,
            },
            self.name_field.text().strip() or "Modal",
        )
