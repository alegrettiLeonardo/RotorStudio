"""Fixed-tolerance verifier for additive UCS bearing-order authorities.

Historical A5 tolerances are reused without alteration. This module is
validation-only, never imported by the production solver.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from ucs_bearing_order_cases import ROSS_SHA,specifications,native_model

GOLD=Path(__file__).parent/'ucs_bearing_order'
# Existing A5 gates; derived constant axes inherit the modal tolerance.
TOLERANCES={
 'stiffness_log_n_m':(2e-12,1e-8),
 'natural_frequency_rad_s':(2e-8,2e-6),
 'bearing_speed_rad_s':(2e-12,1e-9),
 'bearing_kxx_n_m':(2e-10,1e-5),'bearing_kyy_n_m':(2e-10,1e-5),
 'intersection_stiffness_n_m':(2e-7,2e-2),
 'intersection_speed_rad_s':(2e-7,2e-5),
 'critical_wn_rad_s':(3e-8,3e-6),'critical_wd_rad_s':(3e-8,3e-6),
 'critical_eigenvalue_real':(3e-8,3e-6),'critical_eigenvalue_imag':(3e-8,3e-6),
 # Dissipative quantities of the undamped critical rotor are zero, modulo
 # eigensolution roundoff. These additional absolute gates do not relax wn.
 'critical_damping_ratio':(0.,1e-8),'critical_log_dec':(0.,1e-8),
}
EXACT=('intersection_mode_index','intersection_coefficient','coefficient_families','bearing_speed_policy')


def load_authority(root=GOLD,check_sources=True):
    m=json.loads((root/'authority.json').read_text(encoding='utf-8'))
    assert m['ross_sha']==ROSS_SHA
    assert set(m['files'])=={name+'.json' for name in specifications()}
    for name,expected in m['files'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
    if check_sources:
        for filename,key in [('generate_ucs_bearing_order_reference.py','generator_sha256'),
                             ('ucs_bearing_order_cases.py','cases_sha256')]:
            assert hashlib.sha256((Path(__file__).parent/filename).read_bytes()).hexdigest()==m[key],filename
    return {name:json.loads((root/(name+'.json')).read_text(encoding='utf-8')) for name in specifications()}


def compare_arrays(actual,expected):
    differences={}
    for name,(rtol,atol) in TOLERANCES.items():
        a=np.asarray(actual[name]);b=np.asarray(expected[name])
        if name=='bearing_speed_rad_s' and expected['bearing_speed_policy']=='constant_10_point_rotor_wn_margin':
            rtol,atol=TOLERANCES['natural_frequency_rad_s']
        assert a.shape==b.shape,(name,a.shape,b.shape)
        assert np.isfinite(a).all() and np.isfinite(b).all(),name
        np.testing.assert_allclose(a,b,rtol=rtol,atol=atol,err_msg=name)
        differences[name]=float(np.max(np.abs(a-b))) if a.size else 0.
    for name in EXACT:
        np.testing.assert_array_equal(actual[name],expected[name],err_msg=name)
    return differences


def check_native(name,g):
    from drm_core import run_ucs
    from drm_core.solver.backend import FortranBackend
    from drm_core.solver.ucs_backend import _validate_model
    spec=specifications()[name]
    assert spec==g['specification']
    model=native_model(spec);before=model.model_hash()
    original=model.canonical_dict()
    supports=_validate_model(None,model,(6,10),7,16,spec['bearing_speed_range'],spec['synchronous'])[5]
    assert supports[0].node==g['selected_bearing_node']
    if spec['family']=='coefficient':assert supports[0].tag==g['selected_bearing_tag']
    result=run_ucs(model,(6,10),num=7,num_modes=16,
        bearing_speed_range=spec['bearing_speed_range'],synchronous=spec['synchronous'])
    assert result.metadata['native_abi']=='rd_ucs_v1'
    differences=compare_arrays(vars(result),g['result'])
    assert model.model_hash()==before and model.canonical_dict()==original
    backend=FortranBackend()
    for sent in g['matrix_sentinels']:
        matrix=backend.ucs_matrices(model,sent['stiffness_n_m'],spec['synchronous'])
        assert np.count_nonzero(matrix['C'])==0
        for key in ['M','G','K']:
            np.testing.assert_allclose(matrix[key],sent[key],rtol=2e-12,
                atol=1e-6 if key=='K' else 2e-12,err_msg=name+': '+key)
    return differences


def verify(candidate=None):
    gold=load_authority();report={}
    if candidate is not None:
        rebuilt=load_authority(candidate)
        for name,g in gold.items():
            other=rebuilt[name]
            for key in ['ross_sha','specification','input_insertion_order','effective_ross_order',
                        'effective_ross_tags','selected_bearing_node','selected_bearing_tag']:
                assert other[key]==g[key],(name,key)
            report[name]=compare_arrays(other['result'],g['result'])
            for a,b in zip(other['matrix_sentinels'],g['matrix_sentinels'],strict=True):
                assert a['stiffness_n_m']==b['stiffness_n_m']
                for key in ['M','G','K']:
                    np.testing.assert_allclose(a[key],b[key],rtol=2e-12,atol=1e-6 if key=='K' else 2e-12)
                assert np.count_nonzero(a['C'])==0 and np.count_nonzero(b['C'])==0
    else:
        for name,g in gold.items():report[name]=check_native(name,g)
    return dict(status='PASS',ross_sha=ROSS_SHA,mode='candidate' if candidate else 'actual_Fortran',
                cases=len(report),max_absolute_differences=report)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args();r=verify(a.candidate);text=json.dumps(r,indent=2)
    if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text+'\n',encoding='utf-8')
    print(text)
