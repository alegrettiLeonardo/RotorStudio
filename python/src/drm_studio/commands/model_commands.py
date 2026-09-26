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


# ---------------------------------------------------------------------------
# B13 â€” advanced bearing transactional CRUD
# ---------------------------------------------------------------------------

def _advanced_ref(index: int):
    from drm_studio.application.session import EntityRef
    return EntityRef("advanced_bearing", int(index))


def _validate_advanced_candidate(model) -> None:
    # B13 edits a stationary-model entity. Existing solver gates remain the
    # authority for coaxial/rotating/run-up use; CRUD does not relax them.
    validate_model(model, analysis="stationary")


class AddAdvancedBearingCommand(QUndoCommand):
    """Insert one fully constructed advanced-bearing domain object."""

    def __init__(self, session, bearing, index: int | None = None, text: str | None = None):
        self.session = session
        self.bearing = copy.deepcopy(bearing)
        self.index = len(session.project.model.advanced_bearings) if index is None else int(index)
        if self.index < 0 or self.index > len(session.project.model.advanced_bearings):
            raise IndexError(f"advanced bearing insertion index {self.index} is out of range")
        self.previous_selection = session.selection
        candidate = copy.deepcopy(session.project.model)
        candidate.advanced_bearings.insert(self.index, copy.deepcopy(self.bearing))
        _validate_advanced_candidate(candidate)
        tag = getattr(self.bearing, "tag", "") or getattr(self.bearing, "model_family", "advanced bearing")
        super().__init__(text or f"Add advanced bearing {tag}")

    def redo(self):
        self.session.project.model.advanced_bearings.insert(self.index, copy.deepcopy(self.bearing))
        self.session.notify_model_changed()
        self.session.set_selection(_advanced_ref(self.index))

    def undo(self):
        current = self.session.project.model.advanced_bearings
        if not (0 <= self.index < len(current)):
            raise IndexError("advanced bearing added by command is no longer present")
        current.pop(self.index)
        self.session.notify_model_changed()
        self.session.set_selection(self.previous_selection)


class EditAdvancedBearingCommand(QUndoCommand):
    """Replace an advanced bearing atomically; undo restores the exact old object."""

    def __init__(self, session, index: int, new_bearing, text: str | None = None):
        self.session = session
        self.index = int(index)
        current = session.project.model.advanced_bearings
        if not (0 <= self.index < len(current)):
            raise IndexError(f"advanced bearing index {self.index} is out of range")
        self.old_bearing = copy.deepcopy(current[self.index])
        self.new_bearing = copy.deepcopy(new_bearing)
        if type(self.old_bearing) is not type(self.new_bearing):
            raise ValueError(
                "B13 Edit does not convert bearing family; create a separate bearing instead"
            )
        candidate = copy.deepcopy(session.project.model)
        candidate.advanced_bearings[self.index] = copy.deepcopy(self.new_bearing)
        _validate_advanced_candidate(candidate)
        super().__init__(text or f"Edit advanced bearing {self.index + 1}")

    def _assign(self, bearing):
        self.session.project.model.advanced_bearings[self.index] = copy.deepcopy(bearing)
        self.session.notify_model_changed()
        self.session.set_selection(_advanced_ref(self.index))

    def redo(self):
        self._assign(self.new_bearing)

    def undo(self):
        self._assign(self.old_bearing)


