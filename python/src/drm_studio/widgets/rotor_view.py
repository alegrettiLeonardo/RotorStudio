from __future__ import annotations

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QBrush, QPen, QPolygonF
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QToolButton, QCheckBox, QStyle
)

from drm_studio.application.session import EntityRef
from .analysis_modules import AnalysisModulesBar


class RotorView(QGraphicsView):
    def __init__(self, session, parent=None):
        self.scene_obj = QGraphicsScene()
        super().__init__(self.scene_obj, parent)
        self.session = session
        self.setBackgroundBrush(QBrush(QColor("#ffffff")))
        self.setDragMode(QGraphicsView.NoDrag)
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
        ypad = max(80.0, max_d * 2.2)

        for i, disk in enumerate(model.disks):
            x = z.get(disk.node)
            if x is None:
                continue
            if disk.disk_type in (1, 3):
                thick = max(6.0, abs(disk.p4) * 1000.0)
                dia = max(max_d * 1.8, abs(disk.p5) * 1000.0)
            else:
                thick = max(8.0, (max_z - min_z) * 0.015)
                dia = max_d * 2.2
            item = self.scene_obj.addRect(
                x - thick / 2.0, -dia / 2.0, thick, dia,
                QPen(QColor("#303030"), 1.2), QBrush(QColor("#c8cdd2"))
            )
            ref = EntityRef("disk", i)
            item.setData(0, ref)
            item.setZValue(1)
            self._entity_items[ref] = item

        for i, shaft in enumerate(model.shafts):
            x1, x2 = z.get(shaft.node1), z.get(shaft.node2)
            if x1 is None or x2 is None:
                continue
            do = getattr(shaft, "outer_diameter_m", None)
            dia = max(8.0, (do * 1000.0) if do is not None else max_d * 0.5)
            rect = QRectF(min(x1, x2), -dia / 2.0, abs(x2 - x1), dia)
            item = self.scene_obj.addRect(
                rect, QPen(QColor("#202020"), 1.1), QBrush(QColor("#2bc8cf"))
            )
            ref = EntityRef("shaft", i)
            item.setData(0, ref)
            item.setZValue(2)
            self._entity_items[ref] = item
            if self.show_element_numbers:
                txt = self.scene_obj.addText(str(i + 1))
                txt.setDefaultTextColor(QColor("#23313f"))
                txt.setPos((x1 + x2) / 2.0 - 5.0, dia / 2.0 + 4.0)
                txt.setZValue(5)

        for i, node in enumerate(model.nodes):
            x = z[node.number]
            dot = self.scene_obj.addEllipse(
                x - 3.2, -3.2, 6.4, 6.4,
                QPen(QColor("#304050"), 1.0), QBrush(QColor("#ffd84d"))
            )
            ref = EntityRef("node", i)
            dot.setData(0, ref)
            dot.setZValue(6)
            self._entity_items[ref] = dot
            if self.show_node_numbers:
                label = self.scene_obj.addText(str(node.number))
                label.setDefaultTextColor(QColor("#1c2732"))
                label.setPos(x - 5.0, max_d / 2.0 + 22.0)
                label.setZValue(6)

        if self.show_bearings:
            for i, bearing in enumerate(model.bearings):
                if bearing.bearing_type == 8:
                    continue
                x = z.get(bearing.node)
                if x is None:
                    continue
                h = max(22.0, max_d * 0.55)
                poly = QPolygonF([
                    QPointF(x, 0.0),
                    QPointF(x - h * 0.45, h),
                    QPointF(x + h * 0.45, h),
                ])
                item = self.scene_obj.addPolygon(
                    poly, QPen(QColor("#155f3a"), 1.4), QBrush(QColor("#72e59f"))
                )
                ref = EntityRef("bearing", i)
                item.setData(0, ref)
                item.setZValue(4)
                self._entity_items[ref] = item
                self.scene_obj.addLine(
                    x - h * 0.7, h, x + h * 0.7, h,
                    QPen(QColor("#155f3a"), 1.2)
                )

        x0 = min_z
        self.scene_obj.addLine(x0, ypad * 0.85, x0 + 55, ypad * 0.85, QPen(QColor("#111"), 1.5))
        self.scene_obj.addLine(x0, ypad * 0.85, x0, ypad * 0.85 - 42, QPen(QColor("#111"), 1.5))
        tx = self.scene_obj.addText("X")
        tx.setPos(x0 + 57, ypad * 0.85 - 10)
        ty = self.scene_obj.addText("Y")
        ty.setPos(x0 - 13, ypad * 0.85 - 57)
        omega = self.scene_obj.addText("Ω ↻")
        omega.setScale(1.35)
        omega.setPos(max_z - 55, -ypad * 0.9)

        self.scene_obj.setSceneRect(
            min_z - 60, -ypad, max(max_z - min_z + 120, 300), ypad * 2
        )
        self._update_selection(self.session.selection)

    def _update_selection(self, ref):
        for entity_ref, item in self._entity_items.items():
            selected = entity_ref == ref
            pen = item.pen()
            pen.setColor(QColor("#ff3131") if selected else QColor("#202020"))
            pen.setWidthF(2.2 if selected else 1.1)
            item.setPen(pen)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.LeftButton:
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

    def zoom_in(self):
        self.scale(1.2, 1.2)

    def zoom_out(self):
        self.scale(1 / 1.2, 1 / 1.2)

    def fit_view(self):
        if self.scene_obj.items():
            self.fitInView(self.scene_obj.sceneRect(), Qt.KeepAspectRatio)

    def set_node_numbers(self, value):
        self.show_node_numbers = bool(value)
        self.rebuild_scene()

    def set_element_numbers(self, value):
        self.show_element_numbers = bool(value)
        self.rebuild_scene()

    def set_bearings(self, value):
        self.show_bearings = bool(value)
        self.rebuild_scene()


class RotorModelPage(QWidget):
    modalRequested = Signal()
    campbellRequested = Signal()
    criticalRequested = Signal()

    def __init__(self, session, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(3, 3, 3, 3)
        controls = QHBoxLayout()

        self.select_button = QToolButton()
        self.select_button.setText("Select")
        self.select_button.setCheckable(True)
        self.select_button.setChecked(True)

        self.zoom_in_button = QToolButton()
        self.zoom_in_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.zoom_in_button.setText("Zoom In")
        self.zoom_out_button = QToolButton()
        self.zoom_out_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        self.zoom_out_button.setText("Zoom Out")
        self.fit_button = QToolButton()
        self.fit_button.setText("Fit View")

        for button in (
            self.select_button, self.zoom_in_button,
            self.zoom_out_button, self.fit_button
        ):
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

        self.zoom_in_button.clicked.connect(self.view.zoom_in)
        self.zoom_out_button.clicked.connect(self.view.zoom_out)
        self.fit_button.clicked.connect(self.view.fit_view)
        self.nodes_check.toggled.connect(self.view.set_node_numbers)
        self.elements_check.toggled.connect(self.view.set_element_numbers)
        self.bearings_check.toggled.connect(self.view.set_bearings)
        self.modules.modalRequested.connect(self.modalRequested)
        self.modules.campbellRequested.connect(self.campbellRequested)
        self.modules.criticalRequested.connect(self.criticalRequested)
