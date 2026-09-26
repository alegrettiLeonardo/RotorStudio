from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDockWidget, QMenu, QMessageBox, QTreeView

from drm_studio.application.session import EntityRef
from drm_studio.commands.model_commands import (
    AddAdvancedBearingCommand,
    DeleteAdvancedBearingCommand,
    DuplicateAdvancedBearingCommand,
    EditAdvancedBearingCommand,
)
from drm_studio.docks.advanced_bearing_editor import (
    AdvancedBearingEditor,
    FAMILY_COEFFICIENT,
    FAMILY_PLAIN,
    FAMILY_TILTING,
    family_for_bearing,
)
from drm_studio.models.project_tree import ProjectTreeModel


class ProjectExplorerDock(QDockWidget):
    """Project tree with B13 engineering CRUD on the Advanced Bearings branch."""

    def __init__(self, session, parent=None):
        super().__init__("Project Explorer", parent)
        self.setObjectName("ProjectExplorerDock")
        self.session = session
        self.tree = QTreeView()
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.model = ProjectTreeModel(session, self.tree)
        self.tree.setModel(self.model)
        self.tree.expandToDepth(2)
        self.setWidget(self.tree)

        self.tree.selectionModel().currentChanged.connect(self._tree_current_changed)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.doubleClicked.connect(self._double_clicked)
        session.selectionChanged.connect(self._session_selection_changed)
        session.projectChanged.connect(lambda: self.tree.expandToDepth(2))

    def _tree_current_changed(self, current, previous):
        ref = self.model.data(current, ProjectTreeModel.EntityRole)
        if ref is not None:
            self.session.set_selection(ref)

    def _session_selection_changed(self, ref):
        idx = self.model.index_for_ref(ref)
        if idx.isValid() and idx != self.tree.currentIndex():
            self.tree.setCurrentIndex(idx)
            self.tree.scrollTo(idx)

    def _double_clicked(self, index):
        ref = self.model.data(index, ProjectTreeModel.EntityRole)
        if ref is not None and ref.kind == "advanced_bearing":
            if self._is_supported_index(ref.index):
                self.edit_advanced_bearing(ref.index)

    def _is_supported_index(self, index: int) -> bool:
        current = self.session.project.model.advanced_bearings
        if not (0 <= int(index) < len(current)):
            return False
        try:
            family_for_bearing(current[int(index)])
            return True
        except TypeError:
            return False

    def _show_context_menu(self, pos):
        index = self.tree.indexAt(pos)
        if not index.isValid():
            return
        context = self.model.data(index, ProjectTreeModel.ContextRole)
        ref = self.model.data(index, ProjectTreeModel.EntityRole)
        if context not in {"advanced_bearings_root", "advanced_bearing"}:
            return

        menu = QMenu(self.tree)
        if context == "advanced_bearings_root":
            menu.addAction(
                "New Coefficient Bearing…",
                lambda: self.create_advanced_bearing(FAMILY_COEFFICIENT),
            )
            menu.addAction(
                "New Plain Journal…",
                lambda: self.create_advanced_bearing(FAMILY_PLAIN),
            )
            menu.addAction(
                "New Tilting Pad…",
                lambda: self.create_advanced_bearing(FAMILY_TILTING),
            )
        elif ref is not None:
            self.tree.setCurrentIndex(index)
            self.session.set_selection(ref)
            supported = self._is_supported_index(ref.index)
            edit = menu.addAction("Edit…", lambda: self.edit_advanced_bearing(ref.index))
            duplicate = menu.addAction("Duplicate", lambda: self.duplicate_advanced_bearing(ref.index))
            delete = menu.addAction("Delete…", lambda: self.delete_advanced_bearing(ref.index))
            edit.setEnabled(supported)
            duplicate.setEnabled(supported)
            delete.setEnabled(supported)
            if not supported:
                menu.addSeparator()
                note = menu.addAction("B13 CRUD is limited to Coefficient / Plain Journal / Tilting Pad")
                note.setEnabled(False)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _require_nodes(self) -> bool:
        if self.session.project.model.nodes:
            return True
        QMessageBox.warning(
            self,
            "Advanced Bearing",
            "No RotorModel nodes exist. Create/import the rotor nodes before adding an advanced bearing.",
        )
        return False

    def create_advanced_bearing(self, family: str):
        if not self._require_nodes():
            return False
        try:
            editor = AdvancedBearingEditor(
                self.session.project.model,
                family=family,
                parent=self,
            )
        except (ValueError, TypeError) as exc:
            QMessageBox.critical(self, "Advanced Bearing", str(exc))
            return False
        if editor.exec() != QDialog.Accepted:
            return False
        try:
            bearing = editor.bearing()
            self.session.undo_stack.push(
                AddAdvancedBearingCommand(self.session, bearing)
            )
            self.session.log(
                "INFO",
                f"Advanced bearing created: {bearing.model_family} at node {bearing.node}",
            )
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Advanced Bearing validation failed", str(exc))
            return False

    def edit_advanced_bearing(self, index: int):
        current = self.session.project.model.advanced_bearings
        if not (0 <= int(index) < len(current)):
            return False
        bearing = current[int(index)]
        try:
            family_for_bearing(bearing)
            editor = AdvancedBearingEditor(
                self.session.project.model,
                bearing=bearing,
                parent=self,
            )
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, "Advanced Bearing", str(exc))
            return False
        if editor.exec() != QDialog.Accepted:
            return False
        try:
            new_bearing = editor.bearing()
            if new_bearing == bearing:
                return True
            self.session.undo_stack.push(
                EditAdvancedBearingCommand(self.session, int(index), new_bearing)
            )
            self.session.log(
                "INFO",
                f"Advanced bearing edited: {new_bearing.model_family} at node {new_bearing.node}",
            )
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Advanced Bearing validation failed", str(exc))
            return False

    def duplicate_advanced_bearing(self, index: int):
        if not self._is_supported_index(index):
            return False
        try:
            self.session.undo_stack.push(
                DuplicateAdvancedBearingCommand(self.session, int(index))
            )
            self.session.log("INFO", f"Advanced bearing {int(index) + 1} duplicated")
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Duplicate Advanced Bearing failed", str(exc))
            return False

    def delete_advanced_bearing(self, index: int, *, confirm: bool = True):
        current = self.session.project.model.advanced_bearings
        if not (0 <= int(index) < len(current)) or not self._is_supported_index(index):
            return False
        bearing = current[int(index)]
        family = getattr(bearing, "model_family", type(bearing).__name__)
        tag = getattr(bearing, "tag", "") or "(untagged)"
        if confirm:
            answer = QMessageBox.question(
                self,
                "Delete Advanced Bearing",
                f"Delete {family} / {tag} at node {bearing.node}?\n\n"
                "The operation is undoable.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False
        try:
            self.session.undo_stack.push(
                DeleteAdvancedBearingCommand(self.session, int(index))
            )
            self.session.log(
                "INFO",
                f"Advanced bearing deleted: {family} / {tag} / node {bearing.node}",
            )
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Delete Advanced Bearing failed", str(exc))
            return False
