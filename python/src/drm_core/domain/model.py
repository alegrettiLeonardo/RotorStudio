from __future__ import annotations
from dataclasses import dataclass, field
from typing import Union
import hashlib, json
from numbers import Real
from .bearings import AdvancedBearing

@dataclass(frozen=True)
class Node:
    number: int
    z_m: float

@dataclass(frozen=True)
class ShaftElement:
    shaft_type: int; node1: int; node2: int; outer_diameter_m: float; inner_diameter_m: float
    rho_kg_m3: float; E_pa: float; G_pa: float=0.0; damping_factor: float=0.0
    axial_force_n: float=0.0; torque_nm: float=0.0
    def legacy_row(self)->list[float]:
        return [self.shaft_type,self.node1,self.node2,self.outer_diameter_m,self.inner_diameter_m,self.rho_kg_m3,self.E_pa,self.G_pa,self.damping_factor,self.axial_force_n,self.torque_nm]

@dataclass(frozen=True)
class TaperedShaftElement:
    shaft_type:int; node1:int; node2:int; outer_diameter_1_m:float; outer_diameter_2_m:float
    inner_diameter_1_m:float; inner_diameter_2_m:float; rho_kg_m3:float; E_pa:float; G_pa:float=0.0; axial_force_n:float=0.0
    def legacy_row(self)->list[float]:
        return [self.shaft_type,self.node1,self.node2,self.outer_diameter_1_m,self.outer_diameter_2_m,self.inner_diameter_1_m,self.inner_diameter_2_m,self.rho_kg_m3,self.E_pa,self.G_pa,self.axial_force_n]

@dataclass(frozen=True)
class AsymmetricShaftElement:
    shaft_type:int; node1:int; node2:int; EIx_nm2:float; EIy_nm2:float; phi_x:float; phi_y:float
    rhoA_kg_m:float; rhoI_kg_m:float; damping_factor:float=0.0; axial_force_n:float=0.0
    def legacy_row(self)->list[float]:
        return [self.shaft_type,self.node1,self.node2,self.EIx_nm2,self.EIy_nm2,self.phi_x,self.phi_y,self.rhoA_kg_m,self.rhoI_kg_m,self.damping_factor,self.axial_force_n]

ShaftLike=Union[ShaftElement,TaperedShaftElement,AsymmetricShaftElement]

@dataclass(frozen=True)
class Disk:
    disk_type: int; node: int; p3: float; p4: float; p5: float; p6: float=0.0
    @staticmethod
    def geometric(node:int,rho_kg_m3:float,thickness_m:float,outer_diameter_m:float,inner_diameter_m:float=0.0,disk_type:int=1)->"Disk":
        return Disk(disk_type,node,rho_kg_m3,thickness_m,outer_diameter_m,inner_diameter_m)
    @staticmethod
    def inertial(node:int,mass_kg:float,diametral_inertia_kgm2:float,polar_inertia_kgm2:float=0.0,disk_type:int=2)->"Disk":
        return Disk(disk_type,node,mass_kg,diametral_inertia_kgm2,polar_inertia_kgm2,0.0)
    @staticmethod
    def anisotropic(node:int,mass_kg:float,Ix_kgm2:float,Iy_kgm2:float,Ip_kgm2:float=0.0,disk_type:int=5)->"Disk":
        return Disk(disk_type,node,mass_kg,Ix_kgm2,Iy_kgm2,Ip_kgm2)

@dataclass(frozen=True)
class Bearing:
    bearing_type: int; node: int; properties: tuple[float,...]=()

@dataclass(frozen=True)
class Force:
    force_type:int; values:tuple[float,...]
    def legacy_row(self)->list[float]: return [self.force_type,*self.values]

@dataclass(frozen=True)
class BendPoint:
    node:int; x_m:float; y_m:float=0.0

