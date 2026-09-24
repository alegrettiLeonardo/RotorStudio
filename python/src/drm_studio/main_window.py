from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QToolBar, QStyle, QTabWidget, QLabel
)

from .application.session import ProjectSession
from .docks import MessagesDock, ProjectExplorerDock, PropertyInspectorDock
from .widgets import RotorModelPage
from .style import APP_STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self, session: ProjectSession | None = None, parent=None):
        super().__init__(parent)
        self.session = session or ProjectSession(parent=self)
        self.setObjectName("RotorDynamicsStudioMainWindow")
        self.resize(1400, 900)
        self.setStyleSheet(APP_STYLESHEET)
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_shell()
        self._connect_session()
        self._restore_settings()
        self._refresh_title()
        self._refresh_status()

    def _std_icon(self, enum):
        return self.style().standardIcon(enum)

    def _build_actions(self):
        self.new_action = QAction(self._std_icon(QStyle.SP_FileIcon), "New", self)
        self.open_action = QAction(self._std_icon(QStyle.SP_DialogOpenButton), "Open", self)
        self.save_action = QAction(self._std_icon(QStyle.SP_DialogSaveButton), "Save", self)
        self.save_as_action = QAction("Save As…", self)
        self.exit_action = QAction("Exit", self)
        self.undo_action = self.session.undo_stack.createUndoAction(self, "Undo")
        self.redo_action = self.session.undo_stack.createRedoAction(self, "Redo")
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.redo_action.setShortcut(QKeySequence.Redo)

        self.new_action.triggered.connect(self.session.new_project)
        self.open_action.triggered.connect(self._choose_open)
        self.save_action.triggered.connect(self._save)
        self.save_as_action.triggered.connect(self._save_as)
        self.exit_action.triggered.connect(self.close)

    def _build_menus(self):
        bar = self.menuBar()
        project = bar.addMenu("Project")
        project.addActions([self.new_action, self.open_action, self.save_action, self.save_as_action])
        project.addSeparator()
        project.addAction(self.exit_action)
        model = bar.addMenu("Model")
        model.addActions([self.undo_action, self.redo_action])
        self.analysis_menu = bar.addMenu("Analysis")
        self.bearings_menu = bar.addMenu("Bearings")
        self.results_menu = bar.addMenu("Results")
        bar.addMenu("Tools")
        bar.addMenu("Help")

    def _build_toolbar(self):
        toolbar = QToolBar("Main", self)
        toolbar.setObjectName("MainToolbar")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(toolbar)
        toolbar.addActions([self.new_action, self.open_action, self.save_action])
        toolbar.addSeparator()
        toolbar.addActions([self.undo_action, self.redo_action])

    def _build_shell(self):
        self.workspace = QTabWidget()
        self.workspace.setDocumentMode(True)
        self.workspace.setMovable(True)
        self.model_page = RotorModelPage(self.session)
        self.workspace.addTab(self.model_page, "Rotor Model")
        self.setCentralWidget(self.workspace)

        self.project_dock = ProjectExplorerDock(self.session, self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.project_dock)

        self.property_dock = PropertyInspectorDock(self.session, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.property_dock)

        self.messages_dock = MessagesDock(self.session, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.messages_dock)

        self.status_units = QLabel("Units: SI (mm, N, kg)")
        self.status_counts = QLabel("")
        self.statusBar().addPermanentWidget(self.status_units)
        self.statusBar().addPermanentWidget(self.status_counts)

    def _connect_session(self):
        self.session.projectChanged.connect(self._refresh_title)
        self.session.modelChanged.connect(self._refresh_status)
        self.session.pathChanged.connect(lambda _: self._refresh_title())
        self.session.dirtyChanged.connect(lambda _: self._refresh_title())

    def _choose_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open RotorStudio Project", "",
            "RotorStudio Project (*.rds *.json);;JSON (*.json);;All Files (*)"
        )
        if path:
            try:
                self.session.open_project(path)
            except Exception as exc:
                QMessageBox.critical(self, "Open project failed", str(exc))

    def open_project(self, path: str | Path):
        self.session.open_project(path)
        self.model_page.view.fit_view()

    def _save(self):
        if self.session.path is None:
            return self._save_as()
        try:
            self.session.save()
        except Exception as exc:
            QMessageBox.critical(self, "Save project failed", str(exc))

    def _save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save RotorStudio Project", "",
            "RotorStudio Project (*.rds);;JSON (*.json)"
        )
        if path:
            if not Path(path).suffix:
                path += ".rds"
            try:
                self.session.save(path)
            except Exception as exc:
                QMessageBox.critical(self, "Save project failed", str(exc))

    def _refresh_title(self):
        name = self.session.path.name if self.session.path else self.session.project.name
        mark = "*" if self.session.dirty else ""
        self.setWindowTitle(f"Rotor Dynamics Studio — {name}{mark}")

    def _refresh_status(self):
        model = self.session.project.model
        bearings = sum(1 for bearing in model.bearings if bearing.bearing_type != 8)
        self.status_counts.setText(
            f"Nodes: {len(model.nodes)}   Elements: {len(model.shafts)}   "
            f"Disks: {len(model.disks)}   Bearings: {bearings}"
        )

    def _restore_settings(self):
        settings = QSettings()
        geometry = settings.value("main/geometry")
        state = settings.value("main/state")
        if geometry is not None:
            self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state)

    def closeEvent(self, event):
        settings = QSettings()
        settings.setValue("main/geometry", self.saveGeometry())
        settings.setValue("main/state", self.saveState())
        super().closeEvent(event)
