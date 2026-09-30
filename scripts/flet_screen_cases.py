"""Small explicit engineering inputs for Flet screen qualification (not goldens).

Coaxial/asymmetric inputs preserve the existing Stage 1 oracle-test fixtures;
the plain-journal case preserves the existing B14 field-test input. Outputs are
always obtained from the current, unchanged native solver, never this module.
"""
from __future__ import annotations
from dataclasses import replace
import numpy as np
from drm_core import (RotorModel,RotorProject,Node,ShaftElement,AsymmetricShaftElement,
    Disk,Bearing,Force,RotorDefinition,AnalysisCase)
from drm_core.domain.bearings import PlainJournalPhysicsBearing
from drm_flet.analysis_catalog import BY_KIND,default_values,build_case


def simple_model():
    return RotorModel(nodes=[Node(1,0.),Node(2,.25),Node(3,.5)],
        shafts=[ShaftElement(2,1,2,.04,0.,7800.,210e9,80e9),ShaftElement(2,2,3,.04,0.,7800.,210e9,80e9)],
        disks=[Disk.inertial(2,3.,.003,.006)],
        bearings=[Bearing(3,1,(1e6,1e6,100.,100.)),Bearing(3,3,(1e6,1e6,100.,100.))],
        forces=[Force(1,(2,.001,.2))])


def coax_model():
    E=2.05e11;G=7.9e10;rho=7800.
    return RotorModel(
        nodes=[Node(1,0),Node(2,.3),Node(3,.6),Node(4,0),Node(5,.3),Node(6,.6)],
        shafts=[ShaftElement(2,1,2,.045,.005,rho,E,G,1e-5),ShaftElement(2,2,3,.045,.005,rho,E,G,1e-5),
                ShaftElement(2,4,5,.04,.004,rho,E,G,1.2e-5),ShaftElement(2,5,6,.04,.004,rho,E,G,1.2e-5)],
        disks=[Disk.geometric(2,rho,.04,.20,.045),Disk.geometric(5,rho,.035,.18,.04)],
        bearings=[Bearing(3,1,(6e6,6e6,80.,80.)),Bearing(3,3,(6e6,6e6,80.,80.)),
                  Bearing(3,4,(5e6,5e6,70.,70.)),Bearing(3,6,(5e6,5e6,70.,70.)),Bearing(20,2,(5,1.2e6,1e6,150.,140.))],
        forces=[Force(1,(5,1.3e-4,.25))],rotors=[RotorDefinition(1,3,1.),RotorDefinition(4,6,-.7)])


def asymmetric_model():
    return RotorModel(nodes=[Node(1,0),Node(2,.3),Node(3,.6)],
        shafts=[AsymmetricShaftElement(12,1,2,1.2e5,1.e5,.08,.09,12.,.004),
                AsymmetricShaftElement(12,2,3,1.2e5,1.e5,.08,.09,12.,.004)],
        disks=[Disk.anisotropic(2,8.,.03,.04,.05)],
        bearings=[Bearing(4,1,(1e6,1e6,2e4,2e4,100.,100.,5.,5.)),Bearing(4,3,(1e6,1e6,2e4,2e4,100.,100.,5.,5.))],
        forces=[Force(1,(2,1e-4,.2)),Force(2,(2,2e-5,-.1))])


def screen_case(kind):
    model=coax_model() if kind.startswith('coaxial') else asymmetric_model() if kind.startswith('asymmetric') else simple_model()
    if kind=='auxiliary_frequency_response':model.forces=[Force(7,(2,10.,-2.))]
    if kind=='foundation_frequency_response':model.forces=[Force(4,(0.,1e-5,0.,2e-5))]
    if kind=='foundation_time_response':model.forces=[Force(5,(0.,1e-5,0.,2e-5,.003))]
    values=default_values(kind,model)
    for spec in BY_KIND[kind].inputs:
        if spec.kind=='grid':
            values[spec.key]['count']=5 if spec.key!='time_s' else 21
    if kind=='general_time_response':
        values['time_s']['stop']=.002
        values['loads']=[{'node':2,'dof':0,'shape':'Sine','values':'2; 100; 0.2'}]
        values['speed']='1000'
    if kind=='forced_response':values['loads']=[{'node':2,'dof':0,'real':'2.125','imag':'-0.75'},{'node':3,'dof':2,'real':'0.2','imag':'0.1'}]
    if kind=='runup':values.update(tspan='0;0.004',alpha='200;10;0')
    if kind=='foundation_time_response':values.update(npts=81,dt=.0001)
    if kind=='ucs':values.update(num=7,num_modes=8,stiffness_range_exponents='5;8')
    if kind=='level1':values.update(num=7)
    if kind=='critical_speeds':values.update(ncrit=2,method='2',with_mode_shapes=True)
    case=build_case(kind,values,model,'Flet_'+kind)
    return RotorProject(name='Qualificação · '+kind,model=model,analyses=[case]),case


def plain_bearing(node=1):
    return PlainJournalPhysicsBearing(node=node,weight_n=112814.90696191376,journal_diameter_m=.3999992,
        radial_clearance_m=.000194564,oil_viscosity_pa_s=.01901574061455835,
        pivot_angle_rad=(np.pi/2,3*np.pi/2),pad_arc_rad=(3.07177948351002,)*2,
        pad_axial_length_m=(.263144,)*2,preload=(0.,)*2,offset=(.5,)*2,
        total_e_x_film=8,total_e_z_film=4,total_e_y_film=4,total_e_y_pad=4,force_tolerance=5e-3,
        max_iterations=60,outer_iterations=12,thermal_type=None)


def bearing_case(scope,cache_root):
    model=simple_model();model.advanced_bearings=[plain_bearing()];model.bearings=[]
    opts=dict(flet_scope=scope,bearing_index=0,bearing_kind='advanced_bearings')
    if scope=='bearing_fields':opts.update(speed_rad_s=100.,frequency_rad_s=85.)
    else:opts.update(speeds_rad_s=[80.,100.,120.],frequencies_rad_s=[50.,100.],interpolation='linear',cache_root=str(cache_root))
    case=AnalysisCase('bearing_matrices',dict(speed_rad_s=100.),'Flet_'+scope,opts)
    return RotorProject('Mancal físico · B14',model,analyses=[case]),case
