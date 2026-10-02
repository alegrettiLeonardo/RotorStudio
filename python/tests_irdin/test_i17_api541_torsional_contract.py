from __future__ import annotations

import pytest

from drm_core.analysis.api541_torsional_contract import (
    API541TorsionalInputError,
    API541TorsionalModel,
    TorsionalConnection,
    TorsionalExcitation,
    TorsionalStation,
    torsional_model_from_irdin,
    validate_api541_torsional_model,
)


def _prov(source):
    return {"source": source, "status": "EXPLICIT_ENGINEERING_INPUT"}


def _model():
    return API541TorsionalModel(
        stations=(
            TorsionalStation("motor rotor", 12.0, _prov("motor drawing")),
            TorsionalStation("motor half coupling", 1.2, _prov("coupling drawing")),
            TorsionalStation("driven equipment", 22.0, _prov("vendor train model")),
        ),
        connections=(
            TorsionalConnection(0, 1, 4.0e6, 120.0, "motor shaft", _prov("shaft calculation")),
            TorsionalConnection(1, 2, 1.5e6, 80.0, "coupling", _prov("coupling vendor")),
        ),
        excitations=(
            TorsionalExcitation(
                station=0,
                torque_nm=2500.0,
                phase_rad=0.0,
                order=2.0,
                name="electromagnetic 2x",
                provenance=_prov("motor electromagnetic study"),
            ),
            TorsionalExcitation(
                station=2,
                torque_nm=-1800.0,
                phase_rad=0.2,
                frequency_hz=120.0,
                name="driven pulsating torque",
                provenance=_prov("driven equipment vendor"),
            ),
        ),
        operating_speed_rpm=1800.0,
        motor_station=0,
        driven_equipment_station=2,
        coupling_connection=1,
        driven_equipment="compressor",
        authority="project/vendor torsional data package",
    )


def test_i17_explicit_torsional_contract_is_ready_but_solver_is_not_claimed():
    model=_model()
    result=validate_api541_torsional_model(model)
    assert result["status"]=="API541_TORSIONAL_INPUT_READY"
    assert result["station_count"]==3
    assert result["connection_count"]==2
    assert result["excitation_count"]==2
    assert result["solver_qualified"] is False
    assert result["whole_api541_compliance_claim"] is False


def test_i17_contract_is_deterministic_and_serial():
    model=_model()
    payload=model.canonical_dict()
    assert payload["stations"][0]["polar_inertia_kgm2"]==12.0
    assert payload["connections"][1]["left_station"]==1
    assert payload["connections"][1]["right_station"]==2
    assert payload["excitations"][0]["order"]==2.0

    broken=API541TorsionalModel(
        stations=model.stations,
        connections=(
            TorsionalConnection(0,2,4.0e6,0.0,"skip",_prov("bad")),
            TorsionalConnection(0,1,1.0e6,0.0,"one",_prov("bad")),
        ),
        excitations=model.excitations,
        operating_speed_rpm=model.operating_speed_rpm,
        motor_station=0,
        driven_equipment_station=2,
        coupling_connection=1,
        driven_equipment=model.driven_equipment,
        authority=model.authority,
    )
    with pytest.raises(API541TorsionalInputError,match="serial adjacent"):
        validate_api541_torsional_model(broken)


@pytest.mark.parametrize(
    "station",
    [
        TorsionalStation("bad",0.0,_prov("x")),
        TorsionalStation("bad",-1.0,_prov("x")),
        TorsionalStation("bad",float("nan"),_prov("x")),
        TorsionalStation("bad",1.0,{}),
    ],
)
def test_i17_invalid_station_fails_closed(station):
    model=_model()
    bad=API541TorsionalModel(
        stations=(station,*model.stations[1:]),
        connections=model.connections,
        excitations=model.excitations,
        operating_speed_rpm=model.operating_speed_rpm,
        motor_station=0,
        driven_equipment_station=2,
        coupling_connection=1,
        driven_equipment=model.driven_equipment,
        authority=model.authority,
    )
    with pytest.raises(API541TorsionalInputError):
        validate_api541_torsional_model(bad)


def test_i17_excitation_requires_exactly_one_frequency_reference():
    model=_model()
    bad_exc=TorsionalExcitation(
        station=0,
        torque_nm=1.0,
        order=1.0,
        frequency_hz=60.0,
        provenance=_prov("bad"),
    )
    bad=API541TorsionalModel(
        stations=model.stations,
        connections=model.connections,
        excitations=(bad_exc,),
        operating_speed_rpm=model.operating_speed_rpm,
        motor_station=0,
        driven_equipment_station=2,
        coupling_connection=1,
        driven_equipment=model.driven_equipment,
        authority=model.authority,
    )
    with pytest.raises(API541TorsionalInputError,match="exactly one"):
        validate_api541_torsional_model(bad)


def test_i17_never_infers_torsional_train_from_lateral_irdin_source():
    with pytest.raises(API541TorsionalInputError,match="does not infer"):
        torsional_model_from_irdin(object())
