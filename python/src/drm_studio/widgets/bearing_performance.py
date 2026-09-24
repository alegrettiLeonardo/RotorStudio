from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QColor, QBrush, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QToolButton, QLabel,
    QGraphicsView, QGraphicsScene, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QPlainTextEdit, QAbstractItemView
)

from drm_studio.docks.bearing_editor import BearingInspectorWidget, _BEARING_NAMES, _schema
from drm_studio.resources import studio_icon


class BearingPerformancePage(QWidget):
    """Mockup-conformant workspace for the bearing/seal physics that Stage 1 owns.

    The page intentionally does not synthesize BePerf pressure/thermal results.
    It provides the visual workspace and the real type-sensitive Stage 1 editor.
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session=session
        outer=QVBoxLayout(self)
        outer.setContentsMargins(4,4,4,4)
        outer.setSpacing(4)

        nav=QHBoxLayout()
        nav.setSpacing(4)
        specs=[
            ("Rigid / K-C","bearing",True),
            ("Short Hydro","bearing",True),
            ("Seal","seal",True),
            ("Tilting-Pad","bearing",False),
            ("Floating-Ring","bearing",False),
            ("Gas Bearing","bearing",False),
            ("Thrust","bearing",False),
        ]
        self.nav_buttons=[]
        for text,icon_name,enabled in specs:
            b=QToolButton()
            b.setText(text)
            b.setIcon(studio_icon(icon_name))
            b.setIconSize(QSize(24,24))
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setMinimumWidth(82)
            b.setMinimumHeight(56)
            b.setEnabled(enabled)
            if not enabled:
                b.setToolTip("NOT AVAILABLE / FUTURE — no qualified Stage 1 solver for this family.")
            nav.addWidget(b)
            self.nav_buttons.append(b)
        nav.addStretch(1)
        outer.addLayout(nav)

        body=QSplitter(Qt.Horizontal)
        self.editor=BearingInspectorWidget(session)
        self.editor.setMinimumWidth(330)
        body.addWidget(self.editor)

        center=QWidget()
        center_layout=QVBoxLayout(center)
        center_layout.setContentsMargins(3,3,3,3)
        self.heading=QLabel("Bearing / Seal Schematic")
        self.heading.setObjectName("SectionHeaderTitle")
        center_layout.addWidget(self.heading)
        self.scene=QGraphicsScene(self)
        self.graphics=QGraphicsView(self.scene)
        self.graphics.setBackgroundBrush(QBrush(QColor("white")))
        center_layout.addWidget(self.graphics,1)

        self.lower_tabs=QTabWidget()
        self.coefficient_note=QPlainTextEdit()
        self.coefficient_note.setReadOnly(True)
        self.lower_tabs.addTab(self.coefficient_note,"Dynamic Coefficients")
        pressure=QWidget(); temperature=QWidget()
        self.lower_tabs.addTab(pressure,"Pressure Distribution")
        self.lower_tabs.addTab(temperature,"Temperature")
        self.lower_tabs.setTabEnabled(1,False)
        self.lower_tabs.setTabEnabled(2,False)
        self.lower_tabs.setTabToolTip(1,"No new Reynolds/pressure solver is part of Stage 2.1.")
        self.lower_tabs.setTabToolTip(2,"No thermal bearing solver is part of Stage 2.1.")
        center_layout.addWidget(self.lower_tabs)
        body.addWidget(center)

        results=QWidget()
        results_layout=QVBoxLayout(results)
        results_layout.setContentsMargins(3,3,3,3)
        title=QLabel("Bearing / Seal Properties")
        title.setObjectName("SectionHeaderTitle")
        results_layout.addWidget(title)
        self.table=QTableWidget(0,3)
        self.table.setHorizontalHeaderLabels(["Parameter","Value","Units"])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        results_layout.addWidget(self.table,1)
        self.boundary=QLabel(
            "Only Stage 1 bearing/seal models are enabled. Unsupported BePerf families remain disabled."
        )
        self.boundary.setWordWrap(True)
        self.boundary.setStyleSheet("color:#60758a;")
        results_layout.addWidget(self.boundary)
        results.setMinimumWidth(270)
        body.addWidget(results)

        body.setStretchFactor(0,3)
        body.setStretchFactor(1,5)
        body.setStretchFactor(2,3)
        outer.addWidget(body,1)

        session.selectionChanged.connect(lambda _:self.refresh())
        session.modelChanged.connect(self.refresh)
        self.refresh()

    def _selected(self):
        ref=self.session.selection
        if ref is None or ref.kind!="bearing":
            return None
        if not (0<=ref.index<len(self.session.project.model.bearings)):
            return None
        return self.session.project.model.bearings[ref.index]

    def refresh(self):
        bearing=self._selected()
        self.scene.clear()
        self.table.setRowCount(0)
        if bearing is None:
            self.heading.setText("Bearing / Seal Schematic — select a bearing in Project Explorer")
            self.coefficient_note.setPlainText("Select a real Stage 1 bearing or seal to inspect its parameters.")
            return

        name=_BEARING_NAMES.get(bearing.bearing_type,f"Type {bearing.bearing_type}")
        self.heading.setText(f"{name} — Node {bearing.node}")
        self._draw_schematic(bearing)
        self._populate_table(bearing)

        if bearing.bearing_type in (3,4,5,6,20):
            self.coefficient_note.setPlainText(
                "The table shows the persisted qualified constant K/C inputs. "
                "No coefficient identification is performed by the UI."
            )
        elif bearing.bearing_type==7:
            self.coefficient_note.setPlainText(
                "Hydrodynamic short-width bearing: Stage 1 computes the supported bearing matrices "
                "through the existing Fortran-backed path. Pressure and thermal fields are not fabricated."
            )
        elif bearing.bearing_type==8:
            self.coefficient_note.setPlainText(
                "Seal model: only the real Stage 1 seal parameters and compatible analyses are exposed."
            )
        else:
            self.coefficient_note.setPlainText("Rigid support boundary condition from the qualified Stage 1 model.")

    def _draw_schematic(self,bearing):
        pen=QPen(QColor("#1e2d39"),1.5)
        blue=QBrush(QColor("#9cc8f6"))
        grey=QBrush(QColor("#d7dce1"))
        cx,cy=210.0,145.0
        outer=118.0
        inner=74.0

        self.scene.addEllipse(QRectF(cx-outer,cy-outer,2*outer,2*outer),pen,QBrush(QColor("#f7f9fb")))
        self.scene.addEllipse(QRectF(cx-inner,cy-inner,2*inner,2*inner),pen,grey)

        if bearing.bearing_type==7:
            # Generic short-bearing annulus. It is geometric context only.
            self.scene.addEllipse(QRectF(cx-94,cy-94,188,188),QPen(QColor("#4b8dc6"),9),QBrush(Qt.NoBrush))
            label=self.scene.addText("Short hydrodynamic bearing")
        elif bearing.bearing_type==8:
            self.scene.addEllipse(QRectF(cx-98,cy-98,196,196),QPen(QColor("#2872b2"),12),QBrush(Qt.NoBrush))
            self.scene.addEllipse(QRectF(cx-88,cy-88,176,176),QPen(QColor("#7fb3df"),5),QBrush(Qt.NoBrush))
            label=self.scene.addText("Seal")
        else:
            # Four stiffness/damping directions without inventing numerical values.
            for dx,dy in ((0,-1),(1,0),(0,1),(-1,0)):
                x2=cx+dx*112; y2=cy+dy*112
                self.scene.addLine(cx+dx*inner,cy+dy*inner,x2,y2,QPen(QColor("#2e6fa6"),3))
            label=self.scene.addText("Support / K-C model")

        label.setDefaultTextColor(QColor("#0a4f98"))
        label.setPos(cx-82,cy+outer+14)
        axis_pen=QPen(QColor("#111111"),1.2)
        self.scene.addLine(cx-140,cy,cx+145,cy,axis_pen)
        self.scene.addLine(cx,cy+140,cx,cy-145,axis_pen)
        xlab=self.scene.addText("X"); xlab.setPos(cx+147,cy-12)
        ylab=self.scene.addText("Y"); ylab.setPos(cx+5,cy-163)
        self.scene.setSceneRect(40,-35,360,365)
        self.graphics.fitInView(self.scene.sceneRect(),Qt.KeepAspectRatio)

    def _populate_table(self,bearing):
        schema=_schema(bearing.bearing_type)
        self.table.setRowCount(len(schema)+2)
        basic=[("Type",str(bearing.bearing_type),_BEARING_NAMES.get(bearing.bearing_type,"")),
               ("Node",str(bearing.node),"")]
        for row,values in enumerate(basic):
            for col,value in enumerate(values):
                self.table.setItem(row,col,QTableWidgetItem(value))
        props=list(bearing.properties)
        for offset,(name,unit,scale) in enumerate(schema,2):
            value=props[offset-2] if offset-2<len(props) else 0.0
            shown=float(value)*scale
            self.table.setItem(offset,0,QTableWidgetItem(name))
            self.table.setItem(offset,1,QTableWidgetItem(f"{shown:.8g}"))
            self.table.setItem(offset,2,QTableWidgetItem(unit))
