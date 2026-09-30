"""Typed engineering editors for every entity exposed by the desktop workbench.

Dataclass fields remain authoritative. Editors preserve unknown provenance and
unchanged SI values; they never convert table families into physical providers.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, fields, replace
import json
import numpy as np
import flet as ft
from drm_core import Node, ShaftElement, TaperedShaftElement, AsymmetricShaftElement, Disk, Bearing, Force, BendPoint, RotorDefinition
from drm_core.domain import bearings as bd
from .editing import specs, form_values, from_form, number, display, canonical, validate_editable_model
from .analysis_catalog import numeric_array, format_vector
from .session import EntityRef

COEFFICIENTS = ('kxx','kxy','kyx','kyy','cxx','cxy','cyx','cyy','mxx','mxy','myx','myy')
VECTOR_KEYS = {'speed_rad_s','frequency_rad_s','pivot_angle_rad','pad_arc_rad','pad_axial_length_m','preload','offset','k_rotate_nm_rad'}
INTEGER_KEYS = {'node','n_balls','n_rollers','max_iterations','outer_iterations','total_e_x_film','total_e_z_film','total_e_y_pad','total_e_y_film'}
CHOICES = {'interpolation':('pchip','linear'), 'thermal_type':('','adiabatic','full'),
           'deform_type':('','pad_mechanical','pad_mechanical_thermal'),
           'geometry':('groove-end_seals','groove','end_seals'), 'bearing_type':('conventional_tilting_pad',)}
LABELS = {
    'node':'Nó','tag':'Identificação','weight_n':'Carga estática','journal_diameter_m':'Diâmetro do munhão',
    'radial_clearance_m':'Folga radial','oil_viscosity_pa_s':'Viscosidade de referência','speed_rad_s':'Eixo de rotação Ω',
    'frequency_rad_s':'Eixo de frequência / precessão ω','interpolation':'Interpolação','pivot_angle_rad':'Ângulo dos pivôs',
    'pad_arc_rad':'Arco de cada sapata','pad_axial_length_m':'Comprimento de cada sapata','preload':'Pré-carga de cada sapata',
    'offset':'Offset de cada sapata','k_rotate_nm_rad':'Rigidez à rotação de cada sapata','pad_thickness_m':'Espessura das sapatas',
    'pad_density_kg_m3':'Densidade das sapatas','fxs_load_n':'Carga adicional X','fys_load_n':'Carga adicional Y',
    'thermal_type':'Modelo térmico','deform_type':'Modelo de deformação','oil_supply_temperature_k':'Temperatura de alimentação',
    'lubricant_density_kg_m3':'Densidade do lubrificante','lubricant_cp_j_kgk':'Calor específico do lubrificante',
    'lubricant_conductivity_w_mk':'Condutividade do lubrificante','viscosity2_pa_s':'Segunda viscosidade medida',
    'temperature1_k':'Temperatura da viscosidade 1','temperature2_k':'Temperatura da viscosidade 2',
    'temperature_journal_k':'Temperatura do munhão','temperature_ambient_k':'Temperatura ambiente','temperature_reference_k':'Temperatura de referência',
    'pad_conductivity_w_mk':'Condutividade da sapata','pad_young_pa':'Módulo de Young da sapata','pad_poisson':'Poisson da sapata',
    'pad_expansion_1_k':'Expansão térmica da sapata','convection_edges_w_m2k':'Convecção nas bordas','convection_back_w_m2k':'Convecção posterior',
    'ambient_pressure_1_pa':'Pressão no contorno 1','ambient_pressure_2_pa':'Pressão no contorno 2','hot_oil_lambda':'Mistura de óleo quente λ',
    'oil_flow_m3_s':'Vazão de óleo','total_e_x_film':'Elementos circunferenciais','total_e_z_film':'Elementos axiais',
    'total_e_y_pad':'Elementos na espessura da sapata','total_e_y_film':'Elementos através do filme',
    'xj_ratio_initial':'Posição inicial xj / c','yj_ratio_initial':'Posição inicial yj / c','relax_p':'Relaxação da pressão',
    'relax_temperature':'Relaxação da temperatura','max_iterations':'Máximo de iterações','outer_iterations':'Iterações externas',
    'force_tolerance':'Tolerância de equilíbrio','field_tolerance':'Tolerância dos campos','n_balls':'Número de esferas',
    'n_rollers':'Número de rolos','d_balls_m':'Diâmetro das esferas','l_rollers_m':'Comprimento dos rolos','static_load_n':'Carga estática',
    'alpha_rad':'Ângulo de contato','cxx_ns_m':'Amortecimento X (opcional)','cyy_ns_m':'Amortecimento Y (opcional)',
    'bearing_length_m':'Comprimento do mancal','axial_length_m':'Comprimento axial','eccentricity_ratio':'Razão de excentricidade',
    'viscosity_pa_s':'Viscosidade','geometry':'Geometria do amortecedor','cavitation':'Cavitação','bearing_type':'Tipo de mancal físico',
}
THERMAL = {'thermal_type','oil_supply_temperature_k','lubricant_density_kg_m3','lubricant_cp_j_kgk','lubricant_conductivity_w_mk',
           'viscosity2_pa_s','temperature1_k','temperature2_k','temperature_journal_k','temperature_ambient_k','temperature_reference_k',
           'ambient_pressure_1_pa','ambient_pressure_2_pa','convection_edges_w_m2k','convection_back_w_m2k','hot_oil_lambda','oil_flow_m3_s'}
DEFORMATION = {'deform_type','pad_conductivity_w_mk','pad_young_pa','pad_poisson','pad_expansion_1_k'}
SOLVER = {'xj_ratio_initial','yj_ratio_initial','relax_p','relax_temperature','max_iterations','outer_iterations','force_tolerance','field_tolerance'}


def unit_for(key):
    if key in COEFFICIENTS:return {'k':'N/m','c':'N·s/m','m':'kg'}[key[0]]
    if key.endswith('_rad_s'):return 'rpm' if key=='speed_rad_s' else 'rad/s'
    for suffix,unit in [('_nm_rad','N·m/rad'),('_ns_m','N·s/m'),('_pa_s','Pa·s'),('_pa','MPa' if key=='pad_young_pa' else 'Pa'),
                        ('_kg_m3','kg/m³'),('_j_kgk','J/(kg·K)'),('_w_mk','W/(m·K)'),('_w_m2k','W/(m²·K)'),
                        ('_m3_s','m³/s'),('_1_k','1/K'),('_k','K'),('_n','N'),('_rad','rad')]:
        if key.endswith(suffix):return unit
    if key.endswith('_m'):return 'mm'
    return ''


def group_for(key):
    if key in COEFFICIENTS:return {'k':'RIGIDEZ K','c':'AMORTECIMENTO C','m':'MASSA M'}[key[0]]
    if key in THERMAL:return 'TÉRMICA'
    if key in DEFORMATION:return 'DEFORMAÇÃO'
    if key in SOLVER:return 'CONVERGÊNCIA'
    if key.startswith('total_e_'):return 'MALHA'
    if key in VECTOR_KEYS-{'speed_rad_s','frequency_rad_s'}:return 'SAPATAS'
    if key in {'speed_rad_s','frequency_rad_s','interpolation'}:return 'EIXOS DA TABELA'
    return 'GERAL / GEOMETRIA'


def data_text(value,unit=''):
    if value is None:return ''
    if isinstance(value,(tuple,list,np.ndarray)):
        a=np.asarray(value)
        if a.ndim==0:return display(a.item(),unit)
        if a.ndim==1:return '; '.join(display(v,unit) for v in a)
        return '\n'.join('; '.join(display(v,unit) for v in row) for row in a)
    if isinstance(value,(str,bool)):return value
    return display(value,unit)


def parse_data(text,key,original,*,optional=False):
    if key=='tag':return str(text).strip()
    if key=='cavitation':
        if not isinstance(text,bool):raise ValueError('Cavitação: esperado verdadeiro/falso.')
        return text
    if key in CHOICES:return (str(text) or None)
    raw=str(text).strip()
    if not raw:
        if key in VECTOR_KEYS:return ()
        if original is None or optional:return None
        raise ValueError(f'{LABELS.get(key,key)}: campo obrigatório.')
    unit=unit_for(key)
    if key in COEFFICIENTS or key in VECTOR_KEYS:
        # A semicolon separates cells; each newline separates matrix rows.
        if '\n' in raw and not raw.startswith('['):
            rows=[numeric_array(line) for line in raw.splitlines() if line.strip()]
            a=np.asarray(rows,dtype=float)
        elif raw.startswith('['):a=numeric_array(raw)
        elif ';' in raw or key in VECTOR_KEYS:a=numeric_array(raw)
        else:return float(canonical(number(raw),unit))
        if key in VECTOR_KEYS and a.ndim!=1:raise ValueError(f'{key}: esperado um vetor.')
        if a.ndim not in (1,2) or a.size>100000:raise ValueError(f'{key}: dimensão inválida ou mais de 100000 valores.')
        conv=np.vectorize(lambda x:canonical(float(x),unit),otypes=[float])(a) if a.size else a
        return tuple(tuple(float(x) for x in row) for row in conv) if conv.ndim==2 else tuple(float(x) for x in conv)
    value=canonical(number(raw,integer=key in INTEGER_KEYS),unit)
    return int(value) if key in INTEGER_KEYS else float(value)


def advanced_values(entity):
    return {f.name:data_text(getattr(entity,f.name),unit_for(f.name)) for f in fields(entity) if f.init and f.name!='provenance'}


def advanced_from_values(entity,values):
    original=advanced_values(entity);change={}
    optional={f.name for f in fields(entity) if 'None' in str(f.type)}
    for key,value in values.items():
        if key not in original:raise ValueError(f'Campo desconhecido: {key}')
        if value!=original[key]:change[key]=parse_data(value,key,getattr(entity,key),optional=key in optional)
    b=replace(entity,**change)
    if b.node!=int(b.node):raise ValueError('Nó deve ser inteiro.')
    bd.validate_advanced_bearing(b)
    return b


# New entities use clearly editable input defaults, never synthetic results.
ADVANCED_CLASSES = (bd.CoefficientBearing,bd.PlainJournalPhysicsBearing,bd.TiltingPadPhysicsBearing,
                    bd.BallBearing,bd.RollerBearing,bd.CylindricalBearing,bd.SqueezeFilmDamper,
                    bd.PlainJournalBearing,bd.PartialArcBearing,bd.EllipticalBearing,bd.OffsetHalvesBearing,
                    bd.MultiLobeBearing,bd.PressureDamBearing,bd.TiltingPadBearing)


def make_entity(kind,model,variant=None):
    nodes=model.nodes;first=nodes[0].number if nodes else 1;last=nodes[-1].number if nodes else 1
    if kind=='nodes':return Node(max([n.number for n in nodes]+[0])+1,(max(n.z_m for n in nodes)+0.1) if nodes else 0.)
    if not nodes:raise ValueError('Adicione nós antes dos elementos.')
    if kind=='shafts':
        if len(nodes)<2:raise ValueError('Um elemento de eixo requer dois nós.')
        n1,n2=nodes[-2].number,nodes[-1].number
        if variant=='TaperedShaftElement':return TaperedShaftElement(22,n1,n2,.05,.04,0.,0.,7800.,210e9,80e9)
        if variant=='AsymmetricShaftElement':return AsymmetricShaftElement(12,n1,n2,1e5,8e4,0.,0.,10.,.01)
        return ShaftElement(2,n1,n2,.05,0.,7800.,210e9,80e9)
    if kind=='disks':
        t=int(variant or 1)
        return Disk.geometric(first,7800.,.05,.2,0.,t) if t in (1,3) else Disk.inertial(first,10.,.01,.02,t) if t in (2,4) else Disk.anisotropic(first,10.,.01,.015,.02,t)
    if kind=='bearings':
        t=int(variant or 3)
        p={1:(),2:(),3:(1e6,1e6,0.,0.),4:(1e6,1e6,0.,0.,0.,0.,0.,0.),5:(1e6,0.,0.,1e6,0.,0.,0.,0.),
           6:tuple(np.diag([1e6,1e6,0.,0.]).ravel())+(0.,)*16,7:(1000.,.05,.025,5e-5,.02),
           8:(0.,.025,.025,5e-5,1.,.01),20:(last,1e6,1e6,0.,0.)}[t]
        return Bearing(t,first,p)
    if kind=='forces':
        t=int(variant or 1);nbase=len(model.bearings)
        if t in (4,5) and not nbase:raise ValueError('A excitação de fundação requer mancais clássicos definidos.')
        p={1:(first,.001,0.),2:(first,.001,0.),3:(),4:(0.,)*(2*nbase),5:(0.,)*(2*nbase)+(.01,),6:(first,.001,0.),7:(first,1.,0.)}[t]
        return Force(t,p)
    if kind=='bend':return BendPoint(first,0.,0.)
    if kind=='rotors':return RotorDefinition(first,last,1.)
    cls=next((x for x in ADVANCED_CLASSES if x.__name__==variant),bd.CoefficientBearing)
    if issubclass(cls,bd.CoefficientBearing):return cls(first,1e6,100.)
    if cls is bd.BallBearing:return cls(first,8,.01,1000.)
    if cls is bd.RollerBearing:return cls(first,12,.01,1000.)
    if cls is bd.CylindricalBearing:return cls(first,1000.,.025,.05,5e-5,.02)
    if cls is bd.SqueezeFilmDamper:return cls(first,.025,.05,5e-5,.3,.02)
    common=dict(node=first,weight_n=1000.,journal_diameter_m=.05,radial_clearance_m=5e-5,oil_viscosity_pa_s=.02,
                pivot_angle_rad=(np.pi/2,3*np.pi/2),pad_arc_rad=(2.8,2.8),pad_axial_length_m=(.025,.025),preload=(.3,.3),offset=(.5,.5))
    if cls is bd.TiltingPadPhysicsBearing:common.update(pad_thickness_m=.01,pad_density_kg_m3=7800.,k_rotate_nm_rad=(0.,0.))
    return cls(**common)


class EntityForm:
    def __init__(self,app,entity,kind,ref=None):
        self.app,self.entity,self.kind,self.ref=app,deepcopy(entity),kind,ref
        self.model_hash=app.session.project.model.model_hash();self.controls={}
        self.advanced=hasattr(entity,'model_family')
        self.original=advanced_values(entity) if self.advanced else form_values(entity)
        groups={}
        defs=([ (k,LABELS.get(k,k.upper() if k in COEFFICIENTS else k),unit_for(k),group_for(k)) for k in self.original ] if self.advanced else
              [(s.key,s.label,s.unit,s.section) for s in specs(entity)])
        for key,label,unit,group in defs:
            value=self.original[key]
            if self.advanced and key in CHOICES:
                ctrl=ft.Dropdown(label=label,value=str(value or ''),options=[ft.DropdownOption(v,v or 'Nenhum / não especificado') for v in CHOICES[key]],text_size=12,dense=True,width=350)
            elif self.advanced and key=='cavitation':ctrl=ft.Checkbox(label=label,value=bool(value))
            else:
                multi=(self.advanced and key in COEFFICIENTS)
                ctrl=ft.TextField(label=label,value=str(value),suffix=ft.Text(unit,size=10) if unit else None,text_size=12,dense=True,width=350,
                                  multiline=multi,min_lines=1,max_lines=5 if multi else 1,
                                  tooltip=f'Campo Core: {key}. '+('Linhas = rotações; colunas = frequências. Células separadas por ;.' if multi else ''))
            self.controls[key]=ctrl;groups.setdefault(group,[]).append(ctrl)
        self.body=ft.Column(spacing=14,scroll=ft.ScrollMode.AUTO,expand=True)
        for group,controls in groups.items():
            self.body.controls += [app.txt(group,11,bold=True,color=app.p.primary),ft.Row(controls,wrap=True,spacing=14,run_spacing=12)]
        if isinstance(entity,Force):self.body.controls.insert(0,app.notice('Forças DRM 1..7. As amplitudes de fundação seguem a ordem dos mancais. A curvatura do tipo 3 é definida na tabela Curvatura.'))
        if isinstance(entity,bd.CoefficientBearing):
            self.body.controls.insert(0,app.notice('K/C/M: constantes, vetores ou matrizes Ω × ω. Separador de células: ;. Nova linha = próxima rotação. Campo YY vazio herda XX; sinais cruzados preservados. Eixos vazios = constante.'))
        if self.advanced:
            self.body.controls.append(app.notice('Proveniência preservada sem alterações. Ativar THD/TEHD exige preencher os dados físicos; campos em branco continuam não especificados.'))
            self.body.controls.append(ft.Text(json.dumps(getattr(entity,'provenance',{}),ensure_ascii=False,indent=2),size=10,selectable=True))
        self.error=ft.Text('',color=app.p.error,size=12,selectable=True)
        self.dialog=ft.AlertDialog(modal=True,title=app.txt(('Editar ' if ref else 'Adicionar ')+type(entity).__name__,17,bold=True),
             content=ft.Container(ft.Column([self.body,self.error],expand=True),width=755,height=560,padding=ft.Padding.only(top=8)),
             actions=[app.button('Cancelar',lambda e:app.page.pop_dialog()),app.button('Aplicar',self.commit,ft.Icons.CHECK,primary=True)])

    def build(self):
        if self.model_hash!=self.app.session.project.model.model_hash():raise ValueError('O modelo mudou enquanto o editor estava aberto. Reabra o formulário.')
        values={k:c.value for k,c in self.controls.items()}
        return advanced_from_values(self.entity,values) if self.advanced else from_form(self.entity,values)

    def commit(self,e=None):
        try:
            if self.app.busy:raise ValueError('Aguarde o cálculo antes de editar o modelo.')
            entity=self.build()
            def change(p):
                items=getattr(p.model,self.kind)
                if self.ref:items[self.ref.index]=entity
                else:items.append(entity)
            self.app.session.transact('Editar '+type(entity).__name__,change)
            self.app.session.selection=self.ref or EntityRef(self.kind,len(getattr(self.app.session.project.model,self.kind))-1)
            self.app.page.pop_dialog();self.app.render();return entity
        except Exception as exc:
            self.error.value=str(exc);self.app.page.update();return None


class EntityActions:
    def entity_dialog(self,e=None,ref=None,entity=None,kind=None):
        if not self.may_edit():return
        ref=ref or (self.session.selection if entity is None else None)
        if ref:entity=getattr(self.session.project.model,ref.kind)[ref.index];kind=ref.kind
        if entity is None:return
        self.active_entity_form=EntityForm(self,entity,kind,ref)
        self.page.show_dialog(self.active_entity_form.dialog)

    def add_dialog(self,e=None,kind=None):
        if not self.may_edit():return
        types={'nodes':[('Node','Nó')],'shafts':[(x,x) for x in ('ShaftElement','TaperedShaftElement','AsymmetricShaftElement')],
               'disks':[(str(t),f'Tipo {t} · '+('Geometria' if t in (1,3) else 'Massa / inércia' if t in (2,4) else 'Anisotrópico')) for t in range(1,7)],
               'bearings':[(str(t),f'Tipo {t}') for t in (1,2,3,4,5,6,7,8,20)],
               'advanced_bearings':[(c.__name__,c.__name__) for c in ADVANCED_CLASSES],
               'forces':[(str(t),s) for t,s in [(1,'Desbalanceamento de massa'),(2,'Desbalanceamento de momento'),(3,'Rotor curvo'),(4,'Fundação harmônica'),(5,'Pulso na fundação'),(6,'Spinner'),(7,'Força auxiliar')]],
               'bend':[('BendPoint','Ponto de curvatura')],'rotors':[('RotorDefinition','Intervalo de nós e fator de rotação')]}
        from .ui_common import NAMES
        collection=ft.Dropdown(label='Coleção',value=kind or 'shafts',options=[ft.DropdownOption(k,NAMES[k]) for k in types],width=420)
        variant=ft.Dropdown(label='Modelo / família',width=420)
        def update(_=None):
            variant.options=[ft.DropdownOption(k,v) for k,v in types[collection.value]];variant.value=types[collection.value][0][0]
            self.page.update()
        collection.on_select=update;update()
        error=ft.Text('',color=self.p.error)
        def choose(_):
            try:
                item=make_entity(collection.value,self.session.project.model,variant.value)
                self.page.pop_dialog();self.entity_dialog(entity=item,kind=collection.value)
            except Exception as exc:error.value=str(exc);self.page.update()
        self.page.show_dialog(ft.AlertDialog(modal=True,title=self.txt('Adicionar elemento',17,bold=True),content=ft.Container(ft.Column([collection,variant,self.notice('Valores iniciais são entradas editáveis, não um projeto dimensionado.'),error],tight=True),width=470),
                                            actions=[self.button('Cancelar',lambda e:self.page.pop_dialog()),self.button('Configurar',choose,primary=True)]))

    def entity_collection_dialog(self,kind):
        """Atomic row editing, crucial for mutually dependent coaxial ranges."""
        from .ui_common import NAMES
        if kind not in ('rotors','bend'):return self.navigate('model')
        if not self.may_edit():return
        entities=deepcopy(getattr(self.session.project.model,kind));original_hash=self.session.project.model.model_hash()
        rows=[];table=ft.Column(spacing=8,scroll=ft.ScrollMode.AUTO,expand=True)
        def add_row(entity):
            values=form_values(entity);controls={s.key:self.field(s.label,values[s.key],s.unit,width=185) for s in specs(entity)}
            entry=(entity,controls);rows.append(entry)
            def remove(_):rows.remove(entry);redraw()
            line=ft.Row([*controls.values(),self.ib(ft.Icons.DELETE_OUTLINE,'Remover linha',remove)],wrap=True)
            entry_controls[id(entry)]=line;redraw()
        def redraw():table.controls=[entry_controls[id(r)] for r in rows];self.page.update()
        entry_controls={}
        for entity in entities:add_row(entity)
        err=ft.Text('',color=self.p.error)
        def commit(_):
            try:
                if self.busy or original_hash!=self.session.project.model.model_hash():raise ValueError('Modelo alterado; reabra o editor.')
                value=[from_form(ent,{k:c.value for k,c in ctr.items()}) for ent,ctr in rows]
                self.session.transact('Editar '+NAMES[kind],lambda p:setattr(p.model,kind,value));self.page.pop_dialog();self.render()
            except Exception as exc:err.value=str(exc);self.page.update()
        self.page.show_dialog(ft.AlertDialog(modal=True,title=self.txt(NAMES[kind],17,bold=True),
              content=ft.Container(ft.Column([self.notice('Todas as linhas são aplicadas em uma única transação; cancelar preserva o modelo.'),table,err],expand=True),width=690,height=460),
              actions=[self.button('Adicionar linha',lambda e:add_row(make_entity(kind,self.session.project.model))),self.button('Cancelar',lambda e:self.page.pop_dialog()),self.button('Aplicar',commit,primary=True)]))
