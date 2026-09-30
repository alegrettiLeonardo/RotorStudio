"""B1 native qualification only. Never generates or rewrites ROSS authority.

Calls the Fortran binding, reads frozen arrays/policy, and records all 113
primary comparisons, 63 lateral selections, independent physics and the
preserved legacy common-domain cross-check. NumPy algebra is validation only.
"""
from __future__ import annotations
import argparse
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from drm_core.solver.sixdof_elements import shaft_matrices, disk_matrices
from validation.b1.tests.test_frozen_authority import locked_integrity
from validation.ross_parity.verify_6dof_elements_candidate import compare_entries, snapshot
from validation.equivalence.element_abi import circular

FROZEN = ROOT / 'validation/ross_parity/6dof_elements'
P = [0, 1, 3, 4, 6, 7, 9, 10]
AXIAL, TORSION = [2, 8], [5, 11]
EPS = np.finfo(np.float64).eps


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8')


def inputs():
    spec = json.loads((ROOT/'validation/b1/element_cases.json').read_text())
    result = {}
    for case in spec['shaft_cases']:
        params = dict(spec['shaft_base']); params.update(case['overrides'])
        material = dict(spec['materials'][params.pop('material')]); material.pop('name')
        params.pop('n'); params['shear_method'] = params.pop('shear_method_calc')
        params.update(material)
        result[case['id']] = ('shaft', params)
    for case in spec['disk_cases']:
        result[case['id']] = ('disk', {k: case[k] for k in ('m', 'Id', 'Ip')})
    assert len(result)==29 and len(spec['shaft_cases'])==26 and len(spec['disk_cases'])==3
    return result


def metrics(a, b, mask=None):
    if mask is None: mask = np.ones(b.shape, dtype=bool)
    indexes = np.argwhere(mask)
    errors = np.abs(a[mask]-b[mask])
    relative = np.divide(errors, np.abs(b[mask]), out=np.zeros_like(errors), where=b[mask]!=0)
    ia, ir = int(errors.argmax()), int(relative.argmax())
    return {'max_absolute_difference':float(errors[ia]),
            'max_absolute_index_zero_based': indexes[ia].tolist(),
            'max_relative_difference_nonzero':float(relative[ir]),
            'max_relative_index_zero_based':indexes[ir].tolist()}


def comparison(a, b, kind, name, policy, lateral=False):
    assert a.shape==b.shape and a.dtype==np.float64 and np.isfinite(a).all()
    groups = []
    outside = True
    if kind=='disk':
        groups = [(f'disk_{name}', np.ones(b.shape, dtype=bool))]
    elif lateral or name not in ('M', 'K'):
        key = f'shaft_{name}_lateral' if name in ('M', 'K') else f'shaft_{name}'
        groups = [(key, np.ones(b.shape, dtype=bool))]
    else:
        covered = np.zeros(b.shape, dtype=bool)
        for label, indices in (('lateral',P),('axial',AXIAL),('torsional',TORSION)):
            mask=np.zeros(b.shape,dtype=bool); mask[np.ix_(indices,indices)]=True
            groups.append((f'shaft_{name}_{label}',mask)); covered |= mask
        outside=bool(np.all(a[~covered]==0) and np.all(b[~covered]==0))
    blocks=[]
    for key,mask in groups:
        result=compare_entries(a[mask],b[mask],policy['blocks'][key])
        result.update(metrics(a,b,mask)); result['block']=key
        blocks.append(result)
    return {'status':'PASS' if outside and all(x['status']=='PASS' for x in blocks) else 'FAIL',
            'structural_cross_block_zeros':outside, 'blocks':blocks, **metrics(a,b)}


