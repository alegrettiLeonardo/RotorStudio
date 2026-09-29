"""A4 immutable authority: frozen ROSS simple Newmark, explicit four-DOF conversion."""
import argparse,json,sys,platform
from pathlib import Path
from datetime import datetime,timezone
from generate_reference import verify_checkout,ROSS_SHA,digest,json_write,git

def generate(root,out):
    root=verify_checkout(root);out=Path(out)
    if out.exists():raise FileExistsError(out)
    sys.path.insert(0,str(root))
    import ross as rs
    import numpy as np
    import scipy
    from ross.utils import convert_6dof_to_4dof,remove_dofs
    assert Path(rs.__file__).resolve()==root/'ross/__init__.py'
    specs={};records={}
    names=['harmonic','pulse','arbitrary','multiple_dofs','moment','cross_coupled','gravity','nonuniform','linear_ramp','nonlinear_speed','speed_axis','frequency_axis','map_2d','zero_force','constant_mass','alternate_parameters']
    for name in names:
        source=name if name in ('cross_coupled','speed_axis','frequency_axis','map_2d') else 'fixed_speed'
        s=json.loads((Path(__file__).parent/'frf'/f'{source}.json').read_text())
        for key in ['free_free','frequencies','speed']:s.pop(key,None)
        for b in s['bearings']:
            for key in ('mxx','myy','mxy','myx'):b.pop(key,None)
        if name=='constant_mass':
            for b in s['bearings']:b.update(mxx=.7,myy=.9)
        if name=='moment':s['inner']=0.0
        t=np.round(np.linspace(0,.04,81),12)
        if name=='nonuniform':t=np.round(.04*np.linspace(0,1,81)**1.3,12)
        variable=name in ('linear_ramp','nonlinear_speed','speed_axis','frequency_axis','map_2d','nonuniform')
        speed=np.round(80+1200*t/.04,9) if variable else 183.
        if name in ('nonlinear_speed','map_2d','nonuniform'):speed=np.round(70+600*np.sin(1.4*np.pi*t/.04)**2,9)
        s.update(time_s=t.tolist(),speed=speed.tolist() if variable else speed,weight=name=='gravity',gamma=.5,beta=.25,tol=1e-6)
        if name=='alternate_parameters':s.update(gamma=.6,beta=.3025)
        mat=rs.Material(name='a4',rho=s['rho'],E=s['E'],G_s=s['G'])
        shafts=[rs.ShaftElement(L=L,idl=s['inner'],odl=d,material=mat,shear_effects=True,rotary_inertia=True,gyroscopic=True) for L,d in zip(s['lengths'],s['diameters'])]
        x=s['disk'];disks=[rs.DiskElement(n=x['node'],m=x['mass'],Id=x['Id'],Ip=x['Ip'])]
        bearings=[rs.BearingElement(n=b['node'],**{k:v for k,v in b.items() if k!='node'}) for b in s['bearings']]
        rotor=convert_6dof_to_4dof(rs.Rotor(shafts,disks,bearings));n=rotor.ndof;F=np.zeros((len(t),n))
        if name=='pulse':F[:,4]=np.where((t>=.004)&(t<=.009),137.,0.)
        elif name=='moment':F[:,6]=17*np.sin(317*t)+11*(t>.012)
        elif name not in ('gravity','zero_force'):
            F[:,4]=137*np.sin(317*t)
            if name!='harmonic':
                F[:,9]=-23+89*t/.04+31*np.sin(227*t)**3
                F[:,6]=17*np.cos(113*t)-31*t/.04
                F[:,15]=-11*np.sin(733*t)+7*(t>.013)
        F=np.round(F,10);s['force_real']=F.T.tolist()
        M=rotor.M();G=rotor.G();S=rotor.Ksdt();omega=np.full(len(t),speed) if not variable else speed
        alpha=np.gradient(omega,t) if variable else np.zeros(len(t))
        C=np.stack([rotor.C(w) for w in omega],axis=2);K=np.stack([rotor.K(w) for w in omega],axis=2)
        Ce=C+G[:,:,None]*omega;Ke=K+S[:,:,None]*alpha
        Fg=rotor.gravitational_force();Fe=F+Fg if s['weight'] else F.copy()
        result=rotor.run_time_response(speed,F.copy(),t,method='newmark',newmark_type='simple',weight=s['weight'],gamma=s['gamma'],beta=s['beta'],tol=s['tol'])
        Ks=np.zeros_like(S);Kd=np.zeros_like(S)
        for i,e in enumerate(shafts):Ks[4*i:4*i+8,4*i:4*i+8]+=remove_dofs(e.Kst())
        for e in disks:Kd[4*e.n:4*e.n+4,4*e.n:4*e.n+4]+=remove_dofs(e.Kdt())
        arrays=dict(M=M,G=G,Ksdt=S,Kshaft=Ks,Kdisk=Kd,C=C,K=K,Ceff=Ce,Keff=Ke,F=Fe.T,F_external=F.T,Fg=Fg,alpha=alpha,q=result.yout.T)
        assert all(np.isfinite(v).all() for v in arrays.values());specs[name]=s;records[name]=arrays
    # Element-only sentinels independent of the assembled time histories.
    elems=dict(shafts=[[.11,.041,0.,7810.],[.37,.087,.019,8050.],[.63,.061,.023,7500.]],disks=[0.,.017,.139,.811])
    element_arrays={}
    for i,(L,od,idd,rho) in enumerate(elems['shafts']):
        element_arrays[f'shaft_{i}']=remove_dofs(rs.ShaftElement(L,idd,od,material=rs.Material(name=f's{i}',rho=rho,E=211e9,G_s=81.2e9)).Kst())
    for i,Ip in enumerate(elems['disks']):element_arrays[f'disk_{i}']=remove_dofs(rs.DiskElement(n=0,m=7,Id=.5,Ip=Ip).Kdt())
    out.mkdir(parents=True)
    for name,s in specs.items():json_write(out/f'{name}.json',s);np.savez_compressed(out/f'{name}.npz',**records[name])
    json_write(out/'elements.json',elems);np.savez_compressed(out/'elements.npz',**element_arrays)
    json_write(out/'authority.json',dict(repository='petrobras/ross',commit=ROSS_SHA,python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,generated_utc=datetime.now(timezone.utc).isoformat(),method='newmark',newmark_type='simple',dof_mapping='convert_6dof_to_4dof before solve: [x,y,alpha,beta]',source_sha256={p:digest(root/p) for p in git(root,'ls-files','ross','LICENSE.md').splitlines() if (root/p).is_file()},files_sha256={p.name:digest(p) for p in out.iterdir()}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ross-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.ross_root,a.out)
