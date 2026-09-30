"""Model, Campbell, bearing and modal result workspaces."""
from .ui_common import *


class WorkspaceViews:
    def model_view(self):
        model=self.session.project.model
        heading=ft.Row([ft.Column([self.txt("Modelo do rotor",23,bold=True),self.txt("Editor de engenharia · geometria, elementos e condições de apoio",11,muted=True)],spacing=4,expand=True),
                        self.button("Adicionar elemento",self.add_dialog,ft.Icons.ADD)],spacing=10)
        svg,self.hitboxes=rotor_svg(model,self.session.selection,dark=self.dark,width=self.model_width,height=self.model_height,
                     zoom=self.zoom,pan=self.pan,nodes=self.show_nodes,elements=self.show_elements,bearings=self.show_bearings,dimensions=self.show_dimensions)
        self.model_image=ft.Image(src=svg,fit=ft.BoxFit.FILL,width=float("inf"),height=float("inf"),gapless_playback=True)
        canvas=ft.Container(ft.GestureDetector(self.model_image,on_tap_down=self.pick_rotor,on_pan_update=self.pan_rotor,drag_interval=35,
                    mouse_cursor=ft.MouseCursor.MOVE),alignment=ft.Alignment.CENTER,expand=True,on_size_change=self.resize_canvas)
        tools=ft.Container(ft.Row([self.ib(ft.Icons.ZOOM_IN,"Ampliar",lambda e:self.zoom_model(1.2)),
                    self.ib(ft.Icons.ZOOM_OUT,"Reduzir",lambda e:self.zoom_model(1/1.2)),
                    self.ib(ft.Icons.FIT_SCREEN,"Ajustar vista",self.fit_model),self.txt("Clique para selecionar · arraste para deslocar",10,muted=True)],spacing=2),height=34,padding=ft.Padding.only(left=8))
        toggles=ft.Row([ft.Checkbox(label=label,value=getattr(self,attr),on_change=lambda e,a=attr:self.model_toggle(a,e.control.value),
                          label_style=ft.TextStyle(size=10,color=self.p.muted)) for label,attr in [("Nós","show_nodes"),("Elementos","show_elements"),("Mancais","show_bearings"),("Cotas","show_dimensions")]],spacing=0)
        plot=self.card("Vista longitudinal",ft.Column([tools,canvas,ft.Container(toggles,height=34)],spacing=0,expand=True),
                   [self.chip(f"{len(model.nodes)} nós"),self.chip(f"{len(model.shafts)} elementos"),self.chip(f"{len(model.disks)} discos")],expand=True)
        z={n.number:n.z_m for n in model.nodes}
        rows=[]
        for i,s in enumerate(model.shafts):
            length=m_to_mm(z[s.node2]-z[s.node1]) if s.node1 in z and s.node2 in z else float('nan')
            rows.append([f"E{i+1:02d}",f"{s.node1} → {s.node2}",f"{length:g}",
                         f"{m_to_mm(s.outer_diameter_m):g}" if hasattr(s,"outer_diameter_m") else "Variável / EI",
                         f"{m_to_mm(s.inner_diameter_m):g}" if hasattr(s,"inner_diameter_m") else "—",f"{s.shaft_type}"])
        selected=self.session.selection.index if self.session.selection and self.session.selection.kind=="shafts" else None
        table=self.card("Elementos do eixo",self.table(["Elemento","Nós","Compr. [mm]","Ø externo [mm]","Ø interno [mm]","Tipo DRM"],rows,
                              selected=selected,select=lambda i:self.select_entity(EntityRef("shafts",i)),height=160))
        actions=ft.Row([self.button(label,lambda e,k=kind:self.analysis_dialog(kind=k),ft.Icons.QUERY_STATS)
                        for kind,label in ANALYSES],spacing=6,scroll=ft.ScrollMode.AUTO)
        return ft.Column([heading,plot,table,actions],spacing=12,expand=True)

    def redraw_model(self):
        if self.document!="model" or not hasattr(self,"model_image"):return
        svg,self.hitboxes=rotor_svg(self.session.project.model,self.session.selection,dark=self.dark,width=self.model_width,height=self.model_height,
              zoom=self.zoom,pan=self.pan,nodes=self.show_nodes,elements=self.show_elements,bearings=self.show_bearings,dimensions=self.show_dimensions)
        self.model_image.src=svg;self.model_image.update()
    def resize_canvas(self,e):
        if e.width>0 and e.height>0:
            self.model_width,self.model_height=float(e.width),float(e.height);self.redraw_model()
    def pick_rotor(self,e):
        point=e.local_position
        for hit in reversed(self.hitboxes):
            if hit.contains(point.x,point.y):self.select_entity(EntityRef(hit.kind,hit.index));break
    def pan_rotor(self,e):
        self.pan+=e.local_delta.x;self.redraw_model()
    def zoom_model(self,factor):
        self.zoom=max(.3,min(8,self.zoom*factor));self.redraw_model()
    def fit_model(self,e=None):self.zoom,self.pan=1.,0.;self.redraw_model()
    def model_toggle(self,attr,value):setattr(self,attr,value);self.redraw_model()

    def result_view(self):
        record=self.record();r=record.execution.result
        points=r if isinstance(r,list) and r and isinstance(r[0],ModalResult) else ([r] if isinstance(r,ModalResult) else None)
        self.speed_index=min(self.speed_index,(len(points)-1) if points else 0)
        if points:
            if points[self.speed_index].eigenvectors is None and self.subview in ('modes','orbits'):
                self.subview='campbell' if len(points)>1 else 'roots'
            if len(points)==1 and self.subview=='campbell':
                self.subview='modes' if points[0].eigenvectors is not None else 'roots'
        title=("Diagrama de Campbell" if len(points)>1 and self.subview=="campbell" else "Forma modal 3D") if points else record.execution.case.name
        if points and self.subview in ("orbits","roots"):title={"orbits":"Órbitas modais","roots":"Lugar das raízes"}[self.subview]
        header=ft.Row([ft.Column([self.txt(title,23,bold=True),self.txt(f"{record.execution.case.name} · {record.execution.analysis_hash[:14]}",11,muted=True)],spacing=4,expand=True),
                        self.chip("ATUAL" if self.session.is_current(record) else "DESATUALIZADO",self.p.success if self.session.is_current(record) else self.p.warning),
                        self.button("Exportar",self.export_png,ft.Icons.FILE_DOWNLOAD_OUTLINED)],spacing=8)
        body=[header]
        if not self.session.is_current(record):body.append(self.notice("O modelo ou caso mudou. Este resultado conserva a geometria original; reexecute para atualizar.",warning=True))
        if points:
            result=points[self.speed_index]
            ids=positive_modes(points[0],len(points[0].eigenvalues))
            self.mode_ordinal=min(self.mode_ordinal,max(0,len(ids)-1))
            rows=[[str(j+1),f"{result.natural_frequency_hz[k]:.4f}",f"{100*result.damping_ratio[k]:.4f}",whirl_label(result,k)] for j,k in enumerate(ids)]
            tabs=[self.button(label,lambda e,key=key:self.set_subview(key),disabled=((len(points)==1 and key=="campbell") or (result.eigenvectors is None and key in ("modes","orbits"))))
                   for key,label in [("campbell","Campbell"),("modes","Modos 3D"),("orbits","Órbitas"),("roots","Lugar das raízes")]]
            body.append(ft.Row(tabs,spacing=5,scroll=ft.ScrollMode.AUTO))
            if len(points)>1 and not any(pt.metadata.get("campbell_outer_tracking") for pt in points[1:]):
                body.append(self.notice("Varredura legada sem tracking modal: linhas conectam índices ordenados, não ramos físicos identificados.",warning=True))
            self.plot_image=ft.Image(src=b"",fit=ft.BoxFit.CONTAIN,expand=True,width=float("inf"),height=float("inf"),gapless_playback=True)
            plot_container=ft.Container(self.plot_image,expand=True,alignment=ft.Alignment.CENTER)
            body.append(self.card("Resultados calculados · Core Fortran",plot_container,[self.chip(f"{rad_s_to_rpm(result.speed_rad_s):g} rpm"),self.chip(f"{len(points)} pontos")],expand=True))
            if self.subview=="modes" or len(points)==1 and self.subview=="campbell":
                self.phase_slider=ft.Slider(min=0,max=360,divisions=180,value=self.phase,on_change=self.phase_changed,expand=True)
                body.append(ft.Row([self.button("Animar",self.animate,ft.Icons.PLAY_ARROW),self.txt("Fase",10,muted=True),self.phase_slider,
                                    self.txt("Amplitude normalizada · não é deslocamento físico",10,muted=True)],spacing=9))
            body.append(self.card("Seleção modal · frequência natural fn",self.table(["Modo","Frequência [Hz]","Amortecimento [%]","Precessão"],rows,
                         selected=self.mode_ordinal,select=self.mode_selected,height=135)))
        else:
            self.plot_image=ft.Image(src=b"",fit=ft.BoxFit.CONTAIN,expand=True,width=float("inf"),height=float("inf"),gapless_playback=True)
            body.append(self.card("Visualização do resultado",self.plot_image,expand=True))
            from .jobs import arrays_of
            rows=[[k,str(v.shape),str(v.dtype)] for k,v in arrays_of(r).items()]
            body.append(self.card("Dados numéricos disponíveis",self.table(["Grandeza Core","Dimensões","Tipo"],rows,height=145)))
        self.redraw_result(update=False)
        return ft.Column(body,spacing=10,expand=True)

    def redraw_result(self,update=True):
        record=self.record()
        if not record or self.plot_image is None:return
        r=record.execution.result
        record.view_selection=dict(view=self.subview,speed_index=self.speed_index,mode_ordinal=self.mode_ordinal,
            phase_deg=self.phase,visual_scale=self.amplitude,elev=self.elev,azim=self.azim,
            damped_frequency=self.damped_frequency,campbell_modes=self.campbell_modes,
            excitation=self.show_excitation,forward=self.show_forward,backward=self.show_backward)
        try:
            if isinstance(r,BearingSweep):fig=bearing_figure(r,dark=self.dark,damping=self.bearing_damping,cursor=min(self.speed_index,len(r.speeds_rad_s)-1))
            else:
                points=r if isinstance(r,list) and r and isinstance(r[0],ModalResult) else ([r] if isinstance(r,ModalResult) else None)
                if points:
                    result=points[self.speed_index];ids=positive_modes(points[0],len(points[0].eigenvalues))
                    if not len(ids):self.subview="roots"
                    k=ids[min(self.mode_ordinal,len(ids)-1)] if len(ids) else 0
                    if len(points)>1 and self.subview=="campbell":
                        fig=campbell_figure(points,dark=self.dark,cursor=self.speed_index,forward=self.show_forward,backward=self.show_backward,
                                            excitation=self.show_excitation,damped=self.damped_frequency,nx=float(record.execution.case.options.get("nx",2.)),count=self.campbell_modes)
                    elif self.subview in ("orbits","roots"):
                        fig,ax=base_figure(self.dark)
                        if self.subview=="roots":
                            for kk in range(len(points[0].eigenvalues)):
                                ev=np.asarray([pt.eigenvalues[kk] for pt in points]);ax.plot(ev.real,ev.imag/(2*np.pi),lw=1,marker="." if len(points)==1 else None)
                            ax.set_xlabel("Parte real do autovalor [s⁻¹]");ax.set_ylabel("Parte imaginária / 2π [Hz]")
                        else:
                            v=result.eigenvectors[:,k];th=np.exp(1j*np.linspace(0,2*np.pi,180))
                            n=max(np.max(np.abs(v[0::4])),np.max(np.abs(v[1::4])),1e-30)
                            for i,node in enumerate(record.model.nodes):
                                ax.plot(np.real(v[4*i]*th)/n,np.real(v[4*i+1]*th)/n,lw=1,label=f"Nó {node.number}")
                            ax.set_aspect("equal");ax.set_xlabel("X normalizado");ax.set_ylabel("Y normalizado")
                            ax.legend(fontsize=7,ncol=3,frameon=False,labelcolor=self.p.muted)
                        fig.subplots_adjust(left=.11,right=.97,top=.93,bottom=.17)
                    else:
                        fig=modal_figure(record.model,result,k,dark=self.dark,phase=self.phase,scale=self.amplitude,elev=self.elev,azim=self.azim,
                                         orbits=self.show_orbits,reference=self.show_reference,markers=self.show_markers)
                else:fig=generic_figure(record,dark=self.dark)
            self.figure=fig;self.plot_png=png_bytes(fig);self.plot_image.src=self.plot_png
        except Exception as exc:
            self.session.log("VISUALIZAÇÃO",str(exc))
            self.plot_image.error_content=ft.Text(str(exc),color=self.p.error)
            self.plot_image.src=b"invalid"
        if update:self.plot_image.update()

    def set_subview(self,key):self.subview=key;self.render()
    def mode_selected(self,i):
        self.mode_ordinal=i
        r=self.record().execution.result;points=r if isinstance(r,list) else [r]
        self.subview="modes" if points[min(self.speed_index,len(points)-1)].eigenvectors is not None else "roots"
        self.render()
    def phase_changed(self,e):self.phase=float(e.control.value);self.redraw_result()
    def amplitude_changed(self,e):self.amplitude=float(e.control.value);self.redraw_result()
    def angle_changed(self,attr,e):setattr(self,attr,float(e.control.value));self.redraw_result()
    def result_toggle(self,attr,value):setattr(self,attr,value);self.redraw_result()
    async def animate(self,e=None):
        self.animating=not self.animating
        if not self.animating:return
        document=self.document
        while self.animating and self.alive and self.document==document:
            self.phase=(self.phase+9)%360
            if hasattr(self,"phase_slider"):self.phase_slider.value=self.phase
            self.redraw_result()
            self.page.update()
            await asyncio.sleep(.12)

    def bearing_view(self):
        refs=[EntityRef(k,i) for k in ("bearings","advanced_bearings") for i,_ in enumerate(getattr(self.session.project.model,k))]
        if self.bearing_ref not in refs:self.bearing_ref=refs[0] if refs else None
        heading=ft.Row([ft.Column([self.txt("Desempenho do mancal",23,bold=True),self.txt("Coeficientes e condições de apoio · avaliação nativa",11,muted=True)],spacing=4,expand=True),
                         self.button("Editar tabela",self.table_dialog,ft.Icons.TABLE_CHART_OUTLINED,disabled=self.bearing_ref is None),
                         self.button("Calcular",self.bearing_analysis,ft.Icons.PLAY_ARROW,primary=True,disabled=self.bearing_ref is None or self.busy)],spacing=8)
        if not refs:return ft.Column([heading,self.notice("Adicione um mancal no editor do rotor.")],spacing=14)
        selector=ft.Dropdown(value=f"{self.bearing_ref.kind}:{self.bearing_ref.index}",options=[ft.DropdownOption(f"{r.kind}:{r.index}",self.label_entity(r.kind,r.index,getattr(self.session.project.model,r.kind)[r.index])) for r in refs],
                             on_select=self.bearing_selected,label="Mancal selecionado",text_size=12,dense=True,height=48)
        bearing=getattr(self.session.project.model,self.bearing_ref.kind)[self.bearing_ref.index]
        symbol=f'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="235"><rect width="100%" height="100%" fill="{self.p.surface}"/><g fill="{self.p.selected}" stroke="{self.p.muted}"><circle cx="150" cy="102" r="66"/><circle cx="150" cy="102" r="53" fill="{self.p.surface}"/><circle cx="150" cy="102" r="32" fill="{self.p.cyan}"/><path d="M 130 161 L 100 190 L 200 190 L 170 161"/></g><path d="M 70 102 H 230 M 150 20 V 198" stroke="{self.p.muted}" stroke-dasharray="5 4"/><text x="150" y="220" text-anchor="middle" font-size="12" fill="{self.p.muted}">Símbolo do apoio · sem escala</text></svg>'
        schematic=self.card("Esquema do apoio",ft.Column([ft.Image(src=symbol.encode(),fit=ft.BoxFit.CONTAIN,expand=True),self.notice("O símbolo não representa folga, filme ou posição de equilíbrio calculados.")],spacing=2,expand=True),expand=True)
        controls=[heading,selector]
        r=self.bearing_record
        if r is not None:
            result=r.execution.result;self.speed_index=min(self.speed_index,len(result.speeds_rad_s)-1)
            self.plot_image=ft.Image(src=b"",fit=ft.BoxFit.CONTAIN,expand=True,width=float("inf"),height=float("inf"),gapless_playback=True)
            curve=self.card("Coeficientes × rotação",self.plot_image,[self.button("Rigidez K",lambda e:self.bearing_metric(False)),self.button("Amort. C",lambda e:self.bearing_metric(True))],expand=True)
            controls.append(ft.Row([ft.Container(schematic,expand=3),ft.Container(curve,expand=6)],expand=True,spacing=12,vertical_alignment=ft.CrossAxisAlignment.STRETCH))
            values=result.C if self.bearing_damping else result.K
            pref="C" if self.bearing_damping else "K";unit="N·s/m" if self.bearing_damping else "N/m"
            rows=[[f"{rad_s_to_rpm(w):g}",*[f"{values[i,a,b]:.6g}" for a,b in [(0,0),(0,1),(1,0),(1,1)]]] for i,w in enumerate(result.speeds_rad_s)]
            controls.append(self.card("Tabela de coeficientes calculados",self.table(["Rotação [rpm]",f"{pref}xx [{unit}]",f"{pref}xy [{unit}]",f"{pref}yx [{unit}]",f"{pref}yy [{unit}]"],rows,
                                 selected=self.speed_index,select=self.bearing_point,height=150)))
            controls.append(self.notice("GL radial restringido: entradas nulas não significam apoio sem rigidez." if result.constrained else "K/C/M avaliados pelo núcleo. Os sinais dos termos cruzados são preservados.",warning=result.constrained))
            if not self.session.is_current(r):controls.append(self.notice("Resultado do mancal desatualizado. Reexecute após a edição.",warning=True))
            self.redraw_result(update=False)
        else:
            controls.append(ft.Row([ft.Container(schematic,width=310),ft.Container(self.notice("Nenhum coeficiente calculado. Selecione o mancal e pressione Calcular."),expand=True)],expand=True,spacing=14))
        return ft.Column(controls,spacing=12,expand=True)

    def bearing_metric(self,damping):self.bearing_damping=damping;self.render()
    def bearing_point(self,i):self.speed_index=i;self.render()
    def bearing_selected(self,e):
        kind,index=e.control.value.split(":");self.bearing_ref=EntityRef(kind,int(index));self.bearing_record=None;self.speed_index=0;self.render()