def qualify(out: Path, library_path=None):
    out=out.resolve()
    if out==FROZEN or out.is_relative_to(FROZEN): raise ValueError('Evidence cannot overwrite immutable authority')
    out.mkdir(parents=True,exist_ok=True)
    frozen_before=snapshot(FROZEN)
    integrity=locked_integrity(FROZEN)
    authority=json.loads((FROZEN/'authority.json').read_text())
    policy=json.loads((FROZEN/'tolerances.json').read_text())
    cases=inputs(); native={}; short={}
    for name,(kind,params) in cases.items():
        obj=(shaft_matrices if kind=='shaft' else disk_matrices)(**params,library_path=library_path)
        matrices={f.name:getattr(obj,f.name) for f in dataclasses.fields(obj)}
        assert all(a.flags.f_contiguous and np.isfinite(a).all() for a in matrices.values())
        native[name]=matrices; short[name.split('_')[0]]=name
        for mat,a in matrices.items():
            dest=out/'arrays'/f'{name.split("_")[0]}_{mat}.npy'; dest.parent.mkdir(exist_ok=True)
            np.save(dest,a,allow_pickle=False)
    primary=[]; lateral=[]; maxima={}
    for record in authority['arrays']:
        name=record['matrix']; cid=record['case_id']; kind=cases[cid][0]
        a=native[cid][name]
        is_lateral=record['category']!='element'
        if is_lateral: a=a[np.ix_(P,P)]
        b=np.load(FROZEN/record['filename'],allow_pickle=False)
        result=comparison(a,b,kind,name,policy,is_lateral)
        result.update(case=cid,matrix=name,reference_file=record['filename'])
        (lateral if is_lateral else primary).append(result)
        if not is_lateral:
            group=maxima.setdefault(f'{kind}_{name}',{'max_absolute_difference':-1.,'max_relative_difference_nonzero':-1.})
            for metric in ('max_absolute_difference','max_relative_difference_nonzero'):
                if result[metric]>group[metric]:
                    index='max_absolute_index_zero_based' if metric=='max_absolute_difference' else 'max_relative_index_zero_based'
                    group[metric]=result[metric]; group[metric+'_case']=cid; group[metric+'_index']=result[index]
    assert len(primary)==113 and len(lateral)==63
    # Loaded-minus-baseline comparisons use the frozen per-entry subtraction floor.
    additions=[]
    rb=np.load(FROZEN/'arrays/S02_K.npy',allow_pickle=False)[np.ix_(P,P)]
    nb=native[short['S02']]['K'][np.ix_(P,P)]
    for prefix,key in [('S20','shaft_axial_load_addition'),('S21','shaft_axial_load_addition'),
                       ('S22','shaft_torque_addition'),('S23','shaft_torque_addition')]:
        rr=np.load(FROZEN/f'arrays/{prefix}_K.npy',allow_pickle=False)[np.ix_(P,P)]
        aa=native[short[prefix]]['K'][np.ix_(P,P)]
        tolerance=policy['blocks'][key]
        floor=tolerance['cancellation_epsilon_multiplier']*EPS*(np.abs(rr)+np.abs(rb))
        item=compare_entries(aa-nb,rr-rb,tolerance,floor=floor,exact_pattern=False)
        item.update(case=prefix,block=key,**metrics(aa-nb,rr-rb))
        additions.append(item)
    checks=[]
    def check(name, ok, **details):
        checks.append({'name':name,'status':'PASS' if bool(ok) else 'FAIL',**details})
    def within(a,b,key):
        return compare_entries(np.asarray(a),np.asarray(b),policy['blocks'][key])['status']=='PASS'
    # All matrices remain observable here before aggregate PASS is possible.
    for cid,(kind,p) in cases.items():
        z=native[cid]; M=z['M']; G=z['G']
        check(cid+':mass_symmetry',np.array_equal(M,M.T))
        try:
            np.linalg.cholesky(M)
            positive=True
        except np.linalg.LinAlgError:
            positive=False
        check(cid+':positive_mass',positive,min_eigenvalue=float(np.linalg.eigvalsh(M).min()))
        check(cid+':gyro_skew',np.array_equal(G,-G.T) and np.all(np.diag(G)==0))
        v=np.linspace(-0.713,1.127,len(M))
        gyrowork=float(v@G@v); bound=1024*EPS*float(np.linalg.norm(G)*np.dot(v,v))
        check(cid+':gyro_no_work',abs(gyrowork)<=bound,residual=abs(gyrowork),bound=bound)
        if kind=='disk':
            dm=np.diag([p['m']]*3+[p['Id']]*2+[p['Ip']]); dg=np.zeros((6,6)); dk=np.zeros((6,6))
            dg[3,4]=p['Ip']; dg[4,3]=-p['Ip']; dk[4,3]=p['Ip']
            check(cid+':direct_input_identities',np.array_equal(M,dm) and np.array_equal(G,dg) and np.array_equal(z['Kdt'],dk))
            continue
        K=z['K']; L=p['L']
        check(cid+':stiffness_symmetry_condition',np.array_equal(K,K.T) if p['torque']==0 else not np.array_equal(K,K.T))
        if not p['gyroscopic']: check(cid+':gyro_disabled',np.count_nonzero(G)==0)
        Al=np.pi*(p['odl']**2-p['idl']**2)/4; Ar=np.pi*(p['odr']**2-p['idr']**2)/4
        Il=np.pi*(p['odl']**4-p['idl']**4)/64; Ir=np.pi*(p['odr']**4-p['idr']**4)/64
        Ae=(Al+Ar)/2; Je=Il+Ir
        patM=np.array([[2.,1.],[1.,2.]]); patK=np.array([[1.,-1.],[-1.,1.]])
        check(cid+':axial_endpoint_mass',within(M[np.ix_(AXIAL,AXIAL)],patM*p['rho']*Ae*L/6,'shaft_M_axial'))
        check(cid+':torsional_endpoint_mass',within(M[np.ix_(TORSION,TORSION)],patM*p['rho']*Je*L/6,'shaft_M_torsional'))
        check(cid+':axial_endpoint_stiffness',within(K[np.ix_(AXIAL,AXIAL)],patK*p['E']*Ae/L,'shaft_K_axial'))
        check(cid+':torsional_endpoint_stiffness',within(K[np.ix_(TORSION,TORSION)],patK*p['G_s']*Je/L,'shaft_K_torsional'))
        cylindrical=p['idl']==p['idr'] and p['odl']==p['odr']
        if cylindrical and p['axial_force']==0 and p['torque']==0:
            rigid=np.zeros((12,6))
            rigid[[0,6],0]=1; rigid[[1,7],1]=1; rigid[[2,8],2]=1; rigid[[5,11],3]=1
            rigid[[3,9],4]=1; rigid[7,4]=-L
            rigid[[4,10],5]=1; rigid[6,5]=L
            for i in range(6):
                res=float(np.abs(K@rigid[:,i]).max())
                limit=4096*EPS*float(np.linalg.norm(K,np.inf))*max(1.,float(np.abs(rigid[:,i]).max()))
                check(cid+f':rigid_{i}',res<=limit,residual=res,bound=limit)
            for indices,stiff,key in [(AXIAL,p['E']*Al/L,'axial'),(TORSION,p['G_s']*(2*Il)/L,'torsion')]:
                q=np.zeros(12); q[indices]=[0.013,-0.007]
                observed=float(0.5*q@K@q); expected=float(0.5*stiff*(q[indices[1]]-q[indices[0]])**2)
                check(cid+':energy_'+key,abs(observed-expected)<=1024*EPS*abs(expected),observed=observed,expected=expected)
            for inds in ([0,6],[1,7],[2,8]):
                q=np.zeros(12); q[inds]=1
                observed=float(q@M@q); expected=p['rho']*Al*L
                check(cid+':rigid_mass_'+str(inds[0]),abs(observed-expected)<=4096*EPS*abs(expected),observed=observed,expected=expected)
    b=native[short['S02']]; d=native[short['S26']]
    ratio=cases[short['S26']][1]['rho']/cases[short['S02']][1]['rho']
    for name in ('M','G','Kst'):
        expected=b[name]*ratio
        check('density_scaling_'+name,np.all(np.abs(d[name]-expected)<=4096*EPS*np.abs(expected)))
    check('density_K_unchanged',np.array_equal(d['K'],b['K']))
    for prefix in ('S03','S04','S05','S06','S07','S08','S09'):
        z=native[short[prefix]]
        check(prefix+':flag_Kst_independent',np.array_equal(z['Kst'],b['Kst']) and np.count_nonzero(z['Kst'])>0)
        check(prefix+':flag_torsional_mass',np.array_equal(z['M'][np.ix_(TORSION,TORSION)],b['M'][np.ix_(TORSION,TORSION)]))
    check('rotary_mass_changes',not np.array_equal(b['M'],native[short['S05']]['M']))
    check('rotary_does_not_control_G',np.array_equal(b['G'],native[short['S05']]['G']))
    check('shear_changes_K',not np.array_equal(b['K'],native[short['S04']]['K']))
    for plus,minus in [('S20','S21'),('S22','S23')]:
        kp=native[short[plus]]['K']; km=native[short[minus]]['K']; k0=b['K']
        residual=np.abs((kp-k0)+(km-k0))
        bound=16*EPS*(np.abs(kp)+np.abs(km)+2*np.abs(k0))
        check(plus+':signed_linearity',np.all(residual<=bound),max_residual=float(residual.max()))
    legacy=[]
    stypes={(False,False,True):1,(True,True,True):2,(True,True,False):3,(True,False,True):4,
            (False,True,True):5,(True,False,False):6,(False,True,False):7,(False,False,False):8}
    eligible=sorted({r['case_id'] for r in authority['arrays'] if r['category']!='element'})
    assert len(eligible)==21
    for cid in eligible:
        p=cases[cid][1]
        assert p['idl']==p['idr'] and p['odl']==p['odr'] and p['shear_method']=='cowper'
        st=stypes[(p['shear_effects'],p['rotary_inertia'],p['gyroscopic'])]
        lm,lg,lk,_=circular(st,p['L'],p['odl'],p['idl'],p['E'],p['G_s'],p['rho'],p['axial_force'],p['torque'],library_path)
        for name,reference in [('M',lm),('K',lk),('G',lg)]:
            result=comparison(native[cid][name][np.ix_(P,P)],reference,'shaft',name,policy,True)
            result.update(case=cid,matrix=name,legacy_stype=st)
            legacy.append(result)
    assert len(legacy)==63
    unchanged=snapshot(FROZEN)==frozen_before
    check('authority_unchanged',unchanged)
    def table(rows): return {'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL','count':len(rows),'results':rows}
    reports={'PRIMARY_PARITY.json':table(primary),'LATERAL_PARITY.json':table(lateral),
             'LOAD_ADDITIONS.json':table(additions),'INVARIANTS.json':table(checks),'LEGACY_CROSSCHECK.json':table(legacy)}
    for name,data in reports.items(): write(out/name,data)
    summary={'status':'PASS' if all(r['status']=='PASS' for r in reports.values()) else 'FAIL',
             'scope':'Native isolated element Linux/Windows execution only; not promotion',
             'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             'authority_integrity':integrity,'primary_matrices':113,'lateral_selections':63,
             'legacy_comparisons':63,'invariant_checks':len(checks),'maxima_by_matrix_type':maxima,
             'report_status':{k:v['status'] for k,v in reports.items()},
             'authority_unchanged':unchanged}
    write(out/'NATIVE_SUMMARY.json',summary)
    print('B1_NATIVE_NUMERICAL_REPORT',json.dumps(summary,sort_keys=True))
    return reports,summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--library')
    args=parser.parse_args()
    _,summary=qualify(args.out,args.library)
    raise SystemExit(0 if summary['status']=='PASS' else 1)
