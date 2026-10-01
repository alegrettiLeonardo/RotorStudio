from __future__ import annotations
from copy import deepcopy
import numpy as np
import pytest

from drm_core import load_irdin_project
from drm_core.solver.facade import SolverFacade
from drm_core.solver.irdin_support_global import assemble_support_global_matrices,support_arrays
from validation.irdin.i0_authority import CASE_PATH


def test_i8_analytical_single_support_block():
    mr=np.zeros((8,8));cr=np.zeros((8,8));gr=np.zeros((8,8));kr=np.zeros((8,8))
    mr[0,0]=7;gr[2,3]=2
    kb=np.array([[[10.,20.],[30.,40.]]]);cb=np.array([[[1.,2.],[3.,4.]]])
    ks=np.array([[[100.,0.],[0.,200.]]]);cs=np.zeros((1,2,2))
    out=assemble_support_global_matrices(rotor_M=mr,rotor_C=cr,rotor_G=gr,rotor_K=kr,
        support_nodes=[2],support_masses=[5.],bearing_K=kb,bearing_C=cb,support_K=ks,support_C=cs)
    assert out.M.shape==(10,10)
    assert out.M[0,0]==7 and out.M[8,8]==5 and out.M[9,9]==5
    np.testing.assert_array_equal(out.K[4:6,4:6],kb[0])
    np.testing.assert_array_equal(out.K[4:6,8:10],-kb[0])
    np.testing.assert_array_equal(out.K[8:10,4:6],-kb[0])
    np.testing.assert_array_equal(out.K[8:10,8:10],kb[0]+ks[0])
    assert out.G[2,3]==2
    assert np.count_nonzero(out.G[8:,:])==0 and np.count_nonzero(out.G[:,8:])==0


def test_i8_st41_global_matrix_dimensions_and_support_blocks():
    p=load_irdin_project(CASE_PATH)
    rotor=deepcopy(p.model)
    rotor.advanced_bearings=[];rotor.bearings=[];rotor.supports=[]
    facade=SolverFacade()
    mr,cr,kr,gr=facade.assemble(rotor,0.0)
    nodes,mass,ks,cs=support_arrays(p.model.supports)
    kb=[];cb=[]
    for b in p.model.advanced_bearings:
        kb.append([[b.kxx[0],b.kxy[0]],[b.kyx[0],b.kyy[0]]])
        cb.append([[b.cxx[0],b.cxy[0]],[b.cyx[0],b.cyy[0]]])
    out=assemble_support_global_matrices(rotor_M=mr,rotor_C=cr,rotor_G=gr,rotor_K=kr,
        support_nodes=nodes,support_masses=mass,bearing_K=np.asarray(kb),bearing_C=np.asarray(cb),
        support_K=ks,support_C=cs)
    nd=4*len(p.model.nodes)
    assert out.M.shape==(nd+4,nd+4)
    for i,s in enumerate(p.model.supports):
        q=nd+2*i
        assert out.M[q,q]==pytest.approx(415.0)
        assert out.M[q+1,q+1]==pytest.approx(415.0)
        r=4*s.node-4
        np.testing.assert_allclose(out.K[r:r+2,q:q+2],-np.asarray(kb[i]),rtol=0,atol=0)


def test_i8_invalid_node_fails_closed():
    z=np.zeros((8,8));tab=np.zeros((1,2,2))
    with pytest.raises(ValueError):
        assemble_support_global_matrices(rotor_M=z,rotor_C=z,rotor_G=z,rotor_K=z,
            support_nodes=[3],support_masses=[1.],bearing_K=tab,bearing_C=tab,support_K=tab,support_C=tab)
