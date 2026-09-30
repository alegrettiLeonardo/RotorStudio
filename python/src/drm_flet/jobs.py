"""Serialized native jobs; no widgets or substitute numerical solvers."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, Future
from copy import deepcopy
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from threading import Event, Lock
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import io
import json
import zipfile
import uuid
import numpy as np
from drm_core import AnalysisService, AnalysisExecution, AnalysisCase, AnalysisCancelled, analysis_hash, collect_build_metadata
from drm_core.solver.facade import SolverFacade
from drm_core.validation.model import validate_model
from drm_core.stage1 import write_analysis_report
from .session import EntityRef

# Native bearing/Fortran state must not be re-entered, including across web sessions.
_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rotorstudio-native")
_CONTROL_LOCK = Lock()
_ACTIVE_JOB = None

@dataclass(frozen=True)
class BearingSweep:
    speeds_rad_s: np.ndarray
    K: np.ndarray
    C: np.ndarray
    M: np.ndarray
    node: int
    label: str
    constrained: bool = False

@dataclass
class ResultRecord:
    execution: AnalysisExecution
    model: object
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class NativeJob:
    def __init__(self, project, case, library_path=None):
        self.project, self.case = deepcopy(project), deepcopy(case)
        self.cancel_event = Event()
        self.lock = Lock()
        self.completed, self.total = 0, 0
        self.state, self.error = "QUEUED", ""
        self.library_path = library_path
        self.native_control = None
        self.future: Future = _POOL.submit(self._run)

    def cancel(self):
        self.cancel_event.set()
        # Never send cancellation to the next job or another web session.
        with _CONTROL_LOCK:
            if _ACTIVE_JOB is self and self.native_control is not None:
                self.native_control.request_cancel()

    def native_progress(self):
        with _CONTROL_LOCK:
            if _ACTIVE_JOB is self and self.native_control is not None:
                return self.native_control.job_progress()
        return None

    def progress(self, completed, total):
        with self.lock: self.completed, self.total = int(completed), int(total)

    def _run(self):
        global _ACTIVE_JOB
        try:
            with _CONTROL_LOCK: _ACTIVE_JOB = self
            if self.cancel_event.is_set(): raise AnalysisCancelled("Cancelado antes de iniciar.")
            self.state = "RUNNING"
            # The frozen ABI passes only the position vector, not a node-ID map.
            # Preserve editable IDs, but never silently pass nonconsecutive IDs
            # to a native array-indexed solver (nor renumber physical references).
            ids=[n.number for n in self.project.model.nodes]
            if ids!=list(range(1,len(ids)+1)) or not ids:
                raise ValueError(f"Nós recebidos: {ids}. A ABI desta interface requer IDs consecutivos 1..N na ordem da lista. Corrija numeração e referências antes de executar; nenhum nó foi renumerado automaticamente.")
            from .editing import validate_editable_model
            validate_editable_model(self.project.model)
            if self.case.options.get("flet_scope") == "bearing_sweep":
                execution = self._bearings()
            elif self.case.options.get("flet_scope") in ("bearing_fields","operating_map"):
                from .bearing_jobs import execute_bearing_extension
                execution = execute_bearing_extension(self)
            else:
                execution = AnalysisService(self.library_path).execute(
                    self.project, self.case, progress_callback=self.progress, cancel_check=self.cancel_event.is_set)
            if self.cancel_event.is_set():
                raise AnalysisCancelled("Cancelado em ponto seguro; a chamada nativa em curso foi concluída.")
            self.state = "COMPLETED"
            return ResultRecord(execution, deepcopy(self.project.model))
        except AnalysisCancelled as e:
            self.state, self.error = "CANCELLED", str(e)
            raise
        except Exception as e:
            self.state, self.error = "FAILED", f"{type(e).__name__}: {e}"
            raise
        finally:
            with _CONTROL_LOCK:
                if _ACTIVE_JOB is self: _ACTIVE_JOB = None

    def _bearings(self):
        readiness = self.project.metadata.get("numerical_readiness") or {}
        if str(readiness.get("status", "READY")).upper() not in {"READY", "QUALIFIED", "PASS"}:
            raise ValueError(f"Projeto bloqueado para análise: {readiness}")
        model = self.project.model
        validate_model(model, analysis="coaxial" if model.rotors else "stationary")
        opt = self.case.options
        ref = EntityRef(str(opt["bearing_kind"]), int(opt["bearing_index"]))
        if ref.kind not in ("bearings", "advanced_bearings"): raise ValueError("Seleção de mancal inválida")
        bearing = getattr(model, ref.kind)[ref.index]
        speeds = np.asarray(opt["speeds_rad_s"], dtype=float)
        if speeds.ndim != 1 or not speeds.size or not np.all(np.isfinite(speeds)):
            raise ValueError("Rotações do mancal devem ser um vetor finito não vazio.")
        facade = SolverFacade(self.library_path)
        kval, cval, mval = [], [], []
        constrained = False
        for j, speed in enumerate(speeds):
            if self.cancel_event.is_set(): raise AnalysisCancelled("Varredura de mancal cancelada entre pontos.")
            if ref.kind == "advanced_bearings":
                result = facade.advanced_bearing(bearing, float(speed), float(speed))
                k, c, m = result.K, result.C, result.M
            else:
                isolated = deepcopy(model)
                isolated.bearings = [bearing]; isolated.advanced_bearings = []
                m0, c0, k0, mask, _ = facade.bearings(isolated, float(speed))
                i = next(i for i, n in enumerate(model.nodes) if n.number == bearing.node)
                sl = slice(4 * i, 4 * i + 2)
                m, c, k = m0[sl, sl], c0[sl, sl], k0[sl, sl]
                constrained = bool(np.any(mask[sl]))
            kval.append(np.asarray(k)[:2, :2].copy())
            cval.append(np.asarray(c)[:2, :2].copy())
            mval.append(np.asarray(m)[:2, :2].copy())
            self.progress(j + 1, speeds.size)
        result = BearingSweep(speeds, np.asarray(kval), np.asarray(cval), np.asarray(mval),
                              bearing.node, getattr(bearing, "tag", "") or f"Nó {bearing.node}", constrained)
        ah = analysis_hash(model, self.case, self.case.options)
        meta = collect_build_metadata(self.library_path, self.case.options)
        meta.update(model_hash=model.model_hash(), analysis_hash=ah,
                    scope="selected-bearing radial K/C/M; synchronous coefficient evaluation")
        return AnalysisExecution(self.case, result, ah, meta)


def arrays_of(value, prefix="result"):
    """Flatten results without pickle/object arrays; preserve complex eigenvectors."""
    result = {}
    if isinstance(value, np.ndarray):
        if value.dtype.kind != "O": result[prefix] = value
    elif is_dataclass(value):
        for f in fields(value):
            if f.name != "metadata": result.update(arrays_of(getattr(value, f.name), prefix + "." + f.name))
    elif isinstance(value, dict):
        for k,v in value.items(): result.update(arrays_of(v,prefix+"."+str(k)))
    elif isinstance(value, (tuple,list)):
        for i, v in enumerate(value): result.update(arrays_of(v, f"{prefix}.{i}"))
    elif isinstance(value, (int,float,complex,str,bool)):
        result[prefix] = np.asarray(value)
    return result


def csv_bytes(record: ResultRecord) -> bytes:
    """Long-form numeric export: quantity, ndarray index and real/imaginary parts.

    Array field names retain Core units, with an explicit metadata companion in
    report bundles. No magnitude-only conversion silently drops phase.
    """
    stream = io.StringIO(newline="")
    w = csv.writer(stream)
    w.writerow(["quantity", "array_index", "real_or_value", "imaginary"])
    for key, array in arrays_of(record.execution.result).items():
        for index in np.ndindex(array.shape):
            value = array[index]
            if np.iscomplexobj(value): w.writerow([key, ":".join(map(str,index)), value.real, value.imag])
            else: w.writerow([key, ":".join(map(str,index)), value, ""])
    return stream.getvalue().encode("utf-8-sig")


def npz_bytes(record: ResultRecord) -> bytes:
    stream = io.BytesIO()
    arrays = arrays_of(record.execution.result)
    arrays["analysis_hash"] = np.asarray(record.execution.analysis_hash)
    arrays["case_json"] = np.asarray(json.dumps(record.execution.case.canonical_dict()))
    np.savez_compressed(stream, **arrays)
    return stream.getvalue()


def report_bytes(record, *, current: bool, png: bytes | None = None) -> bytes:
    """Existing Core report + provenance/status + actual numeric exports."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        with TemporaryDirectory() as d:
            report = write_analysis_report(record.execution, d, stem="analysis")
            for path in report.values(): archive.writestr(Path(path).name, Path(path).read_bytes())
        archive.writestr("data.csv", csv_bytes(record))
        archive.writestr("data.npz", npz_bytes(record))
        archive.writestr("result_context.json", json.dumps({
            "current_against_open_project": current, "status": "CURRENT" if current else "OUTDATED",
            "result_model_hash": record.model.model_hash(), "created_utc": record.created_utc,
            "view_selection": getattr(record,"view_selection",{}),
            "note": "COMPLETED in the Core report describes execution, not freshness against later edits."}, indent=2))
        if png is not None: archive.writestr("plot.png", png)
    return output.getvalue()
