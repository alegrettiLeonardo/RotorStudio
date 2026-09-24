from __future__ import annotations

# A_SOLVER cases: exact executable V2 numerical-solver calls found by static
# scan and then source-reviewed. Every migrated comparison is executed through
# AnalysisService; no solver equations live in these adapters.
SOLVER_CASES = {
    "05_01": {"kind": "modal", "model": "example", "speed": "Rotor_Spd", "reference": "eigenvalues"},
    "05_02": {"kind": "modal", "model": "example", "speed": "Rotor_Spd", "reference": "eigenvalues"},
    "05_03": {"kind": "modal", "model": "example", "speed": "Rotor_Spd", "reference": "eigenvalues"},
    "05_08": {"kind": "modal", "model": "example", "speed": "Rotor_Spd", "reference": "eigenvalues"},
    "05_09": {"kind": "modal", "model": "example", "speed": "Rotor_Spd", "reference": "eigenvalues"},
    "05_11": {"kind": "modal", "model": "model", "speed": "Rotor_Spd", "reference": "eigenvalues"},
    "06_10": {"kind": "response", "model": "example", "speed": "speed_vector", "reference": "response"},
    "06_11": {"kind": "modal", "model": "example", "speed": "Rotor_Spd", "reference": "eigenvalues"},
    "06_11e": {"kind": "modal", "model": "example", "speed": "Rotor_Spd", "reference": "eigenvalues"},
    "06_12": {"kind": "response", "model": "example", "speed": "speed_vector", "reference": "response"},
    "07_10": {"kind": "modal", "model": "example", "speed": "Rotor_Spd", "reference": "eigenvalues"},
    "07_11": {"kind": "asymmetric_modal", "model": "example", "speed": "Rotor_Spd", "reference": "eigenvalues"},
    "08_11": {"kind": "response", "model": "model", "speed": "Rotor_Spd", "reference": "response03"},
    "08_12": {"kind": "response", "model": "example", "speed": "Rotor_Spd", "reference": "response03"},
    "08_14": {"kind": "response", "model": "model", "speed": "Rotor_Spd", "reference": "response03"},
}

# Book calculations that are exact independent oracles for a production
# component/model. The product side still enters through AnalysisService and
# the existing Fortran implementation.
HYBRID_CASES = {
    "04_06": {"kind": "beam_modal", "elements": [1], "bc": "pinned-pinned"},
    "04_07": {"kind": "beam_modal", "elements": [2], "bc": "clamped-clamped"},
    "04_08": {"kind": "beam_modal", "elements": [2], "bc": "clamped-pinned"},
    "04_12": {"kind": "beam_convergence", "elements_var": "lis", "error_var": "err", "exact_var": "exact"},
    "05_04": {"kind": "short_bearing", "speed_var": "Rotor_Spd", "k_var": "Kb", "c_var": "Cb", "ecc_var": "n"},
}
