"""Pre-implementation proof of the assembly convention; validation-only arithmetic."""
import copy
import numpy as np
import pytest
from cases import case,ROOT,NAMES
from drm_core.solver.backend import FortranBackend
from drm_core.solver.bearings_backend import AdvancedBearingBackend

@pytest.mark.parametrize('name',NAMES)
def test_existing_native_matrices_before_frf(name):
    m,s=case(name);bare=copy.deepcopy(m);bare.advanced_bearings=[]
    M0,C0,K0,G=FortranBackend().assemble_matrices(bare,0.)
    provider=AdvancedBearingBackend()
    with np.load(ROOT/f'validation/ross_parity/frf/{name}.npz') as r:
        for i,w in enumerate(s['frequencies']):
            speed=0. if s['free_free'] else (w if s['speed'] is None else s['speed'])
            Mb=np.zeros_like(M0);Cb=Mb.copy();Kb=Mb.copy()
            for b in m.advanced_bearings:
                v=provider.evaluate(b,speed,w);idx=[4*(b.node-1),4*(b.node-1)+1]
                for a,value in [(Mb,v.M),(Cb,v.C),(Kb,v.K)]:a[np.ix_(idx,idx)]+=value
            M=M0+Mb;C=C0+Cb;K=K0+Kb;D=K-w*w*M+1j*w*(C+speed*G)
            for k,a in [('M',M),('C',C),('G',G),('K',K),('Mb',Mb),('Cb',Cb),('Kb',Kb),('D',D)]:
                np.testing.assert_allclose(a,r[k][:,:,i],rtol=2e-12,atol=1e-7 if k in ('K','Kb','D') else 1e-11,err_msg=f'{name}:{k}:{i}')
