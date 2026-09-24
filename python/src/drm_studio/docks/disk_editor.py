from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QComboBox, QSpinBox,
    QDoubleSpinBox, QStackedWidget,
)

from drm_core import Disk
from drm_core.units import m_to_mm, mm_to_m
from drm_core.validation.model import ModelValidationError
from drm_studio.commands import EditDiskCommand


def _spin(decimals=6, minimum=0.0, maximum=1.0e12):
    w = QDoubleSpinBox()
    w.setDecimals(decimals)
    w.setRange(minimum, maximum)
    w.setKeyboardTracking(False)
    return w


class DiskInspectorWidget(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._updating = False
        outer = QVBoxLayout(self)

        form = QFormLayout()
        self.type_combo = QComboBox()
        for t, label in (
            (1, "Geometric circular disk"),
            (2, "Mass + diametral/polar inertia"),
            (3, "Geometric circular disk — no gyro"),
            (4, "Mass/inertia — no gyro"),
            (5, "Anisotropic inertia disk"),
            (6, "Anisotropic inertia disk variant"),
        ):
            self.type_combo.addItem(f"{t} — {label}", t)
        self.node = QSpinBox()
        self.node.setRange(1, 1000000)
        self.node.setKeyboardTracking(False)
        form.addRow("Disk type:", self.type_combo)
        form.addRow("Node:", self.node)
        outer.addLayout(form)

        self.pages = QStackedWidget()
        outer.addWidget(self.pages)

        # Geometric types 1/3
        geo = QWidget(); g = QFormLayout(geo)
        self.rho = _spin(3); self.thickness = _spin(4); self.od = _spin(4); self.id = _spin(4)
        g.addRow("Density (kg/m³):", self.rho)
        g.addRow("Thickness (mm):", self.thickness)
        g.addRow("Outer diameter (mm):", self.od)
        g.addRow("Inner diameter (mm):", self.id)
        self.pages.addWidget(geo)

        # Inertial types 2/4
        inertial = QWidget(); i = QFormLayout(inertial)
        self.mass = _spin(6); self.idiam = _spin(9); self.ipolar = _spin(9)
        i.addRow("Mass (kg):", self.mass)
        i.addRow("Diametral inertia (kg·m²):", self.idiam)
        i.addRow("Polar inertia (kg·m²):", self.ipolar)
        self.pages.addWidget(inertial)

        # Anisotropic types 5/6
        anis = QWidget(); a = QFormLayout(anis)
        self.amass = _spin(6); self.ix = _spin(9); self.iy = _spin(9); self.ip = _spin(9)
        a.addRow("Mass (kg):", self.amass)
        a.addRow("Ix (kg·m²):", self.ix)
        a.addRow("Iy (kg·m²):", self.iy)
        a.addRow("Ip (kg·m²):", self.ip)
        self.pages.addWidget(anis)

        self.error = QLabel("")
        self.error.setWordWrap(True)
        self.error.setStyleSheet("color:#a40000;")
        outer.addWidget(self.error)
        outer.addStretch(1)

        self.type_combo.currentIndexChanged.connect(self._type_changed)
        self.node.editingFinished.connect(self._commit_current)
        for widget in (
            self.rho, self.thickness, self.od, self.id,
            self.mass, self.idiam, self.ipolar,
            self.amass, self.ix, self.iy, self.ip,
        ):
            widget.editingFinished.connect(self._commit_current)

        session.selectionChanged.connect(lambda _: self.refresh())
        session.modelChanged.connect(self.refresh)
        self.refresh()

    def _selection(self):
        ref = self.session.selection
        if ref is None or ref.kind != "disk":
            return None, None
        if not (0 <= ref.index < len(self.session.project.model.disks)):
            return None, None
        return ref.index, self.session.project.model.disks[ref.index]

    @staticmethod
    def _page_for_type(t):
        if t in (1, 3):
            return 0
        if t in (2, 4):
            return 1
        return 2

    def refresh(self):
        self._updating = True
        try:
            index, disk = self._selection()
            self.error.clear()
            self.setEnabled(disk is not None)
            if disk is None:
                return
            pos = self.type_combo.findData(disk.disk_type)
            if pos >= 0:
                self.type_combo.setCurrentIndex(pos)
            self.node.setValue(disk.node)
            self.pages.setCurrentIndex(self._page_for_type(disk.disk_type))
            if disk.disk_type in (1, 3):
                self.rho.setValue(disk.p3)
                self.thickness.setValue(m_to_mm(disk.p4))
                self.od.setValue(m_to_mm(disk.p5))
                self.id.setValue(m_to_mm(disk.p6))
            elif disk.disk_type in (2, 4):
                self.mass.setValue(disk.p3)
                self.idiam.setValue(disk.p4)
                self.ipolar.setValue(disk.p5)
            else:
                self.amass.setValue(disk.p3)
                self.ix.setValue(disk.p4)
                self.iy.setValue(disk.p5)
                self.ip.setValue(disk.p6)
        finally:
            self._updating = False

    def _disk_from_widgets(self, disk_type=None):
        _, old = self._selection()
        if old is None:
            return None
        t = int(self.type_combo.currentData() if disk_type is None else disk_type)
        node = int(self.node.value())
        if t in (1, 3):
            return Disk(t, node, float(self.rho.value()), mm_to_m(self.thickness.value()),
                        mm_to_m(self.od.value()), mm_to_m(self.id.value()))
        if t in (2, 4):
            return Disk(t, node, float(self.mass.value()), float(self.idiam.value()),
                        float(self.ipolar.value()), 0.0)
        return Disk(t, node, float(self.amass.value()), float(self.ix.value()),
                    float(self.iy.value()), float(self.ip.value()))

    def _safe_default(self, t, node):
        if t in (1, 3):
            return Disk(t, node, 7800.0, 0.02, 0.10, 0.02)
        if t in (2, 4):
            return Disk(t, node, 1.0, 0.01, 0.02, 0.0)
        return Disk(t, node, 1.0, 0.01, 0.011, 0.02)

    def _push(self, new_disk, text):
        index, old = self._selection()
        if old is None or new_disk == old:
            return
        try:
            self.session.undo_stack.push(EditDiskCommand(self.session, index, new_disk, text))
            self.error.clear()
            self.session.log("INFO", text)
        except (ModelValidationError, ValueError) as exc:
            self.refresh()
            self.error.setText(str(exc))
            self.session.log("ERROR", str(exc))

    def _type_changed(self):
        if self._updating:
            return
        index, old = self._selection()
        if old is None:
            return
        t = int(self.type_combo.currentData())
        if t == old.disk_type:
            return
        self._push(self._safe_default(t, old.node), f"Change disk {index + 1} type to {t}")

    def _commit_current(self):
        if self._updating:
            return
        index, old = self._selection()
        if old is None:
            return
        self._push(self._disk_from_widgets(), f"Edit disk {index + 1}")
