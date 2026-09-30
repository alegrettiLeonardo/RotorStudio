from __future__ import annotations
import ast
import ctypes as ct
import dataclasses
import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from drm_core.solver import sixdof_elements as api

VALUES=[0.173,0.012,0.047,0.012,0.047,7813.,207e9,79.5e9,0.,0.]
NAMES=['L','idl','odl','idr','odr','rho','E','G_s','axial_force','torque']
GUARD=-982731.125


def raw(kind,values=None,flags=None,lds=None,caps=None):
    n,count=(12,4) if kind=='shaft' else (6,3)
    values=list(values if values is not None else VALUES if kind=='shaft' else [17.125,0.0825,0.134])
    lds=list(lds if lds is not None else [n]*count)
    caps=list(caps if caps is not None else [(n-1)*ld+n for ld in lds])
    buffers=[]; args=[]
    for ld,capacity in zip(lds,caps):
        # Negative tests never claim a huge allocation that was not obtained.
        assert capacity<=10000
        owned=max(n*n,max(0,capacity),n*max(n,min(ld,n+16)))+16
        a=np.full(owned+4,GUARD,dtype=np.float64)
        buffers.append(a)
        args.extend([ct.cast(int(a.ctypes.data)+2*a.itemsize,ct.POINTER(ct.c_double)),ld,capacity])
    lib,shaft,disk=api._functions(os.environ.get('DRMROTOR_LIB'))
    if kind=='shaft': status=int(shaft(*values,*(flags if flags is not None else [1,1,1,1]),*args))
    else: status=int(disk(*values,*args))
    evidence=os.environ.get('B1_NATIVE_EVIDENCE')
    if evidence:
        p=Path(evidence); p.mkdir(parents=True,exist_ok=True)
        with (p/'ABI_OBSERVATIONS.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'kind':kind,'inputs':[repr(v) for v in values],
                                     'flags':flags,'leading_dimensions':lds,'declared_capacities':caps,
                                     'return_status':status,'all_buffers_untouched':bool(all(np.all(a==GUARD) for a in buffers))})+'\n')
    return status,buffers,lds


def unchanged(status,buffers,expected):
    assert status==expected
    assert all(np.all(a==GUARD) for a in buffers)


@pytest.mark.parametrize('position',range(10))
@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-float('inf')])
def test_native_shaft_rejects_all_nonfinite_scalars(position,bad):
    values=VALUES.copy(); values[position]=bad
    status,buffers,_=raw('shaft',values)
    unchanged(status,buffers,10)


@pytest.mark.parametrize('position,bad',[(0,0.),(0,-1.),(1,-1.),(3,-1.),(2,0.012),(4,0.012),
                                        (5,0.),(5,-1.),(6,0.),(6,-1.),(7,0.),(7,-1.)])
def test_native_geometry_material_invalid(position,bad):
    values=VALUES.copy(); values[position]=bad
    status,buffers,_=raw('shaft',values)
    unchanged(status,buffers,10)


@pytest.mark.parametrize('position',range(3))
@pytest.mark.parametrize('bad',[-1,2,17])
def test_native_invalid_booleans(position,bad):
    flags=[1,1,1,1]; flags[position]=bad
    status,buffers,_=raw('shaft',flags=flags)
    unchanged(status,buffers,11)


@pytest.mark.parametrize('method',[-1,0,3,2147483647])
def test_native_invalid_method_even_with_shear_disabled(method):
    status,buffers,_=raw('shaft',flags=[0,1,1,method])
    unchanged(status,buffers,11)


@pytest.mark.parametrize('kind,n,count',[('shaft',12,4),('disk',6,3)])
@pytest.mark.parametrize('badld',[-1,0])
def test_zero_negative_ld_for_every_output(kind,n,count,badld):
    for i in range(count):
        lds=[n]*count; lds[i]=badld
        status,buffers,_=raw(kind,lds=lds,caps=[n*n]*count)
        unchanged(status,buffers,12)


@pytest.mark.parametrize('kind,n,count',[('shaft',12,4),('disk',6,3)])
def test_short_ld_and_capacity_for_every_output(kind,n,count):
    for i in range(count):
        lds=[n]*count; lds[i]=n-1
        status,buffers,_=raw(kind,lds=lds,caps=[n*n]*count)
        unchanged(status,buffers,12)
        for capacity in [-1,0,n*n-1]:
            caps=[n*n]*count; caps[i]=capacity
            status,buffers,_=raw(kind,caps=caps)
            unchanged(status,buffers,13)
        lds=[n]*count; lds[i]=n+3
        status,buffers,_=raw(kind,lds=lds,caps=[n*n]*count)
        unchanged(status,buffers,13)
        lds[i]=2147483647
        status,buffers,_=raw(kind,lds=lds,caps=[n*n]*count)
        unchanged(status,buffers,13)


