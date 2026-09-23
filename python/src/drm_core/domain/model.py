from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Sequence
import hashlib, json

@dataclass(frozen=True)
class Node:
    number: int
    z_m: float

@dataclass(frozen=True)
class ShaftElement:
    shaft_type: int
    node1: int
    node2: int
    outer_diameter_m: float
    inner_diameter_m: float
    rho_kg_m3: float
    E_pa: float
    G_pa: float = 0.0
    damping_factor: float = 0.0
    axial_force_n: float = 0.0
    torque_nm: float = 0.0

@dataclass(frozen=True)
class TaperedShaftElement:
    shaft_type: int
    node1: int
    node2: int
    outer_diameter_1_m: float
    outer_diameter_2_m: float
    inner_diameter_1_m: float
    inner_diameter_2_m: float
    rho_kg_m3: float
    E_pa: float
    G_pa: float = 0.0
    axial_force_n: float = 0.0

@dataclass(frozen=True)
class AsymmetricShaftElement:
    shaft_type: int
    node1: int
    node2: int
    EIx_nm2: float
    EIy_nm2: float
    phi_x: float
    phi_y: float
    rhoA_kg_m: float
    rhoI_kg_m: float
    damping_factor: float = 0.0
    axial_force_n: float = 0.0

@dataclass(frozen=True)
class Disk:
    disk_type: int
    node: int
    p3: float
    p4: float
    p5: float
    p6: float = 0.0

    @staticmethod
    def geometric(node:int,rho_kg_m3:float,thickness_m:float,outer_diameter_m:float,
                  inner_diameter_m:float=0.0,disk_type:int=1)->"Disk":
        return Disk(disk_type,node,rho_kg_m3,thickness_m,outer_diameter_m,inner_diameter_m)

@dataclass(frozen=True)
class Bearing:
    bearing_type: int
    node: int
    properties: tuple[float,...] = ()

@dataclass(frozen=True)
class Force:
    force_type: int
    parameters: tuple[float,...] = ()

    @staticmethod
    def unbalance(node:int,magnitude_kg_m:float,phase_rad:float=0.0)->"Force":
        return Force(1,(float(node),float(magnitude_kg_m),float(phase_rad)))

    @staticmethod
    def couple_unbalance(node:int,magnitude_kg_m2:float,phase_rad:float=0.0)->"Force":
        return Force(2,(float(node),float(magnitude_kg_m2),float(phase_rad)))

    @staticmethod
    def bend_marker()->"Force":
        return Force(3,())

    @staticmethod
    def rotating_moment(node1:int,node2:int,magnitude_nm:float,phase_rad:float=0.0)->"Force":
        return Force(8,(float(node1),float(node2),float(magnitude_nm),float(phase_rad)))

@dataclass(frozen=True)
class BendPoint:
    node: int
    x_m: float
    y_m: float = 0.0

ShaftLike = ShaftElement | TaperedShaftElement | AsymmetricShaftElement

@dataclass
class RotorModel:
    nodes: list[Node] = field(default_factory=list)
    shafts: list[ShaftLike] = field(default_factory=list)
    disks: list[Disk] = field(default_factory=list)
    bearings: list[Bearing] = field(default_factory=list)
    forces: list[Force] = field(default_factory=list)
    bend: list[BendPoint] = field(default_factory=list)

    @classmethod
    def from_legacy_arrays(cls,node,shaft,disc=(),bearing=(),force=(),bend=())->"RotorModel":
        node_rows=[list(r) if isinstance(r,(list,tuple)) else [r] for r in node]
        if node_rows and len(node_rows[0])==1:
            nodes=[Node(i+1,float(r[0])) for i,r in enumerate(node_rows)]
        else:
            nodes=[Node(int(r[0]),float(r[1])) for r in node_rows]
        shafts:list[ShaftLike]=[]
        for r in shaft:
            rr=list(r)
            st=int(round(rr[0])); rr=rr+[0.0]*11
            if 1<=st<=8:
                shafts.append(ShaftElement(st,int(rr[1]),int(rr[2]),*map(float,rr[3:11])))
            elif 21<=st<=28:
                shafts.append(TaperedShaftElement(st,int(rr[1]),int(rr[2]),*map(float,rr[3:11])))
            elif 11<=st<=18:
                shafts.append(AsymmetricShaftElement(st,int(rr[1]),int(rr[2]),*map(float,rr[3:11])))
            else:
                raise ValueError(f"Unsupported legacy shaft type {st}")
        disks=[Disk(int(round(r[0])),int(r[1]),*map(float,(list(r[2:])+[0.0]*4)[:4])) for r in disc]
        bearings=[Bearing(int(round(r[0])),int(r[1]),tuple(map(float,r[2:]))) for r in bearing]
        forces=[Force(int(round(r[0])),tuple(map(float,r[1:]))) for r in force]
        bend_points:list[BendPoint]=[]
        bend_rows=[list(r) if isinstance(r,(list,tuple)) else [r] for r in bend]
        if bend_rows:
            nc=len(bend_rows[0])
            if nc==1:
                if len(bend_rows)!=len(nodes):
                    raise ValueError("Legacy one-column bend requires one row per node")
                bend_points=[BendPoint(nodes[i].number,float(r[0]),0.0) for i,r in enumerate(bend_rows)]
            elif nc==2:
                bend_points=[BendPoint(int(r[0]),float(r[1]),0.0) for r in bend_rows]
            elif nc==3:
                bend_points=[BendPoint(int(r[0]),float(r[1]),float(r[2])) for r in bend_rows]
            else:
                raise ValueError("Legacy bend must have 1, 2 or 3 columns")
        return cls(nodes,shafts,disks,bearings,forces,bend_points)

    def canonical_dict(self):
        return {
            "nodes":[asdict(x) for x in self.nodes],
            "shafts":[{"kind":type(x).__name__,**asdict(x)} for x in self.shafts],
            "disks":[asdict(x) for x in self.disks],
            "bearings":[asdict(x) for x in self.bearings],
            "forces":[asdict(x) for x in self.forces],
            "bend":[asdict(x) for x in self.bend],
        }

    def model_hash(self)->str:
        return hashlib.sha256(json.dumps(self.canonical_dict(),sort_keys=True,separators=(",",":"),default=list).encode()).hexdigest()
