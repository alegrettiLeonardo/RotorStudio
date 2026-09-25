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
class PlainJournalPhysicsBearing:
    """Native Fortran PlainJournal physics provider.

    The production path supports regular-flooded isoviscous, THD
    (adiabatic/full energy equation) and pad-deformation TEHD.  Thermal and
    deformation inputs are explicit so unsupported physics is never silently
    replaced by a constant-coefficient approximation.
    """

    node: int
    weight_n: float
    journal_diameter_m: float
    radial_clearance_m: float
    oil_viscosity_pa_s: float
    pivot_angle_rad: tuple[float, ...]
    pad_arc_rad: tuple[float, ...]
    pad_axial_length_m: tuple[float, ...]
    preload: tuple[float, ...]
    offset: tuple[float, ...]
    fxs_load_n: float = 0.0
    fys_load_n: float = 0.0
    total_e_x_film: int = 20
    total_e_z_film: int = 10
    total_e_y_pad: int = 10
    total_e_y_film: int = 10
    xj_ratio_initial: float = 0.15
    yj_ratio_initial: float = -0.2
    relax_p: float = 0.5
    relax_temperature: float = 0.5
    max_iterations: int = 80
    outer_iterations: int = 30
    force_tolerance: float = 2e-3
    field_tolerance: float = 1e-3
    thermal_type: str | None = None
    deform_type: str | None = None
    pad_thickness_m: float | None = None
    oil_supply_temperature_k: float | None = None
    lubricant_density_kg_m3: float | None = None
    lubricant_cp_j_kgk: float | None = None
    lubricant_conductivity_w_mk: float | None = None
    viscosity2_pa_s: float | None = None
    temperature1_k: float | None = None
    temperature2_k: float | None = None
    temperature_journal_k: float | None = None
    temperature_ambient_k: float | None = None
    temperature_reference_k: float | None = None
    ambient_pressure_1_pa: float = 0.0
    ambient_pressure_2_pa: float = 0.0
    pad_conductivity_w_mk: float | None = None
    pad_young_pa: float | None = None
    pad_poisson: float | None = None
    pad_expansion_1_k: float | None = None
    convection_edges_w_m2k: float = 0.0
    convection_back_w_m2k: float = 0.0
    tag: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    model_family: str = field(default="plain_journal_physics", init=False)


