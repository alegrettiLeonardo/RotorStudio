"""Marshalling only. Rotor matrices, interpolation and complex solves are native."""
from dataclasses import replace
import numpy as np
from drm_core.domain.model import ShaftElement
from drm_core.domain.bearings import CoefficientBearing
from .ffi import configure_general_frf,SolverLibraryError

POLICIES={'synchronous':0,'fixed':1,'free_free':2}

def prepare(backend,model,frequencies,speed=None,free_free=False):
    configure_general_frf(backend.lib)
    f=np.ascontiguousarray(frequencies,dtype=np.float64)
    nn=len(model.nodes);nf=f.size;n=4*nn
    if f.ndim!=1 or nf<1 or nf>10000 or not np.isfinite(f).all() or np.any(f<0):
        raise ValueError('General FRF frequency axis: expected 1..10000 finite nonnegative rad/s values; supply a valid sweep.')
    if nn<2 or nn>128 or 192*n*n*nf+160*n*n>512*1024**2:
        raise ValueError('General FRF full matrices exceed the 512 MiB budget or 2..128 node range; reduce nodes/frequencies.')
    if [x.number for x in model.nodes]!=list(range(1,nn+1)) or len(model.shafts)!=nn-1:
        raise ValueError('General FRF requires an ordered consecutive one-based shaft chain.')
    if model.rotors or model.bend:
        raise ValueError('General FRF coaxial/pre-bend models are outside A2 scope.')
    for i,s in enumerate(model.shafts):
        if not isinstance(s,ShaftElement) or s.shaft_type!=2 or (s.node1,s.node2)!=(i+1,i+2) or any([s.damping_factor,s.axial_force_n,s.torque_nm]):
            raise ValueError('General FRF expects circular Timoshenko type 2, zero damping/preload/torque and an ordered chain.')
    if any(d.disk_type not in (1,2) for d in model.disks) or len(model.disks)>1024:
        raise ValueError('General FRF supports at most 1024 gyroscopic disks, types 1/2.')
    bs=list(model.advanced_bearings)
    if any(not isinstance(b,CoefficientBearing) for b in bs):
        raise ValueError('General FRF requires COEFFICIENT_TABLE / MAP_BACKED bearings; direct physical bearing solvers are blocked. Generate a qualified map first.')
    for b in model.bearings:
        from drm_core.validation.contracts import validate_bearing_contract
        validate_bearing_contract(b)
        p=b.properties
        if b.bearing_type==3 and len(p)>=4:bs.append(CoefficientBearing(b.node,kxx=p[0],kyy=p[1],cxx=p[2],cyy=p[3]))
        elif b.bearing_type==5 and len(p)>=8:bs.append(CoefficientBearing(b.node,kxx=p[0],kxy=p[1],kyx=p[2],kyy=p[3],cxx=p[4],cxy=p[5],cyx=p[6],cyy=p[7]))
        else:raise ValueError('General FRF legacy supports must be constant radial types 3/5; rigid, linked and physical seal/bearing paths are outside A2.')
    if len(bs)>2*nn or any(b.node<1 or b.node>nn for b in bs):raise ValueError('Invalid bearing node/count (at most two bearings per shaft node in total).')
    policy='free_free' if free_free else ('synchronous' if speed is None else 'fixed')
    fixed=0. if speed is None else float(speed)
    if not np.isfinite(fixed):raise ValueError('Rotor speed must be finite rad/s.')
    speeds=np.zeros(nf) if free_free else (f.copy() if speed is None else np.full(nf,fixed))
    _,z,sh,di,_=backend._arrays(replace(model,bearings=[],advanced_bearings=[]))
    if not all(np.isfinite(a).all() for a in (z,sh,di)):raise ValueError('General FRF requires finite SI input arrays.')
    nodes=np.ascontiguousarray([b.node for b in bs],dtype=np.int32)
    coeff=np.zeros((12,len(bs),nf),dtype=np.float64,order='F');metadata=[]
    provider=backend._bearing_provider() if bs else None
    for i,(omega,w) in enumerate(zip(speeds,f)):
        point=[]
        for j,b in enumerate(bs):
            v=provider.evaluate(b,float(omega),float(w))
            coeff[:,j,i]=np.concatenate([v.M.ravel(order='F'),v.C.ravel(order='F'),v.K.ravel(order='F')])
            states=[]
            for axis,query in [(b.speed_rad_s,omega),(b.frequency_rad_s,w)]:
                if len(axis):states.append('extrapolated' if query<min(axis) or query>max(axis) else ('tabulated' if query in axis else 'interpolated'))
            state='extrapolated' if 'extrapolated' in states else ('interpolated' if 'interpolated' in states else ('tabulated' if states else 'constant'))
            point.append(dict(node=b.node,status=state,**v.details))
        metadata.append(point)
    if not np.isfinite(coeff).all():raise SolverLibraryError('Nonfinite native bearing coefficients; FRF rejected.')
    return z,sh,di,nodes,coeff,f,speeds,policy,fixed,metadata

def execute(backend,model,frequencies,speed=None,free_free=False):
    z,sh,di,nodes,coeff,f,speeds,policy,fixed,metadata=prepare(backend,model,frequencies,speed,free_free)
    n=4*len(z);out=[np.empty((n,n,len(f)),dtype=float,order='F') for _ in range(6)];res=np.empty(len(f))
    fn,_=configure_general_frf(backend.lib);p=backend._ptr
    status=fn(len(z),p(z),sh.shape[1],p(sh),di.shape[1],p(di),len(nodes),backend._iptr(nodes),len(f),p(f),POLICIES[policy],fixed,p(coeff),*[p(a) for a in out],p(res))
    if status:raise SolverLibraryError(f'General FRF rd_frf_general_v1 status={status}; singular/nonfinite or invalid system. Check support stiffness and excitation frequencies; no zero-response fallback was used.')
    if not all(np.isfinite(a).all() for a in [*out,res]):raise SolverLibraryError('Nonfinite General FRF result rejected.')
    return f,speeds,out[0]+1j*out[1],out[2]+1j*out[3],out[4]+1j*out[5],res,policy,metadata

def matrices(backend,model,frequency,speed):
    z,sh,di,nodes,coeff,f,_,_,_,_=prepare(backend,model,[frequency],speed)
    n=4*len(z);out=[np.empty((n,n),dtype=float,order='F') for _ in range(9)]
    _,fn=configure_general_frf(backend.lib);p=backend._ptr
    status=fn(len(z),p(z),sh.shape[1],p(sh),di.shape[1],p(di),len(nodes),backend._iptr(nodes),p(coeff),float(speed),float(frequency),*[p(a) for a in out])
    if status:raise SolverLibraryError(f'rd_dynamic_stiffness_v1 status={status}')
    return dict(zip(['M','C','G','K','Mb','Cb','Kb'],out[:7]))|{'D':out[7]+1j*out[8]}
