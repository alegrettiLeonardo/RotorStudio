import argparse,json,numpy as np
from drm_core.domain.model import RotorModel
from drm_core.analysis.modal import run_modal
from drm_core.analysis.frequency_response import run_frequency_response,run_auxiliary_frequency_response,run_foundation_frequency_response
from drm_core.analysis.critical_speed import run_critical_speeds
from drm_core.analysis.coaxial import run_coaxial_modal,run_coaxial_frequency_response
from drm_core.analysis.asymmetric import run_asymmetric_modal,run_asymmetric_frequency_response
from drm_core.units import rpm_to_rad_s,rad_s_to_rpm

def _load(path):
    with open(path,encoding='utf-8') as f:data=json.load(f)
    return RotorModel.from_legacy_arrays(data['node'],data['shaft'],data.get('disc',[]),data.get('bearing',[]),data.get('force',[]),data.get('bend',[]),data.get('rotors',[]))
def main():
    p=argparse.ArgumentParser(prog='drm-cli');sp=p.add_subparsers(dest='cmd',required=True)
    v=sp.add_parser('validate');v.add_argument('model');v.add_argument('--analysis',choices=['stationary','coaxial','rotating'],default='stationary')
    m=sp.add_parser('modal');m.add_argument('model');m.add_argument('--speed-rpm',type=float,default=0);m.add_argument('--lib')
    f=sp.add_parser('frequency-response');f.add_argument('model');f.add_argument('--start-rpm',type=float,required=True);f.add_argument('--stop-rpm',type=float,required=True);f.add_argument('--step-rpm',type=float,required=True);f.add_argument('--lib')
    c=sp.add_parser('critical-speeds');c.add_argument('model');c.add_argument('--nx',type=float,default=1);c.add_argument('--count',type=int,default=5);c.add_argument('--undamped',action='store_true');c.add_argument('--method',type=int,choices=[1,2,3]);c.add_argument('--initial-rpm',type=float,nargs='*');c.add_argument('--lib')
    aux=sp.add_parser('auxiliary-frequency-response');aux.add_argument('model');aux.add_argument('--rotor-speed-rpm',type=float,required=True);aux.add_argument('--start-hz',type=float,required=True);aux.add_argument('--stop-hz',type=float,required=True);aux.add_argument('--step-hz',type=float,required=True);aux.add_argument('--direction',type=float,default=1);aux.add_argument('--lib')
    fdn=sp.add_parser('foundation-frequency-response');fdn.add_argument('model');fdn.add_argument('--rotor-speed-rpm',type=float,required=True);fdn.add_argument('--start-hz',type=float,required=True);fdn.add_argument('--stop-hz',type=float,required=True);fdn.add_argument('--step-hz',type=float,required=True);fdn.add_argument('--lib')
    cm=sp.add_parser('coaxial-modal');cm.add_argument('model');cm.add_argument('--speed-rpm',type=float,default=0);cm.add_argument('--lib')
    cf=sp.add_parser('coaxial-frequency-response');cf.add_argument('model');cf.add_argument('--start-rpm',type=float,required=True);cf.add_argument('--stop-rpm',type=float,required=True);cf.add_argument('--step-rpm',type=float,required=True);cf.add_argument('--lib')
    am=sp.add_parser('asymmetric-modal');am.add_argument('model');am.add_argument('--speed-rpm',type=float,default=0);am.add_argument('--with-eigenvectors',action='store_true');am.add_argument('--lib')
    af=sp.add_parser('asymmetric-frequency-response');af.add_argument('model');af.add_argument('--start-rpm',type=float,required=True);af.add_argument('--stop-rpm',type=float,required=True);af.add_argument('--step-rpm',type=float,required=True);af.add_argument('--lib')
    a=p.parse_args();model=_load(a.model)
    if a.cmd=='validate':
        from drm_core.validation.model import validate_model;validate_model(model,analysis=a.analysis);print('PASS')
    elif a.cmd=='modal':
        r=run_modal(model,rpm_to_rad_s(a.speed_rpm),a.lib);print('\n'.join(f'{x.real:.12e} {x.imag:+.12e}j' for x in r.eigenvalues))
    elif a.cmd=='frequency-response':
        rpm=np.arange(a.start_rpm,a.stop_rpm+0.5*a.step_rpm,a.step_rpm);r=run_frequency_response(model,rpm_to_rad_s(rpm),a.lib)
        for j,s in enumerate(rpm):print(f'{s:.8g},'+','.join(f'{abs(x):.12e}' for x in r.response[:,j]))
    elif a.cmd=='auxiliary-frequency-response':
        hz=np.arange(a.start_hz,a.stop_hz+0.5*a.step_hz,a.step_hz);r=run_auxiliary_frequency_response(model,rpm_to_rad_s(a.rotor_speed_rpm),2*np.pi*hz,a.direction,a.lib)
        for j,xv in enumerate(hz):print(f'{xv:.8g},'+','.join(f'{abs(v):.12e}' for v in r.response[:,j]))
    elif a.cmd=='foundation-frequency-response':
        hz=np.arange(a.start_hz,a.stop_hz+0.5*a.step_hz,a.step_hz);r=run_foundation_frequency_response(model,rpm_to_rad_s(a.rotor_speed_rpm),2*np.pi*hz,a.lib)
        for j,xv in enumerate(hz):print(f'{xv:.8g},'+','.join(f'{abs(v):.12e}' for v in r.response[:,j]))
    elif a.cmd=='critical-speeds':
        kw=dict(NX=a.nx,damped=not a.undamped,ncrit=a.count)
        if a.method is not None:kw['method']=a.method
        if a.initial_rpm is not None:kw['initial_estimates']=rpm_to_rad_s(np.asarray(a.initial_rpm,float))
        r=run_critical_speeds(model,a.lib,**kw)
        for x in r.critical_speeds_rad_s:print(f'{x:.12e} rad/s  {rad_s_to_rpm(x):.8f} rpm')
    elif a.cmd=='coaxial-modal':
        r=run_coaxial_modal(model,rpm_to_rad_s(a.speed_rpm),a.lib);print('\n'.join(f'{x.real:.12e} {x.imag:+.12e}j' for x in r.eigenvalues))
    elif a.cmd=='coaxial-frequency-response':
        rpm=np.arange(a.start_rpm,a.stop_rpm+0.5*a.step_rpm,a.step_rpm);r=run_coaxial_frequency_response(model,rpm_to_rad_s(rpm),a.lib)
        for j,s in enumerate(rpm):print(f'{s:.8g},'+','.join(f'{abs(x):.12e}' for x in r.response[:,j]))
    elif a.cmd=='asymmetric-modal':
        r=run_asymmetric_modal(model,rpm_to_rad_s(a.speed_rpm),a.lib,a.with_eigenvectors);print('\n'.join(f'{x.real:.12e} {x.imag:+.12e}j' for x in r.eigenvalues))
    elif a.cmd=='asymmetric-frequency-response':
        rpm=np.arange(a.start_rpm,a.stop_rpm+0.5*a.step_rpm,a.step_rpm);r=run_asymmetric_frequency_response(model,rpm_to_rad_s(rpm),a.lib)
        for j,s in enumerate(rpm):print(f'{s:.8g},'+','.join(f'{abs(x):.12e}' for x in r.response[:,j]))
if __name__=='__main__':main()
