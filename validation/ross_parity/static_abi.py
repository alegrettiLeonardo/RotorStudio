"""Direct C ABI harness for qualification, independent of production bindings."""
import ctypes as ct
import numpy as np
from drm_core.solver.ffi import load_library

def inputs(spec):
    z=np.r_[0.,np.cumsum(spec['lengths_m'])]
    sh=np.zeros((11,len(z)-1),order='F')
    for i,(L,d) in enumerate(zip(spec['lengths_m'],spec['outer_diameters_m'],strict=True)):
        sh[:,i]=[spec.get('shaft_type',1),i+1,i+2,d,spec['inner_diameter_m'],spec['rho_kg_m3'],spec['E_Pa'],spec['G_Pa'],0,0,0]
    di=np.zeros((6,len(spec['disks'])),order='F')
    for i,d in enumerate(spec['disks']):di[:,i]=[2,d['node']+1,d['mass_kg'],d['Id_kg_m2'],d['Ip_kg_m2'],0]
    supports=spec['supports'];seals=spec.get('seal_nodes',[])
    be=np.zeros((34,len(supports)+len(seals)),order='F')
    for i,n in enumerate(supports):be[:2,i]=[1,n+1]
    for i,n in enumerate(seals,len(supports)):be[:2,i]=[8,n+1]
    return z,sh,di,be

def call_native(spec,library_path=None):
    z,sh,di,be=inputs(spec);nn=len(z);ns=sh.shape[1];nd=di.shape[1]
    lib=load_library(library_path);f=lib.rd_static_v1;dptr=ct.POINTER(ct.c_double)
    f.argtypes=[ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr,ct.c_int,dptr]+[dptr]*8;f.restype=ct.c_int
    ptr=lambda a:a.ctypes.data_as(dptr)
    out=[np.zeros(n) for n in (4*nn,nn,ns,nd,2*ns,2*ns,2*ns,3)]
    status=f(nn,ptr(z),ns,ptr(sh),nd,ptr(di),be.shape[1],ptr(be),*[ptr(a) for a in out])
    if status:raise RuntimeError(f'rd_static_v1 status={status}')
    return dict(zip(('q','reactions','shaft_weights','disk_weights','shear','bending','stations','diagnostics'),out,strict=True))
