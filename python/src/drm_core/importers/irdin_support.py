from __future__ import annotations

"""I3 semantic/domain mapping for historical iRdin bearing supports.

This module maps qualified source fields into an explicit domain object only.
It does not assemble rotor/support matrices; that native step is I4.
"""

import math
from typing import Any

from drm_core.domain.model import BearingSupport


class IrdinSupportMappingError(ValueError):
    pass


def build_bearing_supports(metadata: dict[str,Any]) -> list[BearingSupport]:
    if metadata.get("source_format")!="iRdin/VB6 INI":
        raise IrdinSupportMappingError("support mapping requires iRdin/VB6 metadata")
    sketch=dict(metadata.get("sketch") or {})
    source_supports=list(sketch.get("supports") or [])
    source_bearings=list(sketch.get("bearings") or [])
    result=[]
    seen=set()
    for source in source_supports:
        index=int(source["index"])
        bearing_number=int(source["bearing_number"])
        if bearing_number<1 or bearing_number>len(source_bearings):
            raise IrdinSupportMappingError(
                f"support {index}: bearing_number={bearing_number} outside 1..{len(source_bearings)}"
            )
        if bearing_number in seen:
            raise IrdinSupportMappingError(
                f"support {index}: duplicate support for bearing {bearing_number}"
            )
        seen.add(bearing_number)
        bearing=source_bearings[bearing_number-1]
        values=[
            float(source["mass_kg"]),
            float(source["kxx"]),float(source["kyy"]),
            float(source["kxy"]),float(source["kyx"]),
            float(source["cxx"]),float(source["cyy"]),
            float(source["cxy"]),float(source["cyx"]),
        ]
        if any(not math.isfinite(v) for v in values):
            raise IrdinSupportMappingError(f"support {index}: coefficients/mass must be finite")
        if values[0]<=0:
            raise IrdinSupportMappingError(
                f"support {index}: historical native contract requires mass > 0"
            )
        result.append(BearingSupport(
            bearing_number=bearing_number,
            node=int(bearing["node"]),
            mass_kg=values[0],
            kxx_n_m=values[1],
            kyy_n_m=values[2],
            kxy_n_m=values[3],
            kyx_n_m=values[4],
            cxx_ns_m=values[5],
            cyy_ns_m=values[6],
            cxy_ns_m=values[7],
            cyx_ns_m=values[8],
            tag=str(source.get("name") or f"iRdin support {index}"),
            provenance={
                "source_format":"iRdin/VB6 [Suporte]",
                "source_index":index,
                "source_bearing_number":bearing_number,
                "source_axis_convention":"X/Z",
                "domain_axis_convention":"X/Y",
                "axis_mapping":"X->X; Z->Y; coefficient order/sign unchanged",
                "semantic_authority":"validation/irdin/semantic_contract.json",
            },
        ))
    return result


def support_audit(supports:list[BearingSupport]) -> dict[str,Any]:
    return {
        "status":"PASS",
        "count":len(supports),
        "total_mass_kg":float(sum(x.mass_kg for x in supports)),
        "supports":[
            {
                "bearing_number":x.bearing_number,
                "node":x.node,
                "mass_kg":x.mass_kg,
                "K_n_m":[[x.kxx_n_m,x.kxy_n_m],[x.kyx_n_m,x.kyy_n_m]],
                "C_ns_m":[[x.cxx_ns_m,x.cxy_ns_m],[x.cyx_ns_m,x.cyy_ns_m]],
                "axis_mapping":x.provenance["axis_mapping"],
            }
            for x in supports
        ],
    }


__all__=["IrdinSupportMappingError","build_bearing_supports","support_audit"]
