from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

from drm_core import RotorModel, RotorProject, AnalysisExecution, load_project, save_project


@dataclass(frozen=True)
class EntityRef:
    kind: str
    index: int


@dataclass
class ResultRecord:
    key: str
    execution: AnalysisExecution
    source_model_hash: str
    model_snapshot: Any | None = None
    stale: bool = False

    @property
    def display_name(self) -> str:
        label = self.execution.case.name or self.execution.case.kind
        return f"{label} ⚠ Outdated" if self.stale else label


class ProjectSession(QObject):
    """Single mutable application state for the desktop shell."""

    projectChanged = Signal()
    modelChanged = Signal()
    pathChanged = Signal(object)
    dirtyChanged = Signal(bool)
    selectionChanged = Signal(object)
    resultAdded = Signal(object)
    resultsChanged = Signal()
    logMessage = Signal(str, str)

    def __init__(self, project: RotorProject | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self.project = project or RotorProject("Untitled", RotorModel())
        self.path: Path | None = None
        self.dirty = False
        self.selection: EntityRef | None = None
        self.results: dict[str, ResultRecord] = {}
        self.undo_stack = QUndoStack(self)

    @property
    def current_model_hash(self) -> str:
        return self.project.model.model_hash()

    def set_project(self, project: RotorProject, path: str | Path | None = None) -> None:
        self.project = project
        self.path = Path(path) if path else None
        self.results.clear()
        self.selection = None
        self.undo_stack.clear()
        self._set_dirty(False)
        self.projectChanged.emit()
        self.modelChanged.emit()
        self.selectionChanged.emit(None)
        self.resultsChanged.emit()
        self.pathChanged.emit(self.path)
        self.log("INFO", f"Project loaded: {self.path or project.name}")

    def new_project(self) -> None:
        self.set_project(RotorProject("Untitled", RotorModel()))
        self.log("INFO", "New project created")

    def open_project(self, path: str | Path) -> None:
        p = Path(path)
        self.set_project(load_project(p), p)

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("project path is not set")
        save_project(self.project, target)
        self.path = target
        self._set_dirty(False)
        self.pathChanged.emit(self.path)
        self.log("INFO", f"Project saved: {target}")
        return target

    def upsert_analysis_case(self, case) -> int:
        for i, existing in enumerate(self.project.analyses):
            if existing.name == case.name and existing.kind == case.kind:
                if existing != case:
                    self.project.analyses[i] = case
                    self._set_dirty(True)
                    self.projectChanged.emit()
                return i
        self.project.analyses.append(case)
        self._set_dirty(True)
        self.projectChanged.emit()
        return len(self.project.analyses) - 1

    def set_selection(self, ref: EntityRef | None) -> None:
        if ref == self.selection:
            return
        self.selection = ref
        self.selectionChanged.emit(ref)

    def notify_model_changed(self) -> None:
        self._set_dirty(True)
        current = self.current_model_hash
        changed = False
        for record in self.results.values():
            new_stale = record.source_model_hash != current
            if new_stale != record.stale:
                record.stale = new_stale
                changed = True
        self.modelChanged.emit()
        self.projectChanged.emit()
        if changed:
            self.resultsChanged.emit()

    def add_result(self, execution: AnalysisExecution, model_snapshot=None) -> ResultRecord:
        key = execution.case.name or execution.case.kind
        source = str(execution.build_metadata.get("model_hash", self.current_model_hash))
        record = ResultRecord(
            key=key,
            execution=execution,
            source_model_hash=source,
            model_snapshot=model_snapshot,
            stale=source != self.current_model_hash,
        )
        self.results[key] = record
        self.resultAdded.emit(record)
        self.resultsChanged.emit()
        self.log("INFO", f"Analysis completed: {record.display_name}")
        return record

    def remove_result(self, key: str) -> bool:
        if key not in self.results:
            return False
        del self.results[key]
        self.resultsChanged.emit()
        self.log("INFO", f"Result removed: {key}")
        return True

    def _set_dirty(self, value: bool) -> None:
        value = bool(value)
        if value == self.dirty:
            return
        self.dirty = value
        self.dirtyChanged.emit(value)

    def log(self, level: str, message: str) -> None:
        self.logMessage.emit(level.upper(), message)
