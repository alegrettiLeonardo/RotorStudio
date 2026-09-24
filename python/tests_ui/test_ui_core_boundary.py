from pathlib import Path

import numpy as np

from drm_core.units import (
    mm_to_m, m_to_mm, mpa_to_pa, pa_to_mpa, rpm_to_rad_s, rad_s_to_rpm
)


def test_stage2_unit_helpers_round_trip_sentinel_values():
    assert mm_to_m(53.217) == 0.053217
    assert np.isclose(m_to_mm(mm_to_m(17.413)), 17.413)
    assert mpa_to_pa(207321.0) == 207321.0e6
    assert np.isclose(pa_to_mpa(mpa_to_pa(207321.0)), 207321.0)
    assert np.isclose(rad_s_to_rpm(rpm_to_rad_s(12345.678)), 12345.678)


def test_drm_core_remains_pyside_independent():
    root = Path(__file__).resolve().parents[1] / "src" / "drm_core"
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(errors="replace")
        if "PySide6" in text:
            offenders.append(str(path.relative_to(root)))
    assert offenders == []
