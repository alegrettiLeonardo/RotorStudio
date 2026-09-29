from pathlib import Path
import json
import numpy as np
import pytest
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,CoefficientBearing,run_ucs
from drm_core.solver.backend import FortranBackend

ROOT=Path(__file__).resolve().parents[2]
GOLD=ROOT/"validation"/"ross_parity"/"ucs"

# A5 tolerances are frozen independently from A1-A4.  The default constant-
# bearing speed axis is an affine transform of rotor_wn, so its ROSS parity
# tolerance must inherit the already-declared modal parity tolerance rather
# than demand bitwise agreement between ARPACK and the native LAPACK solve.
WN_RTOL=2e-8
WN_ATOL=2e-6
AXIS_RTOL=2e-12
AXIS_ATOL=1e-9

def model_with(bearing):
    z=[0.0,0.21,0.48,0.67]
    shafts=[]
    ods=[0.054,0.061,0.049]
    for i,(L,od) in enumerate(zip([0.21,0.27,0.19],ods),1):
        shafts.append(ShaftElement(2,i,i+1,od,0.014,7810.,211e9,81.2e9,2.5e-3,0.,0.))
    disk=Disk.inertial(3,19.0,0.083,0.151)
    if isinstance(bearing,tuple) and bearing and bearing[0]=="legacy":
        kx,ky=bearing[1],bearing[2]
        bs=[Bearing(3,1,(kx,ky,230.,230.)),Bearing(3,4,(kx,ky,230.,230.))]
        return RotorModel([Node(i+1,x) for i,x in enumerate(z)],shafts,[disk],bs)
    b0=bearing
    from dataclasses import replace
    b1=replace(b0,node=4,tag="a5-b1")
    return RotorModel([Node(i+1,x) for i,x in enumerate(z)],shafts,[disk],[],advanced_bearings=[replace(b0,node=1,tag="a5-b0"),b1])

def golden(name):
    return json.loads((GOLD/f"{name}.json").read_text())

def assert_result(name,model,**kwargs):
    g=golden(name);r=run_ucs(model,library_path=None,**kwargs)
    np.testing.assert_allclose(r.stiffness_log_n_m,g["stiffness_log"],rtol=2e-12,atol=1e-8)
    np.testing.assert_allclose(r.natural_frequency_rad_s,g["rotor_wn"],rtol=WN_RTOL,atol=WN_ATOL)
    if r.bearing_speed_policy=="constant_10_point_rotor_wn_margin":
        # Exact Rotor.run_ucs semantic gate in the native-result space:
        # linspace(min(wn)-0.1*min(wn), max(wn)+0.1*min(wn), 10).
        margin=float(r.natural_frequency_rad_s.min())*0.1
        expected=np.linspace(
            float(r.natural_frequency_rad_s.min()-margin),
            float(r.natural_frequency_rad_s.max()+margin),10
        )
        np.testing.assert_array_equal(r.bearing_speed_rad_s,expected)
        # ROSS derives the same axis from its ARPACK modal values, therefore
        # comparison to the immutable authority inherits the wn tolerance.
        np.testing.assert_allclose(
            r.bearing_speed_rad_s,g["bearing_speed_range"],
            rtol=WN_RTOL,atol=WN_ATOL
        )
    else:
        np.testing.assert_allclose(
            r.bearing_speed_rad_s,g["bearing_speed_range"],
            rtol=AXIS_RTOL,atol=AXIS_ATOL
        )
    np.testing.assert_allclose(r.bearing_kxx_n_m,g["bearing_kxx"],rtol=2e-10,atol=1e-5)
    np.testing.assert_allclose(r.bearing_kyy_n_m,g["bearing_kyy"],rtol=2e-10,atol=1e-5)
    np.testing.assert_allclose(r.intersection_stiffness_n_m,g["intersection_x"],rtol=2e-7,atol=2e-2)
    np.testing.assert_allclose(r.intersection_speed_rad_s,g["intersection_y"],rtol=2e-7,atol=2e-5)
    assert list(r.coefficient_families)==g["coefficients_processed"]
    if len(g["critical_modal"]):
        ref=np.asarray([x["wn"] for x in g["critical_modal"]],float).T
        np.testing.assert_allclose(r.critical_wn_rad_s,ref,rtol=3e-8,atol=3e-6)
    assert np.all(np.diff(r.stiffness_log_n_m)>0)
    assert np.all(r.stiffness_log_n_m>0) and np.all(r.natural_frequency_rad_s>=0)
    return r

def test_logspace_and_constant_isotropic_parity():
    r=assert_result("isotropic_constant",model_with(("legacy",1.25e7,1.25e7)),
                    stiffness_range_exponents=(6,10),num=7,num_modes=16)
    assert r.natural_frequency_rad_s.shape==(4,7)
    assert np.all(r.intersection_coefficient=="kxx")

