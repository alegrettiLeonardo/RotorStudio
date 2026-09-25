import numpy as np

from drm_core import (
    BallBearing,
    Bearing,
    CoefficientBearing,
    Force,
    Node,
    RotorModel,
    ShaftElement,
    TiltingPadBearing,
)
from drm_core.solver.backend import FortranBackend
from drm_core.solver.bearings_backend import AdvancedBearingBackend
from drm_core.stage1 import RotorProject, load_project, save_project


def _shaft():
    return ShaftElement(
        2, 1, 2, 0.05, 0.0, 7810.0, 211e9, 81.2e9, 0.0, 0.0, 0.0
    )


def _type5(node, kxx, kxy, kyx, kyy, cxx, cxy, cyx, cyy):
    return Bearing(5, node, (kxx, kxy, kyx, kyy, cxx, cxy, cyx, cyy))


def test_native_ball_oracle():
    backend = AdvancedBearingBackend()
    result = backend.evaluate(
        BallBearing(
            node=1,
            n_balls=8,
            d_balls_m=0.03,
            static_load_n=500.0,
            alpha_rad=np.pi / 6,
        ),
        speed_rad_s=100.0,
    )
    np.testing.assert_allclose(result.K[0, 0], 4.64168838e7, rtol=1e-7)
    np.testing.assert_allclose(result.K[1, 1], 1.00906269e8, rtol=1e-7)
    np.testing.assert_allclose(result.C[0, 0], 580.2110481, rtol=1e-7)
    np.testing.assert_allclose(result.C[1, 1], 1261.32836543, rtol=1e-7)


def test_tilting_pad_table_preserves_spin_and_whirl_axes():
    # Linear surface kxx = 10*Omega + omega.  A synchronous-only
    # implementation would return 1650 at (Omega,omega)=(150,20), so this
    # catches accidental collapse of the two ROSS axes.
    bearing = TiltingPadBearing(
        node=1,
        speed_rad_s=(100.0, 200.0),
        frequency_rad_s=(10.0, 30.0),
        kxx=((1010.0, 1030.0), (2010.0, 2030.0)),
        kyy=2.0e6,
        cxx=100.0,
        cyy=200.0,
        interpolation="linear",
        provenance={"ross_sha": "6320eab9f890f1b3cc1710d508b446fe063ca68d"},
    )
    result = AdvancedBearingBackend().evaluate(
        bearing, speed_rad_s=150.0, frequency_rad_s=20.0
    )
    np.testing.assert_allclose(result.K[0, 0], 1520.0, rtol=0, atol=1e-12)
    np.testing.assert_allclose(result.K[1, 1], 2.0e6)
    assert result.details["coefficient_source"] == "precomputed_table"


def test_constant_advanced_bearing_collapses_exactly_to_legacy_modal_path():
    props = (1.2e6, 2.0e4, -3.0e4, 1.4e6, 150.0, 7.0, -5.0, 180.0)
    legacy = RotorModel(
        nodes=[Node(1, 0.0), Node(2, 1.0)],
        shafts=[_shaft()],
        bearings=[_type5(1, *props), _type5(2, *props)],
    )
    advanced = RotorModel(
        nodes=[Node(1, 0.0), Node(2, 1.0)],
        shafts=[_shaft()],
        advanced_bearings=[
            CoefficientBearing(
                node=1,
                kxx=props[0],
                kxy=props[1],
                kyx=props[2],
                kyy=props[3],
                cxx=props[4],
                cxy=props[5],
                cyx=props[6],
                cyy=props[7],
            ),
            CoefficientBearing(
                node=2,
                kxx=props[0],
                kxy=props[1],
                kyx=props[2],
                kyy=props[3],
                cxx=props[4],
                cxy=props[5],
                cyx=props[6],
                cyy=props[7],
            ),
        ],
    )
    backend = FortranBackend()
    a = np.sort_complex(backend.modal_eigenvalues(legacy, 200.0))
    b = np.sort_complex(backend.modal_eigenvalues(advanced, 200.0))
    np.testing.assert_allclose(b, a, rtol=1e-12, atol=1e-8)


def test_speed_dependent_advanced_bearing_is_re_evaluated_per_frf_point():
    speed = np.array([100.0, 200.0])
    variable = CoefficientBearing(
        node=1,
        speed_rad_s=(100.0, 200.0),
        kxx=(1.0e6, 2.0e6),
        kyy=(1.1e6, 2.1e6),
        cxx=(100.0, 200.0),
        cyy=(110.0, 210.0),
        interpolation="linear",
    )
    advanced = RotorModel(
        nodes=[Node(1, 0.0), Node(2, 1.0)],
        shafts=[_shaft()],
        bearings=[_type5(2, 1.5e6, 0, 0, 1.5e6, 150.0, 0, 0, 150.0)],
        advanced_bearings=[variable],
        forces=[Force(1, (2, 1e-3, 0.0))],
    )
    backend = FortranBackend()
    response = backend.frequency_response(advanced, speed)

    manual = np.empty_like(response)
    for j, w in enumerate(speed):
        kxx = 1.0e6 if j == 0 else 2.0e6
        kyy = 1.1e6 if j == 0 else 2.1e6
        cxx = 100.0 if j == 0 else 200.0
        cyy = 110.0 if j == 0 else 210.0
        legacy = RotorModel(
            nodes=[Node(1, 0.0), Node(2, 1.0)],
            shafts=[_shaft()],
            bearings=[
                _type5(1, kxx, 0, 0, kyy, cxx, 0, 0, cyy),
                _type5(2, 1.5e6, 0, 0, 1.5e6, 150.0, 0, 0, 150.0),
            ],
            forces=[Force(1, (2, 1e-3, 0.0))],
        )
        manual[:, j] = backend.frequency_response(legacy, [w])[:, 0]

    np.testing.assert_allclose(response, manual, rtol=1e-12, atol=1e-12)


def test_advanced_bearing_project_roundtrip(tmp_path):
    bearing = TiltingPadBearing(
        node=1,
        speed_rad_s=(100.0, 200.0),
        frequency_rad_s=(50.0, 150.0),
        kxx=((1.0e6, 1.1e6), (1.5e6, 1.6e6)),
        kyy=((0.8e6, 0.9e6), (1.2e6, 1.3e6)),
        cxx=100.0,
        cyy=120.0,
        provenance={"ross_sha": "6320eab9f890f1b3cc1710d508b446fe063ca68d"},
    )
    project = RotorProject(
        "advanced-bearing-roundtrip",
        RotorModel(
            nodes=[Node(1, 0.0), Node(2, 1.0)],
            shafts=[_shaft()],
            advanced_bearings=[bearing],
        ),
    )
    path = save_project(project, tmp_path / "case.rds")
    reopened = load_project(path)
    restored = reopened.model.advanced_bearings[0]
    assert isinstance(restored, TiltingPadBearing)
    assert restored.speed_rad_s == (100.0, 200.0)
    assert restored.frequency_rad_s == (50.0, 150.0)
    assert restored.provenance["ross_sha"].startswith("6320eab9")
