"""A2 authorities: pinned ROSS only, explicit lateral conversion, immutable output."""
import argparse,json,sys,copy,platform
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
    base=dict(lengths=[.21,.27,.19],diameters=[.052,.061,.047],inner=.014,rho=7810.,E=211e9,G=81.2e9,shaft_type=2,
        disk=dict(node=2,mass=7.3,Id=.021,Ip=.039),frequencies=[0.,.01,43.,117.,261.,503.],speed=None,free_free=False,
        bearings=[dict(node=n,kxx=1.13e6,kyy=1.13e6,cxx=173.,cyy=173.) for n in (0,3)])
    specs={}
    for name in ['synchronous','fixed_speed','anisotropic','cross_coupled','free_free','speed_axis','frequency_axis','map_2d']:
        s=copy.deepcopy(base)
        if name!='synchronous':s['speed']=183.
        if name=='free_free':s['free_free']=True
        if name in ('anisotropic','cross_coupled'):
            for b in s['bearings']:b.update(kyy=1.79e6,cyy=231.)
        if name=='cross_coupled':
            for b in s['bearings']:b.update(kxy=17300.,kyx=-29400.,cxy=13.,cyx=-7.)
        if name in ('speed_axis','frequency_axis','map_2d'):
            axis=[0.,100.,300.,600.]
            for b in s['bearings']:
                b['interpolation']='pchip'
                if name!='frequency_axis':b['speed']=axis
                if name!='speed_axis':b['frequency']=axis
                def values(base,ds,df):
                    if name=='map_2d':return [[base+ds*x+df*y+.003*x*y for y in axis] for x in axis]
                    return [base+(ds if name=='speed_axis' else df)*x for x in axis]
                for k,v,ds,df in [('kxx',1.13e6,311.,127.),('kyy',1.79e6,223.,79.),('cxx',173.,.11,.07),('cyy',231.,.09,.03),('mxx',.7,.0003,.0001),('myy',.9,.0002,.0007)]:b[k]=values(v,ds,df)
                b.update(kxy=17300.,kyx=-29400.,cxy=13.,cyx=-7.)
            s['frequencies']=[0.,43.,117.,261.,503.,650.]
        specs[name]=s
    records={}
    for name,s in specs.items():
        mat=rs.Material(name='a2',rho=s['rho'],E=s['E'],G_s=s['G'])
        shafts=[rs.ShaftElement(L=L,idl=s['inner'],odl=d,material=mat,shear_effects=True,rotary_inertia=True,gyroscopic=True) for L,d in zip(s['lengths'],s['diameters'])]
        x=s['disk'];disks=[rs.DiskElement(n=x['node'],m=x['mass'],Id=x['Id'],Ip=x['Ip'])]
        bearings=[rs.BearingElement(n=b['node'],**{k:v for k,v in b.items() if k!='node'}) for b in s['bearings']]
        rotor=convert_6dof_to_4dof(rs.Rotor(shafts,disks,bearings))
        result=rotor.run_freq_response(speed_range=s['frequencies'],speed=s['speed'],free_free=s['free_free'])
        arrays={k:np.zeros((rotor.ndof,rotor.ndof,len(s['frequencies'])),dtype=complex if k=='D' else float) for k in ['M','C','G','K','Mb','Cb','Kb','D']}
        for i,w in enumerate(s['frequencies']):
            speed=0. if s['free_free'] else (w if s['speed'] is None else s['speed'])
            M=rotor.M(w,speed);C=rotor.C(w,speed);G=rotor.G();K=rotor.K(w,speed)
            for k,v in [('M',M),('C',C),('G',G),('K',K),('D',-w*w*M+1j*w*(C+speed*G)+K)]:arrays[k][:,:,i]=v
            for b in bearings:
                dofs=[4*b.n,4*b.n+1]
                for key,fn in [('Mb',b.M),('Cb',b.C),('Kb',b.K)]:arrays[key][np.ix_(dofs,dofs,[i])]=np.asarray(fn(w,speed))[:2,:2,None]
        arrays.update(H_disp=result.freq_resp,H_vel=result.velc_resp,H_acc=result.accl_resp)
        assert all(np.isfinite(a).all() for a in arrays.values())
        records[name]=arrays
    out.mkdir(parents=True)
    for n,s in specs.items():json_write(out/f'{n}.json',s);np.savez(out/f'{n}.npz',**records[n])
    json_write(out/'authority.json',dict(repository='petrobras/ross',commit=ROSS_SHA,python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,generated_utc=datetime.now(timezone.utc).isoformat(),dof_mapping='[x,y,z,alpha,beta,theta] -> [x,y,alpha,beta] via convert_6dof_to_4dof before solve',source_sha256={p:digest(root/p) for p in git(root,'ls-files','ross','LICENSE.md').splitlines() if (root/p).is_file()},files_sha256={p.name:digest(p) for p in out.iterdir()}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ross-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.ross_root,a.out)
