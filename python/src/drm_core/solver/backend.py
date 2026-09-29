from __future__ import annotations
import ctypes as ct
import numpy as np
from .ffi import load_library, configure, SolverLibraryError
from drm_core.domain.model import RotorModel
from drm_core.domain.bearings import CoefficientBearing
from drm_core.validation.model import validate_model
class FortranBackend:
    def __init__(self,library_path=None):
        self.library_path=library_path
        self.lib=configure(load_library(library_path))
        self._advanced_bearing_backend=None
    def ucs(self,model,stiffness_range_exponents,num=20,num_modes=16,bearing_speed_range=None,synchronous=False):
        from .ucs_backend import execute
        return execute(self,model,stiffness_range_exponents,num,num_modes,bearing_speed_range,synchronous)

    def ucs_matrices(self,model,stiffness_n_m,synchronous=False):
        from .ucs_backend import matrices
        return matrices(self,model,stiffness_n_m,synchronous)

    def general_time_response(self,model,time_s,force_real,speed=0.,weight=False,gamma=.5,beta=.25,tol=1e-6):
        from .general_time_backend import execute
        return execute(self,model,time_s,force_real,speed,weight,gamma,beta,tol)

    def forced_response(self,model,frequency_rad_s,force_real,force_imag,speed=None):
        from .forced_response_backend import execute
        return execute(self,model,frequency_rad_s,force_real,force_imag,speed)

    def general_frf(self,model,frequencies,speed=None,free_free=False):
        from .general_frf_backend import execute
        return execute(self,model,frequencies,speed,free_free)

    def static(self,model):
        from .ffi import configure_static
        from drm_core.domain.model import ShaftElement
        fn=configure_static(self.lib)
        if model.rotors or model.advanced_bearings or model.bend:
            raise SolverLibraryError("Static received coaxial/advanced-bearing/pre-bend data; expected a single circular shaft with legacy radial supports. Use the declared A1 scope; linked and advanced support semantics are not qualified.")
        if not 2<=len(model.nodes)<=1000 or [n.number for n in model.nodes]!=list(range(1,len(model.nodes)+1)):
            raise SolverLibraryError("Static nodes: expected 2..1000 consecutive one-based nodes in increasing axial order; renumber/reorder the model.")
        if len(model.shafts)!=len(model.nodes)-1 or any(not isinstance(s,ShaftElement) or (s.node1,s.node2)!=(i+1,i+2) or s.axial_force_n!=0 or s.torque_nm!=0 for i,s in enumerate(model.shafts)):
            raise SolverLibraryError("Static shaft: expected an ordered circular element chain (types 1..8), zero axial preload and torque; tapered/asymmetric/branched/preloaded shafts are outside A1 scope.")
        n,z,sh,di,be=self._arrays(model)
        if not all(np.isfinite(a).all() for a in (z,sh,di,be)):
            raise SolverLibraryError("Static input contains NaN/Inf; expected finite SI geometry, material, mass and support values. Correct the input before solving.")
        outputs=[np.zeros(size,dtype=np.float64) for size in (4*n,n,sh.shape[1],di.shape[1],2*sh.shape[1],2*sh.shape[1],2*sh.shape[1],3)]
        status=fn(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),*(self._ptr(a) for a in outputs))
        if status:
            reason={10:"invalid geometry/mass or no non-seal support",20:"unsupported topology or element",30:"singular system or numerical solve failure"}.get(status,"native failure")
            raise SolverLibraryError(f"Static rd_static_v1 returned status={status}: {reason}. Expected a connected shaft and at least two distinct non-seal radial supports; correct supports/inputs and retry.")
        if not all(np.isfinite(a).all() for a in outputs):
            raise SolverLibraryError("Static native output is nonfinite; analysis rejected.")
        version=[ct.c_int() for _ in range(3)]
        self.lib.rd_version.argtypes=[ct.POINTER(ct.c_int)]*3
        self.lib.rd_version.restype=ct.c_int
        if self.lib.rd_version(*(ct.byref(v) for v in version)):
            raise SolverLibraryError("Cannot read native solver version")
        return (*outputs,'.'.join(str(v.value) for v in version))

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
    def _advanced_runup_map(self,m:RotorModel,alpha,tspan):
        aa=np.ascontiguousarray(alpha,dtype=np.float64);ts=np.asarray(tspan,dtype=float)
        if aa.shape!=(3,): raise ValueError("alpha must have exactly 3 coefficients [a2,a1,a0]")
        if ts.size!=2: raise ValueError("tspan must contain [t0,tf]")
        omega=np.asarray([2.0*aa[0]*ts[0]+aa[1],2.0*aa[0]*ts[1]+aa[1]],dtype=float)
        lo=float(np.min(omega));hi=float(np.max(omega))
        if not np.isfinite(omega).all() or lo<0.0:
            raise SolverLibraryError("B18 synchronous advanced-bearing run-up requires finite nonnegative rotor speed over the full time span")
        mapped=[]
        methods=set();reference_axis=None
        provider=self._bearing_provider()
        for bearing in m.advanced_bearings:
            if type(bearing) is not CoefficientBearing:
                raise SolverLibraryError(
                    f"{type(bearing).__name__}: B18 does not execute physical Reynolds/THD/TEHD in the ODE; "
                    "generate a B16 synchronous operating map and use its CoefficientBearing"
                )
            if bearing.frequency_rad_s:
                raise SolverLibraryError(
                    f"{bearing.tag or type(bearing).__name__}: B18 requires a synchronous 1-D map with an empty "
                    "frequency axis; asynchronous 2-D maps are not accepted by the initial run-up scope"
                )
            if np.max(np.abs(provider.evaluate(bearing,max(lo,0.0),max(lo,0.0)).M))>1e-14:
                raise SolverLibraryError("B18 cannot silently discard nonzero advanced-bearing M")
            axis=np.asarray(bearing.speed_rad_s,dtype=float)
            if axis.size:
                if axis.size<2:
                    raise SolverLibraryError("B18 speed-dependent coefficient maps require at least two speed points")
                tol=64*np.finfo(float).eps*max(1.0,abs(float(axis[0])),abs(float(axis[-1])))
                if lo<float(axis[0])-tol or hi>float(axis[-1])+tol:
                    raise SolverLibraryError(
                        f"B18 synchronous map coverage [{axis[0]}, {axis[-1]}] rad/s does not cover "
                        f"run-up speed range [{lo}, {hi}] rad/s; extrapolation is not allowed"
                    )
                if reference_axis is None:
                    reference_axis=axis.copy()
                elif axis.shape!=reference_axis.shape or not np.allclose(axis,reference_axis,rtol=0.0,atol=1e-12):
                    raise SolverLibraryError("B18 initial native ABI requires all nonconstant advanced-bearing maps to share the same speed axis")
                methods.add(bearing.interpolation)
            mapped.append(bearing)
        if reference_axis is None:
            if hi<=lo:
                reference_axis=np.asarray([lo,max(lo+1.0,1.0)],dtype=float)
            else:
                reference_axis=np.asarray([lo,hi],dtype=float)
            methods.add("linear")
        if len(methods)>1:
            raise SolverLibraryError("B18 initial native ABI requires one interpolation policy shared by all advanced-bearing maps")
        method=next(iter(methods)) if methods else "linear"
        # Constant bearings are expanded onto the shared map axis. Map-backed
        # bearings are evaluated only at their existing tabulated points here;
        # no physical solver is called in the ODE.
        nmap=len(mapped);ns=len(reference_axis)
        kt=np.empty((4,ns,nmap),dtype=np.float64,order="F")
        ct_=np.empty((4,ns,nmap),dtype=np.float64,order="F")
        nodes=np.empty(nmap,dtype=np.int32)
        for bidx,bearing in enumerate(mapped):
            nodes[bidx]=int(bearing.node)
            for j,w in enumerate(reference_axis):
                evaluation=provider.evaluate(bearing,float(w),float(w))
                if np.max(np.abs(evaluation.M))>1e-14:
                    raise SolverLibraryError("B18 cannot silently discard nonzero advanced-bearing M")
                K=evaluation.K;C=evaluation.C
                kt[:,j,bidx]=[K[0,0],K[1,0],K[0,1],K[1,1]]
                ct_[:,j,bidx]=[C[0,0],C[1,0],C[0,1],C[1,1]]
        return aa,ts,nodes,np.ascontiguousarray(reference_axis),kt,ct_,(1 if method=="pchip" else 2),lo,hi,method

    def runup(self,m:RotorModel,alpha,tspan,nr:int=0,rtol:float=1e-3,atol:float=1e-6,h_init:float=0.0,h_max:float=0.0,max_points:int=200000):
        if m.advanced_bearings:
            if int(nr)!=0:
                raise SolverLibraryError("advanced-bearing run-up reduced-order path is not qualified; set nr=0 for B18 FULL_ORDER")
            aa,ts,nodes,axis,kt,ct_,method,lo,hi,method_name=self._advanced_runup_map(m,alpha,tspan)
            # Build only the historical model arrays here. Advanced bearings
            # travel through the additive coefficient-map ABI, never type-5
            # adaptation and never a Python callback from the ODE.
            legacy=RotorModel(nodes=m.nodes,shafts=m.shafts,disks=m.disks,bearings=m.bearings,forces=m.forces,bend=m.bend,rotors=m.rotors)
            n,z,sh,di,be=self._arrays(legacy);nd=4*n;fo=self._forces(m)
            time=np.empty(max_points,dtype=np.float64);speed=np.empty(max_points,dtype=np.float64);resp=np.empty((nd,max_points),dtype=np.float64,order='F')
            nout=np.zeros(1,dtype=np.int32);nru=np.zeros(1,dtype=np.int32);na=np.zeros(1,dtype=np.int32);nrj=np.zeros(1,dtype=np.int32)
            kflat=np.ascontiguousarray(np.asfortranarray(kt).ravel(order="F"))
            cflat=np.ascontiguousarray(np.asfortranarray(ct_).ravel(order="F"))
            status=self.lib.rd_runup_coeffmap_legacy(
                n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),
                fo.shape[1],self._ptr(fo),len(nodes),self._iptr(nodes),len(axis),self._ptr(axis),self._ptr(kflat),self._ptr(cflat),
                int(method),self._ptr(aa),float(ts[0]),float(ts[1]),float(rtol),float(atol),float(h_init),float(h_max),int(max_points),
                self._ptr(time),self._ptr(resp),self._ptr(speed),self._iptr(nout),self._iptr(nru),self._iptr(na),self._iptr(nrj)
            )
            if status:
                raise SolverLibraryError(
                    f"Fortran rd_runup_coeffmap_legacy returned status={status}; "
                    f"nout={int(nout[0])}, accepted_steps={int(na[0])}, "
                    f"rejected_steps={int(nrj[0])}, map=[{axis[0]}, {axis[-1]}] rad/s, "
                    f"runup=[{lo}, {hi}] rad/s"
                )
            k=int(nout[0])
            return time[:k].copy(),resp[:,:k].copy(order='F'),speed[:k].copy(),{
                "nr_used":int(nru[0]),"max_reduced_frequency_hz":0.0,
                "accepted_steps":int(na[0]),"rejected_steps":int(nrj[0]),"rtol":rtol,"atol":atol,
                "advanced_bearing_scope":"FULL_ORDER|SYNCHRONOUS_COEFFICIENT_POLICY|MAP_BASED|NO_TEHD_IN_ODE",
                "map_speed_min_rad_s":float(axis[0]),"map_speed_max_rad_s":float(axis[-1]),
                "runup_speed_min_rad_s":lo,"runup_speed_max_rad_s":hi,
                "map_points":int(len(axis)),"map_interpolation":method_name,"native_abi":"rd_runup_coeffmap_legacy",
            }
        n,z,sh,di,be=self._arrays(m);nd=4*n;fo=self._forces(m);aa=np.ascontiguousarray(alpha,dtype=np.float64);ts=np.asarray(tspan,dtype=float)
        if aa.shape!=(3,): raise ValueError("alpha must have exactly 3 coefficients [a2,a1,a0]")
        if ts.size!=2: raise ValueError("tspan must contain [t0,tf]")
        time=np.empty(max_points,dtype=np.float64);speed=np.empty(max_points,dtype=np.float64);resp=np.empty((nd,max_points),dtype=np.float64,order='F')
        nout=np.zeros(1,dtype=np.int32);nru=np.zeros(1,dtype=np.int32);na=np.zeros(1,dtype=np.int32);nrj=np.zeros(1,dtype=np.int32);maxf=np.zeros(1,dtype=np.float64)
        status=self.lib.rd_runup_legacy(n,self._ptr(z),sh.shape[1],self._ptr(sh),di.shape[1],self._ptr(di),be.shape[1],self._ptr(be),fo.shape[1],self._ptr(fo),self._ptr(aa),float(ts[0]),float(ts[1]),int(nr),float(rtol),float(atol),float(h_init),float(h_max),int(max_points),self._ptr(time),self._ptr(resp),self._ptr(speed),self._iptr(nout),self._iptr(nru),self._ptr(maxf),self._iptr(na),self._iptr(nrj))
        if status: raise SolverLibraryError(f"Fortran rd_runup_legacy returned status={status}")
        k=int(nout[0]);return time[:k].copy(),resp[:,:k].copy(order='F'),speed[:k].copy(),{"nr_used":int(nru[0]),"max_reduced_frequency_hz":float(maxf[0]),"accepted_steps":int(na[0]),"rejected_steps":int(nrj[0]),"rtol":rtol,"atol":atol}


    def level1(self,m:RotorModel,rotor_speed_rad_s,cross_coupling_node,stiffness_range_n_m,num=5):
        from .level1_backend import execute
        return execute(self,m,rotor_speed_rad_s,cross_coupling_node,stiffness_range_n_m,num)

    def level1_matrices(self,m:RotorModel,rotor_speed_rad_s,cross_coupling_node,Q_n_m):
        from .level1_backend import matrices
        return matrices(self,m,rotor_speed_rad_s,cross_coupling_node,Q_n_m)


    def api617_unbalance(self,m:RotorModel,mode:int,maximum_continuous_speed_rad_s:float,num_modes:int=12):
        from .api617_unbalance_backend import execute
        return execute(self,m,mode,maximum_continuous_speed_rad_s,num_modes)


    def clearance(self,m:RotorModel,**kwargs):
        from .clearance_backend import execute
        return execute(self,m,**kwargs)
