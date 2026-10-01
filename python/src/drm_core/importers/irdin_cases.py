from __future__ import annotations

"""I10 automatic AnalysisCase generation for qualified iRdin lateral projects.

Authority:
- c_div is native CPBSPD: an integer number of Campbell speed points.
- d_div is the legacy synchronous-response rpm increment.
The demonstrated source is frontend_rotordin@647d600... SolverConfiguration and
legacy_import mappings. This module performs only grid/case orchestration.
"""

import math
from typing import Any
import numpy as np

from drm_core.stage1 import AnalysisCase

RPM_TO_RAD_S = 2.0 * math.pi / 60.0


class IrdinCaseMappingError(ValueError):
    pass


def _finite(value: Any, name: str) -> float:
    out=float(value)
    if not math.isfinite(out):
        raise IrdinCaseMappingError(f"{name} must be finite")
    return out


def campbell_speed_grid_rpm(metadata: dict[str, Any]) -> np.ndarray:
    legacy=dict(metadata.get("legacy_irdin") or {})
    cfg=dict(legacy.get("campbell") or {})
    start=_finite(cfg.get("start_rpm",0.0),"c_rpmi")
    end=_finite(cfg.get("end_rpm",0.0),"c_rpmf")
    raw_points=_finite(cfg.get("division",0.0),"c_div")
    points=int(round(raw_points))
    if start < 0.0 or end <= start:
        raise IrdinCaseMappingError("Campbell requires 0 <= c_rpmi < c_rpmf")
    if points < 2 or points > 500 or abs(raw_points-points)>1.0e-9:
        raise IrdinCaseMappingError("c_div/CPBSPD must be an integer number of points in [2,500]")
    return np.linspace(start,end,points,dtype=np.float64)


def response_speed_grid_rpm(metadata: dict[str, Any]) -> np.ndarray:
    legacy=dict(metadata.get("legacy_irdin") or {})
    cfg=dict(legacy.get("response") or {})
    start=_finite(cfg.get("start_rpm",0.0),"d_rpmi")
    end=_finite(cfg.get("end_rpm",0.0),"d_rpmf")
    step=_finite(cfg.get("division",0.0),"d_div")
    if start < 0.0 or end < start or step <= 0.0:
        raise IrdinCaseMappingError("response requires 0 <= d_rpmi <= d_rpmf and d_div > 0")
    count=int(math.floor((end-start)/step+1.0e-12))+1
    if count < 1 or count > 10000:
        raise IrdinCaseMappingError(f"response grid count {count} outside [1,10000]")
    values=start+step*np.arange(count,dtype=np.float64)
    return values[values <= end + 1.0e-9*max(1.0,abs(end))]


def build_legacy_analysis_cases(metadata: dict[str, Any]) -> list[AnalysisCase]:
    camp_rpm=campbell_speed_grid_rpm(metadata)
    response_rpm=response_speed_grid_rpm(metadata)
    authority="frontend_rotordin@647d600bc1d32a05de62ee457942e00285b572e3"
    return [
        AnalysisCase(
            "irdin_modal_sweep",
            {"speeds_rad_s":(camp_rpm*RPM_TO_RAD_S).tolist()},
            "iRdin Campbell",
            {
                "source_format":"iRdin/VB6 INI",
                "grid_semantics":"c_div=CPBSPD number of points",
                "source_speed_rpm":camp_rpm.tolist(),
                "authority":authority,
            },
        ),
        AnalysisCase(
            "irdin_synchronous_response",
            {"speeds_rad_s":(response_rpm*RPM_TO_RAD_S).tolist()},
            "iRdin Unbalance Response",
            {
                "source_format":"iRdin/VB6 INI",
                "grid_semantics":"d_div=response rpm increment",
                "source_speed_rpm":response_rpm.tolist(),
                "authority":authority,
            },
        ),
    ]


__all__=[
    "RPM_TO_RAD_S","IrdinCaseMappingError","campbell_speed_grid_rpm",
    "response_speed_grid_rpm","build_legacy_analysis_cases",
]