@dataclass(frozen=True)
class TiltingPadPhysicsBearing:
    """Native Fortran conventional tilting-pad physics provider.

    The provider solves journal and pad equilibrium, Reynolds pressure,
    dynamic perturbations, exact pad-DOF condensation at the requested whirl
    frequency and the regular-flooded THD/TEHD loop.
    """

    node: int
    weight_n: float
    journal_diameter_m: float
    radial_clearance_m: float
    oil_viscosity_pa_s: float
    pad_thickness_m: float
    pad_density_kg_m3: float
    pivot_angle_rad: tuple[float, ...]
    pad_arc_rad: tuple[float, ...]
    pad_axial_length_m: tuple[float, ...]
    preload: tuple[float, ...]
    offset: tuple[float, ...]
    k_rotate_nm_rad: tuple[float, ...]
    fxs_load_n: float = 0.0
    fys_load_n: float = 0.0
    total_e_x_film: int = 20
    total_e_z_film: int = 10
    total_e_y_pad: int = 10
    total_e_y_film: int = 10
    xj_ratio_initial: float = 0.15
    yj_ratio_initial: float = -0.2
    relax_p: float = 0.5
    max_iterations: int = 80
    bearing_type: str = "conventional_tilting_pad"
    thermal_type: str | None = None
    deform_type: str | None = None
    oil_supply_temperature_k: float | None = None
    oil_flow_m3_s: float | None = None
    lubricant_density_kg_m3: float | None = None
    lubricant_cp_j_kgk: float | None = None
    lubricant_conductivity_w_mk: float | None = None
    viscosity2_pa_s: float | None = None
    temperature1_k: float | None = None
    temperature2_k: float | None = None
    temperature_journal_k: float | None = None
    temperature_ambient_k: float | None = None
    temperature_reference_k: float | None = None
    ambient_pressure_1_pa: float = 0.0
    ambient_pressure_2_pa: float = 0.0
    pad_conductivity_w_mk: float | None = None
    pad_young_pa: float | None = None
    pad_poisson: float | None = None
    pad_expansion_1_k: float | None = None
    convection_edges_w_m2k: float = 0.0
    convection_back_w_m2k: float = 0.0
    relax_temperature: float = 0.5
    outer_iterations: int = 30
    force_tolerance: float = 2e-3
    field_tolerance: float = 1e-3
    tag: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    model_family: str = field(default="tilting_pad_physics", init=False)


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
    | PlainJournalPhysicsBearing
    | TiltingPadPhysicsBearing
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
    "PlainJournalPhysicsBearing": PlainJournalPhysicsBearing,
    "TiltingPadPhysicsBearing": TiltingPadPhysicsBearing,
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
    tuple_fields = (
        "speed_rad_s",
        "frequency_rad_s",
        "pivot_angle_rad",
        "pad_arc_rad",
        "pad_axial_length_m",
        "preload",
        "offset",
        "k_rotate_nm_rad",
    )
    for key in tuple_fields:
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
    if isinstance(bearing, TiltingPadPhysicsBearing):
        arrays = (
            bearing.pivot_angle_rad,
            bearing.pad_arc_rad,
            bearing.pad_axial_length_m,
            bearing.preload,
            bearing.offset,
            bearing.k_rotate_nm_rad,
        )
        n = len(bearing.pivot_angle_rad)
        if n < 1 or any(len(a) != n for a in arrays):
            raise ValueError("TiltingPad physical per-pad arrays must be non-empty and have equal lengths")
        scalars = [
            bearing.weight_n,
            bearing.journal_diameter_m,
            bearing.radial_clearance_m,
            bearing.oil_viscosity_pa_s,
            bearing.pad_thickness_m,
            bearing.pad_density_kg_m3,
            *bearing.pivot_angle_rad,
            *bearing.pad_arc_rad,
            *bearing.pad_axial_length_m,
            *bearing.preload,
            *bearing.offset,
            *bearing.k_rotate_nm_rad,
        ]
        if (
            bearing.weight_n <= 0
            or bearing.journal_diameter_m <= 0
            or bearing.radial_clearance_m <= 0
            or bearing.oil_viscosity_pa_s <= 0
            or bearing.pad_thickness_m <= 0
            or bearing.pad_density_kg_m3 < 0
        ):
            raise ValueError("TiltingPad weight/diameter/clearance/viscosity/thickness must be > 0 and density >= 0")
        if any(x <= 0 for x in bearing.pad_arc_rad) or any(x <= 0 for x in bearing.pad_axial_length_m):
            raise ValueError("TiltingPad pad arc and axial length must be > 0")
        if any(not 0 <= x < 1 for x in bearing.preload):
            raise ValueError("TiltingPad preload must satisfy 0 <= preload < 1")
        if any(not 0 < x < 1 for x in bearing.offset):
            raise ValueError("TiltingPad offset must satisfy 0 < offset < 1")
        if bearing.total_e_x_film < 2 or bearing.total_e_x_film % 2 or bearing.total_e_z_film < 2 or bearing.total_e_z_film % 2:
            raise ValueError("TiltingPad Reynolds element counts must be even and >= 2")
        if bearing.total_e_y_pad < 2 or bearing.total_e_y_pad % 2:
            raise ValueError("TiltingPad radial pad element count must be even and >= 2")
        if bearing.bearing_type != "conventional_tilting_pad":
            raise ValueError("native TiltingPad physics currently qualifies conventional_tilting_pad only")
        if bearing.thermal_type not in {None, "adiabatic", "full"}:
            raise ValueError("TiltingPad thermal_type must be None, 'adiabatic' or 'full'")
        if bearing.deform_type not in {None, "pad_mechanical", "pad_mechanical_thermal"}:
            raise ValueError("TiltingPad deform_type must be None, 'pad_mechanical' or 'pad_mechanical_thermal'")
        if bearing.total_e_y_pad < 2 or bearing.total_e_y_pad % 2 or bearing.total_e_y_film < 2:
            raise ValueError("TiltingPad transverse pad/film meshes must be >= 2; pad mesh must be even")
        if bearing.outer_iterations < 1 or bearing.field_tolerance <= 0:
            raise ValueError("TiltingPad outer_iterations must be >=1 and field_tolerance >0")
        thermal_values = (
            bearing.oil_supply_temperature_k,
            bearing.oil_flow_m3_s,
            bearing.lubricant_density_kg_m3,
            bearing.lubricant_cp_j_kgk,
            bearing.lubricant_conductivity_w_mk,
            bearing.viscosity2_pa_s,
            bearing.temperature1_k,
            bearing.temperature2_k,
            bearing.temperature_reference_k,
            bearing.ambient_pressure_1_pa,
            bearing.ambient_pressure_2_pa,
            bearing.pad_conductivity_w_mk,
            bearing.pad_young_pa,
            bearing.pad_poisson,
            bearing.pad_expansion_1_k,
        )
        for value in thermal_values:
            if value is not None and not isfinite(float(value)):
                raise ValueError("TiltingPad thermal/TEHD properties must be finite when supplied")
    elif isinstance(bearing, PlainJournalPhysicsBearing):
        arrays = (
            bearing.pivot_angle_rad,
            bearing.pad_arc_rad,
            bearing.pad_axial_length_m,
            bearing.preload,
            bearing.offset,
        )
        n = len(bearing.pivot_angle_rad)
        if n < 1 or any(len(a) != n for a in arrays):
            raise ValueError("PlainJournal physical per-pad arrays must be non-empty and have equal lengths")
        scalars = [
            bearing.weight_n,
            bearing.journal_diameter_m,
            bearing.radial_clearance_m,
            bearing.oil_viscosity_pa_s,
            *bearing.pivot_angle_rad,
            *bearing.pad_arc_rad,
            *bearing.pad_axial_length_m,
            *bearing.preload,
            *bearing.offset,
        ]
        if bearing.weight_n <= 0 or bearing.journal_diameter_m <= 0 or bearing.radial_clearance_m <= 0 or bearing.oil_viscosity_pa_s <= 0:
            raise ValueError("PlainJournal weight/diameter/clearance/viscosity must be > 0")
        if any(x <= 0 for x in bearing.pad_arc_rad) or any(x <= 0 for x in bearing.pad_axial_length_m):
            raise ValueError("PlainJournal pad arc and axial length must be > 0")
        if any(not 0 <= x < 1 for x in bearing.preload):
            raise ValueError("PlainJournal preload must satisfy 0 <= preload < 1")
        if any(not 0 <= x <= 1 for x in bearing.offset):
            raise ValueError("PlainJournal offset must satisfy 0 <= offset <= 1")
        if bearing.total_e_x_film < 2 or bearing.total_e_x_film % 2 or bearing.total_e_z_film < 2 or bearing.total_e_z_film % 2:
            raise ValueError("PlainJournal Reynolds element counts must be even and >= 2")
        if bearing.thermal_type not in {None, "adiabatic", "full"}:
            raise ValueError("PlainJournal thermal_type must be None, 'adiabatic' or 'full'")
        if bearing.deform_type not in {None, "pad_mechanical", "pad_mechanical_thermal"}:
            raise ValueError("PlainJournal deform_type must be None, 'pad_mechanical' or 'pad_mechanical_thermal'")
        if bearing.total_e_y_pad < 2 or bearing.total_e_y_pad % 2 or bearing.total_e_y_film < 2:
            raise ValueError("PlainJournal transverse pad/film meshes must be >= 2; pad mesh must be even")
        if bearing.outer_iterations < 1 or bearing.field_tolerance <= 0:
            raise ValueError("PlainJournal outer_iterations must be >=1 and field_tolerance >0")
        for value in (
            bearing.temperature_reference_k,
            bearing.ambient_pressure_1_pa,
            bearing.ambient_pressure_2_pa,
        ):
            if value is not None and not isfinite(float(value)):
                raise ValueError("PlainJournal reference temperature / ambient pressures must be finite")
    elif isinstance(bearing, BallBearing):
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

    if isinstance(bearing, (PlainJournalPhysicsBearing, TiltingPadPhysicsBearing)):
        if bearing.thermal_type is not None:
            required = {
                "oil_supply_temperature_k": bearing.oil_supply_temperature_k,
                "lubricant_density_kg_m3": bearing.lubricant_density_kg_m3,
                "lubricant_cp_j_kgk": bearing.lubricant_cp_j_kgk,
                "lubricant_conductivity_w_mk": bearing.lubricant_conductivity_w_mk,
                "viscosity2_pa_s": bearing.viscosity2_pa_s,
                "temperature1_k": bearing.temperature1_k,
                "temperature2_k": bearing.temperature2_k,
            }
            missing = [name for name, value in required.items() if value is None]
            if missing:
                raise ValueError(f"native THD requires explicit properties: {', '.join(missing)}")
            if bearing.thermal_type == "full" and bearing.pad_conductivity_w_mk is None:
                raise ValueError("full THD requires pad_conductivity_w_mk")
        if bearing.deform_type is not None:
            required = {
                "pad_young_pa": bearing.pad_young_pa,
                "pad_poisson": bearing.pad_poisson,
                "pad_expansion_1_k": bearing.pad_expansion_1_k,
            }
            missing = [name for name, value in required.items() if value is None]
            if missing:
                raise ValueError(f"native TEHD requires explicit properties: {', '.join(missing)}")
        if bearing.deform_type == "pad_mechanical_thermal" and bearing.thermal_type is None:
            raise ValueError("pad_mechanical_thermal deformation requires thermal_type")
    if any(not isfinite(float(x)) for x in scalars):
        raise ValueError("advanced bearing physical inputs must be finite")
