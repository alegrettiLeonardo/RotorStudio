from __future__ import annotations
import ctypes as ct
import numpy as np
from .ffi import load_library, configure, SolverLibraryError
from drm_core.domain.model import RotorModel
from drm_core.validation.model import validate_model
class FortranBackend:
    def __init__(self,library_path=None):
        self.library_path=library_path
        self.lib=configure(load_library(library_path))
        self._advanced_bearing_backend=None
    def _bearing_provider(self):
        if self._advanced_bearing_backend is None:
            from .bearings_backend import AdvancedBearingBackend
            self._advanced_bearing_backend=AdvancedBearingBackend(rotor_library_path=self.library_path)
        return self._advanced_bearing_backend
    @staticmethod
    def _ptr(a): return a.ctypes.data_as(ct.POINTER(ct.c_double))
    @staticmethod
    def _iptr(a): return a.ctypes.data_as(ct.POINTER(ct.c_int))
    def _arrays(self,m:RotorModel,analysis="stationary",speed_rad_s=None,frequency_rad_s=None):
        validate_model(m,analysis=analysis); n=len(m.nodes)
        z=np.ascontiguousarray([x.z_m for x in m.nodes],dtype=np.float64)
        sh=np.zeros((11,len(m.shafts)),dtype=np.float64,order='F')
        for j,s in enumerate(m.shafts): sh[:,j]=s.legacy_row()
        di=np.zeros((6,len(m.disks)),dtype=np.float64,order='F')
        for j,d in enumerate(m.disks): di[:,j]=[d.disk_type,d.node,d.p3,d.p4,d.p5,d.p6]
        bearings=list(m.bearings)
        if m.advanced_bearings:
            if speed_rad_s is None:
                raise SolverLibraryError(
                    "advanced bearings require an explicit rotor speed evaluation point"
                )
            frequency_rad_s=float(speed_rad_s) if frequency_rad_s is None else float(frequency_rad_s)
            provider=self._bearing_provider()
            bearings.extend(
                provider.as_legacy_bearing(b,float(speed_rad_s),frequency_rad_s)
                for b in m.advanced_bearings
            )
        be=np.zeros((34,len(bearings)),dtype=np.float64,order='F')
        for j,b in enumerate(bearings):
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
        n,_,_,_,be=self._arrays(m,"coaxial" if m.rotors else "stationary",speed_rad_s,speed_rad_s);nd=4*n
        outs=[np.empty((nd,nd),dtype=np.float64,order='F') for _ in range(3)]
        mask=np.empty(nd,dtype=np.int32);ecc=np.empty(be.shape[1],dtype=np.float64)
        status=self.lib.rd_bearings_legacy(n,be.shape[1],self._ptr(be),float(speed_rad_s),*(self._ptr(x) for x in outs),self._iptr(mask),self._ptr(ecc))
        if status: raise SolverLibraryError(f"Fortran rd_bearings_legacy returned status={status}")
        return (*outs,mask.astype(bool),ecc)
    def modal_eigenvalues(self,m:RotorModel,speed_rad_s:float)->np.ndarray:
        n,z,sh,di,be=self._arrays(m,speed_rad_s=speed_rad_s,frequency_rad_s=speed_rad_s);ndof=4*n;nout=2*(ndof-self._nzero(m));er=np.empty(nout);ei=np.empty(nout)
        status=self.lib.rd_modal_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(speed_rad_s),nout,self._ptr(er),self._ptr(ei))
        if status: raise SolverLibraryError(f"Fortran rd_modal_legacy returned status={status}")
        return er+1j*ei
    def modal_eigensystem(self,m:RotorModel,speed_rad_s:float):
        n,z,sh,di,be=self._arrays(m,speed_rad_s=speed_rad_s,frequency_rad_s=speed_rad_s);ndof=4*n;nout=2*(ndof-self._nzero(m));er=np.empty(nout);ei=np.empty(nout);vr=np.empty((ndof,nout),dtype=np.float64,order='F');vi=np.empty_like(vr,order='F');ecc=np.empty(be.shape[1],dtype=np.float64)
        status=self.lib.rd_modal_legacy_vectors(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(speed_rad_s),nout,self._ptr(er),self._ptr(ei),self._ptr(vr),self._ptr(vi),self._ptr(ecc))
        if status: raise SolverLibraryError(f"Fortran rd_modal_legacy_vectors returned status={status}")
        return er+1j*ei,vr+1j*vi,ecc
    def modal_eigenvalues_at_frequency(self,m:RotorModel,speed_rad_s:float,frequency_rad_s:float)->np.ndarray:
        """Stationary modal solve with bearing coefficients at (Omega, omega).

        The rotor/gyroscopic speed passed to Fortran remains speed_rad_s.
        Only the advanced-bearing coefficient evaluation uses frequency_rad_s.
        """
        n,z,sh,di,be=self._arrays(
            m,speed_rad_s=float(speed_rad_s),frequency_rad_s=float(frequency_rad_s)
        )
        ndof=4*n;nout=2*(ndof-self._nzero(m));er=np.empty(nout);ei=np.empty(nout)
        status=self.lib.rd_modal_legacy(
            n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),
            be.shape[1],self._ptr(be),float(speed_rad_s),nout,self._ptr(er),self._ptr(ei)
        )
        if status:
            raise SolverLibraryError(
                f"Fortran rd_modal_legacy returned status={status} at "
                f"rotor speed={speed_rad_s}, whirl frequency={frequency_rad_s}"
            )
        return er+1j*ei

    def modal_eigensystem_at_frequency(self,m:RotorModel,speed_rad_s:float,frequency_rad_s:float):
        """Eigenpairs with Omega kept on the gyroscopic term and omega on bearings."""
        n,z,sh,di,be=self._arrays(
            m,speed_rad_s=float(speed_rad_s),frequency_rad_s=float(frequency_rad_s)
        )
        ndof=4*n;nout=2*(ndof-self._nzero(m))
        er=np.empty(nout);ei=np.empty(nout)
        vr=np.empty((ndof,nout),dtype=np.float64,order='F');vi=np.empty_like(vr,order='F')
        ecc=np.empty(be.shape[1],dtype=np.float64)
        status=self.lib.rd_modal_legacy_vectors(
            n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),
            be.shape[1],self._ptr(be),float(speed_rad_s),nout,self._ptr(er),self._ptr(ei),
            self._ptr(vr),self._ptr(vi),self._ptr(ecc)
        )
        if status:
            raise SolverLibraryError(
                f"Fortran rd_modal_legacy_vectors returned status={status} at "
                f"rotor speed={speed_rad_s}, whirl frequency={frequency_rad_s}"
            )
        return er+1j*ei,vr+1j*vi,ecc

    def assemble_matrices(self,m:RotorModel,speed_rad_s:float):
        n,z,sh,di,be=self._arrays(m,speed_rad_s=speed_rad_s,frequency_rad_s=speed_rad_s);nd=4*n; outs=[np.empty((nd,nd),order='F') for _ in range(4)]
        status=self.lib.rd_assemble_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(speed_rad_s),*(self._ptr(x) for x in outs))
        if status: raise SolverLibraryError(f"Fortran rd_assemble_legacy returned status={status}")
        return tuple(outs)
    def frequency_response(self,m:RotorModel,speeds_rad_s)->np.ndarray:
        speeds=np.ascontiguousarray(speeds_rad_s,dtype=np.float64)
        if not m.advanced_bearings:
            n,z,sh,di,be=self._arrays(m);nd=4*n;fo=self._forces(m);bd=self._bend(m)
            rr=np.empty((nd,len(speeds)),dtype=np.float64,order='F');ri=np.empty_like(rr,order='F')
            status=self.lib.rd_freq_rsp_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),fo.shape[1],self._ptr(fo),bd.shape[1],self._ptr(bd),len(speeds),self._ptr(speeds),self._ptr(rr),self._ptr(ri))
            if status: raise SolverLibraryError(f"Fortran rd_freq_rsp_legacy returned status={status}")
            return rr+1j*ri
        nd=4*len(m.nodes);response=np.empty((nd,len(speeds)),dtype=np.complex128)
        fo=self._forces(m);bd=self._bend(m)
        for j,speed in enumerate(speeds):
            n,z,sh,di,be=self._arrays(m,speed_rad_s=float(speed),frequency_rad_s=float(speed))
            one=np.ascontiguousarray([speed],dtype=np.float64)
            rr=np.empty((nd,1),dtype=np.float64,order='F');ri=np.empty_like(rr,order='F')
            status=self.lib.rd_freq_rsp_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),fo.shape[1],self._ptr(fo),bd.shape[1],self._ptr(bd),1,self._ptr(one),self._ptr(rr),self._ptr(ri))
            if status: raise SolverLibraryError(f"Fortran rd_freq_rsp_legacy returned status={status} at speed={speed}")
            response[:,j]=rr[:,0]+1j*ri[:,0]
        return response
    def auxiliary_frequency_response(self,m:RotorModel,rotor_speed_rad_s:float,omega_rad_s,direction=1.0):
        om=np.ascontiguousarray(omega_rad_s,dtype=np.float64);fo=self._forces(m);nd=4*len(m.nodes)
        if not m.advanced_bearings:
            n,z,sh,di,be=self._arrays(m);rr=np.empty((nd,len(om)),dtype=np.float64,order='F');ri=np.empty_like(rr,order='F')
            status=self.lib.rd_freq_aux_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),fo.shape[1],self._ptr(fo),float(rotor_speed_rad_s),len(om),self._ptr(om),float(direction),self._ptr(rr),self._ptr(ri))
            if status: raise SolverLibraryError(f"Fortran rd_freq_aux_legacy returned status={status}")
            return rr+1j*ri
        response=np.empty((nd,len(om)),dtype=np.complex128)
        for j,frequency in enumerate(om):
            n,z,sh,di,be=self._arrays(m,speed_rad_s=float(rotor_speed_rad_s),frequency_rad_s=float(frequency))
            one=np.ascontiguousarray([frequency],dtype=np.float64)
            rr=np.empty((nd,1),dtype=np.float64,order='F');ri=np.empty_like(rr,order='F')
            status=self.lib.rd_freq_aux_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),fo.shape[1],self._ptr(fo),float(rotor_speed_rad_s),1,self._ptr(one),float(direction),self._ptr(rr),self._ptr(ri))
            if status: raise SolverLibraryError(f"Fortran rd_freq_aux_legacy returned status={status} at excitation frequency={frequency}")
            response[:,j]=rr[:,0]+1j*ri[:,0]
        return response
    def foundation_frequency_response(self,m:RotorModel,rotor_speed_rad_s:float,omega_rad_s):
        om=np.ascontiguousarray(omega_rad_s,dtype=np.float64);fo=self._forces(m);nd=4*len(m.nodes)
        if not m.advanced_bearings:
            n,z,sh,di,be=self._arrays(m);rr=np.empty((nd,len(om)),dtype=np.float64,order='F');ri=np.empty_like(rr,order='F')
            status=self.lib.rd_freq_fdn_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),fo.shape[1],self._ptr(fo),float(rotor_speed_rad_s),len(om),self._ptr(om),self._ptr(rr),self._ptr(ri))
            if status: raise SolverLibraryError(f"Fortran rd_freq_fdn_legacy returned status={status}")
            return rr+1j*ri
        response=np.empty((nd,len(om)),dtype=np.complex128)
        for j,frequency in enumerate(om):
            n,z,sh,di,be=self._arrays(m,speed_rad_s=float(rotor_speed_rad_s),frequency_rad_s=float(frequency))
            one=np.ascontiguousarray([frequency],dtype=np.float64)
            rr=np.empty((nd,1),dtype=np.float64,order='F');ri=np.empty_like(rr,order='F')
            status=self.lib.rd_freq_fdn_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),fo.shape[1],self._ptr(fo),float(rotor_speed_rad_s),1,self._ptr(one),self._ptr(rr),self._ptr(ri))
            if status: raise SolverLibraryError(f"Fortran rd_freq_fdn_legacy returned status={status} at excitation frequency={frequency}")
            response[:,j]=rr[:,0]+1j*ri[:,0]
        return response
    def critical_speeds(self,m:RotorModel,NX=1.0,damped=True,ncrit=5,max_iterations=20,tol=1e-6,method=None,initial_estimates=None,return_diagnostics=False):
        if m.advanced_bearings:
            if method not in (None,3):
                raise ValueError("advanced bearings use the qualified iterative critical-speed method 3; direct/fixed-index methods are not enabled")
            nx=abs(float(NX))
            if nx <= 0:
                raise ValueError("NX must be nonzero for advanced-bearing critical-speed iteration")
            if initial_estimates is None:
                eig=self.modal_eigenvalues(m,1.0)
                measure=np.abs(eig.imag) if damped else np.abs(eig)
                candidates=np.sort(measure[np.isfinite(measure) & (measure>1e-9)]/nx)
                unique=[]
                for value in candidates:
                    if not unique or abs(value-unique[-1])>1e-7*max(1.0,abs(value)):
                        unique.append(float(value))
                if len(unique)<ncrit:
                    raise SolverLibraryError(f"only {len(unique)} initial critical-speed candidates found; requested {ncrit}")
                estimates=np.asarray(unique[:ncrit],dtype=float)
            else:
                estimates=np.asarray(initial_estimates,dtype=float)
                if estimates.size!=ncrit:
                    raise ValueError("advanced-bearing critical speeds require one initial estimate per requested critical speed")
            out=np.empty(ncrit,dtype=np.float64);iterations=np.zeros(ncrit,dtype=np.int32);converged=np.zeros(ncrit,dtype=np.int32)
            for i,guess in enumerate(estimates):
                current=max(float(guess),1e-9)
                for it in range(1,max_iterations+1):
                    eig=self.modal_eigenvalues(m,current)
                    measure=np.abs(eig.imag) if damped else np.abs(eig)
                    estimates_at_speed=measure/nx
                    finite=np.isfinite(estimates_at_speed)
                    if not np.any(finite):
                        raise SolverLibraryError(f"no finite eigenvalue estimate at critical-speed iteration {it}")
                    idx=int(np.argmin(np.where(finite,np.abs(estimates_at_speed-current),np.inf)))
                    updated=float(estimates_at_speed[idx])
                    iterations[i]=it
                    if abs(updated-current)<=float(tol)*max(1.0,abs(updated)):
                        current=updated;converged[i]=1;break
                    current=max(updated,1e-9)
                out[i]=current
            return (out,iterations,converged.astype(bool)) if return_diagnostics else out
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
        if m.advanced_bearings: raise SolverLibraryError("advanced bearings are not yet qualified for coaxial rotor assembly")
        n,z,sh,di,be=self._arrays(m,"coaxial");ro=self._rotors(m);nd=4*n;nout=2*(nd-self._nzero(m));er=np.empty(nout);ei=np.empty(nout);vr=np.empty((nd,nout),order='F');vi=np.empty_like(vr,order='F')
        status=self.lib.rd_coax_modal_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),ro.shape[1],self._ptr(ro),float(speed_rad_s),nout,self._ptr(er),self._ptr(ei),self._ptr(vr),self._ptr(vi))
        if status: raise SolverLibraryError(f"Fortran rd_coax_modal_legacy returned status={status}")
        return er+1j*ei,vr+1j*vi
    def coaxial_frequency_response(self,m:RotorModel,speeds_rad_s):
        if m.advanced_bearings: raise SolverLibraryError("advanced bearings are not yet qualified for coaxial rotor assembly")
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
    def foundation_time_response(self,m:RotorModel,rotor_speed_rad_s:float,dt:float,npts:int,nr:int=0,rtol:float=1e-3,atol:float=1e-6,h_init:float=0.0,h_max:float=0.0):
        if m.advanced_bearings: raise SolverLibraryError("advanced-bearing time-domain foundation response is not qualified yet; use a prequalified constant legacy bearing or frequency-domain analysis")
        n,z,sh,di,be=self._arrays(m);nd=4*n
        rows=[f for f in m.forces if f.force_type==5]
        if not rows: raise ValueError("foundation time response requires one Force type 5")
        vals=rows[0].values;need=2*len(m.bearings)+1
        if len(vals)<need: raise ValueError(f"Force type 5 received {len(vals)} values; expected {need}: 2 per bearing plus pulse_duration")
        amp=np.ascontiguousarray(vals[:2*len(m.bearings)],dtype=np.float64);pulse=float(vals[2*len(m.bearings)])
        resp=np.empty((nd,npts),dtype=np.float64,order='F');force=np.empty(npts,dtype=np.float64);time=np.empty(npts,dtype=np.float64)
        nru=np.zeros(1,dtype=np.int32);na=np.zeros(1,dtype=np.int32);nrj=np.zeros(1,dtype=np.int32);maxf=np.zeros(1,dtype=np.float64)
        status=self.lib.rd_time_fdn_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),float(rotor_speed_rad_s),self._ptr(amp),pulse,float(dt),int(npts),int(nr),float(rtol),float(atol),float(h_init),float(h_max),self._ptr(resp),self._ptr(force),self._ptr(time),self._iptr(nru),self._ptr(maxf),self._iptr(na),self._iptr(nrj))
        if status: raise SolverLibraryError(f"Fortran rd_time_fdn_legacy returned status={status}")
        return time,resp,force,{"nr_used":int(nru[0]),"max_reduced_frequency_hz":float(maxf[0]),"accepted_steps":int(na[0]),"rejected_steps":int(nrj[0]),"rtol":rtol,"atol":atol}
    def runup(self,m:RotorModel,alpha,tspan,nr:int=0,rtol:float=1e-3,atol:float=1e-6,h_init:float=0.0,h_max:float=0.0,max_points:int=200000):
        if m.advanced_bearings: raise SolverLibraryError("advanced-bearing run-up requires a separately qualified time-varying coefficient update policy; it is intentionally blocked")
        n,z,sh,di,be=self._arrays(m);nd=4*n;fo=self._forces(m);aa=np.ascontiguousarray(alpha,dtype=np.float64);ts=np.asarray(tspan,dtype=float)
        if aa.shape!=(3,): raise ValueError("alpha must have exactly 3 coefficients [a2,a1,a0]")
        if ts.size!=2: raise ValueError("tspan must contain [t0,tf]")
        time=np.empty(max_points,dtype=np.float64);speed=np.empty(max_points,dtype=np.float64);resp=np.empty((nd,max_points),dtype=np.float64,order='F')
        nout=np.zeros(1,dtype=np.int32);nru=np.zeros(1,dtype=np.int32);na=np.zeros(1,dtype=np.int32);nrj=np.zeros(1,dtype=np.int32);maxf=np.zeros(1,dtype=np.float64)
        status=self.lib.rd_runup_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),fo.shape[1],self._ptr(fo),self._ptr(aa),float(ts[0]),float(ts[1]),int(nr),float(rtol),float(atol),float(h_init),float(h_max),int(max_points),self._ptr(time),self._ptr(resp),self._ptr(speed),self._iptr(nout),self._iptr(nru),self._ptr(maxf),self._iptr(na),self._iptr(nrj))
        if status: raise SolverLibraryError(f"Fortran rd_runup_legacy returned status={status}")
        k=int(nout[0]);return time[:k].copy(),resp[:,:k].copy(order='F'),speed[:k].copy(),{"nr_used":int(nru[0]),"max_reduced_frequency_hz":float(maxf[0]),"accepted_steps":int(na[0]),"rejected_steps":int(nrj[0]),"rtol":rtol,"atol":atol}
