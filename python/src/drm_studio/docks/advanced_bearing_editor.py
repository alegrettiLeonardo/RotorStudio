from __future__ import annotations

import json
import math
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from drm_core.domain.bearings import (
    CoefficientBearing,
    PlainJournalPhysicsBearing,
    TiltingPadPhysicsBearing,
    validate_advanced_bearing,
)


FAMILY_COEFFICIENT = "coefficient"
FAMILY_PLAIN = "plain_journal_physics"
FAMILY_TILTING = "tilting_pad_physics"

FAMILY_LABELS = {
    FAMILY_COEFFICIENT: "Coefficient Bearing",
    FAMILY_PLAIN: "Plain Journal — Native Physics",
    FAMILY_TILTING: "Tilting Pad — Native Physics",
}


def family_for_bearing(bearing) -> str:
    # B13 is deliberately limited to these exact domain types. Other B12
    # advanced-bearing families remain readable but are not silently promoted.
    if type(bearing) is CoefficientBearing:
        return FAMILY_COEFFICIENT
    if type(bearing) is PlainJournalPhysicsBearing:
        return FAMILY_PLAIN
    if type(bearing) is TiltingPadPhysicsBearing:
        return FAMILY_TILTING
    raise TypeError(f"B13 editor does not support {type(bearing).__name__}")


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} received {value!r}; expected a finite numeric value.")
    return value


def _parse_float(edit: QLineEdit, name: str) -> float:
    text = edit.text().strip()
    if not text:
        raise ValueError(f"{name} is empty; expected a finite numeric value.")
    try:
        return _finite(float(text), name)
    except ValueError as exc:
        if "received" in str(exc) or "empty" in str(exc):
            raise
        raise ValueError(f"{name} received {text!r}; expected a finite numeric value.") from exc


def _parse_optional_float(edit: QLineEdit, name: str) -> float | None:
    text = edit.text().strip()
    if not text:
        return None
    try:
        return _finite(float(text), name)
    except ValueError as exc:
        if "received" in str(exc):
            raise
        raise ValueError(f"{name} received {text!r}; expected blank or a finite numeric value.") from exc


def _parse_int(edit: QLineEdit, name: str) -> int:
    value = _parse_float(edit, name)
    rounded = int(round(value))
    if not math.isclose(value, rounded, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"{name} received {value}; expected an integer value.")
    return rounded


def _set_text(edit: QLineEdit, value: Any, scale: float = 1.0, offset: float = 0.0) -> None:
    if value is None:
        edit.setText("")
        return
    edit.setText(f"{(float(value) * scale + offset):.15g}")


def _parse_json_numeric(text: str, name: str):
    raw = text.strip()
    if not raw:
        raise ValueError(f"{name} is empty; expected scalar, vector, or matrix data.")
    try:
        if raw[0] in "[({":
            normalized = raw.replace("(", "[").replace(")", "]").replace("{", "[").replace("}", "]")
            value = json.loads(normalized)
        else:
            value = float(raw)
    except Exception as exc:
        raise ValueError(
            f"{name} received {raw!r}; expected a number, [v1, v2], or [[r1...], [r2...]]."
        ) from exc

    def convert(item):
        if isinstance(item, list):
            return [convert(x) for x in item]
        if isinstance(item, bool):
            raise ValueError(f"{name} contains boolean data; expected numeric coefficient values.")
        return _finite(float(item), name)

    return convert(value)


def _data_text(value) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.15g}"
    return json.dumps(value, separators=(", ", ": "))


def _axis_from_text(edit: QLineEdit, name: str) -> tuple[float, ...]:
    text = edit.text().strip()
    if not text:
        return ()
    value = _parse_json_numeric(text if text.startswith("[") else f"[{text}]", name)
    if not isinstance(value, list) or any(isinstance(x, list) for x in value):
        raise ValueError(f"{name} received {text!r}; expected a one-dimensional axis.")
    return tuple(float(x) for x in value)


def _axis_text(axis) -> str:
    return ", ".join(f"{float(x):.15g}" for x in axis)


def _readonly(text: str = "") -> QLineEdit:
    widget = QLineEdit(text)
    widget.setReadOnly(True)
    return widget


def _field(text: str = "") -> QLineEdit:
    return QLineEdit(text)


def _with_unit(widget: QWidget, unit: str) -> QWidget:
    host = QWidget()
    layout = QHBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(widget, 1)
    label = QLabel(unit)
    label.setStyleSheet("color:#667788;")
    layout.addWidget(label)
    return host


