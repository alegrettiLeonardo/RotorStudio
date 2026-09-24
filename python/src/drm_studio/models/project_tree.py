from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt

from drm_studio.application.session import EntityRef


@dataclass
class _TreeNode:
    label: str
    ref: EntityRef | None = None
    parent: "_TreeNode | None" = None
    children: list["_TreeNode"] = field(default_factory=list)

    def add(self, label: str, ref: EntityRef | None = None) -> "_TreeNode":
        child = _TreeNode(label, ref, self)
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
        project = self.root.add(p.name or "Rotor Project")

        m = p.model
        model = project.add("Model")
        nodes = model.add(f"Nodes ({len(m.nodes)})")
        for i, n in enumerate(m.nodes):
            self._add_ref(nodes, f"Node {n.number}", EntityRef("node", i))

        shafts = model.add(f"Shaft Elements ({len(m.shafts)})")
        for i, s in enumerate(m.shafts):
            self._add_ref(shafts, f"Shaft Element {i + 1}  ({s.node1}–{s.node2})", EntityRef("shaft", i))

        disks = model.add(f"Disks ({len(m.disks)})")
        for i, d in enumerate(m.disks):
            self._add_ref(disks, f"Disk {i + 1}  (Node {d.node})", EntityRef("disk", i))

        bearing_indices = [i for i, b in enumerate(m.bearings) if b.bearing_type != 8]
        seal_indices = [i for i, b in enumerate(m.bearings) if b.bearing_type == 8]
        bearings = model.add(f"Bearings ({len(bearing_indices)})")
        for j, i in enumerate(bearing_indices, 1):
            b = m.bearings[i]
            self._add_ref(bearings, f"Bearing {j}  (Type {b.bearing_type}, Node {b.node})", EntityRef("bearing", i))

        seals = model.add(f"Seals ({len(seal_indices)})")
        for j, i in enumerate(seal_indices, 1):
            b = m.bearings[i]
            self._add_ref(seals, f"Seal {j}  (Node {b.node})", EntityRef("bearing", i))

        forces = model.add(f"Forces ({len(m.forces)})")
        for i, f in enumerate(m.forces):
            self._add_ref(forces, f"Force {i + 1}  (Type {f.force_type})", EntityRef("force", i))
        model.add("Constraints (0)")

        rotors = model.add(f"Rotor Definitions ({len(m.rotors)})")
        for i, r in enumerate(m.rotors):
            self._add_ref(rotors, f"Rotor {i + 1}  ({r.node1}–{r.node2}, ×{r.speed_factor:g})", EntityRef("rotor", i))

        analysis = project.add("Analysis")
        cases = analysis.add(f"Cases ({len(p.analyses)})")
        for i, c in enumerate(p.analyses):
            name = c.name or c.kind
            self._add_ref(cases, f"{name}  [{c.kind}]", EntityRef("analysis", i))
        for label in (
            "Modal / Characteristic Roots", "Campbell Diagram", "Critical Speeds",
            "Synchronous Response", "Frequency Response", "Foundation Excitation",
            "Time Response", "Run-up / Run-down", "Coaxial Rotor", "Asymmetric Rotor",
        ):
            analysis.add(label)

        results = project.add("Results")
        for record in self.session.results.values():
            results.add(record.display_name)

        self.endResetModel()

    def _add_ref(self, parent: _TreeNode, label: str, ref: EntityRef):
        node = parent.add(label, ref)
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
