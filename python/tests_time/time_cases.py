import json
from pathlib import Path
import numpy as np
from drm_core.domain.model import RotorModel,Node,ShaftElement,Disk
from drm_core.domain.bearings import CoefficientBearing
ROOT=Path(__file__).resolve().parents[2]
NAMES=sorted(p.stem for p in (ROOT/'validation/ross_parity/time_response').glob('*.npz') if p.stem!='elements')
def case(name):
    s=json.loads((ROOT/f'validation/ross_parity/time_response/{name}.json').read_text())
    z=np.r_[0.,np.cumsum(s['lengths'])];x=s['disk']
    bs=[]
    for b in s['bearings']:
        p=dict(b);p['node']+=1
        p['speed_rad_s']=tuple(p.pop('speed',[]));p['frequency_rad_s']=tuple(p.pop('frequency',[]))
        bs.append(CoefficientBearing(**p))
    m=RotorModel([Node(i+1,float(v)) for i,v in enumerate(z)],
        [ShaftElement(2,i+1,i+2,d,s['inner'],s['rho'],s['E'],s['G']) for i,d in enumerate(s['diameters'])],
        [Disk.inertial(x['node']+1,x['mass'],x['Id'],x['Ip'])],advanced_bearings=bs)
    return m,s
