from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QLabel, QLineEdit, QMessageBox, QSpinBox
)
from drm_core import AnalysisCase


class UCSSetupDialog(QDialog):
    """A5 setup surface. Values are canonical SI and stiffness inputs are exponents."""

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("UCS / Undamped Critical Speed Map")
        self.resize(620, 430)
        form = QFormLayout(self)

        self.name_field = QLineEdit("Undamped Critical Speed Map")
        self.exp_min = QDoubleSpinBox()
        self.exp_max = QDoubleSpinBox()
        for field in (self.exp_min, self.exp_max):
            field.setRange(-12.0, 18.0)
            field.setDecimals(3)
            field.setSingleStep(0.5)
        self.exp_min.setValue(6.0)
        self.exp_max.setValue(11.0)

        self.points = QSpinBox()
        self.points.setRange(2, 256)
        self.points.setValue(20)

        self.num_modes = QSpinBox()
        self.num_modes.setRange(4, max(4, 8 * len(model.nodes)))
        self.num_modes.setSingleStep(4)
        self.num_modes.setValue(min(16, self.num_modes.maximum()))

        self.explicit_bearing_range = QCheckBox(
            "Use explicit bearing speed range (exactly 30 evaluation points)"
        )
        self.bearing_start = QDoubleSpinBox()
        self.bearing_stop = QDoubleSpinBox()
        for field in (self.bearing_start, self.bearing_stop):
            field.setRange(0.0, 1.0e7)
            field.setDecimals(6)
            field.setSuffix(" rad/s")
            field.setEnabled(False)
        self.bearing_start.setValue(0.0)
        self.bearing_stop.setValue(1000.0)
        self.explicit_bearing_range.toggled.connect(self.bearing_start.setEnabled)
        self.explicit_bearing_range.toggled.connect(self.bearing_stop.setEnabled)

        self.synchronous = QCheckBox("Rouch synchronous formulation")
        self.synchronous.setToolTip(
            "Uses the frozen ROSS synchronous=True mass formulation for the UCS map. "
            "Critical-point modal solves retain the authority's standard non-Rouch semantics."
        )

        form.addRow("Case", self.name_field)
        form.addRow("Stiffness exponent min", self.exp_min)
        form.addRow("Stiffness exponent max", self.exp_max)
        exponent_note = QLabel(
            "Exponent semantics: 6 means 10^6 N/m, not 6 N/m. "
            "The native grid is logspace(exp_min, exp_max, points)."
        )
        exponent_note.setWordWrap(True)
        form.addRow(exponent_note)
        form.addRow("Stiffness points", self.points)
        form.addRow("num_modes", self.num_modes)
        form.addRow(self.explicit_bearing_range)
        form.addRow("Bearing speed start", self.bearing_start)
        form.addRow("Bearing speed stop", self.bearing_stop)
        form.addRow(self.synchronous)

        scope = QLabel(
            "A5 declared scope: single 4-DOF shaft line; non-linked radial supports; "
            "legacy constant type 3/5 or qualified coefficient/map-backed bearings. "
            "Seals are excluded from the temporary UCS rotor. PointMass, linked/housing "
            "supports and rated-speed-derived stiffness defaults fail closed."
        )
        scope.setWordWrap(True)
        form.addRow(scope)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def analysis_case(self):
        start = float(self.exp_min.value())
        stop = float(self.exp_max.value())
        if not stop > start:
            raise ValueError(
                f"stiffness exponent max={stop:g}; expected a value greater than min={start:g}"
            )
        num_modes = int(self.num_modes.value())
        if num_modes % 4:
            raise ValueError(
                f"num_modes={num_modes}; A5 GUI requires a multiple of 4 so "
                "Rotor.run_ucs returns exactly num_modes//4 branches"
            )
        bearing_range = None
        if self.explicit_bearing_range.isChecked():
            b0 = float(self.bearing_start.value())
            b1 = float(self.bearing_stop.value())
            if not b1 > b0:
                raise ValueError(
                    f"bearing speed range=({b0:g}, {b1:g}) rad/s; expected stop > start"
                )
            bearing_range = (b0, b1)

        parameters = dict(
            stiffness_range_exponents=(start, stop),
            num=int(self.points.value()),
            num_modes=num_modes,
            bearing_speed_range=bearing_range,
            synchronous=bool(self.synchronous.isChecked()),
        )
        return AnalysisCase(
            "ucs",
            parameters,
            self.name_field.text().strip() or "Undamped Critical Speed Map",
            {"intersection_index": 0, "speed_units": "rad/s"},
        )

    def accept(self):
        try:
            self.analysis_case()
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Invalid UCS input", str(exc))
            return
        super().accept()
