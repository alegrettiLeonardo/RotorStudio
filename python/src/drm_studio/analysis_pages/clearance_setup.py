from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import (
    QCheckBox,QDialog,QDialogButtonBox,QDoubleSpinBox,QFormLayout,QLabel,QLineEdit,
    QMessageBox,QSpinBox
)
from drm_core import AnalysisCase


def _ints(text,name):
    try:values=[int(x.strip()) for x in text.split(",") if x.strip()]
    except Exception as exc:raise ValueError(f"{name}: expected comma-separated integer nodes") from exc
    if not values:raise ValueError(f"{name}: at least one value is required")
    return values


def _floats(text,name):
    try:values=[float(x.strip()) for x in text.split(",") if x.strip()]
    except Exception as exc:raise ValueError(f"{name}: expected comma-separated numeric values") from exc
    if not values or not np.isfinite(values).all():raise ValueError(f"{name}: finite values are required")
    return values


def _tags(text,n,prefix):
    values=[x.strip() for x in text.split(",")]
    if len(values)!=n:return [f"{prefix} {i+1}" for i in range(n)]
    return [x or f"{prefix} {i+1}" for i,x in enumerate(values)]


class ClearanceSetupDialog(QDialog):
    """A8 close-clearance input surface with explicit engineering semantics."""

    def __init__(self,model,parent=None):
        super().__init__(parent);self.model=model
        self.setWindowTitle("API 617 Close-Clearance Analysis");self.resize(720,680)
        form=QFormLayout(self)
        self.name_field=QLineEdit("API 617 Close-Clearance")

        self.speed_start=QDoubleSpinBox();self.speed_stop=QDoubleSpinBox()
        for w in (self.speed_start,self.speed_stop):
            w.setRange(0,1e7);w.setDecimals(6);w.setSuffix(" rad/s")
        self.speed_start.setValue(0);self.speed_stop.setValue(1047.1975511965977)
        self.speed_points=QSpinBox();self.speed_points.setRange(2,10000);self.speed_points.setValue(101)

        self.nma=QDoubleSpinBox();self.nmc=QDoubleSpinBox()
        for w in (self.nma,self.nmc):
            w.setRange(0,1e7);w.setDecimals(6);w.setSuffix(" rad/s")
        self.nma.setValue(733.0382858376183);self.nmc.setValue(942.4777960769379)

        self.probe_nodes=QLineEdit("1,7");self.probe_angles=QLineEdit("45,-45")
        self.probe_tags=QLineEdit("DE-45,NDE-45")
        self.clear_nodes=QLineEdit("1,4,7");self.clear_radial_um=QLineEdit("100,250,120")
        self.clear_tags=QLineEdit("DE,eye,NDE")

        self.mode=QSpinBox();self.mode.setRange(1,32);self.mode.setValue(1)
        self.num_modes=QSpinBox();self.num_modes.setRange(4,64);self.num_modes.setSingleStep(2);self.num_modes.setValue(12)

        self.cap_enabled=QCheckBox("Apply scale-factor cap")
        self.cap=QDoubleSpinBox();self.cap.setRange(1e-9,1e6);self.cap.setDecimals(6);self.cap.setValue(6.0)
        self.cap.setEnabled(False);self.cap_enabled.toggled.connect(self.cap.setEnabled)

        self.explicit=QCheckBox("Use explicit unbalance instead of A7 placement")
        self.ub_nodes=QLineEdit("4");self.ub_mag=QLineEdit("0.00012443432344562272");self.ub_phase_deg=QLineEdit("0")
        for w in (self.ub_nodes,self.ub_mag,self.ub_phase_deg):w.setEnabled(False)
        self.explicit.toggled.connect(lambda v:[w.setEnabled(v) for w in (self.ub_nodes,self.ub_mag,self.ub_phase_deg)])

        form.addRow("Case",self.name_field)
        form.addRow("Speed sweep start",self.speed_start);form.addRow("Speed sweep stop",self.speed_stop)
        form.addRow("Speed points",self.speed_points);form.addRow("Minimum allowable speed Nma",self.nma)
        form.addRow("Maximum continuous speed Nmc",self.nmc)
        form.addRow("Radial probe nodes [one-based]",self.probe_nodes)
        form.addRow("Probe angles [deg]",self.probe_angles);form.addRow("Probe tags",self.probe_tags)
        form.addRow("Clearance nodes [one-based]",self.clear_nodes)
        form.addRow("Radial running clearances [µm]",self.clear_radial_um);form.addRow("Clearance tags",self.clear_tags)
        form.addRow("Forward mode (1 = first)",self.mode);form.addRow("Modal eigenvalues requested",self.num_modes)
        form.addRow(self.cap_enabled,self.cap);form.addRow(self.explicit)
        form.addRow("Explicit unbalance nodes [one-based]",self.ub_nodes)
        form.addRow("Explicit magnitudes [kg·m]",self.ub_mag);form.addRow("Explicit phases [deg]",self.ub_phase_deg)

        note=QLabel(
            "A8 uses synchronous full-order response. Nma and Nmc are inserted into "
            "the speed axis. Radial probe amplitudes and clearance amplitudes are "
            "peak-to-peak. The limit is 75% of diametral clearance. A cap is applied "
            "only when explicitly enabled; the API 617 value is 6."
        );note.setWordWrap(True);form.addRow(note)
        scope=QLabel(
            "Declared A8 scope: qualified single 4-DOF type-2 shaft line, disk types "
            "1/2, legacy radial type 3/5 or qualified coefficient/map-backed supports. "
            "Clearance locations are analysis-local inputs; no Reynolds/THD/TEHD solve, "
            "linked support, PointMass, coaxial/asymmetric or fault physics is performed."
        );scope.setWordWrap(True);form.addRow(scope)

        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);form.addRow(buttons)

    def analysis_case(self):
        if self.speed_stop.value()<=self.speed_start.value():raise ValueError("Speed sweep stop must be greater than start.")
        if not 0<=self.nma.value()<=self.nmc.value() or self.nmc.value()<=0:raise ValueError("Expected 0 <= Nma <= Nmc and Nmc > 0.")
        pn=_ints(self.probe_nodes.text(),"Probe nodes");pa=_floats(self.probe_angles.text(),"Probe angles")
        cn=_ints(self.clear_nodes.text(),"Clearance nodes");cr=_floats(self.clear_radial_um.text(),"Clearances")
        if len(pn)!=len(pa):raise ValueError("Probe node and angle counts must match.")
        if len(cn)!=len(cr):raise ValueError("Clearance node and radial-clearance counts must match.")
        if any(v<=0 for v in cr):raise ValueError("Radial running clearances must be > 0 µm.")
        params=dict(
            speed_range_rad_s=np.linspace(float(self.speed_start.value()),float(self.speed_stop.value()),int(self.speed_points.value())).tolist(),
            minimum_allowable_speed_rad_s=float(self.nma.value()),
            maximum_continuous_speed_rad_s=float(self.nmc.value()),
            probe_nodes=pn,probe_angles_rad=np.deg2rad(pa).tolist(),probe_tags=_tags(self.probe_tags.text(),len(pn),"Probe"),
            clearance_nodes=cn,radial_clearance_m=(np.asarray(cr)*1e-6).tolist(),clearance_tags=_tags(self.clear_tags.text(),len(cn),"Node"),
            mode=int(self.mode.value())-1,num_modes=int(self.num_modes.value()),
            scale_factor_cap=float(self.cap.value()) if self.cap_enabled.isChecked() else None,
        )
        if self.explicit.isChecked():
            un=_ints(self.ub_nodes.text(),"Explicit unbalance nodes")
            um=_floats(self.ub_mag.text(),"Explicit unbalance magnitudes")
            up=_floats(self.ub_phase_deg.text(),"Explicit unbalance phases")
            if not(len(un)==len(um)==len(up)):raise ValueError("Explicit unbalance node/magnitude/phase counts must match.")
            params.update(unbalance_nodes=un,unbalance_magnitude_kg_m=um,unbalance_phase_rad=np.deg2rad(up).tolist())
        return AnalysisCase("clearance",params,self.name_field.text().strip() or "API 617 Close-Clearance",{"selected_clearance_index":0})

    def accept(self):
        try:self.analysis_case()
        except (ValueError,TypeError) as exc:
            QMessageBox.warning(self,"Invalid close-clearance input",str(exc));return
        super().accept()
