from __future__ import annotations

"""Qualified I2 mass/inertia interpretation for imported iRdin projects.

No solver call lives here. The output is an explicit logical RotorMassSpan plus
a deterministic slice description matching the demonstrated legacy package
contract. Native disk materialization remains a later gate.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable

from drm_core.domain.model import Disk, Node, RotorMassSpan


class IrdinMassMappingError(ValueError):
    pass


@dataclass(frozen=True)
class MassSlice:
    source_index: int
    slice_index: int
    z_start_m: float
    length_m: float
    mass_kg: float
    outer_diameter_m: float
    inner_diameter_m: float
    diametral_inertia_kgm2: float
    polar_inertia_kgm2: float

    @property
    def z_center_m(self) -> float:
        return self.z_start_m + 0.5*self.length_m


def disk_inertias_kg_m2(
    mass_kg: float,
    length_m: float,
    outer_diameter_m: float,
    inner_diameter_m: float,
) -> tuple[float, float]:
    """Return (diametral Id, polar Ip) using the demonstrated RotorDin contract."""
    values=(mass_kg,length_m,outer_diameter_m,inner_diameter_m)
    if any(not math.isfinite(float(x)) for x in values):
        raise IrdinMassMappingError("mass geometry/inertia inputs must be finite")
    if mass_kg < 0.0 or length_m <= 0.0 or outer_diameter_m <= 0.0:
        raise IrdinMassMappingError("mass>=0, length>0 and OD>0 are required")
    if inner_diameter_m < 0.0 or inner_diameter_m >= outer_diameter_m:
        raise IrdinMassMappingError("expected 0 <= ID < OD")
    ip=mass_kg/8.0*(outer_diameter_m**2+inner_diameter_m**2)
    id_=0.5*ip+mass_kg*length_m**2/12.0
    return float(id_),float(ip)


def _sections(sketch: dict[str, Any]) -> list[dict[str, Any]]:
    sections=list(sketch.get("sections") or [])
    if not sections:
        raise IrdinMassMappingError("iRdin sketch has no shaft sections")
    return sections


def _section_at(sketch: dict[str, Any], position_mm: float) -> tuple[dict[str, Any],float,float]:
    x0=0.0
    tol=1e-9
    for section in _sections(sketch):
        length=float(section["length_mm"])
        x1=x0+length
        if position_mm <= x1+tol:
            if position_mm < x0-tol:
                break
            ratio=0.0 if length<=0 else max(0.0,min(1.0,(position_mm-x0)/length))
            return section,x0,ratio
        x0=x1
    raise IrdinMassMappingError(
        f"mass center {position_mm:g} mm is outside shaft length {x0:g} mm"
    )


def _physical_shaft_outer_mm(sketch: dict[str, Any], position_mm: float) -> float:
    section,_x0,ratio=_section_at(sketch,position_mm)
    left=float(section["diameter_mm"])
    right=float(section.get("final_diameter_mm") or left)
    return left+(right-left)*ratio


def _effective_geometry_mm(
    sketch: dict[str, Any],
    mass: dict[str, Any],
    *,
    center_mm: float,
) -> tuple[float,float,dict[str,Any]]:
    source_outer=float(mass.get("outer_diameter_mm") or 0.0)
    source_inner=float(mass.get("inner_diameter_mm") or 0.0)
    local_outer=_physical_shaft_outer_mm(sketch,center_mm)
    section,_,_=_section_at(sketch,center_mm)

    if source_outer > 0.0:
        outer=source_outer
        outer_source="EXPLICIT_IRDIN"
    else:
        outer=local_outer
        outer_source="LOCAL_PHYSICAL_SHAFT_OD"

    if source_inner > 0.0:
        inner=source_inner
        inner_source="EXPLICIT_IRDIN"
    elif source_outer <= 0.0:
        # Historical zero/zero special case: disk OD falls back to shaft and
        # the bore stays zero rather than creating ID==OD.
        inner=0.0
        inner_source="LEGACY_SOLID_DISK_FALLBACK"
    elif int(section.get("rib_count") or 0)>0 and float(section.get("package_diameter_mm") or 0.0)>0.0:
        inner=float(section["package_diameter_mm"])
        inner_source="RIBBED_PACKAGE_DPCT"
    else:
        inner=local_outer
        inner_source="LOCAL_PHYSICAL_SHAFT_OD"

    if outer<=0 or inner<0 or inner>=outer:
        raise IrdinMassMappingError(
            f"invalid resolved mass geometry at {center_mm:g} mm: OD={outer:g}, ID={inner:g}"
        )
    return outer,inner,{
        "outer_source":outer_source,
        "inner_source":inner_source,
        "source_segment_index":int(section["index"]),
        "local_physical_shaft_od_mm":float(local_outer),
    }


def build_mass_spans(metadata: dict[str,Any]) -> list[RotorMassSpan]:
    """Map preserved iRdin mass records into explicit source-qualified spans."""
    if metadata.get("source_format")!="iRdin/VB6 INI":
        raise IrdinMassMappingError("mass-span mapping requires iRdin/VB6 metadata")
    sketch=dict(metadata.get("sketch") or {})
    masses=list(sketch.get("masses") or [])
    divisions=max(1,int(sketch.get("package_divisions") or 1))
    result=[]
    intervals=[]
    shaft_length=float(sketch.get("shaft_length_mm") or 0.0)
    for source in masses:
        idx=int(source["index"])
        xi=float(source["xi_mm"])
        length=float(source["length_mm"])
        mass=float(source["mass_kg"])
        package=bool(source.get("package"))
        ump=bool(source.get("ump"))
        if ump:
            raise IrdinMassMappingError(
                f"mass {idx}: UMP producer-side scale is not qualified by I1"
            )
        if not all(math.isfinite(v) for v in (xi,length,mass)):
            raise IrdinMassMappingError(f"mass {idx}: non-finite Xi/LC/mass")
        if xi<0 or length<=0 or mass<0 or xi+length>shaft_length+1e-9:
            raise IrdinMassMappingError(f"mass {idx}: invalid Xi/LC span")
        for ia,ib,j in intervals:
            if xi < ib-1e-9 and ia < xi+length-1e-9:
                raise IrdinMassMappingError(f"mass {idx}: overlaps mass {j}")
        intervals.append((xi,xi+length,idx))
        center=xi+0.5*length
        outer_mm,inner_mm,geometry=_effective_geometry_mm(sketch,source,center_mm=center)
        id_,ip=disk_inertias_kg_m2(
            mass,length/1000.0,outer_mm/1000.0,inner_mm/1000.0
        )
        result.append(RotorMassSpan(
            z_start_m=xi/1000.0,
            length_m=length/1000.0,
            mass_kg=mass,
            outer_diameter_m=outer_mm/1000.0,
            inner_diameter_m=inner_mm/1000.0,
            package=package,
            divisions=divisions if package else 1,
            diametral_inertia_kgm2=id_,
            polar_inertia_kgm2=ip,
            inertia_source="LEGACY_GEOMETRY_DERIVED",
            tag=f"iRdin mass {idx}",
            provenance={
                "source_format":"iRdin/VB6 [Massas]",
                "source_index":idx,
                "source_values":dict(source),
                "geometry_resolution":geometry,
                "semantic_authority":"validation/irdin/semantic_contract.json",
            },
        ))
    return result


def span_slices(span:RotorMassSpan) -> list[MassSlice]:
    count=int(span.divisions if span.package else 1)
    if count<1:
        raise IrdinMassMappingError("mass divisions must be >= 1")
    length=span.length_m/count
    mass=span.mass_kg/count
    result=[]
    source_index=int(span.provenance.get("source_index",0))
    for i in range(count):
        id_,ip=disk_inertias_kg_m2(
            mass,length,span.outer_diameter_m,span.inner_diameter_m
        )
        result.append(MassSlice(
            source_index=source_index,
            slice_index=i+1,
            z_start_m=span.z_start_m+i*length,
            length_m=length,
            mass_kg=mass,
            outer_diameter_m=span.outer_diameter_m,
            inner_diameter_m=span.inner_diameter_m,
            diametral_inertia_kgm2=id_,
            polar_inertia_kgm2=ip,
        ))
    return result


def all_mass_slices(spans:Iterable[RotorMassSpan]) -> list[MassSlice]:
    return [piece for span in spans for piece in span_slices(span)]


def materialize_mass_disks(
    spans: Iterable[RotorMassSpan],
    nodes: Iterable[Node],
) -> list[Disk]:
    """Map qualified slices to existing inertial disks at exact FE stations."""
    nodes=list(nodes)
    positions={int(node.number):float(node.z_m) for node in nodes}
    result=[]
    for piece in all_mass_slices(spans):
        if not positions:
            raise IrdinMassMappingError("mass materialization requires FE nodes")
        distances={node:abs(z-piece.z_center_m) for node,z in positions.items()}
        node=min(distances,key=distances.get)
        if distances[node] > 1.0e-10:
            raise IrdinMassMappingError(
                f"no exact FE node at mass slice center {piece.z_center_m:.12g} m"
            )
        result.append(Disk.inertial(
            node,
            piece.mass_kg,
            piece.diametral_inertia_kgm2,
            piece.polar_inertia_kgm2,
            disk_type=2,
        ))
    return result


def mass_audit(spans:Iterable[RotorMassSpan]) -> dict[str,Any]:
    spans=list(spans)
    slices=all_mass_slices(spans)
    total=sum(x.mass_kg for x in slices)
    if total<=0:
        center=0.0
    else:
        center=sum(x.mass_kg*x.z_center_m for x in slices)/total
    polar=sum(x.polar_inertia_kgm2 for x in slices)
    # Whole assembly diametral inertia about its mass centroid.
    diametral=sum(
        x.diametral_inertia_kgm2+x.mass_kg*(x.z_center_m-center)**2
        for x in slices
    )
    logical_total=sum(x.mass_kg for x in spans)
    logical_moment=sum(x.mass_kg*x.z_center_m for x in spans)
    return {
        "status":"PASS",
        "logical_spans":len(spans),
        "materialized_slices":len(slices),
        "mass_kg":float(total),
        "logical_mass_kg":float(logical_total),
        "center_m":float(center),
        "logical_first_moment_kg_m":float(logical_moment),
        "slice_first_moment_kg_m":float(sum(x.mass_kg*x.z_center_m for x in slices)),
        "polar_inertia_sum_kgm2":float(polar),
        "diametral_inertia_about_cg_kgm2":float(diametral),
        "slices":[asdict(x)|{"z_center_m":x.z_center_m} for x in slices],
    }


__all__=[
    "IrdinMassMappingError","MassSlice","disk_inertias_kg_m2",
    "build_mass_spans","span_slices","all_mass_slices","materialize_mass_disks","mass_audit",
]
