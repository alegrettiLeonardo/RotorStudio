"""I17 explicit API 541 torsional-train input contract.

This stage intentionally contains no torsional eigensolver. The ST41 iRdin
source does not contain a complete driven-train torsional model, so no inertia,
shaft/coupling stiffness or excitation is inferred from the lateral import.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import math
from typing import Any


class API541TorsionalInputError(ValueError):
    pass


@dataclass(frozen=True)
class TorsionalStation:
    name: str
    polar_inertia_kgm2: float
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TorsionalConnection:
    left_station: int
    right_station: int
    stiffness_nm_rad: float
    damping_nms_rad: float = 0.0
    name: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TorsionalExcitation:
    station: int
    torque_nm: float
    phase_rad: float = 0.0
    order: float | None = None
    frequency_hz: float | None = None
    name: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class API541TorsionalModel:
    stations: tuple[TorsionalStation, ...]
    connections: tuple[TorsionalConnection, ...]
    excitations: tuple[TorsionalExcitation, ...]
    operating_speed_rpm: float
    motor_station: int
    driven_equipment_station: int
    coupling_connection: int
    driven_equipment: str
    authority: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "stations": [asdict(x) for x in self.stations],
            "connections": [asdict(x) for x in self.connections],
            "excitations": [asdict(x) for x in self.excitations],
            "operating_speed_rpm": float(self.operating_speed_rpm),
            "motor_station": int(self.motor_station),
            "driven_equipment_station": int(self.driven_equipment_station),
            "coupling_connection": int(self.coupling_connection),
            "driven_equipment": str(self.driven_equipment),
            "authority": str(self.authority),
            "metadata": dict(self.metadata),
        }


def _finite(value: float, label: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise API541TorsionalInputError(f"{label} must be finite")
    return value


def validate_api541_torsional_model(model: API541TorsionalModel) -> dict[str, Any]:
    if not isinstance(model, API541TorsionalModel):
        raise API541TorsionalInputError("expected API541TorsionalModel")

    speed = _finite(model.operating_speed_rpm, "operating_speed_rpm")
    if speed <= 0.0:
        raise API541TorsionalInputError("operating_speed_rpm must be > 0")

    stations = tuple(model.stations)
    n = len(stations)
    if n < 2 or n > 128:
        raise API541TorsionalInputError("torsional train requires 2..128 stations")
    if len(model.connections) != n - 1:
        raise API541TorsionalInputError("serial torsional train requires exactly n-1 connections")

    names = []
    for i, station in enumerate(stations):
        name = str(station.name).strip()
        if not name:
            raise API541TorsionalInputError(f"station {i}: name is required")
        if name in names:
            raise API541TorsionalInputError(f"station {i}: duplicate name {name!r}")
        names.append(name)
        inertia = _finite(station.polar_inertia_kgm2, f"station {i} polar inertia")
        if inertia <= 0.0:
            raise API541TorsionalInputError(f"station {i}: polar inertia must be > 0")
        if not dict(station.provenance):
            raise API541TorsionalInputError(f"station {i}: provenance is required")

    expected_edges = {(i, i + 1) for i in range(n - 1)}
    actual_edges = set()
    for i, connection in enumerate(model.connections):
        left = int(connection.left_station)
        right = int(connection.right_station)
        if left > right:
            left, right = right, left
        if left < 0 or right >= n or left == right:
            raise API541TorsionalInputError(f"connection {i}: invalid station indices")
        actual_edges.add((left, right))
        k = _finite(connection.stiffness_nm_rad, f"connection {i} stiffness")
        c = _finite(connection.damping_nms_rad, f"connection {i} damping")
        if k <= 0.0:
            raise API541TorsionalInputError(f"connection {i}: stiffness must be > 0")
        if c < 0.0:
            raise API541TorsionalInputError(f"connection {i}: damping must be >= 0")
        if not dict(connection.provenance):
            raise API541TorsionalInputError(f"connection {i}: provenance is required")
    if actual_edges != expected_edges:
        raise API541TorsionalInputError(
            "I17 initial scope requires a serial adjacent-station torsional train"
        )

    if not model.excitations:
        raise API541TorsionalInputError("at least one torsional excitation is required")
    for i, excitation in enumerate(model.excitations):
        station = int(excitation.station)
        if station < 0 or station >= n:
            raise API541TorsionalInputError(f"excitation {i}: invalid station")
        torque = _finite(excitation.torque_nm, f"excitation {i} torque")
        _finite(excitation.phase_rad, f"excitation {i} phase")
        if torque == 0.0:
            raise API541TorsionalInputError(f"excitation {i}: torque must be nonzero")
        has_order = excitation.order is not None
        has_frequency = excitation.frequency_hz is not None
        if has_order == has_frequency:
            raise API541TorsionalInputError(
                f"excitation {i}: declare exactly one of order or frequency_hz"
            )
        if has_order and _finite(excitation.order, f"excitation {i} order") <= 0.0:
            raise API541TorsionalInputError(f"excitation {i}: order must be > 0")
        if has_frequency and _finite(excitation.frequency_hz, f"excitation {i} frequency") <= 0.0:
            raise API541TorsionalInputError(f"excitation {i}: frequency_hz must be > 0")
        if not dict(excitation.provenance):
            raise API541TorsionalInputError(f"excitation {i}: provenance is required")

    for label, index in (
        ("motor_station", model.motor_station),
        ("driven_equipment_station", model.driven_equipment_station),
    ):
        index = int(index)
        if index < 0 or index >= n:
            raise API541TorsionalInputError(f"{label} outside 0..{n-1}")
    if int(model.motor_station) == int(model.driven_equipment_station):
        raise API541TorsionalInputError("motor and driven equipment stations must differ")

    coupling = int(model.coupling_connection)
    if coupling < 0 or coupling >= len(model.connections):
        raise API541TorsionalInputError("coupling_connection is invalid")
    if not str(model.driven_equipment).strip():
        raise API541TorsionalInputError("driven_equipment declaration is required")
    if not str(model.authority).strip():
        raise API541TorsionalInputError("torsional input authority/provenance is required")

    return {
        "status": "API541_TORSIONAL_INPUT_READY",
        "station_count": n,
        "connection_count": len(model.connections),
        "excitation_count": len(model.excitations),
        "operating_speed_rpm": speed,
        "motor_station": int(model.motor_station),
        "driven_equipment_station": int(model.driven_equipment_station),
        "coupling_connection": coupling,
        "driven_equipment": str(model.driven_equipment),
        "authority": str(model.authority),
        "solver_qualified": False,
        "whole_api541_compliance_claim": False,
    }


def torsional_model_from_irdin(*_args, **_kwargs):
    raise API541TorsionalInputError(
        "I17 does not infer a torsional train from an iRdin lateral file. "
        "Provide explicit polar inertias, torsional connections, driven-equipment "
        "definition, coupling data and torque/electrical excitations."
    )


__all__ = [
    "API541TorsionalInputError",
    "TorsionalStation",
    "TorsionalConnection",
    "TorsionalExcitation",
    "API541TorsionalModel",
    "validate_api541_torsional_model",
    "torsional_model_from_irdin",
]
