"""Validation file-driver access; no time integration in Python."""
import os,subprocess,io
from pathlib import Path
import numpy as np
from drm_core.solver.backend import FortranBackend
from drm_core.solver.general_frf_backend import prepare

def probe(m,s):
    b=FortranBackend();t=np.asarray(s['time_s']);om=np.broadcast_to(s['speed'],t.shape).copy()
    z,sh,di,nodes,coef,*_=prepare(b,m,om,vector_response=True)
    text=' '.join(map(str,[len(z),sh.shape[1],di.shape[1],len(nodes),len(t),int(np.ndim(s['speed'])>0),int(s['weight']),s['gamma'],s['beta'],s['tol']]))+'\n'
    for a in (z,sh,di,nodes,t,om,coef,s['force_real']):text+=' '.join(map(str,np.asarray(a).ravel(order='F')))+'\n'
    exe=Path(os.environ['DRMROTOR_LIB']).parent/('time_probe.exe' if os.name=='nt' else 'time_probe')
    result=subprocess.run([str(exe)],input=text,text=True,capture_output=True,check=True)
    out=np.loadtxt(io.StringIO(result.stdout)).reshape(len(t),len(z)*4,3)
    return tuple(out[:,:,i].T for i in range(3))
