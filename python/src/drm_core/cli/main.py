import argparse,json,numpy as np
from drm_core.domain.model import RotorModel
from drm_core.analysis.modal import run_modal
from drm_core.analysis.frequency_response import run_frequency_response
from drm_core.analysis.critical_speed import run_critical_speeds
from drm_core.units import rpm_to_rad_s,rad_s_to_rpm

def _load(path):
    with open(path,encoding='utf-8') as f:data=json.load(f)
    return RotorModel.from_legacy_arrays(data['node'],data['shaft'],data.get('disc',[]),data.get('bearing',[]),data.get('force',[]),data.get('bend',[]))
def main():
    p=argparse.ArgumentParser(prog='drm-cli');sp=p.add_subparsers(dest='cmd',required=True)
    v=sp.add_parser('validate');v.add_argument('model')
    m=sp.add_parser('modal');m.add_argument('model');m.add_argument('--speed-rpm',type=float,default=0);m.add_argument('--lib')
    f=sp.add_parser('frequency-response');f.add_argument('model');f.add_argument('--start-rpm',type=float,required=True);f.add_argument('--stop-rpm',type=float,required=True);f.add_argument('--step-rpm',type=float,required=True);f.add_argument('--lib')
    c=sp.add_parser('critical-speeds');c.add_argument('model');c.add_argument('--nx',type=float,default=1);c.add_argument('--count',type=int,default=5);c.add_argument('--undamped',action='store_true');c.add_argument('--lib')
    a=p.parse_args();model=_load(a.model)
    if a.cmd=='validate':
        from drm_core.validation.model import validate_model;validate_model(model);print('PASS')
    elif a.cmd=='modal':
        r=run_modal(model,rpm_to_rad_s(a.speed_rpm),a.lib);print('\n'.join(f'{x.real:.12e} {x.imag:+.12e}j' for x in r.eigenvalues))
    elif a.cmd=='frequency-response':
        rpm=np.arange(a.start_rpm,a.stop_rpm+0.5*a.step_rpm,a.step_rpm);r=run_frequency_response(model,rpm_to_rad_s(rpm),a.lib)
        for j,s in enumerate(rpm):print(f'{s:.8g},'+','.join(f'{abs(x):.12e}' for x in r.response[:,j]))
    elif a.cmd=='critical-speeds':
        r=run_critical_speeds(model,a.lib,NX=a.nx,damped=not a.undamped,ncrit=a.count)
        for x in r.critical_speeds_rad_s:print(f'{x:.12e} rad/s  {rad_s_to_rpm(x):.8f} rpm')
if __name__=='__main__':main()
