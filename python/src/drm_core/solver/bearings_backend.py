from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass, field

import numpy as np

from drm_core.domain.bearings import (
    AdvancedBearing,
    BallBearing,
    CoefficientBearing,
    CylindricalBearing,
    RollerBearing,
    SqueezeFilmDamper,
    validate_advanced_bearing,
)
from drm_core.domain.model import Bearing
from .bearings_ffi import configure_bearing_library, load_bearing_library
from .ffi import SolverLibraryError


_INTERP = {"pchip": 1, "linear": 2}
_SFD_GEOMETRY = {"groove": 1, "end_seals": 2, "groove-end_seals": 3}


@dataclass(frozen=True)
class BearingEvaluation:
    K: np.ndarray
    C: np.ndarray
    M: np.ndarray
    model_family: str
    details: dict = field(default_factory=dict)


class AdvancedBearingBackend:
    """Native non-AMB bearing coefficient provider.

    Native physics is used for BallBearing, RollerBearing,
    CylindricalBearing and SqueezeFilmDamper.  Advanced fluid-film families
    such as TiltingPadBearing are accepted through their already-solved
    ROSS-style coefficient tables; this is deliberately distinct from
    claiming a native TEHD operating-point solver for those families.
    """

    def __init__(self, library_path=None, rotor_library_path=None):
        self.lib = configure_bearing_library(
            load_bearing_library(library_path, rotor_library_path=rotor_library_path)
        )

    @staticmethod
    def _ptr(a: np.ndarray):
        return a.ctypes.data_as(ct.POINTER(ct.c_double))

    @staticmethod
    def _status(status: int, operation: str) -> None:
        if status:
            raise SolverLibraryError(
                f"native bearing {operation} returned status={status}"
            )

    def _interp1(self, axis, values, query, method):
        x = np.ascontiguousarray(axis, dtype=np.float64)
        y = np.ascontiguousarray(values, dtype=np.float64)
        out = ct.c_double()
        status = self.lib.rb_interp1_c(
            len(x),
            self._ptr(x),
            self._ptr(y),
            float(query),
            _INTERP[method],
            ct.byref(out),
        )
        self._status(status, "1-D interpolation")
        return float(out.value)

    def _interp2(self, speed, frequency, values, speed_q, frequency_q, method):
        sp = np.ascontiguousarray(speed, dtype=np.float64)
        fr = np.ascontiguousarray(frequency, dtype=np.float64)
        grid = np.asarray(values, dtype=np.float64)
        # The C ABI consumes the Fortran column-major ordering used by rb_interp2.
        flat = np.ascontiguousarray(np.asfortranarray(grid).ravel(order="F"))
        out = ct.c_double()
        status = self.lib.rb_interp2_c(
            len(sp),
            self._ptr(sp),
            len(fr),
            self._ptr(fr),
            self._ptr(flat),
            float(speed_q),
            float(frequency_q),
            _INTERP[method],
            ct.byref(out),
        )
        self._status(status, "2-D interpolation")
        return float(out.value)

    def _coefficient_value(self, bearing: CoefficientBearing, value, speed, frequency):
        a = np.asarray(value, dtype=np.float64)
        if a.ndim == 0:
            return float(a)
        ns, nf = len(bearing.speed_rad_s), len(bearing.frequency_rad_s)
        if ns and nf:
            return self._interp2(
                bearing.speed_rad_s,
                bearing.frequency_rad_s,
                a,
                speed,
                frequency,
                bearing.interpolation,
            )
        if ns:
            return self._interp1(
                bearing.speed_rad_s, a, speed, bearing.interpolation
            )
        if nf:
            return self._interp1(
                bearing.frequency_rad_s, a, frequency, bearing.interpolation
            )
        raise SolverLibraryError(
            "coefficient array supplied without a speed or frequency axis"
        )

    def _coefficient_bearing(self, bearing: CoefficientBearing, speed, frequency):
        kyy = bearing.kxx if bearing.kyy is None else bearing.kyy
        cyy = bearing.cxx if bearing.cyy is None else bearing.cyy
        myy = bearing.mxx if bearing.myy is None else bearing.myy
        get = lambda value: self._coefficient_value(
            bearing, value, speed, frequency
        )
        K = np.array(
            [[get(bearing.kxx), get(bearing.kxy)], [get(bearing.kyx), get(kyy)]],
            dtype=float,
        )
        C = np.array(
            [[get(bearing.cxx), get(bearing.cxy)], [get(bearing.cyx), get(cyy)]],
            dtype=float,
        )
        M = np.array(
            [[get(bearing.mxx), get(bearing.mxy)], [get(bearing.myx), get(myy)]],
            dtype=float,
        )
        return BearingEvaluation(
            K,
            C,
            M,
            bearing.model_family,
            {
                "speed_rad_s": float(speed),
                "frequency_rad_s": float(frequency),
                "interpolation": bearing.interpolation,
                "coefficient_source": "precomputed_table",
            },
        )

    def _rolling(self, bearing, roller=False):
        outputs = [ct.c_double() for _ in range(4)]
        cxx = bearing.cxx_ns_m
        cyy = bearing.cyy_ns_m
        if roller:
            status = self.lib.rb_roller_coefficients_c(
                float(bearing.n_rollers),
                float(bearing.l_rollers_m),
                float(bearing.static_load_n),
                float(bearing.alpha_rad),
                int(cxx is not None),
                float(cxx or 0.0),
                int(cyy is not None),
                float(cyy or 0.0),
                *(ct.byref(v) for v in outputs),
            )
            operation = "RollerBearing"
        else:
            status = self.lib.rb_ball_coefficients_c(
                float(bearing.n_balls),
                float(bearing.d_balls_m),
                float(bearing.static_load_n),
                float(bearing.alpha_rad),
                int(cxx is not None),
                float(cxx or 0.0),
                int(cyy is not None),
                float(cyy or 0.0),
                *(ct.byref(v) for v in outputs),
            )
            operation = "BallBearing"
        self._status(status, operation)
        kxx, kyy, cxx_v, cyy_v = (x.value for x in outputs)
        K = np.diag([kxx, kyy]).astype(float)
        C = np.diag([cxx_v, cyy_v]).astype(float)
        return BearingEvaluation(
            K, C, np.zeros((2, 2)), bearing.model_family, {"native": True}
        )

    def _cylindrical(self, bearing: CylindricalBearing, speed):
        values = [ct.c_double() for _ in range(12)]
        status = self.lib.rb_cylindrical_coefficients_c(
            float(speed),
            float(bearing.weight_n),
            float(bearing.bearing_length_m),
            float(bearing.journal_diameter_m),
            float(bearing.radial_clearance_m),
            float(bearing.oil_viscosity_pa_s),
            *(ct.byref(v) for v in values),
        )
        self._status(status, "CylindricalBearing")
        ms, som, ecc, attitude, kxx, kxy, kyx, kyy, cxx, cxy, cyx, cyy = (
            v.value for v in values
        )
        return BearingEvaluation(
            np.array([[kxx, kxy], [kyx, kyy]], dtype=float),
            np.array([[cxx, cxy], [cyx, cyy]], dtype=float),
            np.zeros((2, 2)),
            bearing.model_family,
            {
                "native": True,
                "modified_sommerfeld": ms,
                "sommerfeld": som,
                "eccentricity_ratio": ecc,
                "attitude_angle_rad": attitude,
            },
        )

    def _sfd(self, bearing: SqueezeFilmDamper, frequency):
        values = [ct.c_double() for _ in range(4)]
        status = self.lib.rb_sfd_coefficients_c(
            float(frequency),
            float(bearing.axial_length_m),
            float(bearing.journal_diameter_m),
            float(bearing.radial_clearance_m),
            float(bearing.eccentricity_ratio),
            float(bearing.viscosity_pa_s),
            _SFD_GEOMETRY[bearing.geometry],
            int(bool(bearing.cavitation)),
            *(ct.byref(v) for v in values),
        )
        self._status(status, "SqueezeFilmDamper")
        stiffness, damping, theta, p_max = (v.value for v in values)
        return BearingEvaluation(
            np.diag([stiffness, stiffness]).astype(float),
            np.diag([damping, damping]).astype(float),
            np.zeros((2, 2)),
            bearing.model_family,
            {
                "native": True,
                "theta_rad": theta,
                "p_max_pa": p_max,
                "excitation_frequency_rad_s": float(frequency),
            },
        )

    def evaluate(
        self,
        bearing: AdvancedBearing,
        speed_rad_s: float,
        frequency_rad_s: float | None = None,
    ) -> BearingEvaluation:
        validate_advanced_bearing(bearing)
        speed = float(speed_rad_s)
        frequency = speed if frequency_rad_s is None else float(frequency_rad_s)
        if not np.isfinite(speed) or not np.isfinite(frequency):
            raise ValueError("bearing speed and excitation frequency must be finite")

        if isinstance(bearing, CoefficientBearing):
            return self._coefficient_bearing(bearing, speed, frequency)
        if isinstance(bearing, BallBearing):
            return self._rolling(bearing, roller=False)
        if isinstance(bearing, RollerBearing):
            return self._rolling(bearing, roller=True)
        if isinstance(bearing, CylindricalBearing):
            return self._cylindrical(bearing, speed)
        if isinstance(bearing, SqueezeFilmDamper):
            return self._sfd(bearing, frequency)
        raise TypeError(f"unsupported advanced bearing {type(bearing).__name__}")

    def as_legacy_bearing(
        self,
        bearing: AdvancedBearing,
        speed_rad_s: float,
        frequency_rad_s: float | None = None,
    ) -> Bearing:
        result = self.evaluate(bearing, speed_rad_s, frequency_rad_s)
        if np.max(np.abs(result.M)) > 1e-14:
            raise SolverLibraryError(
                f"{type(bearing).__name__} evaluated a nonzero bearing mass matrix; "
                "the qualified 4-DOF RotorStudio legacy assembly cannot silently "
                "discard bearing mass. A dedicated rotor-assembly ABI is required."
            )
        K, C = result.K, result.C
        props = (
            float(K[0, 0]),
            float(K[0, 1]),
            float(K[1, 0]),
            float(K[1, 1]),
            float(C[0, 0]),
            float(C[0, 1]),
            float(C[1, 0]),
            float(C[1, 1]),
        )
        # Legacy type 5 is the already-qualified full 2x2 translational K/C path.
        return Bearing(5, int(bearing.node), props)
