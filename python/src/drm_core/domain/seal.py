from dataclasses import dataclass
import math
@dataclass(frozen=True)
class Seal:
    node:int
    pressure_pa:float
    radius_m:float
    length_m:float
    radial_clearance_m:float
    axial_velocity_m_s:float
    friction_coefficient:float
    def validate(self):
        vals=(self.pressure_pa,self.radius_m,self.length_m,self.radial_clearance_m,self.axial_velocity_m_s,self.friction_coefficient)
        if not all(math.isfinite(float(v)) for v in vals):raise ValueError("Seal: all parameters must be finite")
        if self.node<=0:raise ValueError("Seal.node must be positive")
        if self.pressure_pa<0 or self.radius_m<=0 or self.length_m<=0 or self.radial_clearance_m<=0 or self.axial_velocity_m_s<=0 or self.friction_coefficient<=0:
            raise ValueError("Seal contract: P>=0 and R,L,c,V,fric > 0")
    def as_bearing(self):
        from .model import Bearing
        self.validate()
        return Bearing(8,self.node,(self.pressure_pa,self.radius_m,self.length_m,self.radial_clearance_m,self.axial_velocity_m_s,self.friction_coefficient))
