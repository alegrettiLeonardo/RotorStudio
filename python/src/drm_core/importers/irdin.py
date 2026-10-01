from __future__ import annotations

"""Conservative import of the historical iRdin/VB6 INI calculation format.

B15 maps validated inline iRdin bearing coefficient TABLE records into typed
CoefficientBearing objects without changing K/C signs or values; only the rpm
axis is converted to rad/s. Other legacy entities remain engineering-sketch
metadata until their own numerical mappings are explicitly qualified.
"""

from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import re
from typing import Any

from drm_core.domain.model import (
    Node,
    RotorModel,
    ShaftElement,
    TaperedShaftElement,
)
from drm_core.stage1 import RotorProject
from .bearing_table import BearingTableImportError, parse_irdin_coefficient_table
from .irdin_bearing_policy import IRDIN_LEGACY_INTERPOLATION, legacy_bearing_policy
from .irdin_mass import build_mass_spans, materialize_mass_disks, mass_audit
from .irdin_support import IrdinSupportMappingError, build_bearing_supports
from .irdin_excitation import (
    IrdinExcitationMappingError,
    build_unbalance_forces,
    build_response_probes,
    excitation_audit,
)


_GRID_KEY = re.compile(r"^(\d+)\s*,\s*(\d+)$")


class IrdinImportError(ValueError):
    pass


def _read_text(path: str | Path) -> str:
    source = Path(path)
    if not source.is_file():
        raise IrdinImportError(f"iRdin file not found: {source}")
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return source.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise IrdinImportError(f"could not decode iRdin file: {source}")


def _parse_document(text: str) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line_no, raw in enumerate(
        text.replace("\r\n", "\n").replace("\r", "\n").splitlines(), start=1
    ):
        line = raw.strip()
        if not line or line.startswith((";", "#")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1].strip().casefold(), {})
            continue
        if "=" not in line:
            continue
        if current is None:
            raise IrdinImportError(f"line {line_no}: value outside an INI section")
        key, value = line.split("=", 1)
        current[key.strip().casefold()] = value.strip()
    for required in ("dados", "secoes"):
        if required not in sections:
            raise IrdinImportError(f"iRdin file is missing required [{required.title()}] section")
    return sections


