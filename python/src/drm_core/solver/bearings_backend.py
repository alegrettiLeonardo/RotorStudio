from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass, field

import numpy as np

from drm_core.domain.bearings import (
    AdvancedBearing,
    BallBearing,
    CoefficientBearing,
    CylindricalBearing,
    PlainJournalPhysicsBearing,
    RollerBearing,
    SqueezeFilmDamper,
    validate_advanced_bearing,
)
from drm_core.domain.model import Bearing
from .bearings_ffi import configure_bearing_library, load_bearing_library
from .ffi import SolverLibraryError


_INTERP = {"pchip": 1, "linear": 2}
_SFD_GEOMETRY = {"groove": 1, "end_seals": 2, "groove-end_seals": 3}
_TP_BEARING_TYPE = {
    "conventional_tilting_pad": 1,
    "inlet_groove_tilting_pad": 2,
    "spray_bar_tilting_pad": 3,
}
_TP_EQUILIBRIUM = {"match_eccentricity": 1, "match_load": 2}


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

    def _plain_journal_physics(self, bearing: PlainJournalPhysicsBearing, speed):
        if bearing.thermal_type is not None:
            raise SolverLibraryError(
                "native PlainJournal THD/TEHD is not qualified yet; "
                "thermal_type must be None for the current physics provider"
            )
        arrays = [
            np.ascontiguousarray(v, dtype=np.float64)
            for v in (
                bearing.pivot_angle_rad,
                bearing.pad_arc_rad,
                bearing.pad_axial_length_m,
                bearing.preload,
                bearing.offset,
            )
        ]
        xj = ct.c_double()
        yj = ct.c_double()
        K = np.empty(4, dtype=np.float64)
        C = np.empty(4, dtype=np.float64)
        fx = ct.c_double()
        fy = ct.c_double()
        pmax = ct.c_double()
        iterations = ct.c_int()
        status = self.lib.rb_plain_journal_isoviscous_c(
            float(speed),
            float(bearing.weight_n),
            float(bearing.fxs_load_n),
            float(bearing.fys_load_n),
            float(bearing.journal_diameter_m),
            float(bearing.radial_clearance_m),
            float(bearing.oil_viscosity_pa_s),
            len(arrays[0]),
            *(self._ptr(a) for a in arrays),
            int(bearing.total_e_x_film),
            int(bearing.total_e_z_film),
            float(bearing.xj_ratio_initial),
            float(bearing.yj_ratio_initial),
            float(bearing.relax_p),
            int(bearing.max_iterations),
            float(bearing.force_tolerance),
            ct.byref(xj),
            ct.byref(yj),
            self._ptr(K),
            self._ptr(C),
            ct.byref(fx),
            ct.byref(fy),
            ct.byref(pmax),
            ct.byref(iterations),
        )
        self._status(status, "PlainJournal native isoviscous physics")
        return BearingEvaluation(
            np.asarray(K).reshape((2, 2), order="F"),
            np.asarray(C).reshape((2, 2), order="F"),
            np.zeros((2, 2)),
            bearing.model_family,
            {
                "native": True,
                "physics_provider": "Fortran Reynolds/isoviscous",
                "xj_ratio": float(xj.value),
                "yj_ratio": float(yj.value),
                "eccentricity_ratio": float(np.hypot(xj.value, yj.value)),
                "attitude_angle_rad": float(np.arctan2(-xj.value, -yj.value)),
                "fx_hydro_n": float(fx.value),
                "fy_hydro_n": float(fy.value),
                "p_max_pa": float(pmax.value),
                "iterations": int(iterations.value),
                "thermal_type": None,
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


    def prepare_elliptical_geometry(self, pad_arc_rad: float, preload: float) -> dict:
        arrays = [np.empty(2, dtype=np.float64) for _ in range(4)]
        status = self.lib.rb_elliptical_geometry_c(
            float(pad_arc_rad),
            float(preload),
            *(self._ptr(a) for a in arrays),
        )
        self._status(status, "EllipticalBearing geometry")
        pivot, arc, pre, off = arrays
        return {
            "pivot_angle_rad": pivot.copy(),
            "pad_arc_rad": arc.copy(),
            "preload": pre.copy(),
            "offset": off.copy(),
        }

    def prepare_offset_halves_geometry(
        self, pad_arc_rad: float, preload: float, offset: float
    ) -> dict:
        arrays = [np.empty(2, dtype=np.float64) for _ in range(4)]
        status = self.lib.rb_offset_halves_geometry_c(
            float(pad_arc_rad),
            float(preload),
            float(offset),
            *(self._ptr(a) for a in arrays),
        )
        self._status(status, "OffsetHalvesBearing geometry")
        pivot, arc, pre, off = arrays
        return {
            "pivot_angle_rad": pivot.copy(),
            "pad_arc_rad": arc.copy(),
            "preload": pre.copy(),
            "offset": off.copy(),
        }

    def prepare_plain_journal_geometry(
        self,
        n_pads: int,
        pad_arc_rad: float,
        preload: float,
        pad_axial_length_m: float,
        journal_diameter_m: float,
        pad_thickness_m: float | None = None,
    ) -> dict:
        n = int(n_pads)
        if n < 1:
            raise ValueError("n_pads must be >= 1")
        arrays = [np.empty(n, dtype=np.float64) for _ in range(5)]
        thickness = ct.c_double()
        status = self.lib.rb_plain_journal_geometry_c(
            n,
            float(pad_arc_rad),
            float(preload),
            float(pad_axial_length_m),
            float(journal_diameter_m),
            float(pad_thickness_m or 0.0),
            int(pad_thickness_m is not None),
            *(self._ptr(a) for a in arrays),
            ct.byref(thickness),
        )
        self._status(status, "PlainJournal geometry")
        pivot, arc, pre, off, axial = arrays
        return {
            "pivot_angle_rad": pivot.copy(),
            "pad_arc_rad": arc.copy(),
            "preload": pre.copy(),
            "offset": off.copy(),
            "pad_axial_length_m": axial.copy(),
            "pad_thickness_m": float(thickness.value),
        }

    def prepare_tilting_pad(
        self,
        *,
        journal_diameter_m: float,
        radial_clearance_m: float,
        pad_thickness_m: float,
        pivot_angle_rad,
        pad_arc_rad,
        pad_axial_length_m,
        preload,
        offset,
        bearing_type: str = "conventional_tilting_pad",
        equilibrium_type: str = "match_eccentricity",
        eccentricity: float = 0.3,
        attitude_angle_rad: float = 3.0 * np.pi / 2.0,
        xj: float | None = None,
        yj: float | None = None,
        total_ex_film: int = 30,
        total_ez_film: int = 30,
        total_ey_pad: int = 16,
    ) -> dict:
        arrays = [
            np.ascontiguousarray(v, dtype=np.float64)
            for v in (pivot_angle_rad, pad_arc_rad, pad_axial_length_m, preload, offset)
        ]
        n = len(arrays[0])
        if any(len(a) != n for a in arrays):
            raise ValueError("tilting-pad per-pad arrays must have the same length")
        if bearing_type not in _TP_BEARING_TYPE:
            raise ValueError(f"unsupported tilting-pad bearing_type={bearing_type!r}")
        if equilibrium_type not in _TP_EQUILIBRIUM:
            raise ValueError(f"unsupported equilibrium_type={equilibrium_type!r}")
        use_xy = xj is not None or yj is not None
        if use_xy and (xj is None or yj is None):
            raise ValueError("xj and yj must either both be supplied or both omitted")
        initial = np.empty(2, dtype=np.float64)
        status = self.lib.rb_tilting_pad_prepare_c(
            n,
            float(journal_diameter_m),
            float(radial_clearance_m),
            float(pad_thickness_m),
            *(self._ptr(a) for a in arrays),
            _TP_BEARING_TYPE[bearing_type],
            _TP_EQUILIBRIUM[equilibrium_type],
            float(eccentricity),
            float(attitude_angle_rad),
            int(use_xy),
            float(xj or 0.0),
            float(yj or 0.0),
            int(total_ex_film),
            int(total_ez_film),
            int(total_ey_pad),
            self._ptr(initial),
        )
        self._status(status, "TiltingPad configuration")
        return {
            "n_pads": n,
            "pivot_angle_rad": arrays[0].copy(),
            "pad_arc_rad": arrays[1].copy(),
            "pad_axial_length_m": arrays[2].copy(),
            "preload": arrays[3].copy(),
            "offset": arrays[4].copy(),
            "initial_position": initial.copy(),
            "bearing_type": bearing_type,
            "equilibrium_type": equilibrium_type,
            "mesh": {
                "total_ex_film": int(total_ex_film),
                "total_ez_film": int(total_ez_film),
                "total_ey_pad": int(total_ey_pad),
            },
            "native_stage": "geometry_config_only",
        }


    def reynolds_q4_element(
        self, k_x: float, k_z: float, q: float, l_e: float, w_e: float
    ) -> tuple[np.ndarray, np.ndarray]:
        matrix_flat = np.empty(16, dtype=np.float64)
        column = np.empty(4, dtype=np.float64)
        status = self.lib.rb_reynolds_q4_element_c(
            float(k_x),
            float(k_z),
            float(q),
            float(l_e),
            float(w_e),
            self._ptr(matrix_flat),
            self._ptr(column),
        )
        self._status(status, "Reynolds Q4 element")
        matrix = np.asarray(matrix_flat).reshape((4, 4), order="F")
        return matrix, column.copy()


    def pressure_smooth_isoviscous(
        self,
        *,
        total_e_x: int,
        total_e_z: int,
        arc_length_rad: float,
        pad_length_m: float,
        axial_length_m: float,
        film_thickness_m,
        viscosity_pa_s: float,
        speed_surface_m_s: float,
        cavitation_pressure_pa: float = 0.0,
    ) -> np.ndarray:
        nx = int(total_e_x)
        nz = int(total_e_z)
        h = np.ascontiguousarray(film_thickness_m, dtype=np.float64)
        expected = (nx + 1) * (nz + 1)
        if h.size != expected:
            raise ValueError(
                f"film_thickness_m has {h.size} values; expected {expected} for "
                f"{nx}x{nz} Reynolds elements"
            )
        pressure = np.empty(expected, dtype=np.float64)
        status = self.lib.rb_pressure_smooth_isoviscous_c(
            nx,
            nz,
            float(arc_length_rad),
            float(pad_length_m),
            float(axial_length_m),
            self._ptr(h),
            float(viscosity_pa_s),
            float(speed_surface_m_s),
            float(cavitation_pressure_pa),
            self._ptr(pressure),
        )
        self._status(status, "smooth-pad isoviscous Reynolds pressure")
        return pressure


    def reduce_tilting_pad_dynamics(
        self,
        *,
        K_journal,
        C_journal,
        k_deltax,
        k_deltay,
        k_xdelta,
        k_ydelta,
        k_deltadelta,
        c_deltax,
        c_deltay,
        c_xdelta,
        c_ydelta,
        c_deltadelta,
        pad_length_m,
        pad_thickness_m: float,
        axial_length_m,
        pad_density_kg_m3: float,
        excitation_frequency_rad_s: float,
        k_rotate,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        kj = np.asfortranarray(np.asarray(K_journal, dtype=np.float64).reshape(2, 2))
        cj = np.asfortranarray(np.asarray(C_journal, dtype=np.float64).reshape(2, 2))
        arrays = [
            np.ascontiguousarray(v, dtype=np.float64)
            for v in (
                k_deltax,
                k_deltay,
                k_xdelta,
                k_ydelta,
                k_deltadelta,
                c_deltax,
                c_deltay,
                c_xdelta,
                c_ydelta,
                c_deltadelta,
                pad_length_m,
                axial_length_m,
                k_rotate,
            )
        ]
        n = len(arrays[0])
        if n < 1 or any(len(a) != n for a in arrays):
            raise ValueError("tilting-pad dynamic blocks must be non-empty and have equal lengths")
        kr = np.empty(4, dtype=np.float64)
        cr = np.empty(4, dtype=np.float64)
        ip = np.empty(n, dtype=np.float64)
        status = self.lib.rb_dynamic_reduce_tilts_c(
            n,
            self._ptr(np.ascontiguousarray(kj.ravel(order="F"))),
            self._ptr(np.ascontiguousarray(cj.ravel(order="F"))),
            *(self._ptr(a) for a in arrays[:10]),
            self._ptr(arrays[10]),
            float(pad_thickness_m),
            self._ptr(arrays[11]),
            float(pad_density_kg_m3),
            float(excitation_frequency_rad_s),
            self._ptr(arrays[12]),
            self._ptr(kr),
            self._ptr(cr),
            self._ptr(ip),
        )
        self._status(status, "TiltingPad dynamic reduction")
        return (
            np.asarray(kr).reshape((2, 2), order="F"),
            np.asarray(cr).reshape((2, 2), order="F"),
            ip.copy(),
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
        if isinstance(bearing, PlainJournalPhysicsBearing):
            return self._plain_journal_physics(bearing, speed)
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
