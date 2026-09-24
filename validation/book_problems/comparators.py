from __future__ import annotations

import numpy as np
from validation.equivalence.comparators import (
    rel_fro as _formal_rel_fro,
    match_modes as _formal_match_modes,
    eigenvalue_max_rel as _formal_eigenvalue_max_rel,
    complex_response_rel as _formal_complex_response_rel,
)

# Frozen G5-G12 thresholds. G14 reuses them for like-for-like physics.
MATRIX_REL = 1.0e-12
EIG_REL = 1.0e-8
FREQ_REL = 1.0e-8
MAC_MIN = 0.999999
RESPONSE_REL = 1.0e-8
CRITICAL_REL = 1.0e-6
KAPPA_ABSREL = 1.0e-10

# B-only repeatability uses the strictest already-frozen relative threshold;
# it is not a product-equivalence threshold.
ANALYTICAL_REL = MATRIX_REL


def max_rel(reference, actual) -> float:
    a = np.asarray(reference)
    b = np.asarray(actual)
    if a.shape != b.shape:
        return float("inf")
    if a.size == 0:
        return 0.0
    scale = max(1.0, float(np.max(np.abs(a))))
    return float(np.max(np.abs(a - b)) / scale)


def scalar_vector(reference, actual, threshold: float = ANALYTICAL_REL) -> dict:
    err = max_rel(reference, actual)
    return {
        "metric": "relative",
        "error": err,
        "threshold": threshold,
        "pass": bool(np.isfinite(err) and err <= threshold),
    }


def matrix(reference, actual) -> dict:
    err = _formal_rel_fro(np.asarray(actual), np.asarray(reference))
    return {
        "metric": "matrix_rel",
        "error": err,
        "threshold": MATRIX_REL,
        "pass": bool(np.isfinite(err) and err <= MATRIX_REL),
    }


def eigenvalues(reference, actual) -> dict:
    reference = np.asarray(reference).ravel()
    actual = np.asarray(actual).ravel()
    if reference.shape != actual.shape:
        err = float("inf")
        mapping = []
    else:
        mapping = _formal_match_modes(actual, reference)
        err = _formal_eigenvalue_max_rel(actual, reference, mapping)
    return {
        "metric": "eig_rel",
        "error": err,
        "threshold": EIG_REL,
        "pass": bool(np.isfinite(err) and err <= EIG_REL),
        "matching": "validation.equivalence.comparators.match_modes",
    }


def frequencies(reference, actual) -> dict:
    return scalar_vector(reference, actual, FREQ_REL) | {"metric": "freq_rel"}


def response(reference, actual) -> dict:
    reference = np.asarray(reference)
    actual = np.asarray(actual)
    err = float("inf") if reference.shape != actual.shape else _formal_complex_response_rel(actual, reference)
    return {
        "metric": "complex_response_rel",
        "error": err,
        "threshold": RESPONSE_REL,
        "pass": bool(np.isfinite(err) and err <= RESPONSE_REL),
    }


def critical(reference, actual) -> dict:
    return scalar_vector(reference, actual, CRITICAL_REL) | {"metric": "critical_speed_rel"}


def kappa(reference, actual) -> dict:
    a = np.asarray(reference)
    b = np.asarray(actual)
    if a.shape != b.shape:
        err = float("inf")
    elif a.size == 0:
        err = 0.0
    else:
        abs_err = float(np.max(np.abs(a - b)))
        rel_err = max_rel(a, b)
        err = max(abs_err, rel_err)
    return {
        "metric": "kappa_absrel",
        "error": err,
        "threshold": KAPPA_ABSREL,
        "pass": bool(np.isfinite(err) and err <= KAPPA_ABSREL),
    }


def mac(reference, actual) -> float:
    a = np.asarray(reference, complex).reshape(-1)
    b = np.asarray(actual, complex).reshape(-1)
    den = np.vdot(a, a).real * np.vdot(b, b).real
    if den <= 0:
        return 0.0
    return float(abs(np.vdot(a, b)) ** 2 / den)
