from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QSize
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QToolBar, QStyle, QTabWidget, QLabel,
    QDialog, QComboBox, QWidget
)

from drm_core import AnalysisService
from drm_core.analysis.modal import ModalResult
from drm_core.analysis.critical_speed import CriticalSpeedResult
from drm_core.analysis.frequency_response import FrequencyResponseResult
from drm_core.analysis.transient import TransientResult
from drm_core.analysis.coaxial import CoaxialModalResult, CoaxialFrequencyResponseResult
from drm_core.analysis.asymmetric import AsymmetricModalResult, AsymmetricFrequencyResponseResult
from drm_core.validation.model import validate_model, ModelValidationError

from .application import ProjectSession, SolverJobManager
from .analysis_pages import (
    ModalSetupDialog, CampbellSetupDialog, CriticalSpeedSetupDialog,
    SynchronousResponseSetupDialog, FrequencyResponseSetupDialog,
    FoundationTimeSetupDialog, RunupSetupDialog, SpecialRotorSetupDialog,
)
from .docks import MessagesDock, ProjectExplorerDock, PropertyInspectorDock
from .result_views import (
    ModalResultView, CampbellResultView, CriticalSpeedResultView,
    FrequencyResponseResultView, TransientResultView, SpecialRotorResultView,
)
from .widgets import RotorModelPage, BearingPerformancePage
from .style import APP_STYLESHEET
from .resources import studio_icon
from .commands import ReplaceRotorDefinitionsCommand
from .result_views.io import (
    export_record_csv, export_record_native, export_record_report,
    export_view_plot_bundle, view_figure,
)


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
        self.setWindowIcon(studio_icon("model"))
        self.resize(1440, 900)
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
        self.new_action = QAction(studio_icon("new"), "New", self)
        self.open_action = QAction(studio_icon("open"), "Open", self)
        self.save_action = QAction(studio_icon("save"), "Save", self)
        self.save_as_action = QAction("Save As…", self)
        self.exit_action = QAction("Exit", self)
        self.undo_action = self.session.undo_stack.createUndoAction(self, "Undo")
        self.redo_action = self.session.undo_stack.createRedoAction(self, "Redo")
        self.undo_action.setShortcut(QKeySequence.Undo)
        self.redo_action.setShortcut(QKeySequence.Redo)

        self.modal_action = QAction(studio_icon("modal"), "Modal / Characteristic Roots", self)
        self.campbell_action = QAction(studio_icon("campbell"), "Campbell Diagram", self)
        self.critical_action = QAction(studio_icon("critical"), "Critical Speeds", self)
        self.synchronous_action = QAction(studio_icon("synchronous"), "Synchronous Response", self)
        self.frequency_action = QAction(studio_icon("frequency"), "Frequency Response", self)
        self.foundation_action = QAction(studio_icon("foundation"), "Foundation Excitation", self)
        self.foundation_time_action = QAction(studio_icon("foundation"), "Foundation Time Response", self)
        self.runup_action = QAction(studio_icon("runup"), "Run-up / Run-down", self)
        self.coaxial_action = QAction(studio_icon("coaxial"), "Coaxial Rotor", self)
        self.asymmetric_action = QAction(studio_icon("asymmetric"), "Asymmetric Rotor", self)
        self.bearing_performance_action = QAction(studio_icon("bearing"), "Bearing Performance", self)
        self.cancel_action = QAction(studio_icon("cancel"), "Cancel Analysis", self)
        self.cancel_action.setEnabled(False)
        self.rerun_result_action = QAction(studio_icon("repeat"), "Rerun Current Result", self)
        self.remove_result_action = QAction(studio_icon("delete"), "Remove Current Result", self)
        self.export_plot_action = QAction(studio_icon("export"), "Export Plot Bundle (PNG/SVG/PDF)…", self)
        self.export_csv_action = QAction(studio_icon("export"), "Export Data CSV…", self)
        self.export_native_action = QAction(studio_icon("export"), "Export Native NPZ…", self)
        self.report_action = QAction(studio_icon("report"), "Generate Analysis Report…", self)

        # Mockup command-strip actions. They delegate to existing qualified UI paths.
        self.model_toolbar_action = QAction(studio_icon("model"), "Model", self)
        self.analysis_toolbar_action = QAction(studio_icon("analysis"), "Analysis", self)
        self.results_toolbar_action = QAction(studio_icon("results"), "Results", self)
        self.repeat_toolbar_action = QAction(studio_icon("repeat"), "Repeat", self)
        self.zoom_in_toolbar_action = QAction(studio_icon("zoom_in"), "Zoom In", self)
        self.zoom_out_toolbar_action = QAction(studio_icon("zoom_out"), "Zoom Out", self)
        self.fit_toolbar_action = QAction(studio_icon("fit"), "Fit View", self)
        self.pan_toolbar_action = QAction(studio_icon("pan"), "Pan", self)
        self.pan_toolbar_action.setCheckable(True)
        self.help_toolbar_action = QAction(studio_icon("help"), "Help", self)

        self.new_action.triggered.connect(self.session.new_project)
        self.open_action.triggered.connect(self._choose_open)
        self.save_action.triggered.connect(self._save)
        self.save_as_action.triggered.connect(self._save_as)
        self.exit_action.triggered.connect(self.close)
        self.modal_action.triggered.connect(self._configure_modal)
        self.campbell_action.triggered.connect(self._configure_campbell)
        self.critical_action.triggered.connect(self._configure_critical)
        self.synchronous_action.triggered.connect(self._configure_synchronous)
        self.frequency_action.triggered.connect(self._configure_frequency_response)
        self.foundation_action.triggered.connect(self._configure_foundation_response)
        self.foundation_time_action.triggered.connect(self._configure_foundation_time)
        self.runup_action.triggered.connect(self._configure_runup)
        self.coaxial_action.triggered.connect(self._configure_coaxial)
        self.asymmetric_action.triggered.connect(self._configure_asymmetric)
        self.bearing_performance_action.triggered.connect(self._open_bearing_performance)
        self.cancel_action.triggered.connect(self.jobs.cancel_current)
        self.model_toolbar_action.triggered.connect(self._show_model_workspace)
        self.analysis_toolbar_action.triggered.connect(self._configure_modal)
        self.results_toolbar_action.triggered.connect(self._show_latest_result)
        self.repeat_toolbar_action.triggered.connect(self._rerun_current_result)
        self.zoom_in_toolbar_action.triggered.connect(self._toolbar_zoom_in)
        self.zoom_out_toolbar_action.triggered.connect(self._toolbar_zoom_out)
        self.fit_toolbar_action.triggered.connect(self._toolbar_fit)
        self.pan_toolbar_action.toggled.connect(self._toolbar_pan_toggled)
        self.help_toolbar_action.triggered.connect(self._show_help)
        self.rerun_result_action.triggered.connect(self._rerun_current_result)
        self.remove_result_action.triggered.connect(self._remove_current_result)
        self.export_plot_action.triggered.connect(self._export_current_plot)
        self.export_csv_action.triggered.connect(self._export_current_csv)
        self.export_native_action.triggered.connect(self._export_current_native)
        self.report_action.triggered.connect(self._report_current_result)

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
        self.analysis_menu.addAction(self.campbell_action)
        self.analysis_menu.addAction(self.critical_action)
        self.analysis_menu.addSeparator()
        self.analysis_menu.addAction(self.synchronous_action)
        self.analysis_menu.addAction(self.frequency_action)
        self.analysis_menu.addAction(self.foundation_action)
        self.analysis_menu.addAction(self.foundation_time_action)
        self.analysis_menu.addAction(self.runup_action)
        self.analysis_menu.addSeparator()
        self.analysis_menu.addAction(self.coaxial_action)
        self.analysis_menu.addAction(self.asymmetric_action)
        self.analysis_menu.addSeparator()
        self.analysis_menu.addAction(self.cancel_action)
        self.bearings_menu = bar.addMenu("Bearings")
        self.bearings_menu.addAction(self.bearing_performance_action)
        self.results_menu = bar.addMenu("Results")
        self.results_menu.addActions([self.rerun_result_action, self.remove_result_action])
        self.results_menu.addSeparator()
        self.results_menu.addActions([
            self.export_plot_action, self.export_csv_action,
            self.export_native_action, self.report_action,
        ])
        self.results_menu.aboutToShow.connect(self._refresh_result_actions)
        bar.addMenu("Tools")
        bar.addMenu("Help")

    def _build_toolbar(self):
        toolbar = QToolBar("Main", self)
        toolbar.setObjectName("MainToolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(toolbar)

        toolbar.addActions([self.new_action, self.open_action, self.save_action])
        toolbar.addSeparator()
        toolbar.addActions([
            self.model_toolbar_action,
            self.analysis_toolbar_action,
            self.results_toolbar_action,
            self.repeat_toolbar_action,
            self.report_action,
        ])
        toolbar.addSeparator()
        toolbar.addActions([
            self.zoom_in_toolbar_action,
            self.zoom_out_toolbar_action,
            self.fit_toolbar_action,
            self.pan_toolbar_action,
        ])
        toolbar.addSeparator()

        units_label = QLabel("Units")
        units_label.setStyleSheet("padding-left:5px;padding-right:2px;")
        toolbar.addWidget(units_label)
        self.units_combo = QComboBox()
        self.units_combo.addItem("SI (mm, N, kg)")
        self.units_combo.setToolTip(
            "Stage 2.1 preserves the qualified SI-domain model; this is the current display-unit preset."
        )
        toolbar.addWidget(self.units_combo)
        toolbar.addSeparator()
        toolbar.addAction(self.help_toolbar_action)

    def _build_shell(self):
        self.workspace = QTabWidget()
        self.workspace.setDocumentMode(True)
        self.workspace.setMovable(True)
        self.model_page = RotorModelPage(self.session)
        self.workspace.addTab(self.model_page, studio_icon("model"), "Rotor Model")
        self.bearing_page = BearingPerformancePage(self.session)
        self.workspace.addTab(self.bearing_page, studio_icon("bearing"), "Bearing Performance")
        self.plus_page = QWidget()
        plus_index = self.workspace.addTab(self.plus_page, "+")
        self.workspace.setTabEnabled(plus_index, False)
        self.setCentralWidget(self.workspace)

        self.project_dock = ProjectExplorerDock(self.session, self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.project_dock)

        self.property_dock = PropertyInspectorDock(self.session, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.property_dock)

        self.messages_dock = MessagesDock(self.session, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.messages_dock)

        # Initial CAE proportions from the visual authority. QSettings may
        # subsequently restore a user's customized layout.
        self.project_dock.setMinimumWidth(245)
        self.property_dock.setMinimumWidth(335)
        self.messages_dock.setMinimumHeight(145)
        self.resizeDocks([self.project_dock, self.property_dock], [260, 360], Qt.Horizontal)
        self.resizeDocks([self.messages_dock], [175], Qt.Vertical)

        self.status_job = QLabel("Ready")
        self.status_units = QLabel("Units: SI (mm, N, kg)")
        self.status_counts = QLabel("")
        self.statusBar().addWidget(self.status_job, 1)
        self.statusBar().addPermanentWidget(self.status_units)
        self.statusBar().addPermanentWidget(self.status_counts)

        self.model_page.modalRequested.connect(self._configure_modal)
        self.model_page.campbellRequested.connect(self._configure_campbell)
        self.model_page.criticalRequested.connect(self._configure_critical)
        self.model_page.synchronousRequested.connect(self._configure_synchronous)
        self.model_page.frequencyRequested.connect(self._configure_frequency_response)
        self.model_page.foundationRequested.connect(self._configure_foundation_response)
        self.model_page.runupRequested.connect(self._configure_runup)
        self.model_page.coaxialRequested.connect(self._configure_coaxial)
        self.model_page.asymmetricRequested.connect(self._configure_asymmetric)
        self.model_page.bearingRequested.connect(self._open_bearing_performance)

        self.property_dock.exportPlotRequested.connect(self._export_current_plot)
        self.property_dock.exportCsvRequested.connect(self._export_current_csv)
        self.property_dock.reportRequested.connect(self._report_current_result)
        self.property_dock.rerunRequested.connect(self._rerun_current_result)

    def _connect_session(self):
        self.session.projectChanged.connect(self._refresh_title)
        self.session.modelChanged.connect(self._refresh_status)
        self.session.pathChanged.connect(lambda _: self._refresh_title())
        self.session.dirtyChanged.connect(lambda _: self._refresh_title())
        self.session.resultsChanged.connect(self._refresh_result_tabs)
        self.session.selectionChanged.connect(self._navigate_result_selection)
        self.session.selectionChanged.connect(
            lambda _ref: self._workspace_changed(self.workspace.currentIndex())
        )
        self.workspace.currentChanged.connect(self._workspace_changed)

    def _workspace_changed(self, _index):
        self._refresh_result_actions()
        if self.workspace.currentWidget() is self.bearing_page:
            self.property_dock.show_bearing_context()
            return
        _, record, _ = self._current_result()
        if record is not None:
            self.property_dock.show_result_context(record)
        else:
            self.property_dock.show_entity_context()

    def _show_model_workspace(self):
        self.workspace.setCurrentWidget(self.model_page)

    def _show_latest_result(self):
        if not self._result_tabs:
            return
        view = list(self._result_tabs.values())[-1]
        self.workspace.setCurrentWidget(view)

    def _open_bearing_performance(self):
        self.workspace.setCurrentWidget(self.bearing_page)
        ref = self.session.selection
        if ref is not None and ref.kind == "bearing":
            self.property_dock.tabs.setCurrentWidget(self.property_dock.bearing_tab)

    def _toolbar_zoom_in(self):
        if self.workspace.currentWidget() is self.model_page:
            self.model_page.view.zoom_in()

    def _toolbar_zoom_out(self):
        if self.workspace.currentWidget() is self.model_page:
            self.model_page.view.zoom_out()

    def _toolbar_fit(self):
        if self.workspace.currentWidget() is self.model_page:
            self.model_page.view.fit_view()

    def _toolbar_pan_toggled(self, checked):
        self.model_page.view.set_pan_mode(bool(checked))

    def _show_help(self):
        QMessageBox.information(
            self,
            "Rotor Dynamics Studio",
            "Stage 2.1 Visual Conformance\n\n"
            "Use Project Explorer to select model entities, Analysis to run the "
            "qualified Fortran-backed solvers, and Results to navigate generated workspaces."
        )

    def _connect_jobs(self):
        self.jobs.jobStateChanged.connect(self._job_state_changed)
        self.jobs.progress.connect(self._job_progress)
        self.jobs.completed.connect(self._job_completed)
        self.jobs.cancelled.connect(self._job_cancelled)
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

    def _configure_campbell(self):
        existing = next(
            (case for case in self.session.project.analyses if case.kind == "modal_sweep"),
            None,
        )
        dialog = CampbellSetupDialog(existing, self)
        if dialog.exec() == QDialog.Accepted:
            self.run_analysis(dialog.analysis_case())

    def _configure_critical(self):
        dialog = CriticalSpeedSetupDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.run_analysis(dialog.analysis_case())

    def _configure_synchronous(self):
        dialog = SynchronousResponseSetupDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.run_analysis(dialog.analysis_case())

    def _configure_frequency_response(self):
        dialog = FrequencyResponseSetupDialog("auxiliary", self)
        if dialog.exec() == QDialog.Accepted:
            self.run_analysis(dialog.analysis_case())

    def _configure_foundation_response(self):
        dialog = FrequencyResponseSetupDialog("foundation", self)
        if dialog.exec() == QDialog.Accepted:
            self.run_analysis(dialog.analysis_case())

    def _configure_foundation_time(self):
        dialog = FoundationTimeSetupDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.run_analysis(dialog.analysis_case())

    def _configure_runup(self):
        dialog = RunupSetupDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.run_analysis(dialog.analysis_case())

    def _configure_coaxial(self):
        dialog = SpecialRotorSetupDialog("coaxial", self, self.session.project.model.rotors)
        if dialog.exec() == QDialog.Accepted:
            try:
                definitions = dialog.rotor_definitions()
                if definitions != self.session.project.model.rotors:
                    self.session.undo_stack.push(ReplaceRotorDefinitionsCommand(self.session, definitions))
                self.run_analysis(dialog.analysis_case())
            except (ValueError, ModelValidationError) as exc:
                self.messages_dock.set_checks(["FAIL — " + str(exc)])
                self.session.log("ERROR", str(exc))

    def _configure_asymmetric(self):
        dialog = SpecialRotorSetupDialog("asymmetric", self)
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
            force_types = {force.force_type for force in self.session.project.model.forces}
            required = {
                "frequency_response": ({1, 2, 3}, "mass/couple unbalance or bent-shaft Force type 1, 2, or 3"),
                "auxiliary_frequency_response": ({6, 7}, "spinner or auxiliary-bearing Force type 6 or 7"),
                "foundation_frequency_response": ({4}, "foundation frequency-domain Force type 4"),
                "foundation_time_response": ({5}, "foundation pulse Force type 5"),
            }
            if case.kind in required:
                accepted, description = required[case.kind]
                if not (force_types & accepted):
                    raise ModelValidationError(
                        f"{case.kind}: model has force types {sorted(force_types)}; "
                        f"expected {description}; add the required forcing before analysis"
                    )
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
        self.cancel_action.setEnabled(state in ("QUEUED", "RUNNING"))
        if state in ("QUEUED", "RUNNING", "CANCELLING", "CANCELLED"):
            self.session.log("INFO", f"{state}: {label}")

    def _job_progress(self, case, current, total):
        label = case.name or case.kind
        self.status_job.setText(f"Running: {label} — {current}/{total}")
        self.session.log("INFO", f"{label}: safe sweep point {current}/{total}")

    def _job_cancelled(self, case, reason):
        label = case.name or case.kind
        self.cancel_action.setEnabled(False)
        self.status_job.setText(f"Cancelled: {label}")
        self.session.log("INFO", f"CANCELLED: {label} — {reason}")

    def _job_completed(self, outcome):
        record = self.session.add_result(
            outcome.execution,
            model_snapshot=outcome.model_snapshot,
        )
        self.cancel_action.setEnabled(False)
        self.status_job.setText("Ready")
        if outcome.cancellation_deferred:
            self.session.log(
                "WARNING",
                "Cancellation was requested during a monolithic solver call. "
                "The call was allowed to return safely and the real completed result is retained."
            )
        self._show_result(record)

    def _job_failed(self, failure):
        label = failure.case.name or failure.case.kind
        self.cancel_action.setEnabled(False)
        self.status_job.setText(f"Failed: {label}")
        self.messages_dock.set_checks([
            f"FAIL — analysis: {label}",
            f"solver status: {failure.status}",
            f"{failure.exception_type}: {failure.message}",
            f"action: {failure.guidance}",
        ])
        self.session.log("ERROR", f"{label}: {failure.exception_type}: {failure.message}")
        self.session.log("ERROR", f"Suggested action: {failure.guidance}")
        for line in failure.traceback.rstrip().splitlines():
            self.messages_dock.append_log("TRACE", line)

    def _show_result(self, record):
        result = record.execution.result
        view = None
        prefix = "Result"
        if isinstance(result, ModalResult):
            view = ModalResultView(record)
            prefix = "Modal"
        elif (
            isinstance(result, list)
            and result
            and all(isinstance(item, ModalResult) for item in result)
        ):
            view = CampbellResultView(record)
            prefix = "Campbell"
        elif isinstance(result, CriticalSpeedResult):
            view = CriticalSpeedResultView(record)
            prefix = "Critical Speeds"
        elif isinstance(result, FrequencyResponseResult):
            view = FrequencyResponseResultView(record)
            prefix = "Response"
        elif isinstance(result, TransientResult):
            view = TransientResultView(record)
            prefix = "Transient" if record.execution.case.kind != "runup" else "Run-up"
        elif isinstance(result, (CoaxialModalResult, CoaxialFrequencyResponseResult)):
            view = SpecialRotorResultView(record)
            prefix = "Coaxial"
        elif isinstance(result, (AsymmetricModalResult, AsymmetricFrequencyResponseResult)):
            view = SpecialRotorResultView(record)
            prefix = "Asymmetric"
        if view is None:
            return
        view._tab_prefix = prefix
        old = self._result_tabs.get(record.key)
        if old is not None:
            idx = self.workspace.indexOf(old)
            if idx >= 0:
                self.workspace.removeTab(idx)
            old.deleteLater()
        self._result_tabs[record.key] = view
        plus_index = self.workspace.indexOf(self.plus_page)
        insert_at = plus_index if plus_index >= 0 else self.workspace.count()
        idx = self.workspace.insertTab(insert_at, view, self._result_tab_label(record, view))
        self.workspace.setCurrentIndex(idx)

    def _result_tab_label(self, record, view=None):
        label = record.execution.case.name or record.execution.case.kind
        prefix = getattr(view, "_tab_prefix", "Result")
        return f"{prefix} — {label}" + (" ⚠" if record.stale else "")

    def _refresh_result_tabs(self):
        for key, view in list(self._result_tabs.items()):
            record = self.session.results.get(key)
            if record is None:
                continue
            idx = self.workspace.indexOf(view)
            if idx >= 0:
                self.workspace.setTabText(idx, self._result_tab_label(record, view))
            view.record = record
            view.refresh_stale()

    def _current_result(self):
        current = self.workspace.currentWidget()
        for key, view in self._result_tabs.items():
            if view is current:
                return key, self.session.results.get(key), view
        return None, None, None

    def _refresh_result_actions(self):
        _, record, view = self._current_result()
        enabled = record is not None
        for action in (
            self.rerun_result_action, self.remove_result_action,
            self.export_csv_action, self.export_native_action, self.report_action,
        ):
            action.setEnabled(enabled)
        self.export_plot_action.setEnabled(enabled and view_figure(view) is not None)

    def _navigate_result_selection(self, ref):
        if ref is None or ref.kind != "result":
            return
        records = list(self.session.results.values())
        if not (0 <= ref.index < len(records)):
            return
        view = self._result_tabs.get(records[ref.index].key)
        if view is not None:
            idx = self.workspace.indexOf(view)
            if idx >= 0:
                self.workspace.setCurrentIndex(idx)

    def _rerun_current_result(self):
        _, record, _ = self._current_result()
        if record is not None:
            self.run_analysis(record.execution.case)

    def _remove_current_result(self):
        key, record, view = self._current_result()
        if record is None:
            return
        idx = self.workspace.indexOf(view)
        if idx >= 0:
            self.workspace.removeTab(idx)
        self._result_tabs.pop(key, None)
        view.deleteLater()
        self.session.remove_result(key)

    def _export_current_plot(self):
        _, record, view = self._current_result()
        if record is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Plot Bundle", record.key + ".png", "PNG base (*.png)"
        )
        if not path:
            return
        try:
            written = export_view_plot_bundle(view, Path(path).with_suffix(""))
            self.session.log("INFO", "Plot exports: " + ", ".join(str(p) for p in written.values()))
        except Exception as exc:
            QMessageBox.critical(self, "Plot export failed", str(exc))

    def _export_current_csv(self):
        _, record, _ = self._current_result()
        if record is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Result Data", record.key + ".csv", "CSV (*.csv)"
        )
        if path:
            try:
                self.session.log("INFO", f"Data export: {export_record_csv(record, path)}")
            except Exception as exc:
                QMessageBox.critical(self, "Data export failed", str(exc))

    def _export_current_native(self):
        _, record, _ = self._current_result()
        if record is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Native Result", record.key + ".npz", "NumPy archive (*.npz)"
        )
        if path:
            try:
                self.session.log("INFO", f"Native export: {export_record_native(record, path)}")
            except Exception as exc:
                QMessageBox.critical(self, "Native export failed", str(exc))

    def _report_current_result(self):
        _, record, _ = self._current_result()
        if record is None:
            return
        outdir = QFileDialog.getExistingDirectory(self, "Analysis Report Output Directory")
        if outdir:
            try:
                written = export_record_report(record, outdir)
                self.session.log("INFO", "Report: " + ", ".join(str(p) for p in written.values()))
            except Exception as exc:
                QMessageBox.critical(self, "Report generation failed", str(exc))

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
