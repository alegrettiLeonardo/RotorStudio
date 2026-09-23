from __future__ import annotations
import ctypes as ct
import numpy as np
from .ffi import load_library, configure, SolverLibraryError
from drm_core.domain.model import RotorModel
from drm_core.validation.model import validate_model
class FortranBackend:
    def __init__(self,library_path=None): self.lib=configure(load_library(library_path))
    @staticmethod
    def _ptr(a): return a.ctypes.data_as(ct.POINTER(ct.c_double))
    def _arrays(self,m:RotorModel):
        validate_model(m); n=len(m.nodes)
        z=np.ascontiguousarray([x.z_m for x in m.nodes],dtype=np.float64)
        sh=np.zeros((11,len(m.shafts)),dtype=np.float64,order='F')
        for j,s in enumerate(m.shafts): sh[:,j]=s.legacy_row()
        di=np.zeros((6,len(m.disks)),dtype=np.float64,order='F')
        for j,d in enumerate(m.disks): di[:,j]=[d.disk_type,d.node,d.p3,d.p4,d.p5,d.p6]
        be=np.zeros((34,len(m.bearings)),dtype=np.float64,order='F')
        for j,b in enumerate(m.bearings):
            vals=[b.bearing_type,b.node,*b.properties];be[:min(34,len(vals)),j]=vals[:34]
        return n,z,sh,di,be
    def modal_eigenvalues(self,m:RotorModel,speed_rad_s:float)->np.ndarray:
        n,z,sh,di,be=self._arrays(m);ndof=4*n
        nzero=len(set(d for b in m.bearings for d in (range(4*b.node-3,4*b.node-1) if b.bearing_type==1 else range(4*b.node-3,4*b.node+1) if b.bearing_type==2 else [])))
        nout=2*(ndof-nzero);er=np.empty(nout);ei=np.empty(nout)
        status=self.lib.rd_modal_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(speed_rad_s),nout,self._ptr(er),self._ptr(ei))
        if status: raise SolverLibraryError(f"Fortran rd_modal_legacy returned status={status}")
        return er+1j*ei
    def assemble_matrices(self,m:RotorModel,speed_rad_s:float):
        n,z,sh,di,be=self._arrays(m);nd=4*n; outs=[np.empty((nd,nd),order='F') for _ in range(4)]
        status=self.lib.rd_assemble_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(speed_rad_s),*(self._ptr(x) for x in outs))
        if status: raise SolverLibraryError(f"Fortran rd_assemble_legacy returned status={status}")
        return tuple(outs)
    def frequency_response(self,m:RotorModel,speeds_rad_s)->np.ndarray:
        n,z,sh,di,be=self._arrays(m);speeds=np.ascontiguousarray(speeds_rad_s,dtype=np.float64);nd=4*n
        fo=np.zeros((5,len(m.forces)),dtype=np.float64,order='F')
        for j,f in enumerate(m.forces):
            row=f.legacy_row();fo[:min(5,len(row)),j]=row[:5]
        bd=np.zeros((3,len(m.bend)),dtype=np.float64,order='F')
        for j,b in enumerate(m.bend):bd[:,j]=[b.node,b.x_m,b.y_m]
        rr=np.empty((nd,len(speeds)),dtype=np.float64,order='F');ri=np.empty_like(rr,order='F')
        status=self.lib.rd_freq_rsp_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),fo.shape[1],self._ptr(fo),bd.shape[1],self._ptr(bd),len(speeds),self._ptr(speeds),self._ptr(rr),self._ptr(ri))
        if status: raise SolverLibraryError(f"Fortran rd_freq_rsp_legacy returned status={status}")
        return rr+1j*ri
    def critical_speeds(self,m:RotorModel,NX=1.0,damped=True,ncrit=5,max_iterations=20,tol=1e-6):
        n,z,sh,di,be=self._arrays(m);out=np.empty(ncrit,dtype=np.float64)
        status=self.lib.rd_crit_spd_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(NX),int(bool(damped)),ncrit,max_iterations,float(tol),self._ptr(out))
        if status: raise SolverLibraryError(f"Fortran rd_crit_spd_legacy returned status={status}")
        return out
