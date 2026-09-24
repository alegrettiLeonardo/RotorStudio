from __future__ import annotations

from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QSize
from PySide6.QtGui import QColor, QBrush, QPen, QPolygonF
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QToolButton, QCheckBox, QButtonGroup
)

from drm_studio.application.session import EntityRef
from drm_studio.resources import studio_icon
from .analysis_modules import AnalysisModulesBar


class RotorView(QGraphicsView):
    def __init__(self, session, parent=None):
        self.scene_obj = QGraphicsScene()
        super().__init__(self.scene_obj, parent)
        self.session = session
        self.setBackgroundBrush(QBrush(QColor("#ffffff")))
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHints(self.renderHints())
        self._panning = False
        self._pan_start = None
        self.show_node_numbers = True
        self.show_element_numbers = True
        self.show_bearings = True
        self._entity_items = {}

        session.modelChanged.connect(self.rebuild_scene)
        session.projectChanged.connect(self.rebuild_scene)
        session.selectionChanged.connect(self._update_selection)
        self.rebuild_scene()

    def rebuild_scene(self):
        self.scene_obj.clear()
        self._entity_items = {}
        model = self.session.project.model
        if not model.nodes:
            item = self.scene_obj.addText("No rotor model loaded")
            item.setDefaultTextColor(QColor("#5b6976"))
            self.scene_obj.setSceneRect(0, 0, 800, 400)
            return

        z = {node.number: node.z_m * 1000.0 for node in model.nodes}
        min_z, max_z = min(z.values()), max(z.values())
        max_d = max([getattr(s, "outer_diameter_m", 0.05) * 1000.0 for s in model.shafts] + [50.0])
        ypad = max(90.0, max_d * 2.35)

        # Draw disks behind shaft, matching the mockup visual hierarchy.
        for i, disk in enumerate(model.disks):
            x = z.get(disk.node)
            if x is None:
                continue
            if disk.disk_type in (1, 3):
                thick = max(8.0, abs(disk.p4) * 1000.0)
                dia = max(max_d * 1.9, abs(disk.p5) * 1000.0)
            else:
                thick = max(10.0, (max_z - min_z) * 0.018)
                dia = max_d * 2.25
            item = self.scene_obj.addRect(
                x - thick / 2.0, -dia / 2.0, thick, dia,
                QPen(QColor("#232a30"), 1.3), QBrush(QColor("#c9ced3"))
            )
            ref = EntityRef("disk", i)
            item.setData(0, ref)
            item.setZValue(1)
            self._entity_items[ref] = item

        # Shaft rectangles produce the stepped profile from the real geometry.
        for i, shaft in enumerate(model.shafts):
            x1, x2 = z.get(shaft.node1), z.get(shaft.node2)
            if x1 is None or x2 is None:
                continue
            do = getattr(shaft, "outer_diameter_m", None)
            dia = max(8.0, (do * 1000.0) if do is not None else max_d * 0.5)
            rect = QRectF(min(x1, x2), -dia / 2.0, abs(x2 - x1), dia)
            item = self.scene_obj.addRect(
                rect,
                QPen(QColor("#16242f"), 1.15),
                QBrush(QColor("#2fc9cf"))
            )
            ref = EntityRef("shaft", i)
            item.setData(0, ref)
            item.setZValue(2)
            self._entity_items[ref] = item
            if self.show_element_numbers:
                txt = self.scene_obj.addText(str(i + 1))
                txt.setDefaultTextColor(QColor("#21313e"))
                txt.setPos((x1 + x2) / 2.0 - 5.0, dia / 2.0 + 4.0)
                txt.setZValue(8)

        for i, node in enumerate(model.nodes):
            x = z[node.number]
            dot = self.scene_obj.addEllipse(
                x - 3.0, -3.0, 6.0, 6.0,
                QPen(QColor("#304050"), 1.0), QBrush(QColor("#ffd84d"))
            )
            ref = EntityRef("node", i)
            dot.setData(0, ref)
            dot.setZValue(7)
            self._entity_items[ref] = dot
            if self.show_node_numbers:
                label = self.scene_obj.addText(str(node.number))
                label.setDefaultTextColor(QColor("#182630"))
                label.setPos(x - 5.0, max_d / 2.0 + 22.0)
                label.setZValue(8)

        if self.show_bearings:
            for i, bearing in enumerate(model.bearings):
                x = z.get(bearing.node)
                if x is None:
                    continue
                if bearing.bearing_type == 8:
                    # Seal: compact annular marker, not a fictitious support.
                    r = max(8.0, max_d * 0.18)
                    item = self.scene_obj.addEllipse(
                        x-r, -r, 2*r, 2*r,
                        QPen(QColor("#2568a5"), 2.0), QBrush(Qt.NoBrush)
                    )
                else:
                    h = max(22.0, max_d * 0.55)
                    poly = QPolygonF([
                        QPointF(x, 0.0),
                        QPointF(x - h * 0.45, h),
                        QPointF(x + h * 0.45, h),
                    ])
                    item = self.scene_obj.addPolygon(
                        poly,
                        QPen(QColor("#145d38"), 1.5),
                        QBrush(QColor("#75df9c"))
                    )
                    self.scene_obj.addLine(
                        x - h * 0.70, h, x + h * 0.70, h,
                        QPen(QColor("#145d38"), 1.3)
                    )
                ref = EntityRef("bearing", i)
                item.setData(0, ref)
                item.setZValue(5)
                self._entity_items[ref] = item

        # Axis glyph.
        x0 = min_z
        ay = ypad * 0.86
        self.scene_obj.addLine(x0, ay, x0 + 58, ay, QPen(QColor("#111111"), 1.5))
        self.scene_obj.addLine(x0, ay, x0, ay - 45, QPen(QColor("#111111"), 1.5))
        tx = self.scene_obj.addText("X"); tx.setPos(x0 + 60, ay - 11)
        ty = self.scene_obj.addText("Y"); ty.setPos(x0 - 14, ay - 60)
        omega = self.scene_obj.addText("Ω")
        omega.setScale(1.35)
        omega.setPos(max_z - 46, -ypad * 0.92)
        self.scene_obj.addLine(
            max_z - 28, -ypad * 0.72, max_z - 10, -ypad * 0.55,
            QPen(QColor("#151515"), 1.5)
        )

        self.scene_obj.setSceneRect(
            min_z - 65, -ypad, max(max_z - min_z + 130, 320), ypad * 2
        )
        self._update_selection(self.session.selection)

    def _update_selection(self, ref):
        for entity_ref, item in self._entity_items.items():
            selected = entity_ref == ref
            pen = item.pen()
            pen.setColor(QColor("#ff2f2f") if selected else QColor("#202020"))
            pen.setWidthF(2.3 if selected else 1.15)
            item.setPen(pen)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.LeftButton and self.dragMode() == QGraphicsView.NoDrag:
            item = self.itemAt(event.position().toPoint())
            while item is not None:
                ref = item.data(0)
                if ref is not None:
                    self.session.set_selection(ref)
                    break
                item = item.parentItem()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_start is not None:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self._panning:
            self._panning = False
            self._pan_start = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def zoom_in(self): self.scale(1.2, 1.2)
    def zoom_out(self): self.scale(1 / 1.2, 1 / 1.2)

    def fit_view(self):
        if self.scene_obj.items():
            self.fitInView(self.scene_obj.sceneRect(), Qt.KeepAspectRatio)

    def set_pan_mode(self, enabled):
        self.setDragMode(QGraphicsView.ScrollHandDrag if enabled else QGraphicsView.NoDrag)

    def set_node_numbers(self, value):
        self.show_node_numbers = bool(value); self.rebuild_scene()

    def set_element_numbers(self, value):
        self.show_element_numbers = bool(value); self.rebuild_scene()

    def set_bearings(self, value):
        self.show_bearings = bool(value); self.rebuild_scene()


