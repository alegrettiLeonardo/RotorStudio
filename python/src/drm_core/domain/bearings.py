from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Any, TypeAlias

CoeffData: TypeAlias = float | int | tuple[float, ...] | tuple[tuple[float, ...], ...] | list[float] | list[list[float]]


@dataclass(frozen=True)
class CoefficientBearing:
    """Typed radial bearing represented by ROSS-style K/C/M coefficient tables.

    The coefficient axes preserve the modern ROSS distinction between rotor
    spin speed and excitation/whirl frequency.  Empty axes mean a constant
    coefficient.  One axis gives a 1-D table and both axes give a
    speed-by-frequency grid.

    This class is also the qualified integration boundary for advanced
    hydrodynamic models (PlainJournal/TiltingPad/etc.) while their full TEHD
    operating-point solvers remain standalone qualification work.
    """

    node: int
    kxx: CoeffData
    cxx: CoeffData
    kyy: CoeffData | None = None
    cyy: CoeffData | None = None
    kxy: CoeffData = 0.0
    kyx: CoeffData = 0.0
    cxy: CoeffData = 0.0
    cyx: CoeffData = 0.0
    mxx: CoeffData = 0.0
    myy: CoeffData | None = None
    mxy: CoeffData = 0.0
    myx: CoeffData = 0.0
    speed_rad_s: tuple[float, ...] = ()
    frequency_rad_s: tuple[float, ...] = ()
    interpolation: str = "pchip"
    tag: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    model_family: str = field(default="coefficient", init=False)


@dataclass(frozen=True)
class PlainJournalBearing(CoefficientBearing):
    model_family: str = field(default="plain_journal", init=False)


@dataclass(frozen=True)
class PartialArcBearing(CoefficientBearing):
    model_family: str = field(default="partial_arc", init=False)


@dataclass(frozen=True)
class EllipticalBearing(CoefficientBearing):
    model_family: str = field(default="elliptical", init=False)


@dataclass(frozen=True)
class OffsetHalvesBearing(CoefficientBearing):
    model_family: str = field(default="offset_halves", init=False)


@dataclass(frozen=True)
class MultiLobeBearing(CoefficientBearing):
    model_family: str = field(default="multi_lobe", init=False)


@dataclass(frozen=True)
class PressureDamBearing(CoefficientBearing):
    model_family: str = field(default="pressure_dam", init=False)


@dataclass(frozen=True)
class TiltingPadBearing(CoefficientBearing):
    model_family: str = field(default="tilting_pad", init=False)


@dataclass(frozen=True)
class BallBearing:
    node: int
    n_balls: float
    d_balls_m: float
    static_load_n: float
    alpha_rad: float = 0.0
    cxx_ns_m: float | None = None
    cyy_ns_m: float | None = None
    tag: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    model_family: str = field(default="ball", init=False)


@dataclass(frozen=True)
class RollerBearing:
    node: int
    n_rollers: float
    l_rollers_m: float
    static_load_n: float
    alpha_rad: float = 0.0
    cxx_ns_m: float | None = None
    cyy_ns_m: float | None = None
    tag: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    model_family: str = field(default="roller", init=False)


@dataclass(frozen=True)
class CylindricalBearing:
    node: int
    weight_n: float
    bearing_length_m: float
    journal_diameter_m: float
    radial_clearance_m: float
    oil_viscosity_pa_s: float
    tag: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    model_family: str = field(default="cylindrical", init=False)


@dataclass(frozen=True)
class SqueezeFilmDamper:
    node: int
    axial_length_m: float
    journal_diameter_m: float
    radial_clearance_m: float
    eccentricity_ratio: float
    viscosity_pa_s: float
    geometry: str = "groove-end_seals"
    cavitation: bool = True
    tag: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    model_family: str = field(default="squeeze_film_damper", init=False)


AdvancedBearing: TypeAlias = (
    CoefficientBearing
    | PlainJournalBearing
    | PartialArcBearing
    | EllipticalBearing
    | OffsetHalvesBearing
    | MultiLobeBearing
    | PressureDamBearing
    | TiltingPadBearing
    | BallBearing
    | RollerBearing
    | CylindricalBearing
    | SqueezeFilmDamper
)


_COEFF_CLASSES = {
    "CoefficientBearing": CoefficientBearing,
    "PlainJournalBearing": PlainJournalBearing,
    "PartialArcBearing": PartialArcBearing,
    "EllipticalBearing": EllipticalBearing,
    "OffsetHalvesBearing": OffsetHalvesBearing,
    "MultiLobeBearing": MultiLobeBearing,
    "PressureDamBearing": PressureDamBearing,
    "TiltingPadBearing": TiltingPadBearing,
}
_NATIVE_CLASSES = {
    "BallBearing": BallBearing,
    "RollerBearing": RollerBearing,
    "CylindricalBearing": CylindricalBearing,
    "SqueezeFilmDamper": SqueezeFilmDamper,
}
_ALL_CLASSES = {**_COEFF_CLASSES, **_NATIVE_CLASSES}


def advanced_bearing_to_dict(bearing: AdvancedBearing) -> dict[str, Any]:
    payload = asdict(bearing)
    payload["__type__"] = type(bearing).__name__
    return payload