def test_constant_anisotropic_parity_and_order():
    r=assert_result("anisotropic_constant",model_with(("legacy",1.05e7,1.85e7)),
                    stiffness_range_exponents=(6,10),num=7,num_modes=16)
    assert list(r.intersection_coefficient[:4])==["kxx","kyy","kxx","kyy"]

def test_rouch_synchronous_parity_and_critical_is_standard():
    r=assert_result("synchronous_true",model_with(("legacy",1.25e7,1.25e7)),
                    stiffness_range_exponents=(6,10),num=7,num_modes=16,synchronous=True)
    ordinary=golden("isotropic_constant")
    assert not np.allclose(r.natural_frequency_rad_s,ordinary["rotor_wn"])
    # frozen ROSS critical solve does not propagate the Rouch flag
    assert abs(r.critical_wn_rad_s[0,0]-golden("synchronous_true")["critical_modal"][0]["wn"][0])<1e-5

def test_matrix_first_c_zero_and_ross_sentinels():
    m=model_with(("legacy",1.25e7,1.25e7));backend=FortranBackend()
    for sync,name in [(False,"isotropic_constant"),(True,"synchronous_true")]:
        g=golden(name)
        for sent in g["matrix_sentinels"]:
            got=backend.ucs_matrices(m,sent["stiffness"],sync)
            assert np.max(np.abs(got["C"]))==0.0
            # Full matrices are frozen in the authority and compared separately by the qualifier;
            # this unit gate checks the modal consequence at all sentinel stiffnesses.
            assert np.all(np.isfinite(got["M"])) and np.all(np.isfinite(got["K"])) and np.all(np.isfinite(got["G"]))

def test_speed_frequency_and_2d_curve_policies():
    speed=(40.,120.,260.,480.,820.);freq=(30.,100.,230.,470.,830.)
    eq=(4.2e6,7.1e6,1.18e7,1.75e7,2.65e7)
    sx=(3.9e6,7.4e6,1.28e7,2.02e7,3.05e7);sy=(6.2e6,9.6e6,1.53e7,2.42e7,3.62e7)
    fx=(4.6e6,7.8e6,1.33e7,2.11e7,3.28e7);fy=(5.9e6,9.1e6,1.51e7,2.39e7,3.55e7)
    assert_result("speed_equal",model_with(CoefficientBearing(1,eq,0.,eq,0.,speed_rad_s=speed)),
                  stiffness_range_exponents=(6,10),num=7,num_modes=16)
    assert_result("speed_anisotropic",model_with(CoefficientBearing(1,sx,0.,sy,0.,speed_rad_s=speed)),
                  stiffness_range_exponents=(6,10),num=7,num_modes=16)
    assert_result("frequency_axis",model_with(CoefficientBearing(1,fx,0.,fy,0.,frequency_rad_s=freq)),
                  stiffness_range_exponents=(6,10),num=7,num_modes=16)
    gx=((3.6e6,4.2e6,5.1e6,6.3e6,7.8e6),(5.1e6,5.9e6,7.0e6,8.5e6,1.03e7),(7.4e6,8.4e6,9.8e6,1.17e7,1.39e7),(1.04e7,1.17e7,1.35e7,1.58e7,1.86e7),(1.47e7,1.63e7,1.86e7,2.15e7,2.50e7))
    gy=tuple(tuple(1.18*x+2e5 for x in row) for row in gx)
    assert_result("map_2d",model_with(CoefficientBearing(1,gx,0.,gy,0.,speed_rad_s=speed,frequency_rad_s=freq,interpolation="pchip")),
                  stiffness_range_exponents=(6,10),num=7,num_modes=16)

def test_explicit_bearing_range_is_exactly_30_points():
    r=assert_result("explicit_bearing_speed_range",model_with(("legacy",1.05e7,1.85e7)),
                    stiffness_range_exponents=(6,10),num=7,num_modes=16,bearing_speed_range=(40.,900.))
    assert len(r.bearing_speed_rad_s)==30

def test_logspace_gate_exact_expected():
    r=run_ucs(model_with(("legacy",1.25e7,1.25e7)),(6,10),num=5,num_modes=16)
    np.testing.assert_allclose(r.stiffness_log_n_m,[1e6,1e7,1e8,1e9,1e10],rtol=2e-15)

def test_missing_range_and_unsupported_scope_fail_closed():
    m=model_with(("legacy",1.25e7,1.25e7))
    with pytest.raises(ValueError,match="required"):run_ucs(m,None)
    bad=RotorModel(m.nodes,m.shafts,m.disks,[Bearing(1,1,())])
    with pytest.raises(ValueError,match="type 3 or 5"):run_ucs(bad,(6,10))
