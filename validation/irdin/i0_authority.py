from __future__ import annotations

"""I0 byte/source authority for historical iRdin/VB6 inputs.

Validation-only: this module inventories legacy records. It does not promote
sketch-only entities into numerical rotor physics.
"""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
CASE_NAME = "ST41_1000_B3_60HZ_1675_63536.txt"
CASE_PATH = ROOT / "validation" / "irdin" / "cases" / CASE_NAME
AUTHORITY_DIR = ROOT / "validation" / "irdin" / "authority"
EXPECTED_SOURCE_SHA256 = "b7f14fd34ccce55f2c00c3915725097c12eda9be4161b91ce7ee84c56530f0fc"
GRID_KEY = re.compile(r"^(\\d+)\\s*,\\s*(\\d+)$")

# Existing importer contract only. I1 must independently establish original
# iRdin semantics before any new numerical physics is introduced.
DADOS_MAPPED = {
    "ref", "linha", "carc", "comp", "polos", "freq", "nnom",
    "s_melast", "s_masesp", "s_poisson",
    "c_rpmi", "c_rpmf", "c_div", "c_nrrot", "c_interp",
    "d_rpmi", "d_rpmf", "d_div", "d_nrmodos", "p_div",
}
GRID_COLUMNS = {
    "secoes": {
        0: ("length_mm", "mm", "MODEL"),
        1: ("outside_diameter_mm", "mm", "MODEL"),
        2: ("package_diameter_mm", "mm", "SKETCH_ONLY"),
        3: ("a_mm", "mm", "SKETCH_ONLY"),
        4: ("b_mm", "mm", "SKETCH_ONLY"),
        5: ("c_mm", "mm", "SKETCH_ONLY"),
        6: ("rib_count", None, "SKETCH_ONLY"),
        7: ("inner_diameter_mm", "mm", "MODEL"),
        8: ("final_outside_diameter_mm", "mm", "MODEL"),
        9: ("final_inner_diameter_mm", "mm", "MODEL"),
    },
    "massas": {
        0: ("xi_mm", "mm", "SKETCH_ONLY"),
        1: ("length_mm", "mm", "SKETCH_ONLY"),
        2: ("mass_kg", "kg", "SKETCH_ONLY"),
        3: ("outer_diameter_mm", "mm", "SKETCH_ONLY"),
        4: ("package", None, "SKETCH_ONLY"),
        5: ("ump", None, "SKETCH_ONLY"),
        6: ("inner_diameter_mm", "mm", "SKETCH_ONLY"),
    },
    "mancais": {
        0: ("position_mm", "mm", "MODEL"),
        1: ("constant_kxx", "N/m", "SKETCH_ONLY"),
        2: ("constant_kyy", "N/m", "SKETCH_ONLY"),
        3: ("constant_kxy", "N/m", "SKETCH_ONLY"),
        4: ("constant_kyx", "N/m", "SKETCH_ONLY"),
        5: ("constant_cxx", "N*s/m", "SKETCH_ONLY"),
        6: ("constant_cyy", "N*s/m", "SKETCH_ONLY"),
        7: ("constant_cxy", "N*s/m", "SKETCH_ONLY"),
        8: ("constant_cyx", "N*s/m", "SKETCH_ONLY"),
        10: ("name", None, "MODEL"),
        11: ("coefficient_source", "rpm,N/m,N*s/m", "MODEL"),
    },
    "desbal": {
        0: ("position_mm", "mm", "SKETCH_ONLY"),
        1: ("phase_current_label", "deg", "SKETCH_ONLY"),
        2: ("value_semantics_pending", None, "SKETCH_ONLY"),
    },
    "respo": {
        0: ("position_mm", "mm", "SKETCH_ONLY"),
        1: ("coordinate", None, "SKETCH_ONLY"),
        2: ("orientation_current_label", "deg", "SKETCH_ONLY"),
    },
    "concent": {
        0: ("position_mm", "mm", "SKETCH_ONLY"),
        1: ("mass_kg", "kg", "SKETCH_ONLY"),
        2: ("ix_kg_m2", "kg*m^2", "SKETCH_ONLY"),
        3: ("iy_kg_m2", "kg*m^2", "SKETCH_ONLY"),
        4: ("iz_kg_m2", "kg*m^2", "SKETCH_ONLY"),
    },
    "suporte": {
        0: ("bearing_number", None, "SKETCH_ONLY"),
        1: ("kxx", "N/m", "SKETCH_ONLY"),
        2: ("kyy", "N/m", "SKETCH_ONLY"),
        3: ("kxy", "N/m", "SKETCH_ONLY"),
        4: ("kyx", "N/m", "SKETCH_ONLY"),
        5: ("cxx", "N*s/m", "SKETCH_ONLY"),
        6: ("cyy", "N*s/m", "SKETCH_ONLY"),
        7: ("cxy", "N*s/m", "SKETCH_ONLY"),
        8: ("cyx", "N*s/m", "SKETCH_ONLY"),
        9: ("mass_kg", "kg", "SKETCH_ONLY"),
        10: ("name", None, "SKETCH_ONLY"),
    },
}


