import json
from pathlib import Path
import shutil
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate_reference import generate
from verify_reference import verify,compare
ROOT=Path(__file__).resolve().parents[1]/'static'

def test_integrity():
    verify(ROOT)

def test_self_comparison():
    compare(ROOT,ROOT)

@pytest.mark.parametrize('name',['uniform','stepped_overhung','three_supports'])
def test_equilibrium(name):
    spec=json.loads((ROOT/f'{name}.json').read_text())
    with np.load(ROOT/f'{name}.npz') as d:
        total=d['shaft_weight_N'][0]+sum(d['disk_weight_N'])
        np.testing.assert_allclose(sum(d['bearing_reactions_N']),total,rtol=1e-11,atol=1e-9)
        x=d['nodes_x_m']; lengths=np.array(spec['lengths_m'])
        weights=spec['rho_kg_m3']*np.pi/4*np.array(spec['outer_diameters_m'])**2*lengths*9.8065
        moment_load=sum(weights*(x[:-1]+lengths/2))+sum(d['disk_weight_N']*x[d['disk_nodes'].astype(int)])
        moment_reaction=sum(d['bearing_reactions_N']*x[d['bearing_nodes'].astype(int)])
        np.testing.assert_allclose(moment_reaction,moment_load,rtol=1e-11,atol=1e-9)
        assert d['shear_force_N'].shape==d['bending_moment_Nm'].shape==(2*len(lengths),)

@pytest.mark.parametrize('failure',['corrupt','missing','wrong_sha','extra'])
def test_integrity_fail_closed(tmp_path,failure):
    target=tmp_path/'reference';shutil.copytree(ROOT,target)
    if failure=='corrupt': (target/'uniform.npz').write_bytes(b'corrupt')
    if failure=='missing': (target/'uniform.npz').unlink()
    if failure=='extra': (target/'unexpected.json').write_text('{}')
    if failure=='wrong_sha':
        p=target/'authority.json';m=json.loads(p.read_text());m['commit']='0'*40;p.write_text(json.dumps(m))
    with pytest.raises((ValueError,FileNotFoundError)):verify(target)

def test_generation_rejects_wrong_checkout(tmp_path):
    import subprocess
    subprocess.run(['git','init',str(tmp_path/'repo')],check=True,capture_output=True)
    with pytest.raises(subprocess.CalledProcessError):generate(tmp_path/'repo',tmp_path/'out')
    assert not (tmp_path/'out').exists()
