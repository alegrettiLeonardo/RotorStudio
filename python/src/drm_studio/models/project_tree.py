from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt

from drm_studio.application.session import EntityRef
from drm_studio.resources import studio_icon


@dataclass
class _TreeNode:
    label: str
    ref: EntityRef | None = None
    icon_name: str | None = None
    parent: "_TreeNode | None" = None
    children: list["_TreeNode"] = field(default_factory=list)

    def add(self, label: str, ref: EntityRef | None = None, icon_name: str | None = None) -> "_TreeNode":
        child = _TreeNode(label, ref, icon_name, self)
        self.children.append(child)
        return child

    @property
    def row(self) -> int:
        return 0 if self.parent is None else self.parent.children.index(self)


class ProjectTreeModel(QAbstractItemModel):
    EntityRole = Qt.UserRole + 1

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.root = _TreeNode("root")
        self._ref_to_node: dict[EntityRef, _TreeNode] = {}
        session.projectChanged.connect(self.rebuild)
        session.modelChanged.connect(self.rebuild)
        session.resultsChanged.connect(self.rebuild)
        self.rebuild()

    def rebuild(self):
        self.beginResetModel()
        self.root = _TreeNode("root")
        self._ref_to_node = {}
        p = self.session.project
        project = self.root.add(p.name or "Rotor Project", icon_name="open")

        m = p.model
        model = project.add("Model", icon_name="model")
        nodes = model.add(f"Nodes ({len(m.nodes)})", icon_name="model")
        for i, n in enumerate(m.nodes):
            self._add_ref(nodes, f"Node {n.number}", EntityRef("node", i), "model")

        shafts = model.add(f"Shaft Elements ({len(m.shafts)})", icon_name="coaxial")
        for i, s in enumerate(m.shafts):
            self._add_ref(shafts, f"Shaft Element {i + 1}  ({s.node1}–{s.node2})", EntityRef("shaft", i), "coaxial")

        disks = model.add(f"Disks ({len(m.disks)})", icon_name="critical")
        for i, d in enumerate(m.disks):
            self._add_ref(disks, f"Disk {i + 1}  (Node {d.node})", EntityRef("disk", i), "critical")

        bearing_indices = [i for i, b in enumerate(m.bearings) if b.bearing_type != 8]
        seal_indices = [i for i, b in enumerate(m.bearings) if b.bearing_type == 8]
        bearings = model.add(f"Bearings ({len(bearing_indices)})", icon_name="bearing")
        for j, i in enumerate(bearing_indices, 1):
            b = m.bearings[i]
            self._add_ref(bearings, f"Bearing {j}  (Type {b.bearing_type}, Node {b.node})", EntityRef("bearing", i), "bearing")

        seals = model.add(f"Seals ({len(seal_indices)})", icon_name="seal")
        for j, i in enumerate(seal_indices, 1):
            b = m.bearings[i]
            self._add_ref(seals, f"Seal {j}  (Node {b.node})", EntityRef("bearing", i), "seal")

        forces = model.add(f"Forces ({len(m.forces)})", icon_name="synchronous")
        for i, force in enumerate(m.forces):
            self._add_ref(forces, f"Force {i + 1}  (Type {force.force_type})", EntityRef("force", i), "synchronous")
        model.add("Constraints (0)", icon_name="foundation")

        rotors = model.add(f"Rotor Definitions ({len(m.rotors)})", icon_name="coaxial")
        for i, rotor in enumerate(m.rotors):
            self._add_ref(
                rotors,
                f"Rotor {i + 1}  ({rotor.node1}–{rotor.node2}, ×{rotor.speed_factor:g})",
                EntityRef("rotor", i),
                "coaxial",
            )

        sketch = dict(p.metadata.get("sketch") or {})
        if sketch:
            imported = model.add("Imported Engineering Sketch", icon_name="model")
            imported.add(f"Distributed Masses ({len(sketch.get('masses') or [])})", icon_name="critical")
            imported.add(f"Legacy Bearings ({len(sketch.get('bearings') or [])})", icon_name="bearing")
            imported.add(f"Unbalance Locations ({len(sketch.get('unbalance') or [])})", icon_name="synchronous")
            imported.add(f"Response Probes ({len(sketch.get('probes') or [])})", icon_name="frequency")
            imported.add(f"Supports ({len(sketch.get('supports') or [])})", icon_name="foundation")

        analysis = project.add("Analysis", icon_name="analysis")
        cases = analysis.add(f"Cases ({len(p.analyses)})", icon_name="report")
        for i, case in enumerate(p.analyses):
            name = case.name or case.kind
            self._add_ref(cases, f"{name}  [{case.kind}]", EntityRef("analysis", i), "analysis")
        for label, icon_name in (
            ("Modal / Characteristic Roots", "modal"),
            ("Campbell Diagram", "campbell"),
            ("Critical Speeds", "critical"),
            ("Synchronous Response", "synchronous"),
            ("Frequency Response", "frequency"),
            ("Foundation Excitation", "foundation"),
            ("Time Response", "frequency"),
            ("Run-up / Run-down", "runup"),
            ("Coaxial Rotor", "coaxial"),
            ("Asymmetric Rotor", "asymmetric"),
        ):
            analysis.add(label, icon_name=icon_name)

        results = project.add("Results", icon_name="results")
        for i, record in enumerate(self.session.results.values()):
            self._add_ref(results, record.display_name, EntityRef("result", i), "results")

        self.endResetModel()

    def _add_ref(self, parent: _TreeNode, label: str, ref: EntityRef, icon_name: str | None = None):
        node = parent.add(label, ref, icon_name)
        self._ref_to_node[ref] = node

    def columnCount(self, parent=QModelIndex()):
        return 1

    def rowCount(self, parent=QModelIndex()):
        node = parent.internalPointer() if parent.isValid() else self.root
        return len(node.children)

    def index(self, row, column, parent=QModelIndex()):
        if column != 0 or row < 0:
            return QModelIndex()
        node = parent.internalPointer() if parent.isValid() else self.root
        if row >= len(node.children):
            return QModelIndex()
        return self.createIndex(row, column, node.children[row])

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        parent = node.parent
        if parent is None or parent is self.root:
            return QModelIndex()
        return self.createIndex(parent.row, 0, parent)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if role == Qt.DisplayRole:
            return node.label
        if role == Qt.DecorationRole and node.icon_name:
            return studio_icon(node.icon_name)
        if role == self.EntityRole:
            return node.ref
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def index_for_ref(self, ref: EntityRef | None) -> QModelIndex:
        node = self._ref_to_node.get(ref)
        return QModelIndex() if node is None else self.createIndex(node.row, 0, node)