@dataclass(frozen=True)
class RotorDefinition:
    node1:int; node2:int; speed_factor:float
    def legacy_row(self)->list[float]: return [self.node1,self.node2,self.speed_factor]

@dataclass
class RotorModel:
    nodes:list[Node]=field(default_factory=list)
    shafts:list[ShaftLike]=field(default_factory=list)
    disks:list[Disk]=field(default_factory=list)
    bearings:list[Bearing]=field(default_factory=list)
    forces:list[Force]=field(default_factory=list)
    bend:list[BendPoint]=field(default_factory=list)
    rotors:list[RotorDefinition]=field(default_factory=list)
    advanced_bearings:list[AdvancedBearing]=field(default_factory=list)
    @classmethod
    def from_legacy_arrays(cls,node,shaft,disc,bearing,force=None,bend=None,rotors=None)->"RotorModel":
        nodes=[Node(int(r[0]),float(r[1])) for r in node]
        shafts=[]
        for r in shaft:
            rr=list(r)+[0.0]*11; t=int(round(rr[0]))
            if 1<=t<=8: shafts.append(ShaftElement(t,int(rr[1]),int(rr[2]),*map(float,rr[3:11])))
            elif 21<=t<=28: shafts.append(TaperedShaftElement(t,int(rr[1]),int(rr[2]),*map(float,rr[3:11])))
            elif 11<=t<=18: shafts.append(AsymmetricShaftElement(t,int(rr[1]),int(rr[2]),*map(float,rr[3:11])))
            else: raise ValueError(f"unsupported legacy shaft type {t}")
        disks=[Disk(int(round(r[0])),int(r[1]),*map(float,(list(r[2:])+[0.0]*4)[:4])) for r in disc]
        bearings=[Bearing(int(round(r[0])),int(r[1]),tuple(map(float,r[2:]))) for r in bearing]
        forces=[Force(int(round(r[0])),tuple(map(float,r[1:]))) for r in (force or [])]
        bends=[]
        if bend:
            for i,r in enumerate(bend,1):
                rr=list(r)
                if len(rr)==1: bends.append(BendPoint(i,float(rr[0]),0.0))
                elif len(rr)==2: bends.append(BendPoint(int(rr[0]),float(rr[1]),0.0))
                else: bends.append(BendPoint(int(rr[0]),float(rr[1]),float(rr[2])))
        rdefs=[RotorDefinition(int(r[0]),int(r[1]),float(r[2])) for r in (rotors or [])]
        return cls(nodes,shafts,disks,bearings,forces,bends,rdefs)
    def canonical_dict(self):
        # Hash/persistence canonical form is intentionally numeric-type stable:
        # callers may construct SI fields with int literals while the legacy
        # JSON round-trip restores them as floats. Those representations are
        # physically identical and must not make a valid result appear stale.
        def norm(v):
            if isinstance(v, bool) or v is None:
                return v
            if isinstance(v, Real):
                return float(v)
            if isinstance(v, dict):
                return {str(k): norm(v[k]) for k in sorted(v)}
            if isinstance(v, (list, tuple)):
                return [norm(x) for x in v]
            return v
        def d(x): return norm(vars(x))
        payload={"nodes":[d(x) for x in self.nodes],"shafts":[d(x) for x in self.shafts],"disks":[d(x) for x in self.disks],"bearings":[d(x) for x in self.bearings],"forces":[d(x) for x in self.forces],"bend":[d(x) for x in self.bend],"rotors":[d(x) for x in self.rotors]}
        # Preserve the frozen Stage-1 model hash byte-for-byte for legacy
        # models.  The new key only participates once an advanced bearing is
        # actually present.
        if self.advanced_bearings:
            payload["advanced_bearings"]=[d(x) for x in self.advanced_bearings]
        return payload
    def model_hash(self)->str:
        return hashlib.sha256(json.dumps(self.canonical_dict(),sort_keys=True,separators=(",",":"),default=list).encode()).hexdigest()
