import json
import numpy as np
import pytest
from drm_core.solver.backend import FortranBackend
from time_cases import case,NAMES,ROOT
from matrix_probe import configure,matrices

def test_elements():
    b=FortranBackend();configure(b.lib);p=b._ptr
    root=ROOT/'validation/ross_parity/time_response'
    s=json.loads((root/'elements.json').read_text())
    with np.load(root/'elements.npz') as g:
        for i,args in enumerate(s['shafts']):
            a=np.zeros((8,8),order='F');assert b.lib.rd_transient_shaft_v1(*args,p(a))==0
            np.testing.assert_allclose(a,g[f'shaft_{i}'],rtol=2e-12,atol=1e-14)
        for i,ip in enumerate(s['disks']):
            a=np.zeros((4,4),order='F');assert b.lib.rd_transient_disk_v1(ip,p(a))==0
            np.testing.assert_array_equal(a,g[f'disk_{i}'])

@pytest.mark.parametrize('name',NAMES)
def test_matrix_authority(name):
    b=FortranBackend();m,s=case(name);a=matrices(b,m,s)
    with np.load(ROOT/f'validation/ross_parity/time_response/{name}.npz') as g:
        for key,value in a.items():
            expected=g[key]
            if value.ndim==3 and expected.ndim==2:expected=np.repeat(expected[:,:,None],len(s['time_s']),axis=2)
            if key=='Fg':expected=np.repeat(expected[:,None],len(s['time_s']),axis=1)
            np.testing.assert_allclose(value,expected,rtol=2e-12,atol=1e-7 if key in ('K','Keff') else (1e-8 if key=='alpha' else 1e-11),err_msg=f'{name}: {key}')
        f=np.asarray(s['force_real'])+(a['Fg'] if s['weight'] else 0)
        np.testing.assert_allclose(f,g['F'],rtol=2e-12,atol=1e-11)
        if np.ndim(s['speed']):
            assert np.max(abs(a['Keff']-a['K']))>1
            assert np.max(abs(a['Ceff']-a['C']))>1
            # K1 legacy is zero in qualified undamped shafts, whereas Ksdt is not.
            assert np.max(abs(a['Ksdt']))>0.01

def test_gradient_nonuniform_signed_and_invalid():
    b=FortranBackend();configure(b.lib);p=b._ptr
    for t in (np.array([0.,.3]),np.array([0.,.01,.05,.07,.12])):
        speed=37*t*t-3*t-11;alpha=np.zeros_like(t)
        assert b.lib.rd_speed_gradient_v1(len(t),p(t),p(speed),p(alpha))==0
        np.testing.assert_allclose(alpha,np.gradient(speed,t),rtol=2e-12,atol=1e-11)
    for t in (np.array([0.,0.]),np.array([1.,0.]),np.array([0.,np.nan])):
        assert b.lib.rd_speed_gradient_v1(2,p(t),p(np.ones(2)),p(np.zeros(2)))!=0
