"""Complete native-result documents; controls select stored data, never solve."""
from __future__ import annotations
import asyncio
import json
import numpy as np
import flet as ft
from drm_core.analysis.modal import ModalResult
from .jobs import BearingSweep,arrays_of
from .result_presenter import (present,tabs_for,dof_label,HARMONIC,SPECIAL_MODAL,StaticResult,FrequencyResponseMatrixResult,
    ForcedResponseResult,GeneralTimeResponseResult,CriticalSpeedResult,TransientResult,UCSResult,Level1Result,API617UnbalanceResult,ClearanceResult)
from .plotting import png_bytes


def old_modal(r):
    return isinstance(r,ModalResult) or (isinstance(r,list) and bool(r) and isinstance(r[0],ModalResult))


def point_count(result):
    for attr in ('frequency_rad_s','speeds_rad_s','time_s','critical_speeds_rad_s','intersection_speed_rad_s','cross_coupled_stiffness_n_m'):
        if hasattr(result,attr):return len(getattr(result,attr))
    return 0


class AllResultsViews:
    def result_state(self,record=None):
        record=record or self.record()
        if not hasattr(self,'result_selections'):self.result_selections={}
        state=self.result_selections.setdefault(record.id,{
            'output_dof':record.execution.case.options.get('output_dof',0),
            'input_dof':record.execution.case.options.get('input_dof',0),
            'response':record.execution.case.options.get('response','displacement'),
            'point_index':0,'mode_index':0,'selected_clearance_index':record.execution.case.options.get('selected_clearance_index',0),'probe_index':0,'speed_units':'RPM','phase':0.,'amplitude':1.})
        record.view_selection=dict(state)
        return state

    def result_set(self,key,value):
        self.result_state()[key]=value;self.render()

    def result_view(self):
        record=self.record();r=record.execution.result
        if old_modal(r) or isinstance(r,BearingSweep):return super().result_view()
        state=self.result_state(record);tabs=tabs_for(r)
        if state.get('view') not in dict(tabs):state['view']=tabs[0][0]
        buttons=[self.button(label,lambda e,k=k:self.result_set('view',k),primary=k==state['view']) for k,label in tabs]
        self.plot_image=ft.Image(src=b'',fit=ft.BoxFit.CONTAIN,expand=True,width=float('inf'),height=float('inf'),gapless_playback=True)
        self.redraw_result(update=False)
        p=self.presented_result
        title=ft.Row([ft.Column([self.txt(record.execution.case.name,21,bold=True),self.txt(record.execution.case.kind,11,muted=True)],spacing=3,expand=True),
                      self.chip('ATUAL' if self.session.is_current(record) else 'DESATUALIZADO',self.p.success if self.session.is_current(record) else self.p.warning),
                      self.button('Reconfigurar',lambda e:self.analysis_dialog(kind=record.execution.case.kind,case=record.execution.case),ft.Icons.TUNE,disabled=self.busy)],spacing=10)
        content=[title,ft.Row(buttons,spacing=6,scroll=ft.ScrollMode.AUTO),self.card('Resultado numérico · '+dict(tabs)[state['view']],
                  ft.InteractiveViewer(content=self.plot_image,min_scale=.5,max_scale=8,expand=True),expand=True)]
        if state['view'] in ('modes','ods'):
            content.append(ft.Row([self.button('Animar fase',self.animate_special,ft.Icons.PLAY_ARROW),self.txt('Fase visual',10),
                            ft.Slider(min=0,max=360,divisions=180,value=float(state.get('phase',0)),on_change=self.special_phase,expand=True)],spacing=8))
        if p.headers:
            formatted=[[f'{v:.7g}' if isinstance(v,(float,np.floating)) else str(v) for v in row] for row in p.rows]
            content.append(self.card('Tabela · valores calculados no modelo de origem',self.table(p.headers,formatted,height=150,
                    selected=state.get('point_index') if len(p.rows)==point_count(r) else None,
                    select=(lambda i:self.result_set('point_index',i)) if len(p.rows)==point_count(r) and len(p.rows)>0 else None)))
        if p.note:content.append(self.notice(p.note))
        return ft.Column(content,expand=True,spacing=9)

    def redraw_result(self,update=True):
        record=self.record()
        if not record or self.plot_image is None:return
        r=record.execution.result
        if old_modal(r) or isinstance(r,BearingSweep):return super().redraw_result(update)
        self.presented_result=present(record,self.result_state(record),dark=self.dark)
        self.figure=self.presented_result.figure;self.plot_png=png_bytes(self.figure);self.plot_image.src=self.plot_png
        if update:self.plot_image.update()

    def result_properties(self,record):
        r=record.execution.result
        if old_modal(r) or isinstance(r,BearingSweep):return super().result_properties(record)
        state=self.result_state(record)
        body=[self.txt(record.execution.case.name,14,bold=True),self.chip('ATUAL' if self.session.is_current(record) else 'DESATUALIZADO'),
              self.kv('Tipo',record.execution.case.kind),self.field('Hash do resultado',record.execution.analysis_hash,readonly=True)]
        response_types=(FrequencyResponseMatrixResult,ForcedResponseResult,GeneralTimeResponseResult,TransientResult,*HARMONIC,*SPECIAL_MODAL)
        def select(key,label,values):
            body.append(ft.Dropdown(label=label,value=str(state[key]),options=[ft.DropdownOption(str(k),v) for k,v in values],text_size=11,dense=True,
                 on_select=lambda e,k=key:self.result_set(k,int(e.control.value) if k in ('input_dof','output_dof','point_index','mode_index','selected_clearance_index','probe_index') else e.control.value)))
        dofs=[(i,dof_label(record.model,i)) for i in range(4*len(record.model.nodes))]
        if isinstance(r,response_types):select('output_dof','GL de resposta',dofs)
        if isinstance(r,FrequencyResponseMatrixResult):select('input_dof','GL de excitação',dofs)
        if isinstance(r,(FrequencyResponseMatrixResult,ForcedResponseResult,GeneralTimeResponseResult)):
            select('response','Grandeza',[('displacement','Deslocamento'),('velocity','Velocidade'),('acceleration','Aceleração')])
        count=point_count(r)
        if count and not isinstance(r,(GeneralTimeResponseResult,TransientResult)):
            state['point_index']=min(int(state['point_index']),count-1)
            select('point_index','Ponto calculado',[(i,str(i+1)) for i in range(count)])
        if isinstance(r,SPECIAL_MODAL):
            ids=np.where(r.eigenvalues.imag>0)[0];select('mode_index','Modo oscilatório',[(i,f'{i+1} · índice Core {int(k)+1}') for i,k in enumerate(ids)])
        if isinstance(r,ClearanceResult):
            select('selected_clearance_index','Local da folga',list(enumerate(f'{t} · nó {int(n)}' for t,n in zip(r.clearance_tags,r.clearance_nodes))))
            select('probe_index','Sonda radial',list(enumerate(f'{t} · nó {int(n)}' for t,n in zip(r.probe_tags,r.probe_nodes))))
        if isinstance(r,UCSResult):select('speed_units','Unidade de velocidade',[('RPM','rpm'),('rad/s','rad/s')])
        metadata=record.execution.build_metadata
        for key in ('native_abi','scope','backend'):
            value=getattr(r,'metadata',{}).get(key,metadata.get(key))
            if value is not None:body.append(self.notice(f'{key}: {value}'))
        body.extend([self.notice('Alterar seletores só muda a visualização. Valores continuam associados ao modelo e caso de origem.'),
                     self.button('Reexecutar caso',self.rerun,ft.Icons.REFRESH,disabled=self.busy),
                     self.button('Metadados / diagnóstico',self.result_diagnostics),
                     self.button('PNG',self.export_png),self.button('SVG / PDF / pacote',self.export_formats_dialog),
                     self.button('CSV completo',self.export_csv),self.button('NPZ completo',self.export_npz),self.button('Relatório e dados',self.export_report)])
        return body

    def result_diagnostics(self,e=None):
        record=self.record()
        if not record:return
        r=record.execution.result
        text=json.dumps({'case':{'name':record.execution.case.name,'kind':record.execution.case.kind,'parameters':record.execution.case.parameters,'options':record.execution.case.options},
                         'analysis_hash':record.execution.analysis_hash,'model_hash':record.model.model_hash(),
                         'execution':record.execution.build_metadata,'result':getattr(r,'metadata',{}),'view_selection':getattr(record,'view_selection',{})},
                        ensure_ascii=False,indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else str(x))
        self.page.show_dialog(ft.AlertDialog(title=self.txt('Diagnóstico e rastreabilidade',17,bold=True),
             content=ft.Container(ft.Column([ft.Text(text,size=11,selectable=True)],scroll=ft.ScrollMode.AUTO),width=750,height=520),
             actions=[self.button('Fechar',lambda e:self.page.pop_dialog())]))

    def special_phase(self,e):
        self.result_state()['phase']=float(e.control.value);self.redraw_result()

    async def animate_special(self,e=None):
        self.animating=not self.animating;document=self.document
        while self.animating and self.alive and self.document==document:
            state=self.result_state();state['phase']=(state.get('phase',0)+9)%360
            self.redraw_result();await asyncio.sleep(.12)
