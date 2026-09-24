from __future__ import annotations

from PySide6.QtWidgets import QDockWidget, QTreeView

from drm_studio.models.project_tree import ProjectTreeModel


class ProjectExplorerDock(QDockWidget):
    def __init__(self, session, parent=None):
        super().__init__("Project Explorer", parent)
        self.setObjectName("ProjectExplorerDock")
        self.session = session
        self.tree = QTreeView()
        self.tree.setAlternatingRowColors(True)
        self.tree.setHeaderHidden(True)
        self.model = ProjectTreeModel(session, self.tree)
        self.tree.setModel(self.model)
        self.tree.expandToDepth(2)
        self.setWidget(self.tree)

        self.tree.selectionModel().currentChanged.connect(self._tree_current_changed)
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
