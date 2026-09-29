from PySide6.QtWidgets import (
    QDialog,QDialogButtonBox,QDoubleSpinBox,QFormLayout,QLabel,QLineEdit,
    QMessageBox,QSpinBox
)
from drm_core import AnalysisCase


class Level1SetupDialog(QDialog):
    """A6 explicit Level 1 stability input surface."""

    def __init__(self,model,parent=None):
        super().__init__(parent)
        self.model=model
        self.setWindowTitle("Level 1 Stability Analysis")
        self.resize(620,430)
        form=QFormLayout(self)

        self.name_field=QLineEdit("Level 1 Stability")
        self.speed=QDoubleSpinBox()
        self.speed.setRange(0.0,1.0e7);self.speed.setDecimals(6);self.speed.setSuffix(" rad/s")
        self.speed.setValue(377.0)

        self.node=QSpinBox()
        self.node.setRange(1,max(1,len(model.nodes)))
        self.node.setValue(max(1,(len(model.nodes)+1)//2))

        self.q_start=QDoubleSpinBox()
        self.q_stop=QDoubleSpinBox()
        for w in (self.q_start,self.q_stop):
            w.setRange(0.0,1.0e15);w.setDecimals(3);w.setSuffix(" N/m")
        self.q_start.setValue(0.0);self.q_stop.setValue(2.5e6)

        self.points=QSpinBox();self.points.setRange(2,4096);self.points.setValue(7)

        form.addRow("Case",self.name_field)
        form.addRow("Rotor speed",self.speed)
        form.addRow("Cross-coupling node",self.node)
        form.addRow("Q start",self.q_start)
        form.addRow("Q stop",self.q_stop)
        form.addRow("Q points",self.points)

        note=QLabel(
            "A6 uses an explicit linear Q sweep in N/m. At each Q the native solver "
            "adds Kxy=+Q and Kyx=-Q at the selected node, solves the rotor at the "
            "fixed speed and reports the logarithmic decrement of the first mode "
            "whose frozen-ROSS whirl classification is not Backward. This is not "
            "the UCS exponent convention. RotorStudio does not infer rated speed or "
            "the ambiguous frozen ROSS default Q range."
        )
        note.setWordWrap(True);form.addRow(note)

        scope=QLabel(
            "Declared A6 scope: qualified single 4-DOF type-2 shaft line, disk types "
            "1/2, legacy radial type 3/5 or qualified coefficient/map-backed bearings. "
            "Rigid/linked supports, direct physical-bearing solves, PointMass, coaxial/"
            "asymmetric rotors and fault physics fail closed."
        )
        scope.setWordWrap(True);form.addRow(scope)

        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def analysis_case(self):
        q0=float(self.q_start.value());q1=float(self.q_stop.value())
        if q1<=q0:
            raise ValueError(f"Q stop={q1:g} N/m; expected a value greater than Q start={q0:g} N/m")
        return AnalysisCase(
            "level1",
            dict(
                rotor_speed_rad_s=float(self.speed.value()),
                cross_coupling_node=int(self.node.value()),
                stiffness_range_n_m=(q0,q1),
                num=int(self.points.value()),
            ),
            self.name_field.text().strip() or "Level 1 Stability",
            {"selected_q_index":0},
        )

    def accept(self):
        try:self.analysis_case()
        except (ValueError,TypeError) as exc:
            QMessageBox.warning(self,"Invalid Level 1 input",str(exc));return
        super().accept()