def decode_source(raw: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("cannot decode iRdin authority source")


def parse_source(raw: bytes) -> dict:
    text, encoding = decode_source(raw)
    if raw.count(b"\r\n") == raw.count(b"\n") and b"\r\n" in raw:
        newline = "CRLF"
    elif b"\n" in raw and b"\r" not in raw:
        newline = "LF"
    else:
        newline = "MIXED"
    records = []
    current = None
    for line_no, original in enumerate(text.splitlines(), 1):
        stripped = original.strip()
        if not stripped:
            records.append({"line": line_no, "kind": "blank", "raw": original})
        elif stripped.startswith((";", "#")):
            records.append({"line": line_no, "kind": "comment", "raw": original})
        elif stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
            records.append({"line": line_no, "kind": "section", "section": current, "raw": original})
        elif "=" in stripped and current is not None:
            key, value = stripped.split("=", 1)
            records.append({
                "line": line_no, "kind": "assignment", "section": current,
                "key": key.strip(), "value": value.strip(), "raw": original,
            })
        else:
            records.append({"line": line_no, "kind": "unparsed", "section": current, "raw": original})
    return {
        "schema": 1,
        "source_file": CASE_NAME,
        "source_sha256": sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "encoding": encoding,
        "newline": newline,
        "records": records,
    }


def annotate(section: str, key: str) -> dict:
    sec = section.casefold()
    k = key.casefold()
    if sec == "irdin" and k in {"data", "usuario"}:
        return {"status": "MAPPED", "field": k, "unit": None, "numerical_mapping": "METADATA",
                "authority": "CURRENT_IMPORTER_CONTRACT"}
    if sec == "dados" and k in DADOS_MAPPED:
        numerical = "MODEL" if k in {"s_melast", "s_masesp", "s_poisson"} else "METADATA"
        return {"status": "MAPPED", "field": k, "unit": None, "numerical_mapping": numerical,
                "authority": "CURRENT_IMPORTER_CONTRACT"}
    match = GRID_KEY.match(k)
    if match and sec in GRID_COLUMNS:
        column = int(match.group(2))
        if column in GRID_COLUMNS[sec]:
            field, unit, numerical = GRID_COLUMNS[sec][column]
            return {"status": "MAPPED", "field": field, "unit": unit,
                    "numerical_mapping": numerical, "authority": "CURRENT_IMPORTER_CONTRACT"}
    return {
        "status": "PRESERVED_ONLY",
        "field": "raw_legacy_field",
        "unit": None,
        "numerical_mapping": "NONE",
        "authority": "RAW_SOURCE_ONLY",
    }


def build_inventory(parsed: dict) -> dict:
    fields = []
    for record in parsed["records"]:
        if record["kind"] != "assignment":
            continue
        fields.append({
            "line": record["line"], "section": record["section"],
            "key": record["key"], "value": record["value"],
            **annotate(record["section"], record["key"]),
        })
    return {
        "schema": 1,
        "source_file": parsed["source_file"],
        "source_sha256": parsed["source_sha256"],
        "field_count": len(fields),
        "status_counts": dict(sorted(Counter(x["status"] for x in fields).items())),
        "numerical_mapping_counts": dict(sorted(Counter(x["numerical_mapping"] for x in fields).items())),
        "section_counts": dict(sorted(Counter(x["section"] for x in fields).items())),
        "fields": fields,
        "i0_contract": {
            "all_assignments_must_be_inventoried": True,
            "preserved_only_is_not_a_physics_claim": True,
        },
    }


def source_identity(parsed: dict) -> dict:
    return {
        "schema": 1,
        "source_file": parsed["source_file"],
        "sha256": parsed["source_sha256"],
        "size_bytes": parsed["size_bytes"],
        "encoding": parsed["encoding"],
        "newline": parsed["newline"],
        "git_checkout_policy": "validation/irdin/cases/*.txt -text",
    }


def generated_documents(raw: bytes) -> dict:
    parsed = parse_source(raw)
    return {
        "parsed_source.json": parsed,
        "field_inventory.json": build_inventory(parsed),
        "source_sha256.json": source_identity(parsed),
    }


def normalized_raw_document(parsed: dict) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for record in parsed["records"]:
        if record["kind"] == "section":
            result.setdefault(record["section"].casefold(), {})
        elif record["kind"] == "assignment":
            result.setdefault(record["section"].casefold(), {})[record["key"].casefold()] = record["value"]
    return result


def write_authority() -> None:
    documents = generated_documents(CASE_PATH.read_bytes())
    AUTHORITY_DIR.mkdir(parents=True, exist_ok=True)
    for filename, payload in documents.items():
        (AUTHORITY_DIR / filename).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )


def verify_authority() -> dict:
    raw = CASE_PATH.read_bytes()
    actual_sha = sha256(raw).hexdigest()
    if actual_sha != EXPECTED_SOURCE_SHA256:
        raise AssertionError(f"source SHA256 {actual_sha} != frozen {EXPECTED_SOURCE_SHA256}")
    generated = generated_documents(raw)
    for filename, expected in generated.items():
        actual = json.loads((AUTHORITY_DIR / filename).read_text(encoding="utf-8"))
        if actual != expected:
            raise AssertionError(f"{filename} differs from regenerated authority")
    parsed = generated["parsed_source.json"]
    inventory = generated["field_inventory.json"]
    assignments = [x for x in parsed["records"] if x["kind"] == "assignment"]
    source_lines = [x["line"] for x in assignments]
    inventory_lines = [x["line"] for x in inventory["fields"]]
    if inventory["field_count"] != len(assignments) or source_lines != inventory_lines:
        raise AssertionError("inventory does not cover every assignment in source order")
    if len(set(inventory_lines)) != len(inventory_lines):
        raise AssertionError("duplicate assignment line in inventory")
    unparsed = [x for x in parsed["records"] if x["kind"] == "unparsed"]
    if unparsed:
        raise AssertionError(f"unparsed nonempty source lines: {unparsed}")
    return {
        "status": "PASS", "source_sha256": actual_sha,
        "records": len(parsed["records"]), "assignments": len(assignments),
        "field_inventory": inventory["field_count"],
        "preserved_only": inventory["status_counts"].get("PRESERVED_ONLY", 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.write:
        write_authority()
    if args.verify or not args.write:
        print(json.dumps(verify_authority(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
