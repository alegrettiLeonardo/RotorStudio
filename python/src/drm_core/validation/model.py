from drm_core.domain.model import RotorModel,ShaftElement,TaperedShaftElement,AsymmetricShaftElement
class ModelValidationError(ValueError): pass

def validate_model(m:RotorModel, *, stationary:bool=True)->None:
    if not m.nodes: raise ModelValidationError("RotorModel.nodes: received empty list; expected at least one node; add nodes before analysis")
    ids=[n.number for n in m.nodes]
    if len(ids)!=len(set(ids)): raise ModelValidationError(f"RotorModel.nodes: received duplicate node numbers {ids}; expected unique node numbers; renumber nodes")
    z={n.number:n.z_m for n in m.nodes}
    for i,s in enumerate(m.shafts,1):
        if s.node1 not in z or s.node2 not in z: raise ModelValidationError(f"ShaftElement[{i}]: received connectivity ({s.node1},{s.node2}); expected existing nodes; correct node references")
        L=z[s.node2]-z[s.node1]
        if L<=0: raise ModelValidationError(f"ShaftElement[{i}]: received Le={L}; expected Le > 0; correct node axial positions/connectivity")
        if isinstance(s,ShaftElement):
            if not (s.outer_diameter_m>s.inner_diameter_m>=0): raise ModelValidationError(f"ShaftElement[{i}]: received do={s.outer_diameter_m}, di={s.inner_diameter_m}; expected do > di >= 0; correct diameters")
            if s.E_pa<=0 or s.rho_kg_m3<=0: raise ModelValidationError(f"ShaftElement[{i}]: received E={s.E_pa}, rho={s.rho_kg_m3}; expected E>0 and rho>0; correct material")
            if s.shaft_type not in range(1,9): raise ModelValidationError(f"ShaftElement[{i}]: received type={s.shaft_type}; expected circular type 1..8")
            if s.shaft_type not in (1,5,7,8) and s.G_pa<=0: raise ModelValidationError(f"ShaftElement[{i}]: received G={s.G_pa}; expected G>0 when shear is enabled; correct shear modulus")
        elif isinstance(s,TaperedShaftElement):
            if not (s.outer_diameter_1_m>s.inner_diameter_1_m>=0 and s.outer_diameter_2_m>s.inner_diameter_2_m>=0): raise ModelValidationError(f"TaperedShaftElement[{i}]: invalid end diameters; expected do1>di1>=0 and do2>di2>=0")
            if s.E_pa<=0 or s.rho_kg_m3<=0: raise ModelValidationError(f"TaperedShaftElement[{i}]: expected E>0 and rho>0")
        elif isinstance(s,AsymmetricShaftElement):
            if stationary: raise ModelValidationError(f"AsymmetricShaftElement[{i}]: type={s.shaft_type} belongs to rotating-frame solver; stationary solver does not accept it")
    for i,d in enumerate(m.disks,1):
        if d.node not in z: raise ModelValidationError(f"Disk[{i}]: received node={d.node}; expected existing node; correct node")
        if d.disk_type not in (1,2,3,4): raise ModelValidationError(f"Disk[{i}]: received type={d.disk_type}; expected 1..4; choose supported legacy disk type")
    for i,b in enumerate(m.bearings,1):
        if b.node not in z: raise ModelValidationError(f"Bearing[{i}]: received node={b.node}; expected existing node; correct node")
        if b.bearing_type not in (1,2,3,4,5,6,7,8): raise ModelValidationError(f"Bearing[{i}]: received type={b.bearing_type}; expected legacy type 1..8")
