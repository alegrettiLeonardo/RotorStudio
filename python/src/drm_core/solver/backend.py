from __future__ import annotations
import ctypes as ct
import numpy as np
from .ffi import load_library, configure, SolverLibraryError
from drm_core.domain.model import (
    RotorModel, ShaftElement, TaperedShaftElement, AsymmetricShaftElement
)
from drm_core.validation.model import validate_model

class FortranBackend:
    def __init__(self,library_path=None):
        self.lib=configure(load_library(library_path))

    @staticmethod
    def _dptr(a:np.ndarray):
        return a.ctypes.data_as(ct.POINTER(ct.c_double))

    @staticmethod
    def _iptr(a:np.ndarray):
        return a.ctypes.data_as(ct.POINTER(ct.c_int))

    def version(self)->str:
        a=ct.c_int(); b=ct.c_int(); c=ct.c_int()
        status=self.lib.rd_version(ct.byref(a),ct.byref(b),ct.byref(c))
        if status:
            raise SolverLibraryError(f"Fortran rd_version returned status={status}")
        return f"{a.value}.{b.value}.{c.value}"

    def _legacy_arrays(self,m:RotorModel):
        validate_model(m,stationary=True)
        n=len(m.nodes); ndof=4*n
        ordered=sorted(m.nodes,key=lambda x:x.number)
        z=np.ascontiguousarray([x.z_m for x in ordered],dtype=np.float64)
        sh=np.zeros((11,len(m.shafts)),dtype=np.float64,order='F')
        for j,s in enumerate(m.shafts):
            if isinstance(s,TaperedShaftElement):
                sh[:,j]=[
                    s.shaft_type,s.node1,s.node2,
                    s.outer_diameter_1_m,s.outer_diameter_2_m,
                    s.inner_diameter_1_m,s.inner_diameter_2_m,
                    s.rho_kg_m3,s.E_pa,s.G_pa,s.axial_force_n,
                ]
            elif isinstance(s,ShaftElement):
                sh[:,j]=[
                    s.shaft_type,s.node1,s.node2,
                    s.outer_diameter_m,s.inner_diameter_m,
                    s.rho_kg_m3,s.E_pa,s.G_pa,s.damping_factor,
                    s.axial_force_n,s.torque_nm,
                ]
            else:
                raise SolverLibraryError(
                    "Stationary Fortran path only accepts circular/tapered shafts; "
                    "asymmetric shafts belong to the rotating-frame solver"
                )
        di=np.zeros((6,len(m.disks)),dtype=np.float64,order='F')
        for j,d in enumerate(m.disks):
            di[:,j]=[d.disk_type,d.node,d.p3,d.p4,d.p5,d.p6]
        be=np.zeros((34,len(m.bearings)),dtype=np.float64,order='F')
        for j,b in enumerate(m.bearings):
            vals=[b.bearing_type,b.node,*b.properties]
            if len(vals)>34:
                raise ValueError(f"Bearing[{j+1}] has {len(vals)} legacy columns; maximum is 34")
            be[:len(vals),j]=vals
        zero=set()
        for b in m.bearings:
            if b.bearing_type==1:
                zero.update((4*b.node-3,4*b.node-2))
            elif b.bearing_type==2:
                zero.update(range(4*b.node-3,4*b.node+1))
        return z,sh,di,be,ndof,ndof-len(zero)

    @staticmethod
    def _force_arrays(m:RotorModel):
        fo=np.zeros((5,len(m.forces)),dtype=np.float64,order='F')
        for j,f in enumerate(m.forces):
            vals=[float(f.force_type),*map(float,f.parameters)]
            if len(vals)>5:
                raise ValueError(f"Force[{j+1}] has {len(vals)} legacy columns; freq_rsp accepts at most 5")
            fo[:len(vals),j]=vals
        bn=np.zeros((3,len(m.bend)),dtype=np.float64,order='F')
        for j,b in enumerate(m.bend):
            bn[:,j]=[b.node,b.x_m,b.y_m]
        return fo,bn

    def assemble_stationary(self,m:RotorModel,speed_rad_s:float=0.0):
        z,sh,di,be,ndof,_=self._legacy_arrays(m)
        outs=[np.empty((ndof,ndof),dtype=np.float64,order='F') for _ in range(5)]
        zero=np.empty(ndof,dtype=np.int32)
        ecc=np.zeros(len(m.bearings),dtype=np.float64)
        status=self.lib.rd_assemble_legacy(
            len(m.nodes),self._dptr(z),len(m.shafts),self._dptr(sh),
            len(m.disks),self._dptr(di),len(m.bearings),self._dptr(be),float(speed_rad_s),
            *(self._dptr(x) for x in outs),self._iptr(zero),self._dptr(ecc)
        )
        if status:
            raise SolverLibraryError(f"Fortran rd_assemble_legacy returned status={status}")
        return (*outs,zero.astype(bool),ecc)

    def modal_solution(self,m:RotorModel,speed_rad_s:float):
        z,sh,di,be,ndof,nactive=self._legacy_arrays(m)
        nout=2*nactive
        er=np.empty(nout); ei=np.empty(nout)
        vr=np.zeros((ndof,nout),dtype=np.float64,order='F')
        vi=np.zeros((ndof,nout),dtype=np.float64,order='F')
        ecc=np.zeros(len(m.bearings),dtype=np.float64)
        status=self.lib.rd_modal_full_legacy(
            len(m.nodes),self._dptr(z),len(m.shafts),self._dptr(sh),len(m.disks),self._dptr(di),
            len(m.bearings),self._dptr(be),float(speed_rad_s),nout,
            self._dptr(er),self._dptr(ei),self._dptr(vr),self._dptr(vi),self._dptr(ecc)
        )
        if status:
            raise SolverLibraryError(f"Fortran rd_modal_full_legacy returned status={status}")
        return er+1j*ei, vr+1j*vi, ecc

    def modal_eigenvalues(self,m:RotorModel,speed_rad_s:float)->np.ndarray:
        return self.modal_solution(m,speed_rad_s)[0]

    def frequency_response(self,m:RotorModel,speeds_rad_s)->np.ndarray:
        speeds=np.ascontiguousarray(np.asarray(speeds_rad_s,dtype=np.float64))
        if speeds.ndim!=1 or speeds.size==0:
            raise ValueError("speeds_rad_s must be a non-empty 1-D sequence")
        z,sh,di,be,ndof,_=self._legacy_arrays(m)
        fo,bn=self._force_arrays(m)
        rr=np.empty((ndof,speeds.size),dtype=np.float64,order='F')
        ri=np.empty_like(rr,order='F')
        status=self.lib.rd_frequency_response_legacy(
            len(m.nodes),self._dptr(z),len(m.shafts),self._dptr(sh),len(m.disks),self._dptr(di),
            len(m.bearings),self._dptr(be),len(m.forces),self._dptr(fo),len(m.bend),self._dptr(bn),
            speeds.size,self._dptr(speeds),self._dptr(rr),self._dptr(ri)
        )
        if status:
            raise SolverLibraryError(f"Fortran rd_frequency_response_legacy returned status={status}")
        return rr+1j*ri

    def critical_speeds(self,m:RotorModel,*,NX:float=1.0,damped_NF:bool=True,number_criticals:int=5,
                        max_iterations:int=20,convergence_tol:float=1e-6,method:str='auto',initial_estimates=None):
        z,sh,di,be,ndof,_=self._legacy_arrays(m)
        codes={'auto':0,'direct':1,'iterative-index':2,'iterative-nearest':3,'iterative':2}
        if method not in codes:
            raise ValueError("method must be auto, direct, iterative-index/iterative, or iterative-nearest")
        method_code=codes[method]
        if method_code==3:
            if initial_estimates is None:
                raise ValueError("iterative-nearest requires initial_estimates")
            initial=np.ascontiguousarray(np.asarray(initial_estimates,dtype=np.float64))
            if initial.ndim!=1 or initial.size==0:
                raise ValueError("initial_estimates must be a non-empty 1-D sequence")
            n=int(initial.size)
        else:
            n=int(number_criticals)
            if n<=0:
                raise ValueError("number_criticals must be > 0")
            initial=np.zeros(n,dtype=np.float64) if initial_estimates is None else np.ascontiguousarray(np.asarray(initial_estimates,dtype=np.float64))
            if initial.size<n:
                raise ValueError("initial_estimates shorter than number_criticals")
            initial=np.ascontiguousarray(initial[:n],dtype=np.float64)
        critical=np.empty(n,dtype=np.float64)
        iterations=np.empty(n,dtype=np.int32)
        converged=np.empty(n,dtype=np.int32)
        mr=np.zeros((ndof,n),dtype=np.float64,order='F')
        mi=np.zeros_like(mr,order='F')
        status=self.lib.rd_critical_speeds_full_legacy(
            len(m.nodes),self._dptr(z),len(m.shafts),self._dptr(sh),len(m.disks),self._dptr(di),
            len(m.bearings),self._dptr(be),method_code,float(NX),int(bool(damped_NF)),n,
            int(max_iterations),float(convergence_tol),self._dptr(initial),self._dptr(critical),
            self._iptr(iterations),self._iptr(converged),self._dptr(mr),self._dptr(mi)
        )
        if status:
            raise SolverLibraryError(f"Fortran rd_critical_speeds_full_legacy returned status={status}")
        return critical,mr+1j*mi,iterations,converged.astype(bool)

    def shaft_element_matrices(self,s,Le:float):
        if Le<=0:
            raise ValueError("Le must be > 0")
        p=np.zeros(8,dtype=np.float64)
        if isinstance(s,TaperedShaftElement):
            p[:]=[
                s.outer_diameter_1_m,s.outer_diameter_2_m,s.inner_diameter_1_m,s.inner_diameter_2_m,
                s.rho_kg_m3,s.E_pa,s.G_pa,s.axial_force_n,
            ]
        elif isinstance(s,ShaftElement):
            p[:7]=[
                s.outer_diameter_m,s.inner_diameter_m,s.rho_kg_m3,s.E_pa,s.G_pa,
                s.axial_force_n,s.torque_nm,
            ]
        elif isinstance(s,AsymmetricShaftElement):
            p[:7]=[s.EIx_nm2,s.EIy_nm2,s.phi_x,s.phi_y,s.rhoA_kg_m,s.rhoI_kg_m,s.axial_force_n]
        else:
            raise TypeError(type(s))
        outs=[np.empty((8,8),dtype=np.float64,order='F') for _ in range(4)]
        status=self.lib.rd_shaft_element_legacy(int(s.shaft_type),float(Le),self._dptr(p),*(self._dptr(x) for x in outs))
        if status:
            raise SolverLibraryError(f"Fortran rd_shaft_element_legacy returned status={status}")
        return tuple(outs)
