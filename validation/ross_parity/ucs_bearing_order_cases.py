"""Explicit additive A5 bearing-order fixtures; data/builders only, no solver.

Node numbers in specifications are one-based. ROSS construction explicitly
converts them to its zero-based convention without sorting the input list.
"""
from copy import deepcopy

ROSS_SHA = '6320eab9f890f1b3cc1710d508b446fe063ca68d'
BASE_SHA = '03fef9b0da65c51b7ea3c9a14911cf7f83bcb015'
SPEED = [40.,120.,260.,480.,820.]
FREQUENCY = [30.,100.,230.,470.,830.]
FX = [4.6e6,7.8e6,1.33e7,2.11e7,3.28e7]
FY = [5.9e6,9.1e6,1.51e7,2.39e7,3.55e7]
GX = [[3.6e6,4.2e6,5.1e6,6.3e6,7.8e6],
      [5.1e6,5.9e6,7.0e6,8.5e6,1.03e7],
      [7.4e6,8.4e6,9.8e6,1.17e7,1.39e7],
      [1.04e7,1.17e7,1.35e7,1.58e7,1.86e7],
      [1.47e7,1.63e7,1.86e7,2.15e7,2.50e7]]
GY = [[1.18*x+2e5 for x in row] for row in GX]


def specifications():
    low = dict(node=1,kxx=12.5e6,kyy=12.5e6,tag='lower-first')
    high = dict(node=4,kxx=21e6,kyy=36e6,tag='higher')
    def case(family='legacy3', supports=None, **kwargs):
        return dict(family=family,supports=deepcopy(supports or [high,low]),
                    synchronous=kwargs.get('synchronous',False),
                    bearing_speed_range=kwargs.get('bearing_speed_range'))
    anis = dict(low,kxx=10.5e6,kyy=18.5e6)
    table_high = dict(high,kxx=[21e6,24e6,28e6,32e6,36e6],
                      kyy=[21e6,24e6,28e6,32e6,36e6],
                      speed=[50.,150.,300.,550.,900.])
    speed_low = dict(low,kxx=[4.2e6,7.1e6,1.18e7,1.75e7,2.65e7],
                     kyy=[4.2e6,7.1e6,1.18e7,1.75e7,2.65e7],speed=SPEED)
    freq_low = dict(low,kxx=FX,kyy=FY,frequency=FREQUENCY)
    map_low = dict(low,kxx=GX,kyy=GY,speed=SPEED,frequency=FREQUENCY)
    return {
        'legacy_unsorted_isotropic_first_node':case(),
        'legacy_unsorted_anisotropic':case(supports=[high,anis]),
        'legacy5_unsorted':case('legacy5'),
        'coefficient_constant_unsorted':case('coefficient'),
        'coefficient_speed_unsorted':case('coefficient',[table_high,speed_low]),
        'coefficient_frequency_unsorted':case('coefficient',[table_high,freq_low]),
        'coefficient_2d_unsorted':case('coefficient',[table_high,map_low]),
        'seal_and_unsorted_bearings':case(supports=[
            dict(node=1,seal=True,tag='seal-before'),high,
            dict(node=3,seal=True,tag='seal-between'),dict(low,node=2)]),
        'stable_same_node_order':case(supports=[high,low,dict(anis,tag='lower-second')]),
        'explicit_bearing_speed_range':case(bearing_speed_range=[40.,900.]),
        'already_sorted':case(supports=[low,high]),
        'rouch_unsorted':case(synchronous=True),
    }


def native_model(spec):
    from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,CoefficientBearing
    nodes=[Node(i+1,z) for i,z in enumerate([0.,.21,.48,.67])]
    shafts=[ShaftElement(2,i,i+1,od,.014,7810.,211e9,81.2e9,2.5e-3)
            for i,od in enumerate([.054,.061,.049],1)]
    bearings=[]; advanced=[]
    for b in spec['supports']:
        if b.get('seal'):
            bearings.append(Bearing(8,b['node'],()))
        elif spec['family']=='coefficient':
            advanced.append(CoefficientBearing(b['node'],b['kxx'],0.,b['kyy'],0.,
                speed_rad_s=tuple(b.get('speed',())),frequency_rad_s=tuple(b.get('frequency',())),
                interpolation='pchip',tag=b['tag']))
        elif spec['family']=='legacy5':
            bearings.append(Bearing(5,b['node'],(b['kxx'],0.,0.,b['kyy'],230.,0.,0.,230.)))
        else:
            bearings.append(Bearing(3,b['node'],(b['kxx'],b['kyy'],230.,230.)))
    return RotorModel(nodes,shafts,[Disk.inertial(3,19.,.083,.151)],bearings,advanced_bearings=advanced)


def ross_rotor(rs,spec):
    material=rs.Material(name='a5-order',rho=7810.,E=211e9,G_s=81.2e9)
    shafts=[rs.ShaftElement(L=L,idl=.014,odl=od,material=material,
        shear_effects=True,rotary_inertia=True,gyroscopic=True)
        for L,od in zip([.21,.27,.19],[.054,.061,.049])]
    for sh in shafts:
        sh.alpha=2.5e-3; sh.beta=7.5e-6
    supplied=[]
    for b in spec['supports']:
        if b.get('seal'):
            supplied.append(rs.SealElement(n=b['node']-1,kxx=2e7,cxx=20.,tag=b['tag']))
        else:
            kw=dict(n=b['node']-1,kxx=b['kxx'],kyy=b['kyy'],cxx=0.,tag=b['tag'])
            if 'speed' in b:kw['speed']=b['speed']
            if 'frequency' in b:kw['frequency']=b['frequency']
            supplied.append(rs.BearingElement(**kw))
    original_order=[(b.n+1,b.tag) for b in supplied]
    rotor=rs.Rotor(shafts,[rs.DiskElement(n=2,m=19.,Id=.083,Ip=.151)],supplied)
    assert [(b.n+1,b.tag) for b in supplied]==original_order
    assert [(b.n+1,b.tag) for b in rotor.bearing_elements]==sorted(original_order,key=lambda item:item[0])
    return rotor
