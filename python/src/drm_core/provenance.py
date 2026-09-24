from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json, os, platform
from importlib.metadata import version, PackageNotFoundError

def _json_default(x):
    if hasattr(x,'tolist'): return x.tolist()
    if hasattr(x,'__dict__'): return vars(x)
    return str(x)

def stable_hash(value)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=_json_default).encode()).hexdigest()

def analysis_hash(name:str,options:dict)->str:
    return stable_hash({'analysis':name,'options':options})

def build_information()->dict:
    try: pkg=version('drm-core')
    except PackageNotFoundError: pkg='unknown'
    return {
        'drm_core_version':pkg,
        'python':platform.python_version(),
        'platform':platform.platform(),
        'compiler':platform.python_compiler(),
        'drmrotor_lib':os.environ.get('DRMROTOR_LIB'),
    }

def result_metadata(model,analysis:str,options:dict|None=None,**extra)->dict:
    opts=dict(options or {})
    return {
        'solver_version':'0.5.0',
        'backend':'Fortran2018/ctypes',
        'model_hash':model.model_hash(),
        'analysis':analysis,
        'analysis_hash':analysis_hash(analysis,opts),
        'timestamp':datetime.now(timezone.utc).isoformat(),
        'options':opts,
        'build':build_information(),
        **extra,
    }
