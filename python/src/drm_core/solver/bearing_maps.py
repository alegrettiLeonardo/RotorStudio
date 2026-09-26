from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable

import numpy as np

from drm_core.domain.bearings import (
    AdvancedBearing,
    CoefficientBearing,
    advanced_bearing_to_dict,
    validate_advanced_bearing,
)
from .bearings_backend import AdvancedBearingBackend, BearingCancelledError
from .ffi import SolverLibraryError


CACHE_SCHEMA = 1
MAP_CONTRACT = "B16-v1"
NATIVE_ABI = "drmbearings-B14-fields-v2"
ROSS_AUTHORITY_SHA = "6320eab9f890f1b3cc1710d508b446fe063ca68d"


class BearingMapError(RuntimeError):
    pass


class BearingMapCancelled(BearingMapError):
    pass


class BearingMapCacheCorruption(BearingMapError):
    pass


def _canonical(value: Any):
    if isinstance(value, dict):
        return {str(k): _canonical(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if hasattr(value, "tolist"):
        return _canonical(value.tolist())
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def _json_hash(payload: Any) -> str:
    raw = json.dumps(
        _canonical(payload), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _axis(name: str, values) -> tuple[float, ...]:
    axis = tuple(float(value) for value in values)
    if not axis:
        raise ValueError(f"{name} must contain at least one operating point")
    if any(not np.isfinite(value) for value in axis):
        raise ValueError(f"{name} contains NaN or Inf")
    if any(axis[index] <= axis[index - 1] for index in range(1, len(axis))):
        raise ValueError(f"{name} must be strictly increasing with no duplicates")
    return axis


def canonical_bearing_hash(bearing: AdvancedBearing) -> str:
    validate_advanced_bearing(bearing)
    return _json_hash(advanced_bearing_to_dict(bearing))


def solver_fingerprint_payload(backend: AdvancedBearingBackend) -> dict[str, Any]:
    library_name = str(getattr(backend.lib, "_name", "") or "")
    library_sha = None
    try:
        path = Path(library_name)
        if path.is_file():
            library_sha = _file_hash(path)
    except OSError:
        library_sha = None
    return {
        "native_abi": NATIVE_ABI,
        "native_library_sha256": library_sha or "UNAVAILABLE",
        "ross_authority_sha": ROSS_AUTHORITY_SHA,
        "cache_schema": CACHE_SCHEMA,
    }


def solver_fingerprint(backend: AdvancedBearingBackend) -> str:
    return _json_hash(solver_fingerprint_payload(backend))


@dataclass(frozen=True)
class BearingOperatingMap:
    node: int
    speed_rad_s: tuple[float, ...]
    frequency_rad_s: tuple[float, ...]
    kxx: Any
    kxy: Any
    kyx: Any
    kyy: Any
    cxx: Any
    cxy: Any
    cyx: Any
    cyy: Any
    interpolation: str
    source_bearing_hash: str
    solver_fingerprint: str
    qualification: dict[str, Any] = field(default_factory=dict)
    convergence_summary: dict[str, Any] = field(default_factory=dict)

    @property
    def synchronous(self) -> bool:
        return len(self.frequency_rad_s) == 0

    def validate(self) -> None:
        if int(self.node) < 1:
            raise ValueError(f"node={self.node}; expected node >= 1")
        _axis("speed_rad_s", self.speed_rad_s)
        if self.frequency_rad_s:
            _axis("frequency_rad_s", self.frequency_rad_s)
        if self.interpolation not in {"linear", "pchip"}:
            raise ValueError("interpolation must be 'linear' or 'pchip'")
        expected = (
            (len(self.speed_rad_s), len(self.frequency_rad_s))
            if self.frequency_rad_s
            else (len(self.speed_rad_s),)
        )
        for name in ("kxx", "kxy", "kyx", "kyy", "cxx", "cxy", "cyx", "cyy"):
            array = np.asarray(getattr(self, name), dtype=float)
            if array.shape != expected:
                raise ValueError(f"{name} shape={array.shape}; expected {expected}")
            if not np.isfinite(array).all():
                raise ValueError(f"{name} contains NaN or Inf")
        if len(self.source_bearing_hash) != 64 or len(self.solver_fingerprint) != 64:
            raise ValueError("source_bearing_hash and solver_fingerprint must be SHA256 hex")

    def to_coefficient_bearing(self, *, tag: str = "B16 operating map") -> CoefficientBearing:
        self.validate()
        provenance = {
            "map_contract": MAP_CONTRACT,
            "source_bearing_hash": self.source_bearing_hash,
            "solver_fingerprint": self.solver_fingerprint,
            "qualification": _canonical(self.qualification),
            "convergence_summary": _canonical(self.convergence_summary),
        }
        bearing = CoefficientBearing(
            node=int(self.node),
            speed_rad_s=self.speed_rad_s,
            frequency_rad_s=self.frequency_rad_s,
            interpolation=self.interpolation,
            kxx=self.kxx,
            kxy=self.kxy,
            kyx=self.kyx,
            kyy=self.kyy,
            cxx=self.cxx,
            cxy=self.cxy,
            cyx=self.cyx,
            cyy=self.cyy,
            mxx=0.0,
            mxy=0.0,
            myx=0.0,
            myy=0.0,
            tag=tag,
            provenance=provenance,
        )
        validate_advanced_bearing(bearing)
        return bearing


@dataclass(frozen=True)
class MapCacheResult:
    operating_map: BearingOperatingMap
    cache_key: str
    source: str  # GENERATED, L1, or L2


def _nested(array: np.ndarray):
    return tuple(
        tuple(float(value) for value in row)
        for row in np.asarray(array, dtype=float)
    )


def _vector(array: np.ndarray):
    return tuple(float(value) for value in np.asarray(array, dtype=float))


def generate_operating_map(
    bearing: AdvancedBearing,
    speed_rad_s,
    frequency_rad_s=None,
    *,
    interpolation: str = "pchip",
    backend: AdvancedBearingBackend | None = None,
    progress_callback: Callable[[int, int, dict[str, Any]], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> BearingOperatingMap:
    """Materialize B(Omega, omega)->K,C without carrying full field arrays.

    Empty frequency_rad_s means the synchronous one-dimensional policy
    omega=Omega. Supplying frequency_rad_s creates a full independent 2-D map.
    """
    validate_advanced_bearing(bearing)
    speed = _axis("speed_rad_s", speed_rad_s)
    frequency = () if frequency_rad_s is None else _axis("frequency_rad_s", frequency_rad_s)
    if interpolation not in {"linear", "pchip"}:
        raise ValueError("interpolation must be 'linear' or 'pchip'")
    provider = backend or AdvancedBearingBackend()
    source_hash = canonical_bearing_hash(bearing)
    fingerprint = solver_fingerprint(provider)
    fp_payload = solver_fingerprint_payload(provider)
    shape = (len(speed), len(frequency)) if frequency else (len(speed),)
    arrays = {
        name: np.empty(shape, dtype=float)
        for name in ("kxx", "kxy", "kyx", "kyy", "cxx", "cxy", "cyx", "cyy")
    }
    points = (
        [(i, j, omega, whirl) for i, omega in enumerate(speed) for j, whirl in enumerate(frequency)]
        if frequency
        else [(i, None, omega, omega) for i, omega in enumerate(speed)]
    )
    total = len(points)
    point_summaries = []
    qualifications = set()

    for completed, (i, j, omega, whirl) in enumerate(points, start=1):
        if cancel_check is not None and cancel_check():
            raise BearingMapCancelled(
                f"operating-map generation cancelled before point {completed}/{total}"
            )
        provider.reset_job_control()
        try:
            evaluation = provider.evaluate(
                bearing,
                float(omega),
                float(whirl),
                reset_job_control=False,
            )
        except BearingCancelledError as exc:
            raise BearingMapCancelled(str(exc)) from exc
        if np.max(np.abs(np.asarray(evaluation.M, dtype=float))) > 1.0e-14:
            raise SolverLibraryError(
                "B16 operating maps contain K/C only and cannot silently discard "
                "a nonzero advanced-bearing M matrix"
            )
        target = (i,) if j is None else (i, j)
        arrays["kxx"][target] = evaluation.K[0, 0]
        arrays["kxy"][target] = evaluation.K[0, 1]
        arrays["kyx"][target] = evaluation.K[1, 0]
        arrays["kyy"][target] = evaluation.K[1, 1]
        arrays["cxx"][target] = evaluation.C[0, 0]
        arrays["cxy"][target] = evaluation.C[0, 1]
        arrays["cyx"][target] = evaluation.C[1, 0]
        arrays["cyy"][target] = evaluation.C[1, 1]
        details = dict(evaluation.details)
        if details.get("qualification"):
            qualifications.add(str(details["qualification"]))
        point_summaries.append(
            {
                "speed_rad_s": float(omega),
                "frequency_rad_s": float(whirl),
                "iterations": int(details.get("iterations", 0) or 0),
                "p_max_pa": float(details.get("p_max_pa", 0.0) or 0.0),
                "t_max_k": float(details.get("t_max_k", 0.0) or 0.0),
                "deformation_max_m": float(details.get("deformation_max_m", 0.0) or 0.0),
            }
        )
        if progress_callback is not None:
            progress_callback(
                completed,
                total,
                {
                    "stage": "physical_evaluation",
                    "speed_rad_s": float(omega),
                    "frequency_rad_s": float(whirl),
                },
            )
        if cancel_check is not None and cancel_check():
            raise BearingMapCancelled(
                f"operating-map generation cancelled after point {completed}/{total}"
            )

    result = BearingOperatingMap(
        node=int(bearing.node),
        speed_rad_s=speed,
        frequency_rad_s=frequency,
        kxx=_nested(arrays["kxx"]) if frequency else _vector(arrays["kxx"]),
        kxy=_nested(arrays["kxy"]) if frequency else _vector(arrays["kxy"]),
        kyx=_nested(arrays["kyx"]) if frequency else _vector(arrays["kyx"]),
        kyy=_nested(arrays["kyy"]) if frequency else _vector(arrays["kyy"]),
        cxx=_nested(arrays["cxx"]) if frequency else _vector(arrays["cxx"]),
        cxy=_nested(arrays["cxy"]) if frequency else _vector(arrays["cxy"]),
        cyx=_nested(arrays["cyx"]) if frequency else _vector(arrays["cyx"]),
        cyy=_nested(arrays["cyy"]) if frequency else _vector(arrays["cyy"]),
        interpolation=interpolation,
        source_bearing_hash=source_hash,
        solver_fingerprint=fingerprint,
        qualification={
            "map_contract": MAP_CONTRACT,
            "source_qualifications": sorted(qualifications),
            "ross_authority_sha": ROSS_AUTHORITY_SHA,
            "solver": fp_payload,
            "coefficient_policy": "SYNCHRONOUS" if not frequency else "INDEPENDENT_2D",
        },
        convergence_summary={
            "points": total,
            "completed_points": total,
            "max_iterations": max(
                (item["iterations"] for item in point_summaries), default=0
            ),
            "points_summary": point_summaries,
        },
    )
    result.validate()
    return result


class BearingMapCache:
    """Two-level deterministic B16 coefficient-map cache.

    L1 is an in-memory LRU. L2 is an atomic directory containing manifest.json
    and coefficients.npz. Full pressure/temperature fields are intentionally
    excluded from this cache.
    """

    def __init__(self, root: str | Path | None = None, *, max_l1_entries: int = 8):
        configured = root or os.environ.get("ROTORSTUDIO_BEARING_CACHE")
        self.root = Path(configured) if configured else Path.home() / ".cache" / "RotorStudio" / "bearing_maps"
        self.max_l1_entries = max(1, int(max_l1_entries))
        self._l1: OrderedDict[str, BearingOperatingMap] = OrderedDict()

    def cache_key_for(
        self,
        bearing: AdvancedBearing,
        speed_rad_s,
        frequency_rad_s=None,
        *,
        interpolation: str = "pchip",
        backend: AdvancedBearingBackend | None = None,
    ) -> str:
        provider = backend or AdvancedBearingBackend()
        speed = _axis("speed_rad_s", speed_rad_s)
        frequency = () if frequency_rad_s is None else _axis("frequency_rad_s", frequency_rad_s)
        payload = {
            "cache_schema": CACHE_SCHEMA,
            "map_contract": MAP_CONTRACT,
            "family": str(getattr(bearing, "model_family", type(bearing).__name__)),
            "bearing": advanced_bearing_to_dict(bearing),
            "speed_rad_s": speed,
            "frequency_rad_s": frequency,
            "coefficient_policy": "SYNCHRONOUS" if not frequency else "INDEPENDENT_2D",
            "interpolation": interpolation,
            "native_abi": NATIVE_ABI,
            "solver_fingerprint": solver_fingerprint(provider),
            "ross_authority_sha": ROSS_AUTHORITY_SHA,
        }
        return _json_hash(payload)

    def _remember(self, key: str, operating_map: BearingOperatingMap) -> None:
        self._l1.pop(key, None)
        self._l1[key] = operating_map
        while len(self._l1) > self.max_l1_entries:
            self._l1.popitem(last=False)

    def _disk_path(self, key: str) -> Path:
        return self.root / key

    def invalidate(self, key: str) -> None:
        self._l1.pop(key, None)
        target = self._disk_path(key)
        if target.exists():
            shutil.rmtree(target)

    def _load_disk(self, key: str) -> BearingOperatingMap:
        target = self._disk_path(key)
        manifest_path = target / "manifest.json"
        coeff_path = target / "coefficients.npz"
        if not manifest_path.is_file() or not coeff_path.is_file():
            raise BearingMapCacheCorruption(f"cache {key} is incomplete")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise BearingMapCacheCorruption(f"cache {key} manifest is unreadable") from exc
        if manifest.get("cache_schema") != CACHE_SCHEMA or manifest.get("cache_key") != key:
            raise BearingMapCacheCorruption(f"cache {key} manifest identity mismatch")
        if manifest.get("coefficients_sha256") != _file_hash(coeff_path):
            raise BearingMapCacheCorruption(f"cache {key} coefficient file hash mismatch")
        try:
            with np.load(coeff_path, allow_pickle=False) as data:
                values = {name: np.asarray(data[name], dtype=float) for name in (
                    "kxx", "kxy", "kyx", "kyy", "cxx", "cxy", "cyx", "cyy"
                )}
        except Exception as exc:
            raise BearingMapCacheCorruption(f"cache {key} coefficient file is unreadable") from exc
        frequency = tuple(float(x) for x in manifest["frequency_rad_s"])
        operating_map = BearingOperatingMap(
            node=int(manifest["node"]),
            speed_rad_s=tuple(float(x) for x in manifest["speed_rad_s"]),
            frequency_rad_s=frequency,
            kxx=_nested(values["kxx"]) if frequency else _vector(values["kxx"]),
            kxy=_nested(values["kxy"]) if frequency else _vector(values["kxy"]),
            kyx=_nested(values["kyx"]) if frequency else _vector(values["kyx"]),
            kyy=_nested(values["kyy"]) if frequency else _vector(values["kyy"]),
            cxx=_nested(values["cxx"]) if frequency else _vector(values["cxx"]),
            cxy=_nested(values["cxy"]) if frequency else _vector(values["cxy"]),
            cyx=_nested(values["cyx"]) if frequency else _vector(values["cyx"]),
            cyy=_nested(values["cyy"]) if frequency else _vector(values["cyy"]),
            interpolation=str(manifest["interpolation"]),
            source_bearing_hash=str(manifest["source_bearing_hash"]),
            solver_fingerprint=str(manifest["solver_fingerprint"]),
            qualification=dict(manifest.get("qualification") or {}),
            convergence_summary=dict(manifest.get("convergence_summary") or {}),
        )
        operating_map.validate()
        return operating_map

    def get(self, key: str) -> MapCacheResult | None:
        if key in self._l1:
            value = self._l1.pop(key)
            self._l1[key] = value
            return MapCacheResult(value, key, "L1")
        if not self._disk_path(key).exists():
            return None
        value = self._load_disk(key)
        self._remember(key, value)
        return MapCacheResult(value, key, "L2")

    def put(self, key: str, operating_map: BearingOperatingMap) -> None:
        operating_map.validate()
        self.root.mkdir(parents=True, exist_ok=True)
        target = self._disk_path(key)
        if target.exists():
            # Existing complete cache wins. A corrupt target is rejected by
            # get_or_generate before put is reached.
            self._remember(key, self._load_disk(key))
            return
        temp = Path(tempfile.mkdtemp(prefix=f".{key}.tmp-", dir=str(self.root)))
        try:
            coeff_path = temp / "coefficients.npz"
            np.savez_compressed(
                coeff_path,
                **{
                    name: np.asarray(getattr(operating_map, name), dtype=float)
                    for name in ("kxx", "kxy", "kyx", "kyy", "cxx", "cxy", "cyx", "cyy")
                },
            )
            manifest = {
                "cache_schema": CACHE_SCHEMA,
                "cache_key": key,
                "map_contract": MAP_CONTRACT,
                "node": operating_map.node,
                "speed_rad_s": list(operating_map.speed_rad_s),
                "frequency_rad_s": list(operating_map.frequency_rad_s),
                "interpolation": operating_map.interpolation,
                "source_bearing_hash": operating_map.source_bearing_hash,
                "solver_fingerprint": operating_map.solver_fingerprint,
                "qualification": _canonical(operating_map.qualification),
                "convergence_summary": _canonical(operating_map.convergence_summary),
                "coefficients_sha256": _file_hash(coeff_path),
            }
            (temp / "manifest.json").write_text(
                json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
            )
            os.replace(temp, target)
        finally:
            if temp.exists():
                shutil.rmtree(temp, ignore_errors=True)
        self._remember(key, operating_map)

    def get_or_generate(
        self,
        bearing: AdvancedBearing,
        speed_rad_s,
        frequency_rad_s=None,
        *,
        interpolation: str = "pchip",
        backend: AdvancedBearingBackend | None = None,
        progress_callback=None,
        cancel_check=None,
    ) -> MapCacheResult:
        provider = backend or AdvancedBearingBackend()
        key = self.cache_key_for(
            bearing,
            speed_rad_s,
            frequency_rad_s,
            interpolation=interpolation,
            backend=provider,
        )
        try:
            cached = self.get(key)
        except BearingMapCacheCorruption:
            self.invalidate(key)
            cached = None
        if cached is not None:
            return cached
        operating_map = generate_operating_map(
            bearing,
            speed_rad_s,
            frequency_rad_s,
            interpolation=interpolation,
            backend=provider,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )
        if cancel_check is not None and cancel_check():
            raise BearingMapCancelled("operating-map generation cancelled before cache promotion")
        self.put(key, operating_map)
        return MapCacheResult(operating_map, key, "GENERATED")


__all__ = [
    "BearingOperatingMap",
    "BearingMapCache",
    "MapCacheResult",
    "BearingMapError",
    "BearingMapCancelled",
    "BearingMapCacheCorruption",
    "generate_operating_map",
    "canonical_bearing_hash",
    "solver_fingerprint",
    "solver_fingerprint_payload",
    "CACHE_SCHEMA",
    "MAP_CONTRACT",
    "NATIVE_ABI",
    "ROSS_AUTHORITY_SHA",
]
