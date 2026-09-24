from __future__ import annotations

import copy
from dataclasses import replace

from PySide6.QtGui import QUndoCommand

from drm_core.validation.model import validate_model


class SetShaftPropertyCommand(QUndoCommand):
    """Undoable, pre-validated replacement of one frozen shaft dataclass."""

    def __init__(self, session, shaft_index: int, attribute: str, new_value, text: str | None = None):
        self.session = session
        self.shaft_index = int(shaft_index)
        self.attribute = attribute
        old = session.project.model.shafts[self.shaft_index]
        if not hasattr(old, attribute):
            raise AttributeError(f"{type(old).__name__} has no field {attribute!r}")
        self.old_value = getattr(old, attribute)
        self.new_shaft = replace(old, **{attribute: new_value})

        candidate = copy.deepcopy(session.project.model)
        candidate.shafts[self.shaft_index] = self.new_shaft
        validate_model(candidate, analysis="stationary")

        super().__init__(text or f"Set shaft {self.shaft_index + 1} {attribute}")

    def _assign(self, shaft):
        self.session.project.model.shafts[self.shaft_index] = shaft
        self.session.notify_model_changed()

    def redo(self):
        self._assign(self.new_shaft)

    def undo(self):
        old = self.session.project.model.shafts[self.shaft_index]
        self._assign(replace(old, **{self.attribute: self.old_value}))
