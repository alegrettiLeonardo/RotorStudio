from __future__ import annotations

import json

from validation.irdin.i0_authority import AUTHORITY_DIR, CASE_PATH, normalized_raw_document, parse_source


CONTRACT = CASE_PATH.parents[1] / "semantic_contract.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _raw():
    return normalized_raw_document(parse_source(CASE_PATH.read_bytes()))


def test_i1_semantic_contract_has_frozen_external_provenance():
    contract = _contract()
    assert contract["status"] == "PASS_FOR_ST41_DECLARED_SCOPE"
    source = contract["source_project"]
    assert source["repository"] == "alegrettiLeonardo/frontend_rotordin"
    assert source["commit"] == "647d600bc1d32a05de62ee457942e00285b572e3"
    paths = {item["path"]: item["blob"] for item in source["files"]}
    assert paths["solver/src/source/entrada.f90"] == "fed9da6948bdc106cac51e43bd15ebbcff9b3c2b"
    assert paths["solver/src/source/predad.f90"] == "3aecb69e054179617fb56ff470c4a63c967fa081"
    assert paths["solver/src/source/resp_f.f90"] == "b7b72dcdb135787cce0122f74d143d524af22c0e"
    assert paths["src/rotordin_frontend/physical_parity.py"] == "f822e3d91ada3cde58458b38cc2fae1831be89c8"


def test_i1_st41_mass_contract_and_values_are_source_exact():
    raw = _raw()["massas"]
    rows = {}
    for key, value in raw.items():
        row, col = map(int, key.split(","))
        rows.setdefault(row, {})[col] = value
    assert sorted(rows) == [1, 2, 3]
    assert sum(float(row[2]) for row in rows.values()) == 10680.0
    assert (float(rows[1][0]), float(rows[1][1]), float(rows[1][2]), float(rows[1][3])) == (
        1370.9, 1675.0, 10090.0, 1140.0
    )
    assert int(rows[1][4]) == 1
    assert all(int(row[5]) == 0 for row in rows.values())

    contract = _contract()["mappings"]["Massas"]
    assert contract["0"]["meaning"].startswith("axial start")
    assert contract["1"]["unit"] == "mm"
    assert contract["2"]["unit"] == "kg"
    assert contract["5"]["confidence"] == "PARTIAL"


def test_i1_st41_support_contract_preserves_native_order_and_values():
    raw = _raw()["suporte"]
    rows = {}
    for key, value in raw.items():
        row, col = map(int, key.split(","))
        rows.setdefault(row, {})[col] = value
    assert sorted(rows) == [1, 2]
    for index, row in rows.items():
        assert int(row[0]) == index
        assert float(row[1]) == 2.73e9
        assert float(row[2]) == 3.41e9
        assert all(float(row[col]) == 0.0 for col in range(3, 9))
        assert float(row[9]) == 415.0

    mapping = _contract()["mappings"]["Suporte"]
    assert [mapping[str(i)]["name"] for i in range(10)] == [
        "bearing_number", "kxx", "kzz", "kxz", "kzx",
        "cxx", "czz", "cxz", "czx", "mass_kg",
    ]


def test_i1_st41_unbalance_is_gmm_and_phase_degrees():
    raw = _raw()["desbal"]
    rows = {}
    for key, value in raw.items():
        row, col = map(int, key.split(","))
        rows.setdefault(row, {})[col] = value
    assert [(float(rows[i][0]), float(rows[i][1]), float(rows[i][2])) for i in (1, 2)] == [
        (1370.9, 0.0, 110175.3),
        (3045.9, 0.0, 110175.3),
    ]
    mapping = _contract()["mappings"]["Desbal"]
    assert mapping["1"]["unit"] == "deg"
    assert mapping["2"]["unit"] == "g*mm"


def test_i1_st41_response_contract_is_two_axes_at_each_bearing_station():
    raw = _raw()["respo"]
    rows = {}
    for key, value in raw.items():
        row, col = map(int, key.split(","))
        rows.setdefault(row, {})[col] = value
    observed = [(float(rows[i][0]), int(rows[i][1]), float(rows[i].get(2, 0.0))) for i in (1, 2, 3, 4)]
    assert observed == [
        (550.0, 1, 0.0),
        (550.0, 2, 0.0),
        (3977.0, 1, 0.0),
        (3977.0, 2, 0.0),
    ]
    mapping = _contract()["mappings"]["Respo"]
    assert "horizontal/X" in mapping["1"]["meaning"]
    assert mapping["2"]["unit"] == "deg"
