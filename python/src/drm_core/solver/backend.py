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
    @staticmethod
    def _iptr(a): return a.ctypes.data_as(ct.POINTER(ct.c_int))
    def _arrays(self,m:RotorModel,analysis="stationary"):
        validate_model(m,analysis=analysis); n=len(m.nodes)
        z=np.ascontiguousarray([x.z_m for x in m.nodes],dtype=np.float64)
        sh=np.zeros((11,len(m.shafts)),dtype=np.float64,order='F')
        for j,s in enumerate(m.shafts): sh[:,j]=s.legacy_row()
        di=np.zeros((6,len(m.disks)),dtype=np.float64,order='F')
        for j,d in enumerate(m.disks): di[:,j]=[d.disk_type,d.node,d.p3,d.p4,d.p5,d.p6]
        be=np.zeros((34,len(m.bearings)),dtype=np.float64,order='F')
        for j,b in enumerate(m.bearings):
            vals=[b.bearing_type,b.node,*b.properties];be[:min(34,len(vals)),j]=vals[:34]
        return n,z,sh,di,be
    @staticmethod
    def _forces(m:RotorModel):
        fo=np.zeros((5,len(m.forces)),dtype=np.float64,order='F')
        for j,f in enumerate(m.forces):
            row=f.legacy_row();fo[:min(5,len(row)),j]=row[:5]
        return fo
    @staticmethod
    def _bend(m:RotorModel):
        bd=np.zeros((3,len(m.bend)),dtype=np.float64,order='F')
        for j,b in enumerate(m.bend):bd[:,j]=[b.node,b.x_m,b.y_m]
        return bd
    @staticmethod
    def _rotors(m:RotorModel):
        ro=np.zeros((3,len(m.rotors)),dtype=np.float64,order='F')
        for j,r in enumerate(m.rotors):ro[:,j]=r.legacy_row()
        return ro
    @staticmethod
    def _nzero(m:RotorModel):
        zeros=set()
        for b in m.bearings:
            if b.bearing_type==1: zeros.update((4*b.node-3,4*b.node-2))
            elif b.bearing_type==2: zeros.update(range(4*b.node-3,4*b.node+1))
        return len(zeros)
    def bearings_matrices(self,m:RotorModel,speed_rad_s:float):
        n,_,_,_,be=self._arrays(m,"coaxial" if m.rotors else "stationary");nd=4*n
        outs=[np.empty((nd,nd),dtype=np.float64,order='F') for _ in range(3)]
        mask=np.empty(nd,dtype=np.int32);ecc=np.empty(len(m.bearings),dtype=np.float64)
        status=self.lib.rd_bearings_legacy(n,be.shape[1],self._ptr(be),float(speed_rad_s),*(self._ptr(x) for x in outs),self._iptr(mask),self._ptr(ecc))
        if status: raise SolverLibraryError(f"Fortran rd_bearings_legacy returned status={status}")
        return (*outs,mask.astype(bool),ecc)
    def modal_eigenvalues(self,m:RotorModel,speed_rad_s:float)->np.ndarray:
        n,z,sh,di,be=self._arrays(m);ndof=4*n;nout=2*(ndof-self._nzero(m));er=np.empty(nout);ei=np.empty(nout)
        status=self.lib.rd_modal_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(speed_rad_s),nout,self._ptr(er),self._ptr(ei))
        if status: raise SolverLibraryError(f"Fortran rd_modal_legacy returned status={status}")
        return er+1j*ei
    def assemble_matrices(self,m:RotorModel,speed_rad_s:float):
        n,z,sh,di,be=self._arrays(m);nd=4*n; outs=[np.empty((nd,nd),order='F') for _ in range(4)]
        status=self.lib.rd_assemble_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(speed_rad_s),*(self._ptr(x) for x in outs))
        if status: raise SolverLibraryError(f"Fortran rd_assemble_legacy returned status={status}")
        return tuple(outs)
    def frequency_response(self,m:RotorModel,speeds_rad_s)->np.ndarray:
        n,z,sh,di,be=self._arrays(m);speeds=np.ascontiguousarray(speeds_rad_s,dtype=np.float64);nd=4*n;fo=self._forces(m);bd=self._bend(m)
        rr=np.empty((nd,len(speeds)),dtype=np.float64,order='F');ri=np.empty_like(rr,order='F')
        status=self.lib.rd_freq_rsp_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),fo.shape[1],self._ptr(fo),bd.shape[1],self._ptr(bd),len(speeds),self._ptr(speeds),self._ptr(rr),self._ptr(ri))
        if status: raise SolverLibraryError(f"Fortran rd_freq_rsp_legacy returned status={status}")
        return rr+1j*ri
    def critical_speeds(self,m:RotorModel,NX=1.0,damped=True,ncrit=5,max_iterations=20,tol=1e-6,method=None,initial_estimates=None,return_diagnostics=False):
        n,z,sh,di,be=self._arrays(m);out=np.empty(ncrit,dtype=np.float64)
        if method is None and initial_estimates is None:
            status=self.lib.rd_crit_spd_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(NX),int(bool(damped)),ncrit,max_iterations,float(tol),self._ptr(out))
            if status: raise SolverLibraryError(f"Fortran rd_crit_spd_legacy returned status={status}")
            return out
        if method is None: method=3
        ini=np.ascontiguousarray(initial_estimates if initial_estimates is not None else [],dtype=np.float64)
        if method==3 and len(ini)!=ncrit: raise ValueError("method=3 requires one initial estimate per requested critical speed")
        if len(ini)==0: ini=np.zeros(1,dtype=np.float64);nini=0
        else:nini=len(ini)
        it=np.empty(ncrit,dtype=np.int32);cv=np.empty(ncrit,dtype=np.int32)
        status=self.lib.rd_crit_spd_legacy_ex(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(NX),int(bool(damped)),ncrit,max_iterations,float(tol),int(method),self._ptr(ini),nini,self._ptr(out),self._iptr(it),self._iptr(cv))
        if status: raise SolverLibraryError(f"Fortran rd_crit_spd_legacy_ex returned status={status}")
        return (out,it,cv.astype(bool)) if return_diagnostics else out
    def coaxial_modal(self,m:RotorModel,speed_rad_s:float):
        n,z,sh,di,be=self._arrays(m,"coaxial");ro=self._rotors(m);nd=4*n;nout=2*(nd-self._nzero(m));er=np.empty(nout);ei=np.empty(nout);vr=np.empty((nd,nout),order='F');vi=np.empty_like(vr,order='F')
        status=self.lib.rd_coax_modal_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),ro.shape[1],self._ptr(ro),float(speed_rad_s),nout,self._ptr(er),self._ptr(ei),self._ptr(vr),self._ptr(vi))
        if status: raise SolverLibraryError(f"Fortran rd_coax_modal_legacy returned status={status}")
        return er+1j*ei,vr+1j*vi
    def coaxial_frequency_response(self,m:RotorModel,speeds_rad_s):
        n,z,sh,di,be=self._arrays(m,"coaxial");ro=self._rotors(m);fo=self._forces(m);sp=np.ascontiguousarray(speeds_rad_s,dtype=np.float64);nd=4*n;rr=np.empty((nd,len(sp)),order='F');ri=np.empty_like(rr,order='F')
        status=self.lib.rd_coax_freq_rsp_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),ro.shape[1],self._ptr(ro),fo.shape[1],self._ptr(fo),len(sp),self._ptr(sp),self._ptr(rr),self._ptr(ri))
        if status: raise SolverLibraryError(f"Fortran rd_coax_freq_rsp_legacy returned status={status}")
        return rr+1j*ri
    def asymmetric_assemble(self,m:RotorModel):
        n,z,sh,di,_=self._arrays(m,"rotating");nd=4*n;outs=[np.empty((nd,nd),order='F') for _ in range(6)]
        status=self.lib.rd_asym_assemble_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),*(self._ptr(x) for x in outs))
        if status: raise SolverLibraryError(f"Fortran rd_asym_assemble_legacy returned status={status}")
        return tuple(outs)
    def asymmetric_bearings(self,m:RotorModel):
        n,_,_,_,be=self._arrays(m,"rotating");nd=4*n;outs=[np.empty((nd,nd),order='F') for _ in range(3)];mask=np.empty(nd,dtype=np.int32)
        status=self.lib.rd_bearasym_legacy(n,be.shape[1],self._ptr(be),*(self._ptr(x) for x in outs),self._iptr(mask))
        if status: raise SolverLibraryError(f"Fortran rd_bearasym_legacy returned status={status}")
        return (*outs,mask.astype(bool))
    def asymmetric_modal(self,m:RotorModel,speed_rad_s:float,want_vectors=False):
        n,z,sh,di,be=self._arrays(m,"rotating");nd=4*n;nout=2*(nd-self._nzero(m));er=np.empty(nout);ei=np.empty(nout);vr=np.empty((nd,nout),order='F');vi=np.empty_like(vr,order='F')
        status=self.lib.rd_asym_modal_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(speed_rad_s),int(bool(want_vectors)),nout,self._ptr(er),self._ptr(ei),self._ptr(vr),self._ptr(vi))
        if status: raise SolverLibraryError(f"Fortran rd_asym_modal_legacy returned status={status}")
        return er+1j*ei,vr+1j*vi
    def asymmetric_frequency_response(self,m:RotorModel,speeds_rad_s):
        n,z,sh,di,be=self._arrays(m,"rotating");fo=self._forces(m);sp=np.ascontiguousarray(speeds_rad_s,dtype=np.float64);nd=4*n;resp=np.empty((nd,len(sp)),order='F')
        status=self.lib.rd_asym_freq_rsp_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),fo.shape[1],self._ptr(fo),len(sp),self._ptr(sp),self._ptr(resp))
        if status: raise SolverLibraryError(f"Fortran rd_asym_freq_rsp_legacy returned status={status}")
        return resp
