from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QCheckBox, QComboBox, QMessageBox
)

from drm_core import AnalysisCase
from drm_core.units import rpm_to_rad_s


class CriticalSpeedSetupDialog(QDialog):
    METHODS = (
        ("Legacy automatic", None),
        ("Iterative — fixed eigenvalue (method 2)", 2),
        ("Iterative — closest estimate (method 3)", 3),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Critical Speeds")
        form = QFormLayout(self)

        self.name_field = QLineEdit("Critical Speeds")
        self.nx_field = QDoubleSpinBox()
        self.nx_field.setRange(0.1, 20.0)
        self.nx_field.setDecimals(3)
        self.nx_field.setValue(1.0)

        self.damped_check = QCheckBox("Use damped natural frequency")
        self.damped_check.setChecked(True)

        self.ncrit_field = QSpinBox()
        self.ncrit_field.setRange(1, 100)
        self.ncrit_field.setValue(5)

        self.method_combo = QComboBox()
        for label, method in self.METHODS:
            self.method_combo.addItem(label, method)

        self.max_iter_field = QSpinBox()
        self.max_iter_field.setRange(1, 10000)
        self.max_iter_field.setValue(20)

        self.tol_field = QDoubleSpinBox()
        self.tol_field.setRange(1e-14, 1.0)
        self.tol_field.setDecimals(12)
        self.tol_field.setValue(1e-6)

        self.initial_field = QLineEdit()
        self.initial_field.setPlaceholderText("rpm, comma-separated; required for method 3")

        form.addRow("Case name:", self.name_field)
        form.addRow("NX order:", self.nx_field)
        form.addRow(self.damped_check)
        form.addRow("Number of criticals:", self.ncrit_field)
        form.addRow("Method:", self.method_combo)
        form.addRow("Maximum iterations:", self.max_iter_field)
        form.addRow("Convergence tolerance:", self.tol_field)
        form.addRow("Initial estimates:", self.initial_field)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.method_combo.currentIndexChanged.connect(self._sync_method)
        self._sync_method()

    def _sync_method(self):
        method = self.method_combo.currentData()
        self.initial_field.setEnabled(method == 3)
        self.max_iter_field.setEnabled(method in (2, 3))
        self.tol_field.setEnabled(method in (2, 3))

    def _parse_initial_rpm(self):
        text = self.initial_field.text().strip()
        if not text:
            return []
        try:
            return [float(x.strip()) for x in text.replace(";", ",").split(",") if x.strip()]
        except ValueError as exc:
            raise ValueError("Initial estimates must be numeric rpm values separated by commas.") from exc

    def _accept_if_valid(self):
        method = self.method_combo.currentData()
        if method == 3:
            try:
                estimates = self._parse_initial_rpm()
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid initial estimates", str(exc))
                return
            if len(estimates) != self.ncrit_field.value():
                QMessageBox.warning(
                    self,
                    "Invalid initial estimates",
                    "Method 3 requires exactly one initial estimate per requested critical speed.",
                )
                return
        self.accept()

    def analysis_case(self) -> AnalysisCase:
        method = self.method_combo.currentData()
        parameters = {
            "NX": float(self.nx_field.value()),
            "damped": bool(self.damped_check.isChecked()),
            "ncrit": int(self.ncrit_field.value()),
        }
        if method in (2, 3):
            parameters.update(
                method=int(method),
                max_iterations=int(self.max_iter_field.value()),
                tol=float(self.tol_field.value()),
                return_diagnostics=True,
            )
        if method == 3:
            parameters["initial_estimates"] = [
                float(rpm_to_rad_s(v)) for v in self._parse_initial_rpm()
            ]
        return AnalysisCase(
            "critical_speeds",
            parameters,
            self.name_field.text().strip() or "Critical Speeds",
        )