def _number(value: str | float | int | None, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    text = str(value).strip()
    if not text:
        return float(default)
    text = text.replace("D", "E").replace("d", "e")
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError as exc:
        raise IrdinImportError(f"invalid numeric value in iRdin file: {value!r}") from exc


def _integer(value: str | float | int | None, default: int = 0) -> int:
    if value is None or str(value).strip() == "":
        return int(default)
    number = _number(value)
    rounded = int(round(number))
    if abs(number - rounded) > 1.0e-9:
        raise IrdinImportError(f"invalid integer value in iRdin file: {value!r}")
    return rounded


def _truthy(value: str | float | int | None) -> bool:
    if value is None:
        return False
    text = str(value).strip().casefold()
    if text in {"true", "yes", "sim", "on"}:
        return True
    return bool(_integer(value, 0))


def _grid_rows(section: dict[str, str] | None) -> list[dict[int, str]]:
    grouped: dict[int, dict[int, str]] = defaultdict(dict)
    for key, value in (section or {}).items():
        match = _GRID_KEY.match(key)
        if not match:
            continue
        row = int(match.group(1))
        col = int(match.group(2))
        if row < 1 or col < 0:
            raise IrdinImportError(f"invalid legacy grid index: {key}")
        grouped[row][col] = value
    return [grouped[row] for row in sorted(grouped)]


def _cell(row: dict[int, str], column: int, default: str = "") -> str:
    return row.get(column, default)


def _bearing_table(raw: str, bearing_index: int) -> list[dict[str, float]]:
    value = raw.strip()
    if not value:
        return []
    chunks = [chunk.strip() for chunk in value.split("§") if chunk.strip()]
    if not chunks:
        return []
    if not chunks[0].upper().startswith("TABLE"):
        # External COEF/table paths remain provenance only. The sketch does not
        # attempt to dereference arbitrary historical paths.
        return []
    result: list[dict[str, float]] = []
    fields = ("rpm", "kxx", "kxy", "kyx", "kyy", "cxx", "cxy", "cyx", "cyy")
    for point_no, chunk in enumerate(chunks[1:], start=1):
        values = chunk.replace("|", " ").split()
        if len(values) != 9:
            raise IrdinImportError(
                f"bearing {bearing_index} table point {point_no}: expected rpm + 8 K/C values"
            )
        nums = [_number(v) for v in values]
        result.append(dict(zip(fields, nums)))
    return result


def _shaft_geometry(
    section_rows: list[dict[int, str]],
    *,
    E_pa: float,
    rho_kg_m3: float,
    poisson: float,
) -> tuple[list[Node], list[Any], list[dict[str, Any]]]:
    G_pa = E_pa / (2.0 * (1.0 + poisson))
    nodes = [Node(1, 0.0)]
    shafts: list[Any] = []
    sketch_sections: list[dict[str, Any]] = []
    z_m = 0.0

    for index, row in enumerate(section_rows, start=1):
        length_mm = _number(_cell(row, 0))
        diameter_mm = _number(_cell(row, 1))
        if length_mm <= 0.0 or diameter_mm <= 0.0:
            raise IrdinImportError(
                f"section {index}: length and outside diameter must be positive"
            )
        inner_mm = _number(_cell(row, 7), 0.0)
        final_outer_mm = _number(_cell(row, 8), 0.0)
        final_inner_mm = _number(_cell(row, 9), 0.0)
        if final_outer_mm <= 0.0:
            final_outer_mm = diameter_mm
        if final_inner_mm <= 0.0:
            final_inner_mm = inner_mm

        n1 = index
        n2 = index + 1
        z_m += length_mm / 1000.0
        nodes.append(Node(n2, z_m))

        conical = (
            abs(final_outer_mm - diameter_mm) > 1.0e-12
            or abs(final_inner_mm - inner_mm) > 1.0e-12
        )
        if conical:
            shafts.append(
                TaperedShaftElement(
                    22,
                    n1,
                    n2,
                    diameter_mm / 1000.0,
                    final_outer_mm / 1000.0,
                    inner_mm / 1000.0,
                    final_inner_mm / 1000.0,
                    rho_kg_m3,
                    E_pa,
                    G_pa,
                )
            )
        else:
            shafts.append(
                ShaftElement(
                    2,
                    n1,
                    n2,
                    diameter_mm / 1000.0,
                    inner_mm / 1000.0,
                    rho_kg_m3,
                    E_pa,
                    G_pa,
                )
            )

        sketch_sections.append(
            {
                "index": index,
                "length_mm": length_mm,
                "diameter_mm": diameter_mm,
                "inner_diameter_mm": inner_mm,
                "final_diameter_mm": final_outer_mm,
                "final_inner_diameter_mm": final_inner_mm,
                "package_diameter_mm": _number(_cell(row, 2), 0.0),
                "a_mm": _number(_cell(row, 3), 0.0),
                "b_mm": _number(_cell(row, 4), 0.0),
                "c_mm": _number(_cell(row, 5), 0.0),
                "rib_count": _integer(_cell(row, 6), 0),
            }
        )
    return nodes, shafts, sketch_sections


def _insert_exact_stations(
    nodes: list[Node],
    shafts: list[Any],
    positions_m: list[float],
) -> tuple[list[Node], list[Any], list[int]]:
    """Split shaft elements at requested physical stations without geometry loss."""
    if not positions_m:
        return nodes, shafts, []
    tol = 1.0e-10
    z_by_node = {int(node.number): float(node.z_m) for node in nodes}
    zmin = min(z_by_node.values())
    zmax = max(z_by_node.values())
    for position in positions_m:
        if position < zmin - tol or position > zmax + tol:
            raise IrdinImportError(
                f"bearing position {position * 1000.0:.12g} mm lies outside shaft range "
                f"[{zmin * 1000.0:.12g}, {zmax * 1000.0:.12g}] mm"
            )

    stations = sorted([*z_by_node.values(), *map(float, positions_m)])
    unique: list[float] = []
    for value in stations:
        if not unique or abs(value - unique[-1]) > tol:
            unique.append(value)
    new_nodes = [Node(index + 1, value) for index, value in enumerate(unique)]

    def source_for(midpoint: float):
        for shaft in shafts:
            a = z_by_node[int(shaft.node1)]
            b = z_by_node[int(shaft.node2)]
            lo, hi = min(a, b), max(a, b)
            if lo - tol <= midpoint <= hi + tol:
                return shaft, a, b
        raise IrdinImportError(f"no source shaft element covers z={midpoint:.12g} m")

    new_shafts: list[Any] = []
    for index, (a, b) in enumerate(zip(unique[:-1], unique[1:]), start=1):
        source, source_a, source_b = source_for(0.5 * (a + b))
        if isinstance(source, TaperedShaftElement):
            span = source_b - source_a
            if abs(span) <= tol:
                raise IrdinImportError("zero-length tapered shaft encountered during station insertion")
            fa = (a - source_a) / span
            fb = (b - source_a) / span
            do_a = source.outer_diameter_1_m + fa * (
                source.outer_diameter_2_m - source.outer_diameter_1_m
            )
            do_b = source.outer_diameter_1_m + fb * (
                source.outer_diameter_2_m - source.outer_diameter_1_m
            )
            di_a = source.inner_diameter_1_m + fa * (
                source.inner_diameter_2_m - source.inner_diameter_1_m
            )
            di_b = source.inner_diameter_1_m + fb * (
                source.inner_diameter_2_m - source.inner_diameter_1_m
            )
            new_shafts.append(
                TaperedShaftElement(
                    source.shaft_type, index, index + 1,
                    do_a, do_b, di_a, di_b,
                    source.rho_kg_m3, source.E_pa, source.G_pa, source.axial_force_n,
                )
            )
        elif isinstance(source, ShaftElement):
            new_shafts.append(
                ShaftElement(
                    source.shaft_type, index, index + 1,
                    source.outer_diameter_m, source.inner_diameter_m,
                    source.rho_kg_m3, source.E_pa, source.G_pa,
                    source.damping_factor, source.axial_force_n, source.torque_nm,
                )
            )
        else:
            raise IrdinImportError(
                f"unsupported shaft type during iRdin station insertion: {type(source).__name__}"
            )

    mapped_nodes = []
    for position in positions_m:
        candidates = [abs(node.z_m - position) for node in new_nodes]
        best = min(range(len(candidates)), key=candidates.__getitem__)
        if candidates[best] > tol:
            raise IrdinImportError(f"failed to create exact node for bearing at z={position} m")
        mapped_nodes.append(new_nodes[best].number)
    return new_nodes, new_shafts, mapped_nodes


def load_irdin_project(path: str | Path) -> RotorProject:
    source = Path(path)
    source_text = _read_text(source)
    raw_source = source.read_bytes()
    doc = _parse_document(source_text)
    header = doc.get("irdin", {})
    data = doc["dados"]

    E_pa = _number(data.get("s_melast"), 207.0e9)
    rho_kg_m3 = _number(data.get("s_masesp"), 7850.0)
    poisson = _number(data.get("s_poisson"), 0.3)
    section_rows = _grid_rows(doc.get("secoes"))
    if not section_rows:
        raise IrdinImportError("iRdin [Secoes] section contains no shaft rows")

    nodes, shafts, sketch_sections = _shaft_geometry(
        section_rows,
        E_pa=E_pa,
        rho_kg_m3=rho_kg_m3,
        poisson=poisson,
    )

    # I6 makes every positive bearing/unbalance/probe location an exact FE station
    # before mapping. Negative response positions retain the historical
    # support-reference convention and remain fail-closed until that convention
    # is qualified for a concrete source case.
    bearing_rows = _grid_rows(doc.get("mancais"))
    unbalance_rows = _grid_rows(doc.get("desbal"))
    probe_rows = _grid_rows(doc.get("respo"))
    unbalance = [
        {
            "index": index,
            "position_mm": _number(_cell(row, 0)),
            "phase_deg": _number(_cell(row, 1), 0.0),
            "value": _number(_cell(row, 2), 0.0),
        }
        for index, row in enumerate(unbalance_rows, start=1)
    ]
    probes = [
        {
            "index": index,
            "position_mm": _number(_cell(row, 0)),
            "coordinate": _integer(_cell(row, 1), 1),
            "orientation_deg": _number(_cell(row, 2), 0.0),
        }
        for index, row in enumerate(probe_rows, start=1)
    ]
    bearing_positions_m = [_number(_cell(row, 0)) / 1000.0 for row in bearing_rows]
    package_divisions=max(1,_integer(data.get("p_div"),1))
    raw_mass_rows=_grid_rows(doc.get("massas"))
    mass_center_positions_m=[]
    if raw_mass_rows and not any(_truthy(_cell(row,5)) for row in raw_mass_rows):
        for row in raw_mass_rows:
            xi_mm=_number(_cell(row,0))
            length_mm=_number(_cell(row,1))
            count=package_divisions if _truthy(_cell(row,4)) else 1
            slice_length_mm=length_mm/count
            mass_center_positions_m.extend(
                (xi_mm+(i+0.5)*slice_length_mm)/1000.0
                for i in range(count)
            )
    station_positions_m = [
        *bearing_positions_m,
        *mass_center_positions_m,
        *[item["position_mm"] / 1000.0 for item in unbalance if item["position_mm"] >= 0.0],
        *[item["position_mm"] / 1000.0 for item in probes if item["position_mm"] >= 0.0],
    ]
    nodes, shafts, _ = _insert_exact_stations(nodes, shafts, station_positions_m)

    def exact_node(position_m: float) -> int:
        distances=[abs(float(node.z_m)-float(position_m)) for node in nodes]
        if not distances:
            raise IrdinImportError("iRdin station mapping requires at least one node")
        best=min(range(len(distances)), key=distances.__getitem__)
        if distances[best] > 1.0e-10:
            raise IrdinImportError(
                f"failed to map exact iRdin station at {position_m*1000.0:.12g} mm"
            )
        return int(nodes[best].number)

    bearing_nodes = [exact_node(position) for position in bearing_positions_m]

    masses: list[dict[str, Any]] = []
    for index, row in enumerate(_grid_rows(doc.get("massas")), start=1):
        masses.append(
            {
                "index": index,
                "xi_mm": _number(_cell(row, 0)),
                "length_mm": _number(_cell(row, 1)),
                "mass_kg": _number(_cell(row, 2)),
                "outer_diameter_mm": _number(_cell(row, 3), 0.0),
                "package": _truthy(_cell(row, 4)),
                "ump": _truthy(_cell(row, 5)),
                "inner_diameter_mm": _number(_cell(row, 6), 0.0),
            }
        )

    bearings: list[dict[str, Any]] = []
    advanced_bearings = []
    for index, row in enumerate(bearing_rows, start=1):
        raw_table = _cell(row, 11)
        position_mm = _number(_cell(row, 0))
        name_bearing = _cell(row, 10) or f"Bearing {index}"
        node = int(bearing_nodes[index - 1])
        table_rows: list[dict[str, float]] = []
        table_mapped = False
        interpolation = None
        if raw_table.strip().upper().startswith("TABLE"):
            try:
                imported = parse_irdin_coefficient_table(raw_table, node=node)
            except BearingTableImportError as exc:
                raise IrdinImportError(f"bearing {index}: {exc}") from exc
            table_rows = imported.as_rows()
            interpolation = IRDIN_LEGACY_INTERPOLATION
            policy = legacy_bearing_policy(
                imported.speed_rpm,
                requested_rpm=(
                    _number(data.get("d_rpmi"), 0.0),
                    _number(data.get("d_rpmf"), 0.0),
                    _number(data.get("c_rpmi"), 0.0),
                    _number(data.get("c_rpmf"), 0.0),
                ),
            )
            advanced_bearings.append(
                imported.to_coefficient_bearing(
                    interpolation=interpolation,
                    tag=name_bearing,
                    provenance={
                        "source_bearing_index": index,
                        "source_position_mm": position_mm,
                        "source_name": name_bearing,
                        **policy,
                    },
                )
            )
            table_mapped = True
        bearings.append(
            {
                "index": index,
                "node": node,
                "position_mm": position_mm,
                "name": name_bearing,
                "constant_kc": {
                    "kxx": _number(_cell(row, 1), 0.0),
                    "kyy": _number(_cell(row, 2), 0.0),
                    "kxy": _number(_cell(row, 3), 0.0),
                    "kyx": _number(_cell(row, 4), 0.0),
                    "cxx": _number(_cell(row, 5), 0.0),
                    "cyy": _number(_cell(row, 6), 0.0),
                    "cxy": _number(_cell(row, 7), 0.0),
                    "cyx": _number(_cell(row, 8), 0.0),
                },
                "table": table_rows,
                "table_mapped": table_mapped,
                "interpolation": interpolation,
                "policy": policy if table_mapped else None,
                "raw_source": raw_table,
            }
        )

    concentrated = [
        {
            "index": index,
            "position_mm": _number(_cell(row, 0)),
            "mass_kg": _number(_cell(row, 1), 0.0),
            "ix_kg_m2": _number(_cell(row, 2), 0.0),
            "iy_kg_m2": _number(_cell(row, 3), 0.0),
            "iz_kg_m2": _number(_cell(row, 4), 0.0),
        }
        for index, row in enumerate(_grid_rows(doc.get("concent")), start=1)
    ]
    supports = [
        {
            "index": index,
            "bearing_number": _integer(_cell(row, 0), 0),
            "kxx": _number(_cell(row, 1), 0.0),
            "kyy": _number(_cell(row, 2), 0.0),
            "kxy": _number(_cell(row, 3), 0.0),
            "kyx": _number(_cell(row, 4), 0.0),
            "cxx": _number(_cell(row, 5), 0.0),
            "cyy": _number(_cell(row, 6), 0.0),
            "cxy": _number(_cell(row, 7), 0.0),
            "cyx": _number(_cell(row, 8), 0.0),
            "mass_kg": _number(_cell(row, 9), 0.0),
            "name": _cell(row, 10),
        }
        for index, row in enumerate(_grid_rows(doc.get("suporte")), start=1)
    ]

    name = data.get("comp") or source.stem
    sketch = {
        "style": "dyrobes_reference",
        "shaft_length_mm": sum(x["length_mm"] for x in sketch_sections),
        "sections": sketch_sections,
        "masses": masses,
        "bearings": bearings,
        "unbalance": unbalance,
        "probes": probes,
        "concentrated_masses": concentrated,
        "supports": supports,
        "package_divisions": package_divisions,
    }

    blockers: list[dict[str, str]] = []

    def block(code: str, message: str) -> None:
        blockers.append({"code": code, "message": message})

    if masses:
        block(
            "IRDIN_DISTRIBUTED_MASS_UNMAPPED",
            "distributed iRdin mass/package records are preserved for the sketch but are not "
            "silently converted to Stage 1 DISK physics",
        )
    unmapped_bearings = [item for item in bearings if not item["table_mapped"]]
    if unmapped_bearings:
        if any(item["raw_source"].strip() for item in unmapped_bearings):
            block(
                "IRDIN_BEARING_COEFFICIENT_TABLE_UNMAPPED",
                "one or more legacy bearing coefficient sources are not inline TABLE records "
                "and remain unmapped",
            )
        else:
            block(
                "IRDIN_BEARING_DEFINITION_UNMAPPED",
                "legacy bearing locations/constant coefficients without inline TABLE data "
                "remain unmapped",
            )
    if concentrated:
        block(
            "IRDIN_CONCENTRATED_MASS_UNMAPPED",
            "legacy concentrated-mass records are preserved pending an explicit qualified mapping",
        )
    if supports:
        block(
            "IRDIN_FLEXIBLE_SUPPORT_UNMAPPED",
            "legacy flexible-support records are preserved for the sketch pending an explicit "
            "qualified numerical mapping",
        )
    reasons = [item["message"] for item in blockers]

    metadata = {
        "source_format": "iRdin/VB6 INI",
        "source_file": source.name,
        "source_path": str(source),
        "source_sha256": sha256(raw_source).hexdigest(),
        "source_size_bytes": len(raw_source),
        "legacy_irdin_raw": {section: dict(values) for section, values in doc.items()},
        "legacy_irdin": {
            "date": header.get("data", ""),
            "user": header.get("usuario", ""),
            "reference": data.get("ref", ""),
            "line": data.get("linha", ""),
            "frame": data.get("carc", ""),
            "component": data.get("comp", ""),
            "poles": _integer(data.get("polos"), 0),
            "frequency_hz": _number(data.get("freq"), 0.0),
            "nominal_rpm": _number(data.get("nnom"), 0.0),
            "young_pa": E_pa,
            "density_kg_m3": rho_kg_m3,
            "poisson": poisson,
            "campbell": {
                "start_rpm": _number(data.get("c_rpmi"), 0.0),
                "end_rpm": _number(data.get("c_rpmf"), 0.0),
                "division": _number(data.get("c_div"), 0.0),
                "critical_count": _integer(data.get("c_nrrot"), 0),
                "interpolation": _integer(data.get("c_interp"), 0),
            },
            "response": {
                "start_rpm": _number(data.get("d_rpmi"), 0.0),
                "end_rpm": _number(data.get("d_rpmf"), 0.0),
                "division": _number(data.get("d_div"), 0.0),
                "modes": _integer(data.get("d_nrmodos"), 0),
            },
        },
        "sketch": sketch,
        "numerical_readiness": {
            "status": "BLOCKED_FOR_NUMERICAL_ANALYSIS" if reasons else "READY",
            "exact_shaft_geometry": True,
            "mapped_inline_bearing_tables": sum(
                1 for item in bearings if item["table_mapped"]
            ),
            "components": {
                "geometry": "PASS",
                "bearing_tables": "PASS" if all(item["table_mapped"] for item in bearings) else "PARTIAL",
                "bearing_extrapolation": (
                    "PASS_I5_LEGACY_POLICY"
                    if bearings and all(
                        item["table_mapped"]
                        and item["interpolation"] == IRDIN_LEGACY_INTERPOLATION
                        for item in bearings
                    )
                    else "NOT_QUALIFIED"
                ),
                "mass_semantics": "PASS" if masses and not any(item["ump"] for item in masses) else ("NOT_APPLICABLE" if not masses else "BLOCKED_BY_UMP_SEMANTICS"),
                "mass_inertia": "PASS_I2_LOGICAL_ONLY" if masses and not any(item["ump"] for item in masses) else ("NOT_APPLICABLE" if not masses else "BLOCKED"),
                "mass_native_materialization": (
                    "NOT_QUALIFIED"
                    if masses and not any(item["ump"] for item in masses)
                    else ("BLOCKED_BY_UMP_SEMANTICS" if masses else "NOT_APPLICABLE")
                ),
                "support_semantics": "PENDING" if supports else "NOT_APPLICABLE",
                "support_native_assembly": "NOT_QUALIFIED" if supports else "NOT_APPLICABLE",
                "unbalance": "PENDING_I6" if unbalance else "NOT_APPLICABLE",
                "probes": "PENDING_I6" if probes else "NOT_APPLICABLE",
            },
            "blockers": blockers,
            "reasons": reasons,
        },
    }

    mass_spans = (
        build_mass_spans(metadata)
        if masses and not any(item["ump"] for item in masses)
        else []
    )
    materialized_disks=[]
    if mass_spans:
        try:
            materialized_disks=materialize_mass_disks(mass_spans,nodes)
            metadata["legacy_irdin"]["mass_audit"]=mass_audit(mass_spans)
            metadata["numerical_readiness"]["components"]["mass_native_materialization"]="PASS_I7_DISK_MATERIALIZATION"
            blockers[:] = [x for x in blockers if x["code"]!="IRDIN_DISTRIBUTED_MASS_UNMAPPED"]
        except Exception as exc:
            metadata["numerical_readiness"]["components"]["mass_native_materialization"]="BLOCKED"
            metadata["numerical_readiness"].setdefault("mapping_diagnostics",[]).append(
                {"component":"mass_native_materialization","message":str(exc)}
            )
    metadata["numerical_readiness"]["blockers"]=blockers
    metadata["numerical_readiness"]["reasons"]=[item["message"] for item in blockers]
    metadata["numerical_readiness"]["status"]=(
        "BLOCKED_FOR_NUMERICAL_ANALYSIS" if blockers else "READY"
    )
    mapped_supports = []
    if supports:
        try:
            mapped_supports = build_bearing_supports(metadata)
            metadata["numerical_readiness"]["components"]["support_semantics"] = "PASS_I3_DOMAIN_ONLY"
        except IrdinSupportMappingError as exc:
            metadata["numerical_readiness"]["components"]["support_semantics"] = "BLOCKED"
            metadata["numerical_readiness"].setdefault("mapping_diagnostics", []).append(
                {"component": "supports", "message": str(exc)}
            )
    mapped_forces = []
    mapped_probes = []
    try:
        mapped_forces = build_unbalance_forces(unbalance, nodes)
        mapped_probes = build_response_probes(probes, nodes)
        audit = excitation_audit(unbalance, probes, mapped_forces, mapped_probes)
        metadata["legacy_irdin"]["excitation_probe_audit"] = audit
        metadata["numerical_readiness"]["components"]["unbalance"] = (
            "PASS_I6_LEGACY_UNBALANCE" if unbalance else "NOT_APPLICABLE"
        )
        metadata["numerical_readiness"]["components"]["probes"] = (
            "PASS_I6_RESPONSE_PROBES" if probes else "NOT_APPLICABLE"
        )
    except IrdinExcitationMappingError as exc:
        metadata["numerical_readiness"]["components"]["unbalance"] = (
            "BLOCKED" if unbalance else "NOT_APPLICABLE"
        )
        metadata["numerical_readiness"]["components"]["probes"] = (
            "BLOCKED" if probes else "NOT_APPLICABLE"
        )
        metadata["numerical_readiness"].setdefault("mapping_diagnostics", []).append(
            {"component": "excitation_probes", "message": str(exc)}
        )
        block(
            "IRDIN_EXCITATION_PROBE_UNMAPPED",
            "legacy unbalance/probe records could not be mapped under the qualified I6 contract",
        )
        metadata["numerical_readiness"]["blockers"] = blockers
        metadata["numerical_readiness"]["reasons"] = [item["message"] for item in blockers]
        metadata["numerical_readiness"]["status"] = "BLOCKED_FOR_NUMERICAL_ANALYSIS"

    model = RotorModel(
        nodes=nodes,
        shafts=shafts,
        disks=materialized_disks,
        advanced_bearings=advanced_bearings,
        mass_spans=mass_spans,
        supports=mapped_supports,
        forces=mapped_forces,
        probes=mapped_probes,
    )
    return RotorProject(name=name, model=model, analyses=[], metadata=metadata)


__all__ = ["IrdinImportError", "load_irdin_project"]
