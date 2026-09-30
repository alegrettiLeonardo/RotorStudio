"""Bearing Performance: native fields, thermal/deformation views and maps."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import json
import re
import numpy as np
import flet as ft
from drm_core import AnalysisCase
from drm_core.units import rpm_to_rad_s,rad_s_to_rpm
from drm_core.domain.bearings import advanced_bearing_to_dict
from drm_core.solver.bearing_maps import canonical_bearing_hash
from .analysis_forms import AxisControl
from .analysis_catalog import grid,materialize_grid
from .editing import number
from .bearing_jobs import BearingFieldResult,BearingMapResult,map_cache
from .session import EntityRef
from .plotting import base_figure,png_bytes
from .result_presenter import Presented

FIELD_TABS=[('summary','Resumo',None,''),('coefficients','K / C / M',None,''),
            ('pressure','Pressão','pressure_field_pa','Pa'),('temperature','Temperatura','temperature_field_k','K'),
            ('film','Espessura do filme','film_thickness_field_m','m'),('deformation','Deformação','deformation_field_m','m'),
            ('pads','Sapatas','pad_load_n','N'),('convergence','Convergência','convergence','')]
MAP_TABS=[('curves','Curvas'),('surface','Mapa 2D'),('coefficients','Coeficientes'),('source','Origem / cache')]


def field_present(record,state,dark=False):
    r=record.execution.result;p=r.payload;ev=p['evaluation'];view=state.get('view','summary');fig,ax=base_figure(dark)
    headers=['Propriedade','Valor'];rows=[];note='Campos calculados explicitamente pelo Core, sem nova solução durante a visualização.'
    if view=='summary':
        rows=[['Família',ev.model_family],['Rotação [rad/s]',r.speed_rad_s],['Frequência [rad/s]',r.frequency_rad_s]]
        rows += [[k,str(v)] for k,v in ev.details.items() if not isinstance(v,(dict,list,tuple,np.ndarray))]
        ax.set_axis_off();text='\n'.join(f'{k}: {v}' for k,v in rows[:15]);ax.text(.03,.98,text,ha='left',va='top',fontsize=10,transform=ax.transAxes)
    elif view=='coefficients':
        key=state.get('coefficient_group','K');a=np.asarray(getattr(ev,key));im=ax.imshow(a,origin='lower',aspect='equal');u={'K':'N/m','C':'N·s/m','M':'kg'}[key]
        fig.colorbar(im,ax=ax,label=key+' ['+u+']');ax.set_xticks([0,1],['X','Y']);ax.set_yticks([0,1],['X','Y']);ax.set_xlabel('Coluna · deslocamento / velocidade / aceleração');ax.set_ylabel('Linha · força')
        headers=['Matriz','Componente','Valor','Unidade']
        rows=[[g,'xy'[i]+'xy'[j],float(getattr(ev,g)[i,j]),{'K':'N/m','C':'N·s/m','M':'kg'}[g]] for g in ('K','C','M') for i in range(2) for j in range(2)]
    elif view=='convergence':
        conv=p.get('convergence') or {};rows=[[k,str(v)] for k,v in conv.items()];ax.set_axis_off()
        ax.text(.02,.98,'\n'.join(f'{k}: {v}' for k,v in rows),va='top',fontsize=10,transform=ax.transAxes)
        note='Diagnósticos finais do solver. Histórico iterativo não retornado não é reconstruído.'
    elif view=='pads':
        loads=np.asarray(p['pad_load_n']).ravel();tilt=np.asarray(ev.details.get('tilt_angle_rad',[])).ravel()
        x=np.arange(len(loads))+1;ax.bar(x,loads);ax.set_xlabel('Sapata');ax.set_ylabel('Carga [N]')
        headers=['Sapata','Carga [N]','Inclinação [rad]'];rows=[[i+1,float(v),float(tilt[i]) if i<len(tilt) else 'não retornada'] for i,v in enumerate(loads)]
    else:
        _,label,key,unit=next(t for t in FIELD_TABS if t[0]==view)
        if p.get(key) is None:raise ValueError(f'{label} não retornada pelo modelo de mancal.')
        a=np.asarray(p[key]);pad=min(max(0,int(state.get('pad_index',0))),a.shape[0]-1)
        theta=np.asarray(p['theta_rad'])[pad]
        if view=='deformation':
            for i in range(a.shape[0]):ax.plot(np.rad2deg(p['theta_rad'][i]),a[i]*1e6,label=f'Sapata {i+1}')
            ax.set_xlabel('Ângulo θ [°]');ax.set_ylabel('Deformação [µm]');ax.legend(fontsize=8)
            headers=['Sapata','θ [rad]','Deformação [m]'];rows=[[i+1,float(t),float(v)] for i in range(a.shape[0]) for t,v in zip(p['theta_rad'][i],a[i])]
        else:
            axial=np.asarray(p['axial_position_m'])[pad]
            image=ax.pcolormesh(axial*1000,np.rad2deg(theta),a[pad],shading='auto');fig.colorbar(image,ax=ax,label=label+' ['+unit+']')
            ax.set_xlabel('Posição axial [mm]');ax.set_ylabel('Ângulo θ [°]')
            headers=['θ [rad]','Z [m]',label+' ['+unit+']'];rows=[[float(t),float(z),float(a[pad,i,j])] for i,t in enumerate(theta) for j,z in enumerate(axial)]
    ax.set_title(dict((t[0],t[1]) for t in FIELD_TABS)[view]);fig.subplots_adjust(left=.12,right=.93,bottom=.17,top=.89)
    return Presented(fig,headers,rows,note)


def map_present(record,state,dark=False):
    result=record.execution.result;r=result.cached.operating_map;view=state.get('view','curves');fig,ax=base_figure(dark)
    prefix=state.get('coefficient_group','K').lower();prefix=prefix if prefix in ('k','c') else 'k';key=state.get('map_coefficient',prefix+'xx')
    keys=[prefix+s for s in ('xx','xy','yx','yy')];u='N/m' if prefix=='k' else 'N·s/m';w=np.asarray(r.speed_rad_s);wf=np.asarray(r.frequency_rad_s)
    j=min(max(int(state.get('frequency_index',0)),0),max(0,len(wf)-1));headers=['Ω [rad/s]','ω [rad/s]',*[k.upper()+' ['+u+']' for k in keys]]
    def at(k,i,j):a=np.asarray(getattr(r,k));return float(a[i,j] if a.ndim==2 else a[i])
    rows=[[float(omega),float(wf[j]) if len(wf) else float(omega),*[at(k,i,j) for k in keys]] for i,omega in enumerate(w)]
    if view=='surface' and len(wf):
        a=np.asarray(getattr(r,key));im=ax.pcolormesh(wf/(2*np.pi),rad_s_to_rpm(w),a,shading='auto');fig.colorbar(im,ax=ax,label=key.upper()+' ['+('N/m' if key.startswith('k') else 'N·s/m')+']');ax.set_xlabel('Frequência independente ω [Hz]');ax.set_ylabel('Rotação Ω [rpm]')
    elif view=='source':
        meta={'Fonte do cache':result.cached.source,'Chave':result.cached.cache_key,'Hash do mancal':r.source_bearing_hash,'Fingerprint do solver':r.solver_fingerprint,
              'Política':'SYNCHRONOUS' if r.synchronous else 'INDEPENDENT_2D','Pontos concluídos':r.convergence_summary.get('completed_points'),
              'Máx. iterações':r.convergence_summary.get('max_iterations'),'Interpolação':r.interpolation}
        headers=['Propriedade','Valor'];rows=[[k,str(v)] for k,v in meta.items()];ax.set_axis_off();ax.text(.02,.98,'\n'.join(f'{k}: {str(v)[:65]}' for k,v in rows),va='top',fontsize=9,transform=ax.transAxes)
    else:
        for k in keys:ax.plot(rad_s_to_rpm(w),[at(k,i,j) for i in range(len(w))],label=k.upper())
        ax.set_xlabel('Rotação Ω [rpm]');ax.set_ylabel(u);ax.legend(fontsize=9)
    ax.set_title('Mapa operacional · '+result.cached.source);fig.subplots_adjust(left=.12,right=.93,bottom=.17,top=.88)
    return Presented(fig,headers,rows,'Mapa B16 de K/C. A massa do mancal não é descartada: o Core rejeita M não nula neste contrato. Sem campos físicos no cache de coeficientes.')


class BearingWorkspaces:
    def bearing_job_dialog(self,e=None,scope='bearing_fields',case=None):
        if self.busy:return self.flash('Aguarde o cálculo em andamento.')
        opt=case.options if case else {};ref=EntityRef(opt.get('bearing_kind','advanced_bearings'),int(opt.get('bearing_index',0))) if case else self.bearing_ref
        if ref is None or ref.kind!='advanced_bearings':return self.error('Modelo do mancal','Selecione um mancal avançado tipado. Os mancais clássicos usam a avaliação de matrizes.')
        b=self.session.project.model.advanced_bearings[ref.index];scope=opt.get('flet_scope',scope)
        name=self.field('Nome do caso',case.name if case else f'{scope}_{ref.index+1}')
        speed=self.field('Rotação do rotor Ω',f"{rad_s_to_rpm(opt.get('speed_rad_s',94.24777960769379)):.17g}",'rpm',width=285)
        freq=self.field('Frequência independente ω',f"{opt.get('frequency_rad_s',94.24777960769379)/(2*np.pi):.17g}",'Hz',width=285)
        v={'mode':'explicit','values':';'.join(format(float(rad_s_to_rpm(w)),'.17g') for w in opt['speeds_rad_s'])} if 'speeds_rad_s' in opt else {'mode':'uniform','start':900,'stop':1200,'count':3}
        axis=AxisControl(self,grid('speeds','Rotações do mapa',900,1200,3,'rpm'),v)
        frequencies=opt.get('frequencies_rad_s');fv={'mode':'explicit','values':';'.join(format(float(w/(2*np.pi)),'.17g') for w in frequencies)} if frequencies else {'mode':'uniform','start':15,'stop':20,'count':2}
        axisf=AxisControl(self,grid('frequencies','Frequências independentes',15,20,2,'Hz'),fv)
        policy=ft.Dropdown(label='Política do mapa',value='independent' if frequencies else 'synchronous',options=[ft.DropdownOption('synchronous','Síncrona · ω=Ω'),ft.DropdownOption('independent','Independente · Ω × ω')],width=310,dense=True)
        interp=ft.Dropdown(label='Interpolação',value=opt.get('interpolation','pchip'),options=[ft.DropdownOption('pchip'),ft.DropdownOption('linear')],width=240,dense=True)
        axisf.root.visible=policy.value=='independent'
        def change_policy(_):axisf.root.visible=policy.value=='independent';self.page.update()
        policy.on_select=change_policy
        err=ft.Text('',color=self.p.error,size=12)
        controls=[name,self.notice(f'{type(b).__name__} · nó {b.node}. A avaliação nativa será executada fora da thread de interface.')]
        controls += [policy,axis.root,axisf.root,interp] if scope=='operating_map' else [ft.Row([speed,freq],wrap=True)]
        controls += [self.notice('Limites de validade, convergência e dados térmicos são verificados pelo Core. Nenhuma aproximação por mancal constante será feita.'),err]
        original_hash=self.session.project.model.model_hash()
        def read_values():
            return (speed.value,freq.value,axis.value,axisf.value,policy.value,interp.value)
        baseline=read_values()
        async def run(_):
            try:
                if original_hash!=self.session.project.model.model_hash():raise ValueError('Modelo alterado; reabra a configuração.')
                if not str(name.value).strip():raise ValueError('Nome do caso obrigatório.')
                if any(c.name==name.value and (case is None or c.name!=case.name) for c in self.session.project.analyses):raise ValueError('Nome já utilizado por outro caso.')
                options={**opt,'flet_scope':scope,'bearing_kind':ref.kind,'bearing_index':ref.index}
                if scope=='operating_map':
                    speeds=rpm_to_rad_s(materialize_grid(axis.value)).tolist();fs=(materialize_grid(axisf.value)*2*np.pi).tolist() if policy.value=='independent' else None
                    if len(speeds)*(len(fs) if fs else 1)>4096:raise ValueError('No máximo 4096 pontos no mapa.')
                    options.update(speeds_rad_s=speeds,frequencies_rad_s=fs,interpolation=interp.value);s=speeds[0]
                else:
                    s=float(rpm_to_rad_s(number(speed.value)));f=number(freq.value)*2*np.pi
                    options.update(speed_rad_s=s,frequency_rad_s=f)
                c=AnalysisCase('bearing_matrices',{'speed_rad_s':s},str(name.value).strip(),options)
                if case is not None and read_values()==baseline:c=replace(case,name=str(name.value).strip())
                if case and c.name!=case.name:self.session.transact('Renomear caso de mancal',lambda p:setattr(p,'analyses',[c if x.name==case.name else x for x in p.analyses]),validate=False)
                self.page.pop_dialog();return await self.run_case(c)
            except Exception as exc:err.value=str(exc);self.page.update()
        self.active_bearing_controls={'name':name,'speed':speed,'frequency':freq,'speed_axis':axis,'frequency_axis':axisf,'policy':policy,'interpolation':interp,'run':run}
        self.page.show_dialog(ft.AlertDialog(modal=True,title=self.txt('Mapa operacional / cache' if scope=='operating_map' else 'Ponto de operação · campos físicos',17,bold=True),
             content=ft.Container(ft.Column(controls,scroll=ft.ScrollMode.AUTO,spacing=14,horizontal_alignment=ft.CrossAxisAlignment.STRETCH),width=660,height=510),
             actions=[self.button('Cancelar',lambda e:self.page.pop_dialog()),self.button('Executar',run,ft.Icons.PLAY_ARROW,primary=True)]))

    def bearing_view(self):
        body=super().bearing_view()
        advanced=self.bearing_ref is not None and self.bearing_ref.kind=='advanced_bearings'
        body.controls.insert(2,ft.Row([self.button('Propriedades completas',lambda e:self.entity_dialog(ref=self.bearing_ref),ft.Icons.TUNE,disabled=self.bearing_ref is None or self.busy),
                  self.button('Resolver ponto / campos',self.bearing_job_dialog,ft.Icons.GRID_ON_OUTLINED,disabled=not advanced or self.busy),
                  self.button('Mapa operacional',lambda e:self.bearing_job_dialog(scope='operating_map'),ft.Icons.MAP_OUTLINED,disabled=not advanced or self.busy)],wrap=True,spacing=7))
        return body

    def result_view(self):
        record=self.record();r=record.execution.result
        if not isinstance(r,(BearingFieldResult,BearingMapResult)):return super().result_view()
        state=self.result_state(record);field=isinstance(r,BearingFieldResult)
        tabs=[(k,l,p is None or r.payload.get(p) is not None) for k,l,p,u in FIELD_TABS] if field else [(k,l,not(k=='surface' and r.cached.operating_map.synchronous)) for k,l in MAP_TABS]
        enabled=[k for k,l,en in tabs if en]
        if state.get('view') not in enabled:state['view']=enabled[0]
        self.plot_image=ft.Image(src=b'',fit=ft.BoxFit.CONTAIN,expand=True,width=float('inf'),height=float('inf'),gapless_playback=True)
        self.redraw_result(update=False);p=self.presented_result
        controls=[ft.Row([self.txt(record.execution.case.name,21,bold=True,expand=True),self.chip('ATUAL' if self.session.is_current(record) else 'DESATUALIZADO'),
                         self.button('Reconfigurar',lambda e:self.bearing_job_dialog(case=record.execution.case),disabled=self.busy)],spacing=8),
                  ft.Row([self.button(label,lambda e,k=k:self.result_set('view',k),disabled=not en,primary=state['view']==k) for k,label,en in tabs],scroll=ft.ScrollMode.AUTO,spacing=6),
                  self.card('Dados nativos · '+dict((k,l) for k,l,en in tabs)[state['view']],ft.InteractiveViewer(content=self.plot_image,expand=True,min_scale=.5,max_scale=8),expand=True)]
        formatted=[[f'{v:.7g}' if isinstance(v,(float,np.floating)) else str(v) for v in row] for row in p.rows]
        controls += [self.card('Dados / condições de cálculo',self.table(p.headers,formatted,height=155)),self.notice(p.note)]
        return ft.Column(controls,spacing=10,expand=True)

    def redraw_result(self,update=True):
        record=self.record()
        if not record or self.plot_image is None:return
        r=record.execution.result
        if not isinstance(r,(BearingFieldResult,BearingMapResult)):return super().redraw_result(update)
        self.presented_result=(field_present if isinstance(r,BearingFieldResult) else map_present)(record,self.result_state(record),self.dark)
        self.figure=self.presented_result.figure;self.plot_png=png_bytes(self.figure);self.plot_image.src=self.plot_png
        if update:self.plot_image.update()

    def result_properties(self,record):
        r=record.execution.result
        if not isinstance(r,(BearingFieldResult,BearingMapResult)):return super().result_properties(record)
        state=self.result_state(record);body=[self.txt('Condições do mancal',14,bold=True),self.field('Hash de análise',record.execution.analysis_hash,readonly=True)]
        state.setdefault('coefficient_group','K');state.setdefault('pad_index',0);state.setdefault('map_coefficient','kxx');state.setdefault('frequency_index',0)
        def choose(key,label,values):
            body.append(ft.Dropdown(label=label,value=str(state[key]),options=[ft.DropdownOption(str(k),str(l)) for k,l in values],text_size=11,dense=True,
                on_select=lambda e,k=key:self.result_set(k,int(e.control.value) if k.endswith('_index') else e.control.value)))
        choose('coefficient_group','Matriz',[('K','Rigidez K'),('C','Amortecimento C')]+([('M','Massa M')] if isinstance(r,BearingFieldResult) else []))
        if isinstance(r,BearingFieldResult):
            body += [self.kv('Ω [rpm]',f'{rad_s_to_rpm(r.speed_rad_s):.6g}'),self.kv('ω [Hz]',f'{r.frequency_rad_s/(2*np.pi):.6g}')]
            if r.payload.get('theta_rad') is not None:choose('pad_index','Sapata',[(i,i+1) for i in range(len(r.payload['theta_rad']))])
            body.append(self.notice('Abas sem campos retornados pelo solver ficam desativadas. Não são mapas estimados pela interface.'))
        else:
            op=r.cached.operating_map
            choose('map_coefficient','Coeficiente do mapa 2D',[(s,s.upper()) for s in ('kxx','kxy','kyx','kyy','cxx','cxy','cyx','cyy')])
            if op.frequency_rad_s:choose('frequency_index','Fatia · ω [Hz]',[(i,f'{v/(2*np.pi):.6g}') for i,v in enumerate(op.frequency_rad_s)])
            body += [self.kv('Cache',r.cached.source),self.field('Chave determinística',r.cached.cache_key,readonly=True),
                     self.button('Aplicar mapa ao modelo',self.apply_operating_map,ft.Icons.CHECK,disabled=self.busy or not self.session.is_current(record)),
                     self.button('Invalidar este cache',self.invalidate_map,ft.Icons.DELETE_OUTLINE,disabled=self.busy)]
        body += [self.button('Reexecutar',self.rerun,ft.Icons.REFRESH,disabled=self.busy),self.button('PNG',self.export_png),self.button('SVG / PDF / pacote',self.export_formats_dialog),
                 self.button('CSV',self.export_csv),self.button('NPZ / campos completos',self.export_npz),self.button('Relatório',self.export_report)]
        return body

    async def apply_operating_map(self,e=None):
        record=self.record()
        if not record or not isinstance(record.execution.result,BearingMapResult):return
        if self.busy or not self.session.is_current(record):return self.error('Mapa desatualizado','Recalcule sobre o modelo atual antes de aplicar.')
        r=record.execution.result;op=r.cached.operating_map;source=self.session.project.model.advanced_bearings[r.bearing_index]
        if canonical_bearing_hash(source)!=op.source_bearing_hash:return self.error('Origem alterada','O mancal atual não corresponde ao hash de origem do mapa.')
        if not await self.confirm('Aplicar mapa operacional','Substituir o mancal selecionado pelo mapa K/C calculado? A definição física será preservada na proveniência; desfazer restaura o modelo.'):return
        b=op.to_coefficient_bearing(tag=getattr(source,'tag','') or 'Mapa operacional')
        b=replace(b,provenance={**b.provenance,'source_bearing':advanced_bearing_to_dict(source)})
        self.session.replace_entity(EntityRef('advanced_bearings',r.bearing_index),b)
        self.session.log('INFO','Mapa K/C aplicado ao modelo; resultados anteriores marcados como desatualizados.');self.render()

    async def invalidate_map(self,e=None):
        record=self.record()
        if not record or not isinstance(record.execution.result,BearingMapResult) or self.busy:return
        r=record.execution.result
        if not re.fullmatch('[0-9a-f]{64}',r.cached.cache_key):raise ValueError('Chave de cache inválida.')
        if not await self.confirm('Invalidar cache','Remover somente a entrada L1/L2 selecionada? O resultado aberto será preservado.'):return
        map_cache(r.cache_root).invalidate(r.cached.cache_key);self.flash('Entrada de cache removida; a próxima execução regenerará o mapa.')

    def refresh_messages(self):
        super().refresh_messages()
        if self.busy and hasattr(self.job,'native_progress'):
            p=self.job.native_progress()
            if p is not None:
                self.progress_text.value=f'{p.stage} · iteração {p.iteration}/{p.max_iterations} · pontos {self.job.completed}/{self.job.total}'
                self.page.update()
