"""Real-Fortran regression for A8 input-vector ownership and shape.

The backing arrays deliberately retain extra VALID values between selected
entries. Reading them as contiguous vectors gives the wrong physical input
without relying on inaccessible memory or on a numerical oracle in production.
"""
from copy import deepcopy

import numpy as np
import pytest

from drm_core import run_clearance
from test_clearance import args_for, standard_model


@pytest.mark.parametrize("field,dtype,filler",[
    ("probe_nodes",np.int32,4),
    ("probe_angles_rad",np.float64,0.123),
    ("clearance_nodes",np.int32,2),
    ("radial_clearance_m",np.float64,2e-3),
])
def test_real_clearance_accepts_strided_vectors_without_changing_physics(field,dtype,filler):
    _,kwargs=args_for("explicit_20_gmm")
    model=standard_model()
    before=deepcopy(model.canonical_dict())
    expected=run_clearance(model,**kwargs)
    values=np.asarray(kwargs[field],dtype=dtype)
    backing=np.empty(2*len(values),dtype=dtype)
    backing[::2]=values
    backing[1::2]=filler
    view=backing[::2]
    assert not view.flags.c_contiguous
    np.testing.assert_array_equal(view,values)
    before_buffer=backing.copy()
    changed=dict(kwargs)
    changed[field]=view
    actual=run_clearance(model,**changed)
    for key,want in vars(expected).items():
        if isinstance(want,np.ndarray):
            np.testing.assert_array_equal(getattr(actual,key),want,err_msg=field+":"+key)
    np.testing.assert_array_equal(backing,before_buffer)
    assert model.canonical_dict()==before


@pytest.mark.parametrize("field",["probe_angles_rad","radial_clearance_m"])
def test_clearance_rejects_rank_two_vectors_before_native_call(field):
    _,kwargs=args_for("explicit_20_gmm")
    values=np.asarray(kwargs[field],dtype=np.float64)
    kwargs[field]=np.column_stack((values,values))
    with pytest.raises(ValueError,match="one-dimensional"):
        run_clearance(standard_model(),**kwargs)
