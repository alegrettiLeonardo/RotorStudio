from __future__ import annotations
import numpy as np
from drm_core import RotorModel,Node,ShaftElement,TaperedShaftElement,AsymmetricShaftElement,Disk,Bearing,Force,BendPoint,RotorDefinition

E=211e9;G=81.2e9;RHO=7810.0

def stationary_model(force=None,bend=None,fluid=False):
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i,i+1,.05,0.,RHO,E,G,2e-5) for i in range(1,7)]
    disks=[Disk.geometric(3,RHO,.07,.28,.05),Disk.geometric(5,RHO,.07,.35,.05)]
    bearings=[Bearing(7,1,(525.,.1,.03,1e-4,.1)),Bearing(7,7,(525.,.1,.03,1e-4,.1))] if fluid else [Bearing(3,1,(1e6,1e6,100.,100.)),Bearing(3,7,(1e6,1e6,100.,100.))]
    return RotorModel(nodes,shafts,disks,bearings,force or [],bend or [])

def auxiliary_model(): return stationary_model([Force(6,(4,1e-4,.25))])
def foundation_freq_model(): return stationary_model([Force(4,(0.,1e-5,0.,2e-5))])
def foundation_time_model():
    m=stationary_model([Force(5,(0.,1e-3,0.,1e-3,.025))])
    m.shafts=[ShaftElement(x.shaft_type,x.node1,x.node2,x.outer_diameter_m,x.inner_diameter_m,x.rho_kg_m3,x.E_pa,x.G_pa,0.,x.axial_force_n,x.torque_nm) for x in m.shafts]
    return m
def response_model():
    return stationary_model([Force(1,(3,2.2e-4,.37)),Force(2,(5,1.3e-5,-.21)),Force(3,()),Force(8,(2,6,8.5,.12))],[BendPoint(1,2e-5,-1e-5),BendPoint(7,-1.5e-5,.5e-5)])

def coaxial_model():
    E0=2.07e11;G0=79.6e9;rho=8300.;z=[0.,.22,.46,0.,.20,.44]
    nodes=[Node(i+1,x) for i,x in enumerate(z)]
    shafts=[ShaftElement(2,1,2,.04,0.,rho,E0,G0),ShaftElement(2,2,3,.04,0.,rho,E0,G0),ShaftElement(2,4,5,.035,0.,rho,E0,G0),ShaftElement(2,5,6,.035,0.,rho,E0,G0)]
    disks=[Disk.inertial(2,7.,.025,.05),Disk.inertial(5,5.,.018,.036)]
    bearings=[Bearing(3,1,(7e6,7e6,80.,80.)),Bearing(3,3,(7e6,7e6,80.,80.)),Bearing(3,4,(6e6,6e6,70.,70.)),Bearing(3,6,(6e6,6e6,70.,70.)),Bearing(20,2,(5,1.2e6,1.1e6,100.,90.))]
    return RotorModel(nodes,shafts,disks,bearings,[Force(1,(5,1.1e-4,.3))],rotors=[RotorDefinition(1,3,1.),RotorDefinition(4,6,-.7)])

def asymmetric_model():
    return RotorModel([Node(1,0.),Node(2,.3),Node(3,.6)],[AsymmetricShaftElement(12,1,2,1.2e5,1e5,.08,.09,12.,.004),AsymmetricShaftElement(12,2,3,1.2e5,1e5,.08,.09,12.,.004)],[Disk.anisotropic(2,8.,.03,.04,.05)],[Bearing(4,1,(1e6,1e6,2e4,2e4,100.,100.,5.,5.)),Bearing(4,3,(1e6,1e6,2e4,2e4,100.,100.,5.,5.))],[Force(1,(2,1e-4,.2)),Force(2,(2,2e-5,-.1))])

def runup_model():
    E0=211e9;G0=E0/(2*(1+.3));rho=7810.;nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i,i+1,.025,0.,rho,E0,G0,0.) for i in range(1,7)]
    return RotorModel(nodes,shafts,[Disk.geometric(7,rho,.04,.25,0.)],[Bearing(3,1,(1e7,2e7,4e5,4e5)),Bearing(3,5,(1e7,2e7,4e5,4e5))],[Force(1,(7,1e-3,0.))])
