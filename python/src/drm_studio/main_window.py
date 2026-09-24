from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QToolBar, QStyle, QTabWidget, QLabel, QDialog
)

from drm_core import AnalysisService
from drm_core.analysis.modal import ModalResult
from drm_core.validation.model import validate_model, ModelValidationError

from .application import ProjectSession, SolverJobManager
from .analysis_pages import ModalSetupDialog
from .docks import MessagesDock, ProjectExplorerDock, PropertyInspectorDock
from .result_views import ModalResultView
from .widgets import RotorModelPage
from .style import APP_STYLESHEET


class MainWindow(QMainWindow):
    def __init__(
        self,
        session: ProjectSession | None = None,
        analysis_service: AnalysisService | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.session = session or ProjectSession(parent=self)
        self.analysis_service = analysis_service or AnalysisService()
        self.jobs = SolverJobManager(self.analysis_service, self)
        self._result_tabs = {}

        self.setObjectName("RotorDynamicsStudioMainWindow")
        self.resize(1400, 900)
        self.setStyleSheet(APP_STYLESHEET)
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_shell()
        self._connect_session()
        self._connect_jobs()
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

        self.modal_action = QAction(
            self._std_icon(QStyle.SP_MediaPlay),
            "Modal / Characteristic Roots",
            self,
        )

        self.new_action.triggered.connect(self.session.new_project)
        self.open_action.triggered.connect(self._choose_open)
        self.save_action.triggered.connect(self._save)
        self.save_as_action.triggered.connect(self._save_as)
        self.exit_action.triggered.connect(self.close)
        self.modal_action.triggered.connect(self._configure_modal)

    def _build_menus(self):
        bar = self.menuBar()
        project = bar.addMenu("Project")
        project.addActions([self.new_action, self.open_action, self.save_action, self.save_as_action])
        project.addSeparator()
        project.addAction(self.exit_action)

        model = bar.addMenu("Model")
        model.addActions([self.undo_action, self.redo_action])

        self.analysis_menu = bar.addMenu("Analysis")
        self.analysis_menu.addAction(self.modal_action)
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
        toolbar.addSeparator()
        toolbar.addAction(self.modal_action)

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

        self.status_job = QLabel("Ready")
        self.status_units = QLabel("Units: SI (mm, N, kg)")
        self.status_counts = QLabel("")
        self.statusBar().addWidget(self.status_job, 1)
        self.statusBar().addPermanentWidget(self.status_units)
        self.statusBar().addPermanentWidget(self.status_counts)

        self.model_page.modalRequested.connect(self._configure_modal)

    def _connect_session(self):
        self.session.projectChanged.connect(self._refresh_title)
        self.session.modelChanged.connect(self._refresh_status)
        self.session.pathChanged.connect(lambda _: self._refresh_title())
        self.session.dirtyChanged.connect(lambda _: self._refresh_title())
        self.session.resultsChanged.connect(self._refresh_result_tabs)

    def _connect_jobs(self):
        self.jobs.jobStateChanged.connect(self._job_state_changed)
        self.jobs.completed.connect(self._job_completed)
        self.jobs.failed.connect(self._job_failed)

    def _choose_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open RotorStudio Project", "",
            "RotorStudio Project (*.rds *.json);;JSON (*.json);;All Files (*)"
        )
        if path:
            try:
                self.open_project(path)
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

    def save_project(self, path: str | Path | None = None):
        return self.session.save(path)

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

    def _configure_modal(self):
        existing = next(
            (case for case in self.session.project.analyses if case.kind == "modal"),
            None,
        )
        dialog = ModalSetupDialog(existing, self)
        if dialog.exec() == QDialog.Accepted:
            self.run_analysis(dialog.analysis_case())

    def run_analysis(self, case) -> bool:
        analysis_family = (
            "coaxial" if case.kind.startswith("coaxial_")
            else "rotating" if case.kind.startswith("asymmetric_")
            else "stationary"
        )
        try:
            validate_model(self.session.project.model, analysis=analysis_family)
        except ModelValidationError as exc:
            self.messages_dock.set_checks([f"FAIL — {exc}"])
            self.session.log("ERROR", str(exc))
            return False

        self.messages_dock.set_checks(["PASS — model validation"])
        self.session.upsert_analysis_case(case)
        self.session.log("INFO", f"Starting {case.kind}: {case.name or case.kind}")
        self.jobs.submit(self.session.project, case)
        return True

    def _job_state_changed(self, state, case):
        label = case.name or case.kind
        self.status_job.setText(f"{state.title()}: {label}")
        if state in ("QUEUED", "RUNNING"):
            self.session.log("INFO", f"{state}: {label}")

    def _job_completed(self, outcome):
        record = self.session.add_result(
            outcome.execution,
            model_snapshot=outcome.model_snapshot,
        )
        self.status_job.setText("Ready")
        self._show_result(record)

    def _job_failed(self, message, trace, case):
        label = case.name or case.kind
        self.status_job.setText(f"Failed: {label}")
        self.session.log("ERROR", f"{label}: {message}")
        for line in trace.rstrip().splitlines():
            self.messages_dock.append_log("TRACE", line)

    def _show_result(self, record):
        result = record.execution.result
        if isinstance(result, ModalResult):
            view = ModalResultView(record)
            old = self._result_tabs.get(record.key)
            if old is not None:
                idx = self.workspace.indexOf(old)
                if idx >= 0:
                    self.workspace.removeTab(idx)
                old.deleteLater()
            self._result_tabs[record.key] = view
            idx = self.workspace.addTab(view, self._result_tab_label(record))
            self.workspace.setCurrentIndex(idx)

    def _result_tab_label(self, record):
        label = record.execution.case.name or record.execution.case.kind
        return f"Modal — {label}" + (" ⚠" if record.stale else "")

    def _refresh_result_tabs(self):
        for key, view in list(self._result_tabs.items()):
            record = self.session.results.get(key)
            if record is None:
                continue
            idx = self.workspace.indexOf(view)
            if idx >= 0:
                self.workspace.setTabText(idx, self._result_tab_label(record))
            view.record = record
            view.refresh_stale()

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