def advanced_bearing_from_dict(payload: dict[str, Any]) -> AdvancedBearing:
    data = dict(payload)
    type_name = str(data.pop("__type__", ""))
    cls = _ALL_CLASSES.get(type_name)
    if cls is None:
        raise ValueError(f"unsupported advanced bearing type {type_name!r}")
    # model_family is init=False on every class and is regenerated by the class.
    data.pop("model_family", None)
    for key in ("speed_rad_s", "frequency_rad_s"):
        if key in data and data[key] is not None:
            data[key] = tuple(float(x) for x in data[key])
    return cls(**data)


def _check_axis(name: str, axis: tuple[float, ...]) -> None:
    if any(not isfinite(float(x)) for x in axis):
        raise ValueError(f"{name}: all values must be finite")
    if any(float(axis[i]) <= float(axis[i - 1]) for i in range(1, len(axis))):
        raise ValueError(f"{name}: values must be strictly increasing")


def _shape(value: CoeffData) -> tuple[int, ...]:
    if isinstance(value, (int, float)):
        return ()
    rows = list(value)
    if not rows:
        return (0,)
    if isinstance(rows[0], (list, tuple)):
        ncol = len(rows[0])
        if any(len(row) != ncol for row in rows):
            raise ValueError("coefficient grid rows must have equal length")
        return (len(rows), ncol)
    return (len(rows),)


def _flatten(value: CoeffData):
    if isinstance(value, (int, float)):
        yield float(value)
        return
    for item in value:
        if isinstance(item, (list, tuple)):
            for x in item:
                yield float(x)
        else:
            yield float(item)


def _validate_coefficient_shape(name: str, value: CoeffData, ns: int, nf: int) -> None:
    shp = _shape(value)
    if any(not isfinite(x) for x in _flatten(value)):
        raise ValueError(f"{name}: coefficient values must be finite")
    if shp == ():
        return
    expected = ()
    if ns and nf:
        expected = (ns, nf)
    elif ns:
        expected = (ns,)
    elif nf:
        expected = (nf,)
    if shp != expected:
        raise ValueError(f"{name}: received shape {shp}, expected scalar or {expected}")


def validate_advanced_bearing(bearing: AdvancedBearing) -> None:
    if int(bearing.node) < 1:
        raise ValueError(f"node={bearing.node}; expected node >= 1")

    if isinstance(bearing, CoefficientBearing):
        if bearing.interpolation not in {"pchip", "linear"}:
            raise ValueError("interpolation must be 'pchip' or 'linear'")
        _check_axis("speed_rad_s", bearing.speed_rad_s)
        _check_axis("frequency_rad_s", bearing.frequency_rad_s)
        ns, nf = len(bearing.speed_rad_s), len(bearing.frequency_rad_s)
        values = {
            "kxx": bearing.kxx,
            "kyy": bearing.kxx if bearing.kyy is None else bearing.kyy,
            "kxy": bearing.kxy,
            "kyx": bearing.kyx,
            "cxx": bearing.cxx,
            "cyy": bearing.cxx if bearing.cyy is None else bearing.cyy,
            "cxy": bearing.cxy,
            "cyx": bearing.cyx,
            "mxx": bearing.mxx,
            "myy": bearing.mxx if bearing.myy is None else bearing.myy,
            "mxy": bearing.mxy,
            "myx": bearing.myx,
        }
        for name, value in values.items():
            _validate_coefficient_shape(name, value, ns, nf)
        return

    scalars = []
    if isinstance(bearing, BallBearing):
        scalars = [bearing.n_balls, bearing.d_balls_m, bearing.static_load_n]
        if bearing.n_balls <= 0 or bearing.d_balls_m <= 0 or bearing.static_load_n < 0:
            raise ValueError("ball bearing expects n_balls>0, d_balls_m>0 and static_load_n>=0")
    elif isinstance(bearing, RollerBearing):
        scalars = [bearing.n_rollers, bearing.l_rollers_m, bearing.static_load_n]
        if bearing.n_rollers <= 0 or bearing.l_rollers_m <= 0 or bearing.static_load_n < 0:
            raise ValueError("roller bearing expects n_rollers>0, l_rollers_m>0 and static_load_n>=0")
    elif isinstance(bearing, CylindricalBearing):
        scalars = [
            bearing.weight_n,
            bearing.bearing_length_m,
            bearing.journal_diameter_m,
            bearing.radial_clearance_m,
            bearing.oil_viscosity_pa_s,
        ]
        if any(x <= 0 for x in scalars):
            raise ValueError("cylindrical bearing physical inputs must all be > 0")
    elif isinstance(bearing, SqueezeFilmDamper):
        scalars = [
            bearing.axial_length_m,
            bearing.journal_diameter_m,
            bearing.radial_clearance_m,
            bearing.viscosity_pa_s,
        ]
        if any(x <= 0 for x in scalars):
            raise ValueError("SFD length/diameter/clearance/viscosity must all be > 0")
        if not 0 <= bearing.eccentricity_ratio < 1:
            raise ValueError("SFD eccentricity_ratio must satisfy 0 <= e < 1")
        if bearing.geometry not in {"groove", "end_seals", "groove-end_seals"}:
            raise ValueError("SFD geometry must be groove, end_seals or groove-end_seals")
    if any(not isfinite(float(x)) for x in scalars):
        raise ValueError("advanced bearing physical inputs must be finite")
