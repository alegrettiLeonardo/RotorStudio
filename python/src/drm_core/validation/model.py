from drm_core.domain.model import RotorModel,ShaftElement,TaperedShaftElement,AsymmetricShaftElement

class ModelValidationError(ValueError):
    pass

def validate_model(m:RotorModel, *, stationary:bool=True)->None:
    if not m.nodes:
        raise ModelValidationError("RotorModel.nodes: received empty list; expected at least one node; add nodes before analysis")
    ids=[n.number for n in m.nodes]
    if len(ids)!=len(set(ids)):
        raise ModelValidationError(f"RotorModel.nodes: received duplicate node numbers {ids}; expected unique node numbers; renumber nodes")
    if sorted(ids)!=list(range(1,len(ids)+1)):
        raise ModelValidationError(f"RotorModel.nodes: received node numbers {ids}; stationary legacy solver expects sequential node numbers 1..{len(ids)} because MATLAB V2 indexes Node_Def by node number; renumber nodes sequentially")
    z={n.number:n.z_m for n in m.nodes}
    for i,s in enumerate(m.shafts,1):
        if s.node1 not in z or s.node2 not in z:
            raise ModelValidationError(f"Shaft[{i}]: received connectivity ({s.node1},{s.node2}); expected existing nodes; correct node references")
        L=z[s.node2]-z[s.node1]
        if L<=0:
            raise ModelValidationError(f"Shaft[{i}]: received Le={L}; expected Le > 0; correct node axial positions/connectivity")
        if isinstance(s,ShaftElement):
            if not (s.outer_diameter_m>s.inner_diameter_m>=0):
                raise ModelValidationError(f"ShaftElement[{i}]: received do={s.outer_diameter_m}, di={s.inner_diameter_m}; expected do > di >= 0; correct diameters")
            if s.E_pa<=0 or s.rho_kg_m3<=0:
                raise ModelValidationError(f"ShaftElement[{i}]: received E={s.E_pa}, rho={s.rho_kg_m3}; expected E>0 and rho>0; correct material")
            if s.shaft_type not in range(1,9):
                raise ModelValidationError(f"ShaftElement[{i}]: received type={s.shaft_type}; expected circular type 1..8; correct shaft type")
            if s.shaft_type not in (1,5,7,8) and s.G_pa<=0:
                raise ModelValidationError(f"ShaftElement[{i}]: received G={s.G_pa}; expected G>0 when shear is enabled; correct shear modulus")
        elif isinstance(s,TaperedShaftElement):
            if s.shaft_type not in range(21,29):
                raise ModelValidationError(f"TaperedShaftElement[{i}]: received type={s.shaft_type}; expected 21..28; correct shaft type")
            if not (s.outer_diameter_1_m>s.inner_diameter_1_m>=0 and s.outer_diameter_2_m>s.inner_diameter_2_m>=0):
                raise ModelValidationError(f"TaperedShaftElement[{i}]: received end diameters do1={s.outer_diameter_1_m}, di1={s.inner_diameter_1_m}, do2={s.outer_diameter_2_m}, di2={s.inner_diameter_2_m}; expected do > di >= 0 at both ends; correct diameters")
            if s.E_pa<=0 or s.rho_kg_m3<=0:
                raise ModelValidationError(f"TaperedShaftElement[{i}]: received E={s.E_pa}, rho={s.rho_kg_m3}; expected E>0 and rho>0; correct material")
            base=s.shaft_type-20
            if base not in (1,5,7,8) and s.G_pa<=0:
                raise ModelValidationError(f"TaperedShaftElement[{i}]: received G={s.G_pa}; expected G>0 when shear is enabled; correct shear modulus")
        elif isinstance(s,AsymmetricShaftElement):
            if stationary:
                raise ModelValidationError(f"AsymmetricShaftElement[{i}]: received type={s.shaft_type}; stationary rotormtx/freq_rsp/crit_spd do not accept types 11..18; use the rotating-frame analysis when it is qualified")
            if s.shaft_type not in range(11,19):
                raise ModelValidationError(f"AsymmetricShaftElement[{i}]: received type={s.shaft_type}; expected 11..18; correct shaft type")
            if min(s.EIx_nm2,s.EIy_nm2,s.rhoA_kg_m)<=0 or s.rhoI_kg_m<0:
                raise ModelValidationError(f"AsymmetricShaftElement[{i}]: received EIx={s.EIx_nm2}, EIy={s.EIy_nm2}, rhoA={s.rhoA_kg_m}, rhoI={s.rhoI_kg_m}; expected positive rigidities/rhoA and rhoI>=0; correct properties")
        else:
            raise ModelValidationError(f"Shaft[{i}]: unsupported Python shaft class {type(s).__name__}; use a supported domain type")
    for i,d in enumerate(m.disks,1):
        if d.node not in z:
            raise ModelValidationError(f"Disk[{i}]: received node={d.node}; expected existing node; correct node")
        if d.disk_type not in (1,2,3,4):
            raise ModelValidationError(f"Disk[{i}]: received type={d.disk_type}; expected 1..4 for stationary analysis; choose supported legacy disk type")
    for i,b in enumerate(m.bearings,1):
        if b.node not in z:
            raise ModelValidationError(f"Bearing[{i}]: received node={b.node}; expected existing node; correct node")
        if b.bearing_type not in (1,2,3,4,5,6,7,8,20):
            raise ModelValidationError(f"Bearing[{i}]: received type={b.bearing_type}; expected legacy type 1..8 or 20; correct bearing type")
        required={1:0,2:0,3:4,4:8,5:8,6:32,7:5,8:6,20:0}[b.bearing_type]
        if len(b.properties)<required:
            raise ModelValidationError(f"Bearing[{i}]: received {len(b.properties)} properties for type={b.bearing_type}; expected at least {required}; complete the bearing definition")
    for i,f in enumerate(m.forces,1):
        if f.force_type in (1,2):
            if len(f.parameters)<3:
                raise ModelValidationError(f"Force[{i}]: received {len(f.parameters)} parameters for type={f.force_type}; expected node,magnitude,phase; complete force")
            if int(f.parameters[0]) not in z:
                raise ModelValidationError(f"Force[{i}]: received node={f.parameters[0]}; expected existing node; correct force node")
        elif f.force_type==3:
            if not m.bend:
                raise ModelValidationError(f"Force[{i}]: received bend force type 3 but RotorModel.bend is empty; define bend points")
        elif f.force_type==8:
            if len(f.parameters)<4:
                raise ModelValidationError(f"Force[{i}]: received {len(f.parameters)} parameters for type=8; expected node1,node2,magnitude,phase; complete force")
            n1,n2=int(f.parameters[0]),int(f.parameters[1])
            if n1 not in z or n2 not in z:
                raise ModelValidationError(f"Force[{i}]: received nodes=({n1},{n2}); expected existing nodes; correct rotating-moment endpoints")
        # Other legacy force types are intentionally ignored by freq_rsp, matching V2.
    for i,bp in enumerate(m.bend,1):
        if bp.node not in z:
            raise ModelValidationError(f"BendPoint[{i}]: received node={bp.node}; expected existing node; correct bend definition")