class DeleteAdvancedBearingCommand(QUndoCommand):
    """Delete one advanced bearing and restore it at its original position on undo."""

    def __init__(self, session, index: int, text: str | None = None):
        self.session = session
        self.index = int(index)
        current = session.project.model.advanced_bearings
        if not (0 <= self.index < len(current)):
            raise IndexError(f"advanced bearing index {self.index} is out of range")
        self.bearing = copy.deepcopy(current[self.index])
        self.previous_selection = session.selection
        candidate = copy.deepcopy(session.project.model)
        candidate.advanced_bearings.pop(self.index)
        _validate_advanced_candidate(candidate)
        super().__init__(text or f"Delete advanced bearing {self.index + 1}")

    def redo(self):
        current = self.session.project.model.advanced_bearings
        if not (0 <= self.index < len(current)):
            raise IndexError( ‰…‘Ù…¹•‰•…É¥¹œÑ¼‘•±•Ñ”¥Ì¹¼±½¹•ÈÁÉ•Í•¹Ðˆ¤(€€€€€€€ÕÉÉ•¹Ð¹Á½À¡Í•±˜¹¥¹‘•à¤(€€€€€€€Í•±˜¹Í•ÍÍ¥½¸¹¹½Ñ¥™å}µ½‘•±}¡…¹• ¤(€€€€€€€¥˜ÕÉÉ•¹Ðè(€€€€€€€€€€€Í•±˜¹Í•ÍÍ¥½¸¹Í•Ñ}Í•±•Ñ¥½¸¡}…‘Ù…¹•‘}É•˜¡µ¥¸¡Í•±˜¹¥¹‘•à°±•¸¡ÕÉÉ•¹Ð¤€´€Ä¤¤¤(€€€€€€€•±Í”è(€€€€€€€€€€€Í•±˜¹Í•ÍÍ¥½¸¹Í•Ñ}Í•±•Ñ¥½¸¡9½¹”¤((€€€‘•˜Õ¹‘¼¡Í•±˜¤è(€€€€€€€Í•±˜¹Í•ÍÍ¥½¸¹ÁÉ½©•Ð¹µ½‘•°¹…‘Ù…¹•‘}‰•…É¥¹Ì¹¥¹Í•ÉÐ¡Í•±˜¹¥¹‘•à°½Áä¹‘••Á½Áä¡Í•±˜¹‰•…É¥¹œ¤¤(€€€€€€€Í•±˜¹Í•ÍÍ¥½¸¹¹½Ñ¥™å}µ½‘•±}¡…¹• ¤(€€€€€€€Í•±˜¹Í•ÍÍ¥½¸¹Í•Ñ}Í•±•Ñ¥½¸¡}…‘Ù…¹•‘}É•˜¡Í•±˜¹¥¹‘•à¤¤(()±…ÍÌÕÁ±¥…Ñ•‘Ù…¹•‘	•…É¥¹½µµ…¹¡EU¹‘½½µµ…¹¤è(€€€€ˆˆ‰É•…Ñ”…¸¥¹‘•Á•¹‘•¹Ð‘••À½ÁäÝ¥Ñ¡½ÕÐ¡…¹¥¹œÁ¡åÍ¥…°Á…É…µ•Ñ•ÉÌ¸ˆˆˆ((€€€‘•˜}}¥¹¥Ñ}|¡Í•±˜°Í•ÍÍ¥½¸°Í½ÕÉ•}¥¹‘•àè¥¹Ð°Ñ•áÐèÍÑÈð9½¹”€ô9½¹”¤è(€€€€€€€Í•±˜¹Í•ÍÍ¥½¸€ôÍ•ÍÍ¥½¸(€€€€€€€Í•±˜¹Í½ÕÉ•}¥¹‘•à€ô¥¹Ð¡Í½ÕÉ•}¥¹‘•à¤(€€€€€€€ÕÉÉ•¹Ð€ôÍ•ÍÍ¥½¸¹ÁÉ½©•Ð¹µ½‘•°¹…‘Ù…¹•‘}‰•…É¥¹Ì(€€€€€€€¥˜¹½Ð€ À€ðôÍ•±˜¹Í½ÕÉ•}¥¹‘•à€ð±•¸¡ÕÉÉ•¹Ð¤¤è(€€€€€€€€€€€É…¥Í”%¹‘•áÉÉ½È¡˜‰…‘Ù…¹•‰•…É¥¹œ¥¹‘•àíÍ•±˜¹Í½ÕÉ•}¥¹‘•áô¥Ì½ÕÐ½˜É…¹”ˆ¤(€€€€€€€Í½ÕÉ”€ô½Áä¹‘••Á½Áä¡ÕÉÉ•¹ÑmÍ•±˜¹Í½ÕÉ•}¥¹‘•át¤(€€€€€€€½±‘}Ñ…œ€ôÍÑÈ¡•Ñ…ÑÑÈ¡Í½ÕÉ”°€‰Ñ…œˆ°€ˆˆ¤¤(€€€€€€€Ñ…œ€ô˜‰í½±‘}Ñ…ô½Áäˆ¥˜½±‘}Ñ…œ•±Í”˜‰í•Ñ…ÑÑÈ¡Í½ÕÉ”°€µ½‘•±}™…µ¥±äœ°€…‘Ù…¹•‰•…É¥¹œœ¥ô½Áäˆ(€€€€€€€Í•±˜¹‰•…É¥¹œ€ôÉ•Á±…”¡Í½ÕÉ”°Ñ…œõÑ…œ¤(€€€€€€€€Œ••Àµ½Áä……¥¸‰•…ÕÍ”™É½é•¸‘…Ñ…±…ÍÍ•Ì…¸ÍÑ¥±°½¹Ñ…¥¸µÕÑ…‰±”(€€€€€€€€ŒÁÉ½Ù•¹…¹”‘¥Ñ¥½¹…É¥•Ì¸Q¡”‘ÕÁ±¥…Ñ”µÕÍÐ‰”¥¹‘•Á•¹‘•¹Ð¸(€€€€€€€Í•±˜¹‰•…É¥¹œ€ô½Áä¹‘••Á½Áä¡Í•±˜¹‰•…É¥¹œ¤(€€€€€€€Í•±˜¹¥¹‘•à€ôÍ•±˜¹Í½ÕÉ•}¥¹‘•à€¬€Ä(€€€€€€€Í•±˜¹ÁÉ•Ù¥½ÕÍ}Í•±•Ñ¥½¸€ôÍ•ÍÍ¥½¸¹Í•±•Ñ¥½¸(€€€€€€€…¹‘¥‘…Ñ”€ô½Áä¹‘••Á½Áä¡Í•ÍÍ¥½¸¹ÁÉ½©•Ð¹µ½‘•°¤(€€€€€€€…¹‘¥‘…Ñ”¹…‘Ù…¹•‘}‰•…É¥¹Ì¹¥¹Í•ÉÐ¡Í•±˜¹¥¹‘•à°½Áä¹‘••Á½Áä¡Í•±˜¹‰•…É¥¹œ¤¤(€€€€€€€}Ù…±¥‘…Ñ•}…‘Ù…¹•‘}…¹‘¥‘…Ñ”¡…¹‘¥‘…Ñ”¤(€€€€€€€ÍÕÁ•È ¤¹}}¥¹¥Ñ}|¡Ñ•áÐ½È˜‰ÕÁ±¥…Ñ”…‘Ù…¹•‰•…É¥¹œíÍ•±˜¹Í½ÕÉ•}¥¹‘•à€¬€Åôˆ¤((€€€‘•˜É•‘¼¡Í•±˜¤è(€€€€€€€Í•±˜¹Í•ÍÍ¥½¸¹ÁÉ½©•Ð¹µ½‘•°¹…‘Ù…¹•‘}‰•…É¥¹Ì¹¥¹Í•ÉÐ¡Í•±˜¹¥¹‘•à°½Áä¹‘••Á½Áä¡Í•±˜¹‰•…É¥¹œ¤¤(€€€€€€€Í•±˜¹Í•ÍÍ¥½¸¹¹½Ñ¥™å}µ½‘•±}¡…¹• ¤(€€€€€€€Í•±˜¹Í•ÍÍ¥½¸¹Í•Ñ}Í•±•Ñ¥½¸¡}…‘Ù…¹•‘}É•˜¡Í•±˜¹¥¹‘•à¤¤((€€€‘•˜Õ¹‘¼¡Í•±˜¤è(€€€€€€€ÕÉÉ•¹Ð€ôÍ•±˜¹Í•ÍÍ¥½¸¹ÁÉ½©•Ð¹µ½‘•°¹…‘Ù…¹•‘}‰•…É¥¹Ì(€€€€€€€¥˜¹½Ð€ À€ðôÍ•±˜¹¥¹‘•à€ð±•¸¡ÕÉÉ•¹Ð¤¤è(€€€€€€€€€€€É…¥Í”%¹‘•áÉÉ½È ‰‘ÕÁ±¥…Ñ•…‘Ù…¹•‰•…É¥¹œ¥Ì¹¼±½¹•ÈÁÉ•Í•¹Ðˆ¤(€€€€€€€ÕÉÉ•¹Ð¹Á½À¡Í•±˜¹¥¹‘•à¤(€€€€€€€Í•±˜¹Í•ÍÍ¥½¸¹¹½Ñ¥™å}µ½‘•±}¡…¹• ¤(€€€€€€€Í•±˜¹Í•ÍÍ¥½¸¹Í•Ñ}Í•±•Ñ¥½¸¡Í•±˜¹ÁÉ•Ù¥½ÕÍ}Í•±•Ñ¥½¸¤(