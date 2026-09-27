import json
import sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'validation/ross_parity'))
from static_abi import call_native

@pytest.mark.parametrize('name',['uniform','stepped_overhung','three_supports'])
def test_a0_immutable_static_abi(name):
    root=ROOT/'validation/ross_parity/static'
    spec=json.loads((root/f'{name}.json').read_text());out=call_native(spec)
    with np.load(root/f'{name}.npz') as ref:
        for key,actual,atol in [
            ('displacement_y_m',out['q'][1::4],1e-13),
            ('bearing_reactions_N',out['reactions'][spec['supports']],1e-8),
            ('shaft_weight_N',[sum(out['shaft_weights'])],1e-8),
            ('disk_weight_N',out['disk_weights'],1e-8),
            ('shear_force_N',out['shear'],1e-8),
            ('bending_moment_Nm',out['bending'],1e-8),
            ('x_m',out['stations'],1e-14)]:
            np.testing.assert_allclose(actual,ref[key],rtol=1e-8,atol=atol,err_msg=key)
    assert abs(out['diagnostics'][0])<1e-8
    assert abs(out['diagnostics'][1])<1e-8
    assert out['diagnostics'][2]<1e-14

@pytest.mark.parametrize('name',['timoshenko_hollow','rotary_eb','no_disk','seal_excluded','mass_disk'])
def test_extended_static(name):
    root=ROOT/'validation/ross_parity/static_extended'
    spec=json.loads((root/f'{name}.json').read_text());out=call_native(spec)
    with np.load(root/f'{name}.npz') as ref:
        for key,actual,atol in [('displacement_y_m',out['q'][1::4],1e-13),('bearing_reactions_N',out['reactions'][spec['supports']],1e-8),('shaft_weight_N',[sum(out['shaft_weights'])],1e-8),('disk_weight_N',out['disk_weights'],1e-8),('shear_force_N',out['shear'],1e-8),('bending_moment_Nm',out['bending'],1e-8),('x_m',out['stations'],1e-14)]:
            np.testing.assert_allclose(actual,ref[key],rtol=1e-8,atol=atol,err_msg=key)
    assert max(abs(out['diagnostics'][:2]))<1e-8
    assert out['diagnostics'][2]<1e-14

def test_all_circular_matrix_entries():
    sys.path.insert(0,str(ROOT/'validation/equivalence'))
    from element_abi import circular
    root=ROOT/'validation/ross_parity/static_extended'
    with np.load(root/'elements.npz') as ref:
        for s in json.loads((root/'elements.json').read_text()):
            M,C,K,K1=circular(s['shaft_type'],s['L'],s['do'],s['di'],s['E'],s['G'],s['rho'],0.,0.)
            for suffix,a in [('M',M),('K',K)]:
                np.testing.assert_allclose(a,ref[s['key']+'_'+suffix],rtol=1e-10,atol=1e-12,err_msg=s['key']+suffix)