@pytest.mark.parametrize('kind,n,count',[('shaft',12,4),('disk',6,3)])
def test_valid_padded_outputs_leave_all_guard_regions(kind,n,count):
    lds=[n+2+i for i in range(count)]
    status,buffers,_=raw(kind,lds=lds)
    assert status==0
    expected=api.shaft_matrices(**dict(zip(NAMES,VALUES))) if kind=='shaft' else api.disk_matrices(m=17.125,Id=0.0825,Ip=0.134)
    for field,array,ld in zip(dataclasses.fields(expected),buffers,lds):
        mask=np.zeros(array.size,dtype=bool); received=np.empty((n,n))
        for col in range(n):
            for row in range(n):
                index=2+row+ld*col
                mask[index]=True; received[row,col]=array[index]
        assert np.all(array[~mask]==GUARD)
        np.testing.assert_array_equal(received,getattr(expected,field.name))
    if kind=='disk':
        assert buffers[2][2+4+lds[2]*3]==0.134
        assert buffers[2][2+3+lds[2]*4]==0.0
    else:
        assert buffers[3][2+0+lds[3]*1]<0.0
        assert buffers[3][2+1+lds[3]*0]==0.0


@pytest.mark.parametrize('position',range(3))
@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-float('inf'),0.,-1.])
def test_native_disk_rejects_nonfinite_and_degenerate_inputs(position,bad):
    values=[17.125,0.0825,0.134]; values[position]=bad
    status,buffers,_=raw('disk',values)
    unchanged(status,buffers,10)


def test_finite_input_overflow_cannot_partially_write_outputs():
    values=VALUES.copy(); values[0]=1e-300
    status,buffers,_=raw('shaft',values)
    unchanged(status,buffers,14)


@pytest.mark.parametrize('value',[np.array([0.173]),np.array(0.173),True,'0.173',0.173+0j])
def test_binding_rejects_non_scalar_contract(value):
    params=dict(zip(NAMES,VALUES)); params['L']=value
    with pytest.raises(api.SixDofInputError) as error: api.shaft_matrices(**params)
    assert error.value.status==10


@pytest.mark.parametrize('value',[0.0,1.0,2,-1,'True',np.array([True])])
def test_binding_flags_are_not_silently_coerced(value):
    with pytest.raises(api.SixDofInputError) as error:
        api.shaft_matrices(**dict(zip(NAMES,VALUES)),gyroscopic=value)
    assert error.value.status==11


def test_binding_owns_f_order_arrays_and_keeps_no_shared_result_buffer():
    a=api.shaft_matrices(**dict(zip(NAMES,VALUES)))
    b=api.shaft_matrices(**dict(zip(NAMES,VALUES)))
    for f in dataclasses.fields(a):
        x,y=getattr(a,f.name),getattr(b,f.name)
        assert x.shape==(12,12) and x.dtype==np.float64 and x.flags.f_contiguous
        assert not np.shares_memory(x,y)
    saved=b.M.copy(); a.M[:]=123
    np.testing.assert_array_equal(b.M,saved)


def test_binding_maps_native_input_error():
    values=dict(zip(NAMES,VALUES)); values['G_s']=0
    with pytest.raises(api.SixDofInputError) as error: api.shaft_matrices(**values)
    assert error.value.status==10


def test_missing_native_symbols_do_not_fall_back(monkeypatch):
    monkeypatch.setattr(api,'load_library',lambda path=None:SimpleNamespace())
    with pytest.raises(api.SolverLibraryError,match='no fallback'):
        api.shaft_matrices(**dict(zip(NAMES,VALUES)))


def test_binding_contains_no_matrix_solver():
    text=inspect.getsource(api); tree=ast.parse(text)
    imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): imports.extend(a.name for a in node.names)
        if isinstance(node,ast.ImportFrom): imports.append(node.module or '')
        assert not isinstance(node,(ast.MatMult,ast.Pow)), 'Physical matrix algebra must not enter production binding'
    assert not any(name.startswith(('scipy','ross')) for name in imports)
    assert 'np.linalg' not in text and 'numpy.linalg' not in text
