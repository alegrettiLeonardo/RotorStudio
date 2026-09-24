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


class EditBearingPropertiesCommand(QUndoCommand):
    """Undoable replacement of the selected Stage 1 Bearing properties."""

    def __init__(self, session, bearing_index: int, new_properties, text: str | None = None):
        from drm_core.domain.model import Bearing
        self.session = session
        self.bearing_index = int(bearing_index)
        self.old_bearing = session.project.model.bearings[self.bearing_index]
        self.new_bearing = Bearing(
            self.old_bearing.bearing_type,
            self.old_bearing.node,
            tuple(float(x) for x in new_properties),
        )
        candidate = copy.deepcopy(session.project.model)
        candidate.bearings[self.bearing_index] = self.new_bearing
        analysis = "coaxial" if self.new_bearing.bearing_type == 20 else "stationary"
        validate_model(candidate, analysis=analysis)
        super().__init__(text or f"Edit bearing {self.bearing_index + 1}")

    def _assign(self, bearing):
        self.session.project.model.bearings[self.bearing_index] = bearing
        self.session.notify_model_changed()

    def redo(self):
        self._assign(self.new_bearing)

    def undo(self):
        self._assign(self.old_bearing)


class EditDiskCommand(QUndoCommand):
    """Undoable replacement of a qualified Stage 1 Disk."""

    def __init__(self, session, disk_index: int, new_disk, text: str | None = None):
        self.session=session;self.disk_index=int(disk_index)
        self.old_disk=session.project.model.disks[self.disk_index]
        self.new_disk=new_disk
        candidate=copy.deepcopy(session.project.model);candidate.disks[self.disk_index]=new_disk
        validate_model(candidate,analysis=_model_validation_family(candidate))
        super().__init__(text or f"Edit disk {self.disk_index+1}")

    def _assign(self,disk):
        self.session.project.model.disks[self.disk_index]=disk
        self.session.notify_model_changed()

    def redo(self):self._assign(self.new_disk)
    def undo(self):self._assign(self.old_disk)



class ReplaceRotorDefinitionsCommand(QUndoCommand):
    """Undoable replacement of qualified coaxial RotorDefinition rows."""

    def __init__(self, session, definitions, text="Edit coaxial rotor definitions"):
        self.session=session
        self.old=list(session.project.model.rotors)
        self.new=list(definitions)
        candidate=copy.deepcopy(session.project.model)
        candidate.rotors=list(self.new)
        validate_model(candidate,analysis="coaxial")
        super().__init__(text)

    def _assign(self,definitions):
        self.session.project.model.rotors=list(definitions)
        self.session.notify_model_changed()

    def redo(self):self._assign(self.new)
    def undo(self):self._assign(self.old)



def _model_validation_family(model):
    from drm_core.domain.model import AsymmetricShaftElement
    if any(isinstance(s, AsymmetricShaftElement) for s in model.shafts):
        return "rotating"
    if model.rotors or any(b.bearing_type == 20 for b in model.bearings):
        return "coaxial"
    return "stationary"


class EditBearingCommand(QUndoCommand):
    """Undoable replacement of bearing type, node and its qualified property tuple."""

    def __init__(self, session, bearing_index: int, new_bearing, text: str | None = None):
        self.session=session;self.bearing_index=int(bearing_index)
        self.old_bearing=session.project.model.bearings[self.bearing_index]
        self.new_bearing=new_bearing
        candidate=copy.deepcopy(session.project.model)
        candidate.bearings[self.bearing_index]=new_bearing
        validate_model(candidate,analysis=_model_validation_family(candidate))
        super().__init__(text or f"Edit bearing {self.bearing_index+1}")

    def _assign(self,bearing):
        self.session.project.model.bearings[self.bearing_index]=bearing
        self.session.notify_model_changed()

    def redo(self):self._assign(self.new_bearing)
    def undo(self):self._assign(self.old_bearing)
