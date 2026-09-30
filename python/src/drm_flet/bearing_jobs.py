"""Standalone bearing field/map jobs over the unchanged native B14/B16 APIs."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
import numpy as np
from drm_core import AnalysisCancelled,AnalysisExecution,analysis_hash,collect_build_metadata
from drm_core.solver.facade import SolverFacade
from drm_core.solver.bearing_maps import BearingMapCache,BearingMapCancelled,MapCacheResult
from drm_core.solver.bearings_backend import BearingCancelledError

@dataclass(frozen=True)
class BearingFieldResult:
    payload: dict
    speed_rad_s: float
    frequency_rad_s: float
    bearing_index: int
    bearing_kind: str = 'advanced_bearings'

@dataclass(frozen=True)
class BearingMapResult:
    cached: MapCacheResult
    bearing_index: int
    cache_root: str
    bearing_kind: str = 'advanced_bearings'

_CACHES={}

def map_cache(root=None):
    root=str(Path(root or os.environ.get('ROTORSTUDIO_BEARING_CACHE') or Path.home()/'.cache'/'RotorStudio'/'bearing_maps').resolve())
    return _CACHES.setdefault(root,BearingMapCache(root))


def execute_bearing_extension(job):
    options=job.case.options;scope=options['flet_scope'];model=job.project.model
    readiness=job.project.metadata.get('numerical_readiness') or {}
    if str(readiness.get('status','READY')).upper() not in {'READY','QUALIFIED','PASS'}:
        raise ValueError(f'Projeto bloqueado: {readiness}')
    if options.get('bearing_kind','advanced_bearings')!='advanced_bearings':raise ValueError('Campos/mapas requerem um mancal avançado tipado.')
    idx=int(options['bearing_index'])
    if idx<0 or idx>=len(model.advanced_bearings):raise ValueError('Índice de mancal fora do projeto.')
    bearing=model.advanced_bearings[idx];facade=SolverFacade(job.library_path);provider=facade.backend._bearing_provider()
    job.native_control=provider;provider.reset_job_control()
    if job.cancel_event.is_set():raise AnalysisCancelled('Cancelado antes da avaliação física.')
    try:
        if scope=='bearing_fields':
            speed=float(options['speed_rad_s']);frequency=float(options['frequency_rad_s'])
            payload=facade.advanced_bearing_fields(bearing,speed,frequency,reset_job_control=False)
            result=BearingFieldResult(payload,speed,frequency,idx);job.progress(1,1)
        elif scope=='operating_map':
            cache=map_cache(options.get("cache_root"));speeds=np.asarray(options['speeds_rad_s'],dtype=float)
            freq=options.get('frequencies_rad_s') or None
            if len(speeds)*(len(freq) if freq is not None else 1)>4096:raise ValueError('Mapa limitado a 4096 pontos físicos por execução.')
            result0=cache.get_or_generate(bearing,speeds,freq,interpolation=options.get('interpolation','pchip'),backend=provider,
                      progress_callback=lambda done,total,details:job.progress(done,total),cancel_check=job.cancel_event.is_set)
            result=BearingMapResult(result0,idx,str(cache.root));total=len(speeds)*(len(freq) if freq else 1);job.progress(total,total)
        else:raise ValueError(f'Escopo de mancal desconhecido: {scope}')
    except (BearingCancelledError,BearingMapCancelled) as exc:raise AnalysisCancelled(str(exc)) from exc
    ah=analysis_hash(model,job.case,options);meta=collect_build_metadata(job.library_path,options)
    meta.update(model_hash=model.model_hash(),analysis_hash=ah,scope=scope,backend='native drmbearings / unchanged Core')
    return AnalysisExecution(job.case,result,ah,meta)
