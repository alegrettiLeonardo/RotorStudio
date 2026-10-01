from __future__ import annotations

"""I6 mapping for qualified iRdin synchronous unbalance and response probes.

The qualified semantic authority is validation/irdin/SEMANTIC_CONTRACT.md:
[Desbal] magnitude is g.mm, phase is degrees, and positive [Respo] stations
refer to physical rotor positions. Production force physics remains in the
existing Fortran synchronous-response path.
"""

from dataclasses import asdict
import math
from typing import Any, Iterable

from drm_core.domain.model import Force, Node, ResponseProbe

GMM_TO_KGM = 1.0e-6


class IrdinExcitationMappingError(ValueError):
    pass


def _exact_node(nodes: Iterable[Node], position_m: float) -> int:
    nodes=list(nodes)
    value=float(position_m)
    if not math.isfinite(value):
        raise IrdinExcitationMappingError("station position must be finite")
    if value < 0.0:
        raise IrdinExcitationMappingError(
            "negative iRdin response/support-reference positions are not qualified by I6"
        )
    if not nodes:
        raise IrdinExcitationMappingError("station mapping requires at least one node")
    distances=[abs(float(node.z_m)-value) for node in nodes]
    best=min(range(len(distances)), key=distances.__getitem__)
    if distances[best] > 1.0e-10:
        raise IrdinExcitationMappingError(
            f"no exact FE node at legacy station {value*1000.0:.12g} mm"
        )
    return int(nodes[best].number)


def build_unbalance_forces(records: list[dict[str, Any]], nodes: Iterable[Node]) -> list[Force]:
    result=[]
    for record in records:
        index=int(record["index"])
        position_mm=float(record["position_mm"])
        phase_deg=float(record.get("phase_deg",0.0))
        source_g_mm=float(record.get("value",0.0))
        if not all(math.isfinite(x) for x in (position_mm,phase_deg,source_g_mm)):
            raise IrdinExcitationMappingError(f"unbalance {index}: values must be finite")
        node=_exact_node(nodes,position_mm/1000.0)
        # Existing Force type 1 contract is (node, U[kg.m], phase[rad]).
        result.append(Force(
            1,
            (
                float(node),
                source_g_mm*GMM_TO_KGM,
                math.radians(phase_deg),
            ),
        ))
    return result


def build_response_probes(records: list[dict[str, Any]], nodes: Iterable[Node]) -> list[ResponseProbe]:
    result=[]
    for record in records:
        index=int(record["index"])
        position_mm=float(record["position_mm"])
        coordinate=int(record.get("coordinate",1))
        orientation_deg=float(record.get("orientation_deg",0.0))
        if not all(math.isfinite(x) for x in (position_mm,orientation_deg)):
            raise IrdinExcitationMappingError(f"probe {index}: values must be finite")
        if coordinate not in (1,2):
            raise IrdinExcitationMappingError(
                f"probe {index}: coordinate={coordinate}; qualified iRdin contract requires 1 (X) or 2 (Z/Y)"
            )
        node=_exact_node(nodes,position_mm/1000.0)
        result.append(ResponseProbe(
            node=node,
            coordinate=coordinate,
            orientation_rad=math.radians(orientation_deg),
            tag=f"iRdin response {index}",
            provenance={
                "source_format":"iRdin/VB6 [Respo]",
                "source_index":index,
                "source_position_mm":position_mm,
                "source_coordinate":coordinate,
                "source_orientation_deg":orientation_deg,
                "source_axis_convention":"X/Z",
                "domain_axis_convention":"X/Y",
                "semantic_authority":"validation/irdin/semantic_contract.json",
            },
        ))
    return result


def excitation_audit(
    unbalance_records: list[dict[str, Any]],
    probe_records: list[dict[str, Any]],
    forces: list[Force],
    probes: list[ResponseProbe],
) -> dict[str, Any]:
    if len(unbalance_records) != len(forces):
        raise IrdinExcitationMappingError("unbalance source/mapped count mismatch")
    if len(probe_records) != len(probes):
        raise IrdinExcitationMappingError("probe source/mapped count mismatch")
    return {
        "status":"PASS",
        "unbalance_count":len(forces),
        "probe_count":len(probes),
        "unbalance_unit_conversion":"g.mm -> kg.m",
        "unbalance_scale":GMM_TO_KGM,
        "phase_conversion":"degree -> radian",
        "force_contract":"Force type 1: (node,U_kg_m,phase_rad); native force amplitude U*omega^2",
        "probe_contract":"coordinate 1=X; coordinate 2=legacy Z mapped to domain Y; orientation in radians",
        "forces":[
            {
                "source_index":int(src["index"]),
                "source_position_mm":float(src["position_mm"]),
                "source_value_g_mm":float(src["value"]),
                "source_phase_deg":float(src.get("phase_deg",0.0)),
                "node":int(force.values[0]),
                "magnitude_kg_m":float(force.values[1]),
                "phase_rad":float(force.values[2]),
            }
            for src,force in zip(unbalance_records,forces)
        ],
        "probes":[asdict(probe) for probe in probes],
    }


__all__=[
    "GMM_TO_KGM","IrdinExcitationMappingError","build_unbalance_forces",
    "build_response_probes","excitation_audit",
]