class AdvancedBearingEditor(QDialog):
    """Transactional B13 editor for the three promoted advanced-bearing families.

    Widget state is an editable draft. No persisted RotorModel object is
    mutated until bearing() builds and validates one complete immutable domain
    object; a QUndoCommand then owns the model transaction.
    """

    def __init__(self, model, *, family: str | None = None, bearing=None, parent=None):
        super().__init__(parent)
        self.model = model
        self.original = bearing
        if bearing is not None:
            inferred = family_for_bearing(bearing)
            if family is not None and family != inferred:
                raise ValueError(f"requested family {family!r} does not match {type(bearing).__name__}")
            family = inferred
        if family not in FAMILY_LABELS:
            raise ValueError(f"unsupported B13 family {family!r}")
        self.family = str(family)
        self._provenance = dict(getattr(bearing, "provenance", {}) or {})

        self.setWindowTitle(("Edit" if bearing is not None else "New") + " Advanced Bearing")
        self.resize(980, 760)
        outer = QVBoxLayout(self)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)

        self._build_general_tab()
        if self.family == FAMILY_COEFFICIENT:
            self._build_coefficient_tab()
        else:
            self._build_physics_tabs()
        self._build_qualification_tab()

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color:#a40000; font-weight:600;")
        outer.addWidget(self.error_label)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._accept_if_valid)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)

        self._populate(bearing)

    def _build_general_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.family_combo = QComboBox()
        for key, label in FAMILY_LABELS.items():
            self.family_combo.addItem(label, key)
        self.family_combo.setCurrentIndex(self.family_combo.findData(self.family))
        self.family_combo.setEnabled(False)
        self.tag_edit = _field()
        self.node_combo = QComboBox()
        for node in self.model.nodes:
            self.node_combo.addItem(f"Node {node.number}  (z={node.z_m:.9g} m)", int(node.number))
        form.addRow("Family:", self.family_combo)
        form.addRow("Tag:", self.tag_edit)
        form.addRow("Node:", self.node_combo)
        note = QLabel(
            "Edits are transactional. Values are converted to canonical SI, a complete frozen domain object is "
            "constructed, validate_advanced_bearing() is applied, and only then can the model command commit it."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#5d6f7f;")
        form.addRow(note)
        self.tabs.addTab(tab, "General")

    def _node(self) -> int:
        if self.node_combo.count() == 0 or self.node_combo.currentIndex() < 0:
            raise ValueError("Node is unavailable; expected one existing RotorModel node.")
        node = int(self.node_combo.currentData())
        valid = {int(n.number) for n in self.model.nodes}
        if node not in valid:
            raise ValueError(f"Node received {node}; expected one of existing RotorModel nodes {sorted(valid)}.")
        return node

    def _build_coefficient_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        axes = QGroupBox("Axes and interpolation")
        form = QFormLayout(axes)
        self.speed_axis = _field()
        self.frequency_axis = _field()
        self.interpolation_combo = QComboBox()
        self.interpolation_combo.addItems(["pchip", "linear"])
        form.addRow("Speed axis ωr:", _with_unit(self.speed_axis, "rad/s"))
        form.addRow("Frequency axis ω:", _with_unit(self.frequency_axis, "rad/s"))
        form.addRow("Interpolation:", self.interpolation_combo)
        layout.addWidget(axes)

        self.coeff_table = QTableWidget(12, 2)
        self.coeff_table.setHorizontalHeaderLabels(["Coefficient", "Scalar / vector / matrix"])
        self.coeff_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.coeff_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.coeff_names = [
            "Kxx", "Kxy", "Kyx", "Kyy",
            "Cxx", "Cxy", "Cyx", "Cyy",
            "Mxx", "Mxy", "Myx", "Myy",
        ]
        for row, name in enumerate(self.coeff_names):
            item = QTableWidgetItem(name)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.coeff_table.setItem(row, 0, item)
            self.coeff_table.setItem(row, 1, QTableWidgetItem("0"))
        layout.addWidget(self.coeff_table, 1)
        warning = QLabel(
            "Bearing mass M is persisted exactly. Nonzero bearing mass is stored by the domain model but remains "
            "fail-closed for the currently qualified legacy rotor assembly. B13 never zeros M automatically."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#805b00;")
        layout.addWidget(warning)
        self.tabs.addTab(tab, "Coefficients")

    def _coefficient_bearing(self):
        speed = _axis_from_text(self.speed_axis, "speed_rad_s")
        frequency = _axis_from_text(self.frequency_axis, "frequency_rad_s")
        data = {}
        for row, name in enumerate(self.coeff_names):
            item = self.coeff_table.item(row, 1)
            data[name.lower()] = _parse_json_numeric("" if item is None else item.text(), name)
        bearing = CoefficientBearing(
            node=self._node(),
            kxx=data["kxx"], cxx=data["cxx"],
            kyy=data["kyy"], cyy=data["cyy"],
            kxy=data["kxy"], kyx=data["kyx"],
            cxy=data["cxy"], cyx=data["cyx"],
            mxx=data["mxx"], myy=data["myy"],
            mxy=data["mxy"], myx=data["myx"],
            speed_rad_s=speed,
            frequency_rad_s=frequency,
            interpolation=str(self.interpolation_combo.currentText()),
            tag=self.tag_edit.text().strip(),
            provenance=dict(self._provenance),
        )
        validate_advanced_bearing(bearing)
        return bearing

    def _build_physics_tabs(self):
        self._build_geometry_tab()
        self._build_pads_tab()
        self._build_lubricant_tab()
        self._build_operating_tab()
        self._build_thermal_tab()
        self._build_deformation_tab()
        self._build_mesh_tab()
        self._build_solver_tab()

    def _build_geometry_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.weight = _field()
        self.journal_diameter_mm = _field()
        self.clearance_um = _field()
        form.addRow("Weight / static load:", _with_unit(self.weight, "N"))
        form.addRow("Journal diameter:", _with_unit(self.journal_diameter_mm, "mm"))
        form.addRow("Radial clearance:", _with_unit(self.clearance_um, "µm"))
        if self.family == FAMILY_TILTING:
            self.pad_thickness_mm = _field()
            self.pad_density = _field()
            form.addRow("Pad thickness:", _with_unit(self.pad_thickness_mm, "mm"))
            form.addRow("Pad density:", _with_unit(self.pad_density, "kg/m³"))
            self.bearing_type = _readonly("conventional_tilting_pad")
            form.addRow("Physical bearing type:", self.bearing_type)
        else:
            self.pad_thickness_mm = _field()
            form.addRow("Pad thickness (optional):", _with_unit(self.pad_thickness_mm, "mm"))
        self.tabs.addTab(tab, "Geometry")

    def _build_pads_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        columns = ["Pad", "Pivot angle [deg]", "Pad arc [deg]", "Axial length [mm]", "Preload", "Offset"]
        if self.family == FAMILY_TILTING:
            columns.append("K rotate [N·m/rad]")
        self.pads = QTableWidget(0, len(columns))
        self.pads.setHorizontalHeaderLabels(columns)
        self.pads.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pads.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pads.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.pads, 1)
        buttons = QHBoxLayout()
        add = QPushButton("Add Pad")
        remove = QPushButton("Remove Pad")
        add.clicked.connect(self.add_pad)
        remove.clicked.connect(self.remove_selected_pad)
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        note = QLabel("Pad-table edits remain draft data. One accepted dialog produces one logical undoable transaction.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#5d6f7f;")
        layout.addWidget(note)
        self.tabs.addTab(tab, "Pads")

    def add_pad(self, values=None):
        row = self.pads.rowCount()
        self.pads.insertRow(row)
        default = values or (0.0, 60.0, 50.0, 0.3, 0.5, 0.0)
        index = QTableWidgetItem(str(row + 1))
        index.setFlags(index.flags() & ~Qt.ItemIsEditable)
        self.pads.setItem(row, 0, index)
        n_editable = self.pads.columnCount() - 1
        for col in range(n_editable):
            value = default[col] if col < len(default) else 0.0
            self.pads.setItem(row, col + 1, QTableWidgetItem(f"{float(value):.15g}"))

    def remove_selected_pad(self):
        row = self.pads.currentRow()
        if row < 0 and self.pads.rowCount():
            row = self.pads.rowCount() - 1
        if row >= 0:
            self.pads.removeRow(row)
            for r in range(self.pads.rowCount()):
                self.pads.item(r, 0).setText(str(r + 1))

    def _pad_arrays(self):
        if self.pads.rowCount() < 1:
            raise ValueError("Pads received 0 rows; expected at least one pad/land row.")
        pivot, arc, length, preload, offset, krotate = [], [], [], [], [], []
        for row in range(self.pads.rowCount()):
            values = []
            for col in range(1, self.pads.columnCount()):
                item = self.pads.item(row, col)
                text = "" if item is None else item.text().strip()
                if not text:
                    raise ValueError(f"Pad {row + 1}, column {col} is empty; expected a finite numeric value.")
                try:
                    values.append(_finite(float(text), f"Pad {row + 1} column {col}"))
                except Exception as exc:
                    raise ValueError(
                        f"Pad {row + 1}, column {col} received {text!r}; expected a finite numeric value."
                    ) from exc
            pvt, pa, le, pre, off = values[:5]
            if not 0.0 <= pre < 1.0:
                raise ValueError(f"{FAMILY_LABELS[self.family]} preload received {pre}; expected 0 <= preload < 1.")
            if self.family == FAMILY_TILTING and not 0.0 < off < 1.0:
                raise ValueError(f"TiltingPad offset received {off}; expected 0 < offset < 1.")
            if self.family == FAMILY_PLAIN and not 0.0 <= off <= 1.0:
                raise ValueError(f"PlainJournal offset received {off}; expected 0 <= offset <= 1.")
            pivot.append(math.radians(pvt))
            arc.append(math.radians(pa))
            length.append(le * 1.0e-3)
            preload.append(pre)
            offset.append(off)
            if self.family == FAMILY_TILTING:
                krotate.append(values[5])
        return tuple(pivot), tuple(arc), tuple(length), tuple(preload), tuple(offset), tuple(krotate)

    def _build_lubricant_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.oil_viscosity = _field()
        self.lub_density = _field()
        self.lub_cp = _field()
        self.lub_conductivity = _field()
        self.viscosity2 = _field()
        form.addRow("Oil viscosity:", _with_unit(self.oil_viscosity, "Pa·s"))
        form.addRow("Lubricant density (optional):", _with_unit(self.lub_density, "kg/m³"))
        form.addRow("Lubricant cp (optional):", _with_unit(self.lub_cp, "J/(kg·K)"))
        form.addRow("Lubricant conductivity (optional):", _with_unit(self.lub_conductivity, "W/(m·K)"))
        form.addRow("Second viscosity (optional):", _with_unit(self.viscosity2, "Pa·s"))
        self.tabs.addTab(tab, "Lubricant")

    def _build_operating_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.fxs, self.fys = _field(), _field()
        self.oil_supply_c = _field()
        self.temperature1_c, self.temperature2_c = _field(), _field()
        self.temperature_journal_c, self.temperature_ambient_c, self.temperature_reference_c = _field(), _field(), _field()
        self.ambient_pressure_1, self.ambient_pressure_2 = _field(), _field()
        form.addRow("Fx static load:", _with_unit(self.fxs, "N"))
        form.addRow("Fy static load:", _with_unit(self.fys, "N"))
        form.addRow("Oil supply temperature:", _with_unit(self.oil_supply_c, "°C"))
        form.addRow("Temperature 1 (optional):", _with_unit(self.temperature1_c, "°C"))
        form.addRow("Temperature 2 (optional):", _with_unit(self.temperature2_c, "°C"))
        form.addRow("Journal temperature (optional):", _with_unit(self.temperature_journal_c, "°C"))
        form.addRow("Ambient temperature (optional):", _with_unit(self.temperature_ambient_c, "°C"))
        form.addRow("Reference temperature (optional):", _with_unit(self.temperature_reference_c, "°C"))
        form.addRow("Ambient pressure 1:", _with_unit(self.ambient_pressure_1, "Pa"))
        form.addRow("Ambient pressure 2:", _with_unit(self.ambient_pressure_2, "Pa"))
        if self.family == FAMILY_TILTING:
            self.oil_flow = _field()
            form.addRow("Oil flow (optional):", _with_unit(self.oil_flow, "m³/s"))
        self.tabs.addTab(tab, "Operating Conditions")

    def _build_thermal_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.thermal_type = QComboBox()
        self.thermal_type.addItem("None", None)
        self.thermal_type.addItem("adiabatic", "adiabatic")
        self.thermal_type.addItem("full", "full")
        self.convection_edges, self.convection_back, self.hot_oil_lambda = _field(), _field(), _field()
        form.addRow("Thermal model:", self.thermal_type)
        form.addRow("Convection — edges:", _with_unit(self.convection_edges, "W/(m²·K)"))
        form.addRow("Convection — back:", _with_unit(self.convection_back, "W/(m²·K)"))
        form.addRow("Hot-oil λ:", self.hot_oil_lambda)
        self.thermal_dependent_widgets = [self.convection_edges, self.convection_back, self.hot_oil_lambda]
        self.thermal_type.currentIndexChanged.connect(self._sync_dynamic_sections)
        self.tabs.addTab(tab, "Thermal")

    def _build_deformation_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.deform_type = QComboBox()
        self.deform_type.addItem("None", None)
        self.deform_type.addItem("pad_mechanical", "pad_mechanical")
        self.deform_type.addItem("pad_mechanical_thermal", "pad_mechanical_thermal")
        self.pad_conductivity, self.pad_young_mpa, self.pad_poisson, self.pad_expansion = _field(), _field(), _field(), _field()
        form.addRow("Deformation model:", self.deform_type)
        form.addRow("Pad conductivity (optional):", _with_unit(self.pad_conductivity, "W/(m·K)"))
        form.addRow("Pad Young modulus (optional):", _with_unit(self.pad_young_mpa, "MPa"))
        form.addRow("Pad Poisson (optional):", self.pad_poisson)
        form.addRow("Pad expansion (optional):", _with_unit(self.pad_expansion, "1/K"))
        self.deform_dependent_widgets = [self.pad_young_mpa, self.pad_poisson, self.pad_expansion]
        self.deform_type.currentIndexChanged.connect(self._sync_dynamic_sections)
        self.tabs.addTab(tab, "Deformation")

    def _build_mesh_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.total_e_x_film, self.total_e_z_film = _field(), _field()
        self.total_e_y_pad, self.total_e_y_film = _field(), _field()
        form.addRow("Film elements X:", self.total_e_x_film)
        form.addRow("Film elements Z:", self.total_e_z_film)
        form.addRow("Pad elements Y:", self.total_e_y_pad)
        form.addRow("Film elements Y:", self.total_e_y_film)
        self.tabs.addTab(tab, "Mesh")

    def _build_solver_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        self.xj_initial, self.yj_initial = _field(), _field()
        self.relax_p, self.relax_temperature = _field(), _field()
        self.max_iterations, self.outer_iterations = _field(), _field()
        self.force_tolerance, self.field_tolerance = _field(), _field()
        form.addRow("xj/C initial:", self.xj_initial)
        form.addRow("yj/C initial:", self.yj_initial)
        form.addRow("Pressure relaxation:", self.relax_p)
        form.addRow("Temperature relaxation:", self.relax_temperature)
        form.addRow("Max iterations:", self.max_iterations)
        form.addRow("Outer iterations:", self.outer_iterations)
        form.addRow("Force tolerance:", self.force_tolerance)
        form.addRow("Field tolerance:", self.field_tolerance)
        self.tabs.addTab(tab, "Solver Controls")

    def _sync_dynamic_sections(self):
        thermal_enabled = self.thermal_type.currentData() is not None
        deform_enabled = self.deform_type.currentData() is not None
        for widget in self.thermal_dependent_widgets:
            widget.setEnabled(thermal_enabled)
        for widget in self.deform_dependent_widgets:
            widget.setEnabled(deform_enabled)
        # Do not clear values when sections are temporarily disabled.

    @staticmethod
    def _c_to_k(value: float | None) -> float | None:
        return None if value is None else value + 273.15

    @staticmethod
    def _k_to_c(value: float | None) -> float | None:
        return None if value is None else value - 273.15

    def _physics_common(self):
        pivot, arc, length, preload, offset, krotate = self._pad_arrays()
        common = dict(
            node=self._node(),
            weight_n=_parse_float(self.weight, "weight_n"),
            journal_diameter_m=_parse_float(self.journal_diameter_mm, "journal diameter") * 1.0e-3,
            radial_clearance_m=_parse_float(self.clearance_um, "radial clearance") * 1.0e-6,
            oil_viscosity_pa_s=_parse_float(self.oil_viscosity, "oil_viscosity_pa_s"),
            pivot_angle_rad=pivot, pad_arc_rad=arc, pad_axial_length_m=length,
            preload=preload, offset=offset,
            fxs_load_n=_parse_float(self.fxs, "fxs_load_n"),
            fys_load_n=_parse_float(self.fys, "fys_load_n"),
            total_e_x_film=_parse_int(self.total_e_x_film, "total_e_x_film"),
            total_e_z_film=_parse_int(self.total_e_z_film, "total_e_z_film"),
            total_e_y_pad=_parse_int(self.total_e_y_pad, "total_e_y_pad"),
            total_e_y_film=_parse_int(self.total_e_y_film, "total_e_y_film"),
            xj_ratio_initial=_parse_float(self.xj_initial, "xj_ratio_initial"),
            yj_ratio_initial=_parse_float(self.yj_initial, "yj_ratio_initial"),
            relax_p=_parse_float(self.relax_p, "relax_p"),
            relax_temperature=_parse_float(self.relax_temperature, "relax_temperature"),
            max_iterations=_parse_int(self.max_iterations, "max_iterations"),
            outer_iterations=_parse_int(self.outer_iterations, "outer_iterations"),
            force_tolerance=_parse_float(self.force_tolerance, "force_tolerance"),
            field_tolerance=_parse_float(self.field_tolerance, "field_tolerance"),
            thermal_type=self.thermal_type.currentData(),
            deform_type=self.deform_type.currentData(),
            oil_supply_temperature_k=self._c_to_k(_parse_optional_float(self.oil_supply_c, "oil supply temperature")),
            lubricant_density_kg_m3=_parse_optional_float(self.lub_density, "lubricant_density_kg_m3"),
            lubricant_cp_j_kgk=_parse_optional_float(self.lub_cp, "lubricant_cp_j_kgk"),
            lubricant_conductivity_w_mk=_parse_optional_float(self.lub_conductivity, "lubricant_conductivity_w_mk"),
            viscosity2_pa_s=_parse_optional_float(self.viscosity2, "viscosity2_pa_s"),
            temperature1_k=self._c_to_k(_parse_optional_float(self.temperature1_c, "temperature1")),
            temperature2_k=self._c_to_k(_parse_optional_float(self.temperature2_c, "temperature2")),
            temperature_journal_k=self._c_to_k(_parse_optional_float(self.temperature_journal_c, "temperature_journal")),
            temperature_ambient_k=self._c_to_k(_parse_optional_float(self.temperature_ambient_c, "temperature_ambient")),
            temperature_reference_k=self._c_to_k(_parse_optional_float(self.temperature_reference_c, "temperature_reference")),
            ambient_pressure_1_pa=_parse_float(self.ambient_pressure_1, "ambient_pressure_1_pa"),
            ambient_pressure_2_pa=_parse_float(self.ambient_pressure_2, "ambient_pressure_2_pa"),
            pad_conductivity_w_mk=_parse_optional_float(self.pad_conductivity, "pad_conductivity_w_mk"),
            pad_young_pa=(
                None if (v := _parse_optional_float(self.pad_young_mpa, "pad_young")) is None else v * 1.0e6
            ),
            pad_poisson=_parse_optional_float(self.pad_poisson, "pad_poisson"),
            pad_expansion_1_k=_parse_optional_float(self.pad_expansion, "pad_expansion_1_k"),
            convection_edges_w_m2k=_parse_float(self.convection_edges, "convection_edges_w_m2k"),
            convection_back_w_m2k=_parse_float(self.convection_back, "convection_back_w_m2k"),
            hot_oil_lambda=_parse_float(self.hot_oil_lambda, "hot_oil_lambda"),
            tag=self.tag_edit.text().strip(),
            provenance=dict(self._provenance),
        )
        return common, krotate

    def _physics_bearing(self):
        common, krotate = self._physics_common()
        if self.family == FAMILY_PLAIN:
            thickness = _parse_optional_float(self.pad_thickness_mm, "pad_thickness")
            bearing = PlainJournalPhysicsBearing(
                **common,
                pad_thickness_m=None if thickness is None else thickness * 1.0e-3,
            )
        else:
            bearing = TiltingPadPhysicsBearing(
                **common,
                pad_thickness_m=_parse_float(self.pad_thickness_mm, "pad_thickness") * 1.0e-3,
                pad_density_kg_m3=_parse_float(self.pad_density, "pad_density_kg_m3"),
                k_rotate_nm_rad=krotate,
                bearing_type="conventional_tilting_pad",
                oil_flow_m3_s=_parse_optional_float(self.oil_flow, "oil_flow_m3_s"),
            )
        validate_advanced_bearing(bearing)
        return bearing

    def _build_qualification_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        warning = QLabel(
            "Qualification and authority claims are read-only. This editor cannot create or alter a ROSS parity "
            "claim, authority SHA, provider provenance, or any text used to release a solver bridge."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#805b00; font-weight:600;")
        layout.addWidget(warning)
        form = QFormLayout()
        self.qual_family = _readonly(FAMILY_LABELS[self.family])
        self.qual_native, self.qual_sha, self.qual_provider, self.qual_state = _readonly(), _readonly(), _readonly(), _readonly()
        form.addRow("Model family:", self.qual_family)
        form.addRow("Native physics qualification:", self.qual_native)
        form.addRow("ROSS authority SHA:", self.qual_sha)
        form.addRow("Provider provenance:", self.qual_provider)
        form.addRow("Qualification state:", self.qual_state)
        layout.addLayout(form)
        self.provenance_json = QPlainTextEdit()
        self.provenance_json.setReadOnly(True)
        layout.addWidget(QLabel("Persisted provenance (read-only):"))
        layout.addWidget(self.provenance_json, 1)
        self.tabs.addTab(tab, "Qualification")

    def _populate_qualification(self):
        provenance = dict(self._provenance)
        self.qual_native.setText(str(provenance.get("native_physics_qualification", provenance.get("qualification", ""))))
        self.qual_sha.setText(str(provenance.get("ross_authority_sha", "")))
        self.qual_provider.setText(str(provenance.get("provider_provenance", provenance.get("provider", ""))))
        self.qual_state.setText(str(provenance.get("qualification_state", provenance.get("qualification", ""))))
        self.provenance_json.setPlainText(json.dumps(provenance, indent=2, sort_keys=True, default=str))

    def _populate(self, bearing):
        if bearing is None:
            self._populate_defaults()
        elif self.family == FAMILY_COEFFICIENT:
            self._populate_coefficient(bearing)
        else:
            self._populate_physics(bearing)
        self._populate_qualification()
        if bearing is not None:
            pos = self.node_combo.findData(int(bearing.node))
            self.node_combo.setCurrentIndex(pos)
            self.tag_edit.setText(str(getattr(bearing, "tag", "")))
        if self.family != FAMILY_COEFFICIENT:
            self._sync_dynamic_sections()

    def _populate_defaults(self):
        if self.node_combo.count():
            self.node_combo.setCurrentIndex(0)
        self.tag_edit.setText("")
        if self.family == FAMILY_COEFFICIENT:
            self.speed_axis.clear()
            self.frequency_axis.clear()
            self.interpolation_combo.setCurrentText("pchip")
            defaults = {
                "Kxx": 1.0e6, "Kxy": 0.0, "Kyx": 0.0, "Kyy": 1.0e6,
                "Cxx": 100.0, "Cxy": 0.0, "Cyx": 0.0, "Cyy": 100.0,
                "Mxx": 0.0, "Mxy": 0.0, "Myx": 0.0, "Myy": 0.0,
            }
            for row, name in enumerate(self.coeff_names):
                self.coeff_table.item(row, 1).setText(_data_text(defaults[name]))
            return

        _set_text(self.weight, 1000.0)
        _set_text(self.journal_diameter_mm, 100.0)
        _set_text(self.clearance_um, 75.0)
        _set_text(self.oil_viscosity, 0.02)
        _set_text(self.fxs, 0.0)
        _set_text(self.fys, 0.0)
        self.oil_supply_c.setText("")
        for field in (
            self.lub_density, self.lub_cp, self.lub_conductivity, self.viscosity2,
            self.temperature1_c, self.temperature2_c, self.temperature_journal_c,
            self.temperature_ambient_c, self.temperature_reference_c,
            self.pad_conductivity, self.pad_young_mpa, self.pad_poisson, self.pad_expansion,
        ):
            field.setText("")
        _set_text(self.ambient_pressure_1, 0.0)
        _set_text(self.ambient_pressure_2, 0.0)
        self.thermal_type.setCurrentIndex(0)
        self.deform_type.setCurrentIndex(0)
        _set_text(self.convection_edges, 0.0)
        _set_text(self.convection_back, 0.0)
        _set_text(self.hot_oil_lambda, 0.0)
        _set_text(self.total_e_x_film, 20)
        _set_text(self.total_e_z_film, 10)
        _set_text(self.total_e_y_pad, 10)
        _set_text(self.total_e_y_film, 10)
        _set_text(self.xj_initial, 0.15)
        _set_text(self.yj_initial, -0.2)
        _set_text(self.relax_p, 0.5)
        _set_text(self.relax_temperature, 0.5)
        _set_text(self.max_iterations, 80)
        _set_text(self.outer_iterations, 30)
        _set_text(self.force_tolerance, 0.002)
        _set_text(self.field_tolerance, 0.001)
        self.pads.setRowCount(0)
        if self.family == FAMILY_PLAIN:
            self.pad_thickness_mm.setText("")
            for values in ((90.0, 176.0, 50.0, 0.0, 0.5), (270.0, 176.0, 50.0, 0.0, 0.5)):
                self.add_pad(values)
        else:
            _set_text(self.pad_thickness_mm, 12.7)
            _set_text(self.pad_density, 7800.0)
            self.oil_flow.setText("")
            for pivot in (18.0, 90.0, 162.0, 234.0, 306.0):
                self.add_pad((pivot, 60.0, 50.0, 0.4, 0.5, 0.0))

    def _populate_coefficient(self, b: CoefficientBearing):
        self.speed_axis.setText(_axis_text(b.speed_rad_s))
        self.frequency_axis.setText(_axis_text(b.frequency_rad_s))
        self.interpolation_combo.setCurrentText(str(b.interpolation))
        values = {
            "Kxx": b.kxx, "Kxy": b.kxy, "Kyx": b.kyx, "Kyy": b.kxx if b.kyy is None else b.kyy,
            "Cxx": b.cxx, "Cxy": b.cxy, "Cyx": b.cyx, "Cyy": b.cxx if b.cyy is None else b.cyy,
            "Mxx": b.mxx, "Mxy": b.mxy, "Myx": b.myx, "Myy": b.mxx if b.myy is None else b.myy,
        }
        for row, name in enumerate(self.coeff_names):
            self.coeff_table.item(row, 1).setText(_data_text(values[name]))

    def _populate_physics(self, b):
        _set_text(self.weight, b.weight_n)
        _set_text(self.journal_diameter_mm, b.journal_diameter_m, 1.0e3)
        _set_text(self.clearance_um, b.radial_clearance_m, 1.0e6)
        _set_text(self.oil_viscosity, b.oil_viscosity_pa_s)
        if self.family == FAMILY_TILTING:
            _set_text(self.pad_thickness_mm, b.pad_thickness_m, 1.0e3)
            _set_text(self.pad_density, b.pad_density_kg_m3)
            _set_text(self.oil_flow, b.oil_flow_m3_s)
        else:
            _set_text(self.pad_thickness_mm, b.pad_thickness_m, 1.0e3)
        self.pads.setRowCount(0)
        for i in range(len(b.pivot_angle_rad)):
            vals = [
                math.degrees(b.pivot_angle_rad[i]),
                math.degrees(b.pad_arc_rad[i]),
                b.pad_axial_length_m[i] * 1.0e3,
                b.preload[i],
                b.offset[i],
            ]
            if self.family == FAMILY_TILTING:
                vals.append(b.k_rotate_nm_rad[i])
            self.add_pad(vals)

        _set_text(self.fxs, b.fxs_load_n)
        _set_text(self.fys, b.fys_load_n)
        _set_text(self.lub_density, b.lubricant_density_kg_m3)
        _set_text(self.lub_cp, b.lubricant_cp_j_kgk)
        _set_text(self.lub_conductivity, b.lubricant_conductivity_w_mk)
        _set_text(self.viscosity2, b.viscosity2_pa_s)
        _set_text(self.oil_supply_c, self._k_to_c(b.oil_supply_temperature_k))
        _set_text(self.temperature1_c, self._k_to_c(b.temperature1_k))
        _set_text(self.temperature2_c, self._k_to_c(b.temperature2_k))
        _set_text(self.temperature_journal_c, self._k_to_c(b.temperature_journal_k))
        _set_text(self.temperature_ambient_c, self._k_to_c(b.temperature_ambient_k))
        _set_text(self.temperature_reference_c, self._k_to_c(b.temperature_reference_k))
        _set_text(self.ambient_pressure_1, b.ambient_pressure_1_pa)
        _set_text(self.ambient_pressure_2, b.ambient_pressure_2_pa)
        _set_text(self.pad_conductivity, b.pad_conductivity_w_mk)
        _set_text(self.pad_young_mpa, None if b.pad_young_pa is None else b.pad_young_pa * 1.0e-6)
        _set_text(self.pad_poisson, b.pad_poisson)
        _set_text(self.pad_expansion, b.pad_expansion_1_k)
        _set_text(self.convection_edges, b.convection_edges_w_m2k)
        _set_text(self.convection_back, b.convection_back_w_m2k)
        _set_text(self.hot_oil_lambda, b.hot_oil_lambda)
        self.thermal_type.setCurrentIndex(self.thermal_type.findData(b.thermal_type))
        self.deform_type.setCurrentIndex(self.deform_type.findData(b.deform_type))
        _set_text(self.total_e_x_film, b.total_e_x_film)
        _set_text(self.total_e_z_film, b.total_e_z_film)
        _set_text(self.total_e_y_pad, b.total_e_y_pad)
        _set_text(self.total_e_y_film, b.total_e_y_film)
        _set_text(self.xj_initial, b.xj_ratio_initial)
        _set_text(self.yj_initial, b.yj_ratio_initial)
        _set_text(self.relax_p, b.relax_p)
        _set_text(self.relax_temperature, b.relax_temperature)
        _set_text(self.max_iterations, b.max_iterations)
        _set_text(self.outer_iterations, b.outer_iterations)
        _set_text(self.force_tolerance, b.force_tolerance)
        _set_text(self.field_tolerance, b.field_tolerance)

    def bearing(self):
        if self.family == FAMILY_COEFFICIENT:
            return self._coefficient_bearing()
        return self._physics_bearing()

    def _accept_if_valid(self):
        try:
            self.bearing()
        except Exception as exc:
            self.error_label.setText(str(exc))
            return
        self.error_label.clear()
        self.accept()
