"""Qt/Flet independent application state around the existing Core dataclasses."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
from typing import Callable
import os
import numpy as np
from drm_core import (RotorProject, RotorModel, Node, ShaftElement, Disk, Force,
                      CoefficientBearing, AnalysisCase, save_project, load_project, analysis_hash)
from drm_core.units import rpm_to_rad_s
from drm_core.validation.model import validate_model

COLLECTIONS = ("nodes", "shafts", "disks", "bearings", "advanced_bearings", "forces", "bend", "rotors")

@dataclass(frozen=True)
class EntityRef:
    kind: str
    index: int

@dataclass
class HistoryEntry:
    before: RotorProject
    after: RotorProject
    before_selection: EntityRef | None
    after_selection: EntityRef | None
    label: str


def reference_project() -> RotorProject:
    """Explicit synthetic input, not a precomputed/fake result or user machine."""
    positions = [0, .1, .2, .35, .5, .6, .8, 1, 1.2, 1.3, 1.45, 1.6, 1.8]
    diameters = [.04, .05, .065, .11, .10, .14, .14, .10, .09, .06, .055, .04]
    model = RotorModel(nodes=[Node(i + 1, z) for i, z in enumerate(positions)])
    model.shafts = [ShaftElement(2, i + 1, i + 2, d, 0, 7850, 210e9, 80.77e9)
                    for i, d in enumerate(diameters)]
    model.disks = [Disk.geometric(5, 7850, .055, .32, .11),
                   Disk.geometric(9, 7850, .055, .36, .10)]
    for node, tag in [(3, "A"), (11, "B")]:
        model.advanced_bearings.append(CoefficientBearing(
            node=node, tag=tag, speed_rad_s=tuple(rpm_to_rad_s([0, 1500, 3000, 6000])),
            kxx=(1e7, 1.12e7, 1.24e7, 1.48e7), kyy=(.9e7, 1e7, 1.1e7, 1.3e7),
            cxx=(1500, 1560, 1620, 1740), cyy=(1800, 1860, 1920, 2040),
            interpolation="linear", provenance={"source": "Flet reference input; synthetic, not measured"}))
    model.forces = [Force(1, (7, .001, 0.0))]
    project = RotorProject("Rotor de exemplo", model, metadata={
        "description": "Entrada sintética para explorar a interface. Resultados somente após cálculo real.",
        "source": "drm_flet.reference_project", "numerical_readiness": {"status": "READY"}})
    validate_model(model)
    return project


class StudioSession:
    """One authoritative project, transactional edits and snapshot-based undo/redo."""
    def __init__(self, project: RotorProject | None = None):
        self.project = deepcopy(project if project is not None else reference_project())
        self.path: Path | None = None
        self.selection: EntityRef | None = EntityRef("shafts", 5) if len(self.project.model.shafts) > 5 else None
        self.records = []
        self.history: list[HistoryEntry] = []
        self.cursor = 0
        self.saved_hash: str | None = None
        self.messages: list[tuple[str, str]] = []
        self.log("INFO", "Projeto aberto. Nenhum resultado é criado sem execução do núcleo.")

    @property
    def dirty(self) -> bool:
        return self.project.project_hash() != self.saved_hash

    @property
    def can_undo(self): return self.cursor > 0
    @property
    def can_redo(self): return self.cursor < len(self.history)

    def log(self, level: str, message: str):
        self.messages.append((level, str(message)))
        self.messages = self.messages[-300:]

    def selected(self):
        if not self.selection: return None
        values = getattr(self.project.model, self.selection.kind)
        return values[self.selection.index] if 0 <= self.selection.index < len(values) else None

    def select(self, ref: EntityRef | None):
        if ref is not None:
            if ref.kind not in COLLECTIONS or not 0 <= ref.index < len(getattr(self.project.model, ref.kind)):
                raise ValueError(f"Seleção inexistente: {ref}")
        self.selection = ref

    def transact(self, label: str, mutation: Callable[[RotorProject], None], *, selection=None,
                 validate: bool = True):
        candidate = deepcopy(self.project)
        mutation(candidate)
        if validate:
            from .editing import validate_editable_model
            validate_editable_model(candidate.model)
        after_sel = self.selection if selection is None else selection
        if candidate.project_hash() == self.project.project_hash(): return
        entry = HistoryEntry(deepcopy(self.project), deepcopy(candidate), self.selection, after_sel, label)
        self.history[self.cursor:] = [entry]
        if len(self.history) > 100: self.history.pop(0)
        self.cursor = len(self.history)
        self.project, self.selection = candidate, after_sel
        self.log("EDIÇÃO", label)

    def replace_entity(self, ref: EntityRef, value):
        if ref.kind not in COLLECTIONS: raise ValueError("Coleção inválida")
        def edit(p): getattr(p.model, ref.kind)[ref.index] = value
        self.transact(f"{ref.kind}[{ref.index + 1}] atualizado", edit, selection=ref)

    def add_entity(self, kind: str, value):
        if kind not in COLLECTIONS: raise ValueError("Coleção inválida")
        ref = EntityRef(kind, len(getattr(self.project.model, kind)))
        self.transact(f"Adicionar {kind}", lambda p: getattr(p.model, kind).append(value), selection=ref)
        return ref

    def remove_entity(self, ref: EntityRef):
        def edit(p): getattr(p.model, ref.kind).pop(ref.index)
        self.transact(f"Remover {ref.kind}[{ref.index + 1}]", edit)
        self.selection = None
        self.history[self.cursor - 1].after_selection = None

    def set_case(self, case: AnalysisCase):
        def edit(p):
            indices = [i for i, x in enumerate(p.analyses) if x.name == case.name]
            if indices: p.analyses[indices[0]] = case
            else: p.analyses.append(case)
        self.transact(f"Caso {case.name} configurado", edit, validate=False)

    def undo(self):
        if not self.can_undo: return
        self.cursor -= 1
        entry = self.history[self.cursor]
        self.project, self.selection = deepcopy(entry.before), entry.before_selection
        self.log("UNDO", entry.label)

    def redo(self):
        if not self.can_redo: return
        entry = self.history[self.cursor]
        self.project, self.selection = deepcopy(entry.after), entry.after_selection
        self.cursor += 1
        self.log("REDO", entry.label)

    def is_current(self, record) -> bool:
        if self.project.model.model_hash() != record.model.model_hash(): return False
        case = next((a for a in self.project.analyses if a.name == record.execution.case.name), record.execution.case)
        return record.execution.analysis_hash == analysis_hash(
            self.project.model, case, record.execution.build_metadata.get("options", {}))

    def save(self, path: str | Path):
        """Core format, atomic replacement; an unsuccessful save never marks clean."""
        path = Path(path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=path.parent, prefix=".rotorstudio-", suffix=".json", delete=False) as f:
            temporary = Path(f.name)
        try:
            save_project(self.project, temporary)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        self.path, self.saved_hash = path, self.project.project_hash()
        self.log("SALVO", str(path))

    def as_bytes(self) -> bytes:
        with TemporaryDirectory() as d:
            path = Path(d) / "project.json"
            save_project(self.project, path)
            return path.read_bytes()

    def open(self, path: str | Path):
        path = Path(path).expanduser().resolve()
        if path.suffix.lower() == ".txt":
            from drm_core import load_irdin_project
            project = load_irdin_project(path)
            self.reset(project)
            # Legacy import must be saved as a new Core project; never overwrite it.
            self.log("IMPORTADO", str(path))
        else:
            project = load_project(path)
            self.reset(project)
            self.path, self.saved_hash = path, self.project.project_hash()

    def open_bytes(self, contents: bytes, suffix=".json"):
        with TemporaryDirectory() as d:
            p = Path(d) / ("project" + suffix)
            p.write_bytes(contents)
            self.open(p)
        self.path = None

    def reset(self, project: RotorProject):
        self.project = deepcopy(project)
        self.selection = None
        self.history.clear(); self.cursor = 0; self.records.clear()
        self.path = None; self.saved_hash = None
        self.log("PROJETO", self.project.name)
