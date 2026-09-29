from PySide6.QtWidgets import (
    QDialog,QDialogButtonBox,QDoubleSpinBox,QFormLayout,QLabel,QLineEdit,
    QMessageBox,QSpinBox
)
from drm_core import AnalysisCase


class API617UnbalanceSetupDialog(QDialog):
    """A7 explicit API 617 unbalance-placement input surface."""

    def __init__(self,model,parent=None):
        super().__init__(parent)
        self.model=model
        self.setWindowTitle("API 617 Unbalance Placement")
        self.resize(650,390)
        form=QFormLayout(self)

        self.name_field=QLineEdit("API 617 Unbalance Placement")
        self.speed=QDoubleSpinBox()
        self.speed.setRange(1e-9,1.0e7);self.speed.setDecimals(6);self.speed.setSuffix(" rad/s")
        self.speed.setValue(942.4777960769379)

        self.mode=QSpinBox()
        self.mode.setRange(1,32);self.mode.setValue(1)

        self.num_modes=QSpinBox()
        self.num_modes.setRange(4,64);self.num_modes.setSingleStep(2);self.num_modes.setValue(12)

        form.addRow("Case",self.name_field)
        form.addRow("Maximum continuous speed Nmc",self.speed)
        form.addRow("Forward mode (1 = first)",self.mode)
        form.addRow("Modal eigenvalues requested",self.num_modes)

        note=QLabel(
            "A7 follows the frozen ROSS API 617 placement semantics. The selected "
            "mode is counted over forward modes after the amplitude-weighted whirl "
            "ratio filter. Antinodes are selected from the mode shape and the "
            "native solver computes Ua = 2 Ur using the recovered static journal "
            "loads or overhung mass. Nmc is explicit and is not inferred."
        )
        note.setWordWrap(True);form.addRow(note)

        scope=QLabel(
            "Declared A7 scope: qualified single 4-DOF type-2 shaft line, disk "
            "types 1/2, legacy type 3/5 radial supports or qualified coefficient/"
            "map-backed supports at synchronous Nmc. Close-clearance acceptance "
            "is A8 and is not calculated here."
        )
        scope.setWordWrap(True);form.addRow(scope)

        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def analysis_case(self):
        nm=int(self.num_modes.value())
        if nm%2:
            raise ValueError("Modal eigenvalues requested must be even.")
        return AnalysisCase(
            "api617_unbalance",
            dict(
                mode=int(self.mode.value())-1,
                maximum_continuous_speed_rad_s=float(self.speed.value()),
                num_modes=nm,
            ),
            self.name_field.text().strip() or "API 617 Unbalance Placement",
            {},
        )

    def accept(self):
        try:self.analysis_case()
        except (ValueError,TypeError) as exc:
            QMessageBox.warning(self,"Invalid API 617 input",str(exc));return
        super().accept()