class RotorModelPage(QWidget):
    modalRequested = Signal()
    campbellRequested = Signal()
    criticalRequested = Signal()
    synchronousRequested = Signal()
    frequencyRequested = Signal()
    foundationRequested = Signal()
    runupRequested = Signal()
    coaxialRequested = Signal()
    asymmetricRequested = Signal()
    bearingRequested = Signal()

    def __init__(self, session, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(3, 3, 3, 3)
        outer.setSpacing(4)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)

        self.select_button = QToolButton()
        self.select_button.setText("Select")
        self.select_button.setIcon(studio_icon("model"))
        self.select_button.setCheckable(True)
        self.select_button.setChecked(True)

        self.pan_button = QToolButton()
        self.pan_button.setText("Pan")
        self.pan_button.setIcon(studio_icon("pan"))
        self.pan_button.setCheckable(True)

        self.zoom_in_button = QToolButton()
        self.zoom_in_button.setIcon(studio_icon("zoom_in"))
        self.zoom_in_button.setText("Zoom In")

        self.zoom_out_button = QToolButton()
        self.zoom_out_button.setIcon(studio_icon("zoom_out"))
        self.zoom_out_button.setText("Zoom Out")

        self.fit_button = QToolButton()
        self.fit_button.setIcon(studio_icon("fit"))
        self.fit_button.setText("Fit View")

        mode_group=QButtonGroup(self)
        mode_group.setExclusive(True)
        mode_group.addButton(self.select_button)
        mode_group.addButton(self.pan_button)

        for button in (
            self.select_button, self.pan_button, self.zoom_in_button,
            self.zoom_out_button, self.fit_button
        ):
            button.setIconSize(QSize(18,18))
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            controls.addWidget(button)

        controls.addStretch(1)
        self.nodes_check = QCheckBox("Show Node Numbers")
        self.nodes_check.setChecked(True)
        self.elements_check = QCheckBox("Show Element Numbers")
        self.elements_check.setChecked(True)
        self.bearings_check = QCheckBox("Show Bearings")
        self.bearings_check.setChecked(True)
        controls.addWidget(self.nodes_check)
        controls.addWidget(self.elements_check)
        controls.addWidget(self.bearings_check)
        outer.addLayout(controls)

        self.view = RotorView(session)
        outer.addWidget(self.view, 1)
        self.modules = AnalysisModulesBar()
        outer.addWidget(self.modules)

        self.select_button.toggled.connect(lambda checked: self.view.set_pan_mode(False) if checked else None)
        self.pan_button.toggled.connect(self.view.set_pan_mode)
        self.zoom_in_button.clicked.connect(self.view.zoom_in)
        self.zoom_out_button.clicked.connect(self.view.zoom_out)
        self.fit_button.clicked.connect(self.view.fit_view)
        self.nodes_check.toggled.connect(self.view.set_node_numbers)
        self.elements_check.toggled.connect(self.view.set_element_numbers)
        self.bearings_check.toggled.connect(self.view.set_bearings)
        self.modules.modalRequested.connect(self.modalRequested)
        self.modules.campbellRequested.connect(self.campbellRequested)
        self.modules.criticalRequested.connect(self.criticalRequested)
        self.modules.synchronousRequested.connect(self.synchronousRequested)
        self.modules.frequencyRequested.connect(self.frequencyRequested)
        self.modules.foundationRequested.connect(self.foundationRequested)
        self.modules.runupRequested.connect(self.runupRequested)
        self.modules.coaxialRequested.connect(self.coaxialRequested)
        self.modules.asymmetricRequested.connect(self.asymmetricRequested)
        self.modules.bearingRequested.connect(self.bearingRequested)
