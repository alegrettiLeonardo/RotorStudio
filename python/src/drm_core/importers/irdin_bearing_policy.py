"""Historical iRdin/RotorDin coefficient-table speed policy.

The interpolation algorithm is executed natively by drmbearings. This module
only records the demonstrated source range policy and classifies requested
speeds for provenance/reporting.
"""
from __future__ import annotations
from math import isfinite

IRDIN_LEGACY_INTERPOLATION = "irdin_lagrange"
IRDIN_RECOMMENDED_LOWER_FACTOR = 0.75
IRDIN_RECOMMENDED_UPPER_FACTOR = 1.25


def legacy_speed_status(speed_rpm: tuple[float, ...], query_rpm: float) -> str:
    axis=tuple(float(x) for x in speed_rpm)
    q=float(query_rpm)
    if len(axis)<2 or not isfinite(q):
        raise ValueError("legacy iRdin speed policy requires >=2 finite table points and finite query")
    lower=IRDIN_RECOMMENDED_LOWER_FACTOR*axis[0]
    upper=IRDIN_RECOMMENDED_UPPER_FACTOR*axis[-1]
    if any(abs(q-x)<=1e-12*max(1.0,abs(x)) for x in axis):
        return "TABULATED"
    if axis[0] < q < axis[-1]:
        return "INTERPOLATED"
    if lower <= q <= upper:
        return "EXTRAPOLATED_WITHIN_LEGACY_RECOMMENDED_RANGE"
    return "EXTRAPOLATED_OUTSIDE_LEGACY_RECOMMENDED_RANGE"


def legacy_bearing_policy(speed_rpm, *, requested_rpm=()):
    axis=tuple(float(x) for x in speed_rpm)
    if len(axis)<2 or any(not isfinite(x) for x in axis):
        raise ValueError("iRdin coefficient table requires at least two finite speeds")
    if any(axis[i] <= axis[i-1] for i in range(1,len(axis))):
        raise ValueError("iRdin coefficient table speeds must be strictly increasing")
    req=tuple(float(x) for x in requested_rpm if isfinite(float(x)))
    lower=IRDIN_RECOMMENDED_LOWER_FACTOR*axis[0]
    upper=IRDIN_RECOMMENDED_UPPER_FACTOR*axis[-1]
    return {
        "legacy_interpolation": IRDIN_LEGACY_INTERPOLATION,
        "source_table_speed_range_rpm": [axis[0],axis[-1]],
        "legacy_recommended_speed_range_rpm": [lower,upper],
        "legacy_recommended_factors": [IRDIN_RECOMMENDED_LOWER_FACTOR,IRDIN_RECOMMENDED_UPPER_FACTOR],
        "requested_speed_status": [
            {"rpm":q,"status":legacy_speed_status(axis,q)} for q in req
        ],
        "authority": "frontend_rotordin@647d600bc1d32a05de62ee457942e00285b572e3:intlag/lmvpar",
        "below_first_semantics": "THREE_POINT_LAGRANGE_FOR_N_GE_3",
        "upper_edge_semantics": "LINEAR_LAST_TWO_POINTS",
        "recommended_range_is_warning_not_clamp": True,
    }


__all__=[
    "IRDIN_LEGACY_INTERPOLATION","IRDIN_RECOMMENDED_LOWER_FACTOR",
    "IRDIN_RECOMMENDED_UPPER_FACTOR","legacy_speed_status","legacy_bearing_policy",
]
