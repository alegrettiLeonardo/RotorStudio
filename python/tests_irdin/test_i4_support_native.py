from __future__ import annotations
import ctypes as ct, os
import numpy as np, pytest
from drm_core import load_irdin_project
from drm_core.solver.ffi import load_library
from drm_core.solver.irdin_support_native import IrdinSupportInputError,support_element_matrices
from validation.irdin.i0_authority import CASE_PATH

def _project(): return load_irdin_project(CASE_PATH)

def test_i4_support_kernel_reproduces_historical_block_assembly():
    s=_project().model.supports[0]
    kb=np.array([[10.,20.],[30.,40.]]);cb=np.array([[1.,2.],[3.,4.]])
    out=support_element_matrices(bearing_K=kb,bearing_C=cb,support=s)
    ks=np.array([[s.kxx_n_m,s.kxy_n_m],[s.kyx_n_m,s.kyy_n_m]])
    cs=np.array([[s.cxx_ns_m,s.cxy_ns_m],[s.cyx_ns_m,s.cyy_ns_m]])
    np.testing.assert_array_equal(out.M,np.diag([0.,0.,415.,415.]))
    np.testing.assert_array_equal(out.K,np.block([[kb,-kb],[-kb,kb+ks]]))
    np.testing.assert_array_equal(out.C,np.block([[cb,-cb],[-cb,cb+cs]]))

def test_i4_st41_first_table_point_keeps_cross_coupling_signs():
    p=_project();s=p.model.supports[0];b=p.model.advanced_bearings[0]
    kb=np.array([[b.kxx[0],b.kxy[0]],[b.kyx[0],b.kyy[0]]])
    cb=np.array([[b.cxx[0],b.cxy[0]],[b.cyx[0],b.cyy[0]]])
    out=support_element_matrices(bearing_K=kb,bearing_C=cb,support=s)
    assert out.K[0,1]==b.kxy[0] and out.K[1,0]==b.kyx[0]
    assert out.K[0,2]==-b.kxx[0] and out.K[1,2]==-b.kyx[0]
    assert out.K[2,2]==b.kxx[0]+s.kxx_n_m and out.K[3,3]==b.kyy[0]+s.kyy_n_m

def test_i4_binding_rejects_bad_shapes_and_nonfinite():
    s=_project().model.supports[0]
    with pytest.raises(IrdinSupportInputError,match="shape"): support_element_matrices(bearing_K=np.ones(4),bearing_C=np.eye(2),support=s)
    bad=np.eye(2);bad[0,0]=np.nan
    with pytest.raises(IrdinSupportInputError,match="NaN/Inf"): support_element_matrices(bearing_K=bad,bearing_C=np.eye(2),support=s)

def test_i4_abi_capacity_failure_does_not_write_outputs():
    lib=load_library(os.environ.get("DRMROTOR_LIB"));fn=lib.rd_irdin_support_matrices_v1
    D,I,P=ct.c_double,ct.c_int,ct.POINTER(ct.c_double)
    fn.argtypes=[D,P,P,P,P,P,I,I,P,I,I,P,I,I];fn.restype=I
    z=np.ascontiguousarray(np.eye(2).ravel(order="F"),dtype=np.float64)
    sent=[np.full(24,1234567.,dtype=np.float64) for _ in range(3)];ptr=lambda a:a.ctypes.data_as(P)
    status=int(fn(415.,ptr(z),ptr(z),ptr(z),ptr(z),ptr(sent[0]),4,15,ptr(sent[1]),4,16,ptr(sent[2]),4,16))
    assert status==13
    for a in sent: np.testing.assert_array_equal(a,np.full(24,1234567.))

def test_i4_keeps_global_readiness_blocked():
    p=_project();r=p.metadata["numerical_readiness"]
    assert r["status"]=="BLOCKED_FOR_NUMERICAL_ANALYSIS"
    assert r["components"]["support_native_assembly"]=="PASS_I8_GLOBAL_MATRICES"
    assert "IRDIN_EXPANDED_SOLVER_UNQUALIFIED" in {x["code"] for x in r["blockers"]}
