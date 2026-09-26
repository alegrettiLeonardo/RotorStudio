from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any

from drm_core.domain.bearings import CoefficientBearing, validate_advanced_bearing
from drm_core.units import rpm_to_rad_s


IRDIN_SPEED_UNIT = "rpm"
IRDIN_STIFFNESS_UNIT = "N/m"
IRDIN_DAMPING_UNIT = "N*s/m"
IRDIN_COORDINATE_CONVENTION = "X/Y"
IRDIN_CROSS_COUPLING_CONVENTION = "force-row/displacement-column"
IRDIN_COLUMNS = ("rpm", "kxx", "kxy", "kyx", "kyy", "cxx", "cxy", "cyx", "cyy")


class BearingTableImportError(ValueError):
    pass


@dataclass(frozen=True)
class ImportedBearingTable:
    """Validated, source-faithful iRdin bearing coefficient table.

    The intermediate object keeps the source speed axis in rpm. Conversion to
    the RotorStudio domain is explicit and applies only rpm -> rad/s. K/C
    values and cross-coupling signs are never modified.
    """

    node: int
    speed_rpm: tuple[float, ...]
    kxx: tuple[float, ...]
    kxy: tuple[float, ...]
    kyx: tuple[float, ...]
    kyy: tuple[float, ...]
    cxx: tuple[float, ...]
    cxy: tuple[float, ...]
    cyx: tuple[float, ...]
    cyy: tuple[float, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if int(self.node) < 1:
            raise BearingTableImportError(f"node={self.node}; expected node >= 1")
        arrays = (
            self.speed_rpm, self.kxx, self.kxy, self.kyx, self.kyy,
            self.cxx, self.cxy, self.cyx, self.cyy,
        )
        n = len(self.speed_rpm)
        if n < 1:
            raise BearingTableImportError("bearing coefficient table is empty")
        if any(len(values) != n for values in arrays):
            raise BearingTableImportError("bearing coefficient columns have inconsistent lengths")
        if any(not isfinite(float(value)) for values in arrays for value in values):
            raise BearingTableImportError("bearing coefficient table contains NaN or Inf")
        if any(self.speed_rpm[i] <= self.speed_rpm[i - 1] for i in range(1, n)):
            raise BearingTableImportError(
                "rpm axis must be strictly increasing and contain no duplicate values"
            )

    def as_rows(self) -> list[dict[str, float]]:
        self.validate()
        return [
            dict(zip(IRDIN_COLUMNS, values))
            for values in zip(
                self.speed_rpm, self.kxx, self.kxy, self.kyx, self.kyy,
                self.cxx, self.cxy, self.cyx, self.cyy,
            )
        ]

    def to_coefficient_bearing(
        self,
        *,
        interpolation: str = "pchip",
        tag: str = "",
        provenance: dict[str, Any] | None = None,
    ) -> CoefficientBearing:
        self.validate()
        if interpolation not in {"linear", "pchip"}:
            raise BearingTableImportError(
                f"interpolation={interpolation!r}; expected 'linear' or 'pchip'"
            )
        merged = {
            "source_format": "iRdin/VB6 TABLE",
            "source_speed_unit": IRDIN_SPEED_UNIT,
            "source_stiffness_unit": IRDIN_STIFFNESS_UNIT,
            "source_damping_unit": IRDIN_DAMPING_UNIT,
            "coordinate_convention": IRDIN_COORDINATE_CONVENTION,
            "cross_coupling_convention": IRDIN_CROSS_COUPLING_CONVENTION,
            "sign_transform": "NONE",
            "b15_mapping": "IRDIN_COEFFICIENT_TABLE_IMPORT",
            **dict(self.metadata),
            **dict(provenance or {}),
        }
        bearing = CoefficientBearing(
            node=int(self.node),
            speed_rad_s=tuple(float(rpm_to_rad_s(value)) for value in self.speed_rpm),
            frequency_rad_s=(),
            interpolation=interpolation,
            kxx=self.kxx,
            kxy=self.kxy,
            kyx=self.kyx,
            kyy=self.kyy,
            cxx=self.cxx,
            cxy=self.cxy,
            cyx=self.cyx,
            cyy=self.cyy,
            mxx=0.0,
            mxy=0.0,
            myx=0.0,
            myy=0.0,
            tag=tag,
            provenance=merged,
        )
        validate_advanced_bearing(bearing)
        return bearing


def _strict_number(value: str) -> float:
    text = str(value).strip().replace("D", "E").replace("d", "e")
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        number = float(text)
    except ValueError as exc:
        raise BearingTableImportError(f"invalid numeric table value {value!r}") from exc
    if not isfinite(number):
        raise BearingTableImportError(f"non-finite table value {value!r}")
    return number


def parse_coefficient_table(
    raw: str,
    *,
    node: int,
    speed_unit: str,
    stiffness_unit: str,
    damping_unit: str,
    coordinate_convention: str,
    cross_coupling_convention: str,
    source_format: str = "bearing coefficient table",
) -> ImportedBearingTable:
    if int(node) < 1:
        raise BearingTableImportError(f"node={node}; expected node >= 1")
    expected_contract = {
        "speed_unit": IRDIN_SPEED_UNIT,
        "stiffness_unit": IRDIN_STIFFNESS_UNIT,
        "damping_unit": IRDIN_DAMPING_UNIT,
        "coordinate_convention": IRDIN_COORDINATE_CONVENTION,
        "cross_coupling_convention": IRDIN_CROSS_COUPLING_CONVENTION,
    }
    received = {
        "speed_unit": str(speed_unit),
        "stiffness_unit": str(stiffness_unit),
        "damping_unit": str(damping_unit),
        "coordinate_convention": str(coordinate_convention),
        "cross_coupling_convention": str(cross_coupling_convention),
    }
    for key, expected in expected_contract.items():
        if received[key] != expected:
            raise BearingTableImportError(
                f"{key}={received[key]!r} is unknown/ambiguous; expected explicit {expected!r}"
            )

    chunks = [part.strip() for part in str(raw).split("§") if part.strip()]
    if not chunks or chunks[0].casefold() != "table":
        raise BearingTableImportError("expected inline TABLE§... coefficient source")
    data_chunks = chunks[1:]
    if not data_chunks:
        raise BearingTableImportError("bearing coefficient table is empty")

    first_tokens = tuple(token.strip() for token in data_chunks[0].split("|"))
    # Only an explicit rpm/Kxx/... label row is treated as a header.  A
    # malformed first numeric point (including NaN/Inf) must fail as data
    # rather than being reinterpreted as a header.
    if first_tokens and first_tokens[0].casefold() == "rpm":
        header = tuple(token.casefold() for token in first_tokens)
        if header != IRDIN_COLUMNS:
            raise BearingTableImportError(
                f"invalid coefficient columns {first_tokens!r}; expected {IRDIN_COLUMNS!r}"
            )
        data_chunks = data_chunks[1:]
        if not data_chunks:
            raise BearingTableImportError("bearing coefficient table contains a header but no data")

    columns = [[] for _ in IRDIN_COLUMNS]
    for point_no, chunk in enumerate(data_chunks, start=1):
        tokens = tuple(token.strip() for token in chunk.split("|"))
        if len(tokens) != len(IRDIN_COLUMNS):
            raise BearingTableImportError(
                f"table point {point_no}: received {len(tokens)} columns; "
                f"expected {len(IRDIN_COLUMNS)} ({'|'.join(IRDIN_COLUMNS)})"
            )
        values = tuple(_strict_number(token) for token in tokens)
        for column, value in zip(columns, values):
            column.append(value)

    table = ImportedBearingTable(
        node=int(node),
        speed_rpm=tuple(columns[0]),
        kxx=tuple(columns[1]),
        kxy=tuple(columns[2]),
        kyx=tuple(columns[3]),
        kyy=tuple(columns[4]),
        cxx=tuple(columns[5]),
        cxy=tuple(columns[6]),
        cyx=tuple(columns[7]),
        cyy=tuple(columns[8]),
        metadata={"source_format": source_format},
    )
    table.validate()
    return table


def parse_irdin_coefficient_table(raw: str, *, node: int) -> ImportedBearingTable:
    return parse_coefficient_table(
        raw,
        node=node,
        speed_unit=IRDIN_SPEED_UNIT,
        stiffness_unit=IRDIN_STIFFNESS_UNIT,
        damping_unit=IRDIN_DAMPING_UNIT,
        coordinate_convention=IRDIN_COORDINATE_CONVENTION,
        cross_coupling_convention=IRDIN_CROSS_COUPLING_CONVENTION,
        source_format="iRdin/VB6 inline TABLE",
    )


__all__ = [
    "BearingTableImportError",
    "ImportedBearingTable",
    "parse_coefficient_table",
    "parse_irdin_coefficient_table",
    "IRDIN_SPEED_UNIT",
    "IRDIN_STIFFNESS_UNIT",
    "IRDIN_DAMPING_UNIT",
    "IRDIN_COORDINATE_CONVENTION",
    "IRDIN_CROSS_COUPLING_CONVENTION",
    "IRDIN_COLUMNS",
]
