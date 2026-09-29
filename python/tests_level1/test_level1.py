from pathlib import Path
import json
import numpy as np
import pytest

from drm_core import (
    Bearing,CoefficientBearing,Disk,Node,RotorModel,ShaftElement,run_level1
)
from drm_core.solver.backend import FortranBackend

ROOT=Path(__file__).resolve().parents[2]
GOLD=ROOT/"validation"/"ross_parity"/"level1"


def golden(name):
    return json.loads((GOLD/f"{name}.json").read_text())


def rotor(bearings,advanced=()):
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[
        ShaftElement(2,i+1,i+2,.05,0.,7810.,211e9,81.2e9)
        for i in range(6)
    ]
    disks=[
        Disk.geometric(3,7810.,.07,.28,.05),
        Disk.geometric(5,7810.,.06,.24,.05),
    ]
    return RotorModel(nodes,shafts,disks,list(bearings),advanced_bearings=list(advanced))


def legacy_pair(kxx=1e6,kyy=.8e6,cxx=180.,cyy=140.):
    props=(kxx,0.,0.,kyy,cxx,0.,0.,cyy)
    return [Bearing(5,1,props),Bearing(5,7,props)]


def model_for(name):
    if name=="zero_speed_fixture":
        return rotor(legacy_pair(1e6,.8e6,0.,0.))
    if name in ("rated_speed_midspan","application_at_support"):
        return rotor(legacy_pair())
    if name=="anisotropic_damped":
        return rotor([
            Bearing(5,1,(1.3e6,0.,0.,.7e6,420.,0.,0.,250.)),
            Bearing(5,7,(1.1e6,0.,0.,.9e6,360.,0.,0.,290.)),
        ])
    if name=="speed_dependent":
        speed=(0.,200.,400.,600.,800.)
        kx=(.90e6,1.02e6,1.16e6,1.33e6,1.53e6)
        ky=(.72e6,.82e6,.94e6,1.09e6,1.26e6)
        cx=(220.,205.,190.,176.,165.)
        cy=(180.,169.,158.,148.,139.)
        a=[
            CoefficientBearing(1,kx,cx,ky,cy,speed_rad_s=speed),
            CoefficientBearing(7,tuple(1.08*x for x in kx),tuple(.95*x for x in cx),
                               tuple(1.05*x for x in ky),tuple(1.03*x for x in cy),
                               speed_rad_s=speed),
        ]
        return rotor([],a)
    if name=="map_2d":
        sp=(100.,250.,400.,550.,700.);fr=sp
        gx=(
            (.72e6,.76e6,.80e6,.84e6,.88e6),
            (.86e6,.91e6,.96e6,1.01e6,1.07e6),
            (1.02e6,1.08e6,1.15e6,1.22e6,1.30e6),
            (1.20e6,1.27e6,1.35e6,1.44e6,1.54e6),
            (1.40e6,1.48e6,1.57e6,1.67e6,1.78e6),
        )
        gy=tuple(tuple(.79*x+7.5e4 for x in row) for row in gx)
        gcx=(
            (240.,230.,220.,210.,200.),
            (230.,220.,210.,200.,190.),
            (220.,210.,200.,190.,180.),
            (210.,200.,190.,180.,170.),
            (200.,190.,180.,170.,160.),
        )
        gcy=tuple(tuple(.82*x+15. for x in row) for row in gcx)
        scale=lambda a,f:tuple(tuple(f*x for x in row) for row in a)
        a=[
            CoefficientBearing(1,gx,gcx,gy,gcy,speed_rad_s=sp,frequency_rad_s=fr),
            CoefficientBearing(7,scale(gx,1.05),scale(gcx,.97),scale(gy,1.03),scale(gcy,1.02),
                               speed_rad_s=sp,frequency_rad_s=fr),
        ]
        return rotor([],a)
    raise KeyError(name)


CASES=[
    "zero_speed_fixture","rated_speed_midspan","application_at_support",
    "anisotropic_damped","speed_dependent","map_2d",
]


@pytest.mark.parametrize("name",CASES)
def test_level1_frozen_ross_4dof_parity(name):
    g=golden(name);inp=g["input"]
    r=run_level1(
        model_for(name),
        rotor_speed_rad_s=inp["rated_w_rad_s"],
        cross_coupling_node=inp["rotorstudio_node_one_based"],
        stiffness_range_n_m=inp["stiffness_range_n_m"],
        num=inp["num"],
    )
    ref=g["ross_adapted_4dof"]
    np.testing.assert_allclose(r.cross_coupled_stiffness_n_m,g["ross_level1"]["stiffness_range"],rtol=0,atol=1e-8)
    np.testing.assert_allclose(r.log_dec,ref["log_dec"],rtol=3e-8,atol=3e-10)
    np.testing.assert_array_equal(r.selected_mode_index,np.asarray(ref["selected_index"])-1)
    for j,p in enumerate(ref["points"]):
        np.testing.assert_allclose(r.eigenvalue_real[:,j],p["evalues_real"][:r.eigenvalue_real.shape[0]],rtol=3e-8,atol=3e-7)
        np.testing.assert_allclose(r.eigenvalue_imag[:,j],p["evalues_imag"][:r.eigenvalue_imag.shape[0]],rtol=3e-8,atol=3e-7)
        np.testing.assert_allclose(r.modal_log_dec[:,j],p["log_dec"][:r.modal_log_dec.shape[0]],rtol=3e-8,atol=3e-9)
        labels=np.asarray(p["directions"][:r.mode_direction_code.shape[0]])
        code=np.where(labels=="Forward",1,np.where(labels=="Mixed",2,3))
        np.testing.assert_array_equal(r.mode_direction_code[:,j],code)


@pytest.mark.parametrize("name",["rated_speed_midspan","anisotropic_damped","map_2d"])
def test_level1_matrix_first_sentinels(name):
    g=golden(name);inp=g["input"];backend=FortranBackend();m=model_for(name)
    for sent in g["ross_adapted_4dof"]["matrix_sentinels"]:
        got=backend.level1_matrices(
            m,inp["rated_w_rad_s"],inp["rotorstudio_node_one_based"],sent["Q"]
        )
        for key in ("M","C","G","K"):
            np.testing.assert_allclose(got[key],sent[key],rtol=2e-11,atol=2e-7)


def test_linear_q_semantics_and_no_branch_tracking():
    g=golden("zero_speed_fixture");inp=g["input"]
    r=run_level1(model_for("zero_speed_fixture"),inp["rated_w_rad_s"],
                 inp["rotorstudio_node_one_based"],inp["stiffness_range_n_m"],inp["num"])
    np.testing.assert_array_equal(
        r.cross_coupled_stiffness_n_m,
        np.linspace(*inp["stiffness_range_n_m"],inp["num"])
    )
    assert list(r.selected_mode_index)==[0,0,2,0,0]


def test_default_range_and_unsupported_scope_fail_closed():
    m=model_for("rated_speed_midspan")
    with pytest.raises(ValueError,match="required"):
        run_level1(m,377.,4,None,5)
    with pytest.raises(ValueError,match="cross_coupling_node"):
        run_level1(m,377.,99,(0.,1e6),5)
    bad=RotorModel(m.nodes,m.shafts,m.disks,[Bearing(1,1,())])
    with pytest.raises(ValueError,match="type 3/5"):
        run_level1(bad,377.,4,(0.,1e6),5)
