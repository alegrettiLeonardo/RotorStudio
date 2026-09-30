"""Contextual properties, diagnostics and job progress views."""
from .ui_common import *


class PropertiesViews:
    def inspector(self):
        record=self.record()
        if self.document=="model":title="Propriedades do elemento";body=self.element_properties()
        elif self.document=="bearings":title="Propriedades do mancal";body=self.bearing_properties()
        elif record:title="Propriedades do resultado";body=self.result_properties(record)
        else:title="Propriedades";body=[self.notice("Selecione um elemento ou resultado.")]
        footer=[]
        if self.document=="model" and self.session.selected() is not None:
            footer=[ft.Container(body.pop(),padding=12,height=61,border=ft.Border(top=ft.BorderSide(1,self.p.line)))]
        return ft.Container(ft.Column([ft.Container(self.txt(title,12,bold=True),padding=ft.Padding.symmetric(horizontal=14,vertical=13),height=43,
                            border=ft.Border(bottom=ft.BorderSide(1,self.p.line))),
                            ft.Container(ft.Column(body,spacing=8,scroll=ft.ScrollMode.AUTO,expand=True),padding=14,expand=True),*footer],spacing=0,expand=True),
                            width=300,bgcolor=self.p.surface,border=ft.Border(left=ft.BorderSide(1,self.p.line)))

    def element_properties(self):
        entity=self.session.selected();ref=self.session.selection
        if entity is None:return [self.notice("Clique na geometria, árvore ou tabela para selecionar um elemento."),self.button("Adicionar elemento",self.add_dialog,ft.Icons.ADD)]
        self.form_entity=entity
        controls=[self.txt(self.label_entity(ref.kind,ref.index,entity),14,bold=True),self.txt(type(entity).__name__,10,muted=True),ft.Divider(color=self.p.line)]
        definitions=specs(entity)
        if definitions:
            values=form_values(entity);section=None
            if ref.kind=="shafts":
                z={n.number:n.z_m for n in self.session.project.model.nodes}
                controls.append(self.field("Comprimento (derivado dos nós)",f"{m_to_mm(z[entity.node2]-z[entity.node1]):g}","mm",readonly=True))
            for spec in definitions:
                if spec.section!=section:section=spec.section;controls.append(self.txt(section,9,bold=True,muted=True))
                field=self.field(spec.label,values[spec.key],spec.unit,key=f"property-{spec.key}")
                field.disabled=self.busy
                self.form_fields[spec.key]=field;controls.append(field)
            self.form_original=values
        else:
            text=entity_json(entity);self.json_original=text
            self.json_field=self.field("Definição tipada · unidades SI",text,multiline=True,key="entity-json")
            self.json_field.disabled=self.busy
            controls += [self.notice("Editor estrutural: preserva todos os campos e unidades canônicas do Core."),self.json_field]
        controls += [self.notice("Aplicar valida o modelo antes de confirmar. Cancelar ou uma entrada inválida não modifica o projeto."),
                     ft.Row([self.button("Restaurar",lambda e:self.render()),self.button("Aplicar",self.apply_clicked,ft.Icons.CHECK,primary=True,key="apply-properties")],spacing=8)]
        return controls

    def result_properties(self,record):
        current=self.session.is_current(record)
        controls=[self.txt(record.execution.case.name,14,bold=True),self.chip("ATUAL" if current else "DESATUALIZADO",self.p.success if current else self.p.warning),
                  self.kv("Análise",record.execution.case.kind),self.kv("Backend","Fortran 2018 / ctypes"),
                  self.field("Hash de análise",record.execution.analysis_hash,readonly=True)]
        r=record.execution.result
        points=r if isinstance(r,list) and r and isinstance(r[0],ModalResult) else ([r] if isinstance(r,ModalResult) else None)
        if points:
            self.speed_index=min(self.speed_index,len(points)-1)
            result=points[self.speed_index];ids=positive_modes(points[0],12)
            self.mode_ordinal=min(self.mode_ordinal,max(0,len(ids)-1))
            controls.append(ft.Dropdown(label="Ponto calculado [rpm]",value=str(self.speed_index),options=[ft.DropdownOption(str(i),f"{rad_s_to_rpm(p.speed_rad_s):g}") for i,p in enumerate(points)],on_select=self.speed_selected,text_size=12,dense=True))
            controls.append(ft.Dropdown(label="Modo oscilatório",value=str(self.mode_ordinal),options=[ft.DropdownOption(str(i),f"{i+1} · {whirl_label(result,k)} · {result.natural_frequency_hz[k]:.3f} Hz") for i,k in enumerate(ids)],on_select=lambda e:self.mode_selected(int(e.control.value)),text_size=12,dense=True))
            if len(ids):
                k=ids[self.mode_ordinal]
                controls.extend([self.kv("Frequência natural fn",f"{result.natural_frequency_hz[k]:.4f} Hz"),
                                 self.kv("Frequência amortecida fd",f"{abs(result.eigenvalues[k].imag)/(2*np.pi):.4f} Hz"),
                                 self.kv("Amortecimento",f"{result.damping_ratio[k]*100:.4f} %"),
                                 self.kv("Precessão",whirl_label(result,k))])
            controls.append(self.txt("EXIBIÇÃO",9,bold=True,muted=True))
            if self.subview=="campbell" and len(points)>1:
                for label,attr in [("Precessão direta · FW","show_forward"),("Precessão retrógrada · BW","show_backward"),("Excitações 1× / 2×","show_excitation"),("Exibir frequência amortecida fd","damped_frequency")]:
                    controls.append(ft.Checkbox(label=label,value=getattr(self,attr),label_style=ft.TextStyle(size=11),on_change=lambda e,a=attr:self.result_toggle(a,e.control.value)))
                controls.append(self.notice("Cursor restrito aos pontos realmente calculados. Tracking modal executado pelo Core, não pela interface."))
            else:
                for label,attr in [("Órbitas nas estações","show_orbits"),("Referência não deformada","show_reference"),("Marcadores dos nós","show_markers")]:
                    controls.append(ft.Checkbox(label=label,value=getattr(self,attr),label_style=ft.TextStyle(size=11),on_change=lambda e,a=attr:self.result_toggle(a,e.control.value)))
                controls += [self.txt("Amplificação visual",10,muted=True),ft.Slider(min=.2,max=2,divisions=36,value=self.amplitude,on_change=self.amplitude_changed),
                             self.txt("Azimute da câmera",10,muted=True),ft.Slider(min=-180,max=180,divisions=72,value=self.azim,on_change=lambda e:self.angle_changed("azim",e)),
                             self.txt("Elevação da câmera",10,muted=True),ft.Slider(min=-70,max=70,divisions=28,value=self.elev,on_change=lambda e:self.angle_changed("elev",e)),
                             self.notice("O modo tem amplitude normalizada. A animação não é uma resposta transiente nem uma amplitude física.")]
        controls += [ft.Divider(color=self.p.line),self.button("Reexecutar",self.rerun,ft.Icons.REFRESH,disabled=self.busy),
                    self.button("PNG",self.export_png,ft.Icons.IMAGE_OUTLINED),self.button("CSV / valores complexos",self.export_csv,ft.Icons.TABLE_CHART_OUTLINED),
                    self.button("Relatório + dados NPZ",self.export_report,ft.Icons.DESCRIPTION_OUTLINED)]
        return controls

    def speed_selected(self,e):self.speed_index=int(e.control.value);self.render()

    def bearing_properties(self):
        ref=self.bearing_ref
        if ref is None:return [self.notice("Nenhum mancal no projeto.")]
        values=getattr(self.session.project.model,ref.kind)
        if ref.index>=len(values):return [self.notice("Selecione novamente o mancal.")]
        b=values[ref.index]
        controls=[self.txt(self.label_entity(ref.kind,ref.index,b),14,bold=True),self.txt(type(b).__name__,11,muted=True),
                  self.kv("Nó",b.node),self.kv("Política de avaliação","Síncrona · ω = Ω")]
        if isinstance(b,CoefficientBearing):
            controls += [self.kv("Interpolação",b.interpolation),self.kv("Pontos de rotação",len(b.speed_rad_s)),
                         self.kv("Pontos de frequência",len(b.frequency_rad_s)),self.notice("Tabela tipada. Importação e interpolação preservam as unidades e os sinais Kxy/Kyx/Cxy/Cyx.")]
        controls += [self.button("Editar propriedades",lambda e:self.select_entity(ref)),self.button("Editar / importar tabela",self.table_dialog),
                     ft.Divider(color=self.p.line)]
        if self.bearing_record:
            r=self.bearing_record.execution.result;i=min(self.speed_index,len(r.speeds_rad_s)-1)
            controls.append(self.chip("ATUAL" if self.session.is_current(self.bearing_record) else "DESATUALIZADO"))
            controls.append(self.kv("Ponto calculado",f"{rad_s_to_rpm(r.speeds_rad_s[i]):g} rpm"))
            for prefix,array,unit in [("K",r.K,"N/m"),("C",r.C,"N·s/m"),("M",r.M,"kg")]:
                for a,c in [(0,0),(0,1),(1,0),(1,1)]:controls.append(self.kv(f"{prefix}{'xy'[a]}{'xy'[c]}",f"{array[i,a,c]:.5g} {unit}"))
            controls += [self.button("Exportar CSV",self.export_csv),self.button("Relatório",self.export_report)]
        else:controls.append(self.notice("Nenhum resultado nativo calculado para esta seleção."))
        return controls

    def messages(self):
        self.message_rows=ft.Column([self.message_row(level,text) for level,text in self.session.messages[-3:]],spacing=4)
        self.progress_bar=ft.ProgressBar(value=None if self.busy else 0,height=3,visible=self.busy,color=self.p.primary,bgcolor=self.p.line)
        self.progress_text=self.txt("Execução nativa em andamento" if self.busy else "Mensagens",10,bold=True)
        return ft.Container(ft.Column([self.progress_bar,ft.Row([self.progress_text,self.txt("Diagnósticos e execução",10,muted=True)],spacing=22),self.message_rows],spacing=7),
                            bgcolor=self.p.surface,height=116,padding=ft.Padding.symmetric(horizontal=15,vertical=10),
                            border=ft.Border(top=ft.BorderSide(1,self.p.line)))

    def message_row(self,level,text):
        color=self.p.error if level=="ERRO" else (self.p.warning if level=="AVISO" else self.p.primary)
        return ft.Row([self.txt(level,9,bold=True,color=color),self.txt(text,10,muted=True,expand=True)],spacing=12)

    def refresh_messages(self):
        self.message_rows.controls=[self.message_row(l,t) for l,t in self.session.messages[-3:]]
        if self.busy:
            self.progress_bar.visible=True
            self.progress_bar.value=self.job.completed/self.job.total if self.job.total else None
            self.progress_text.value=f"{self.job.state} · {self.job.completed}/{self.job.total} pontos" if self.job.total else f"{self.job.state} · chamada nativa"
        else:self.progress_bar.visible=False;self.progress_text.value="Mensagens"
        self.status_text.value=self.status();self.page.update()

