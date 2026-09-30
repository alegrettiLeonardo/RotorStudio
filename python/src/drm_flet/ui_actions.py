"""Transactional editor, persistence, native jobs and export handlers."""
from .ui_common import *


class EditorActions:
    def form_changed(self):
        if self.form_fields:return any(str(c.value)!=self.form_original.get(k,"") for k,c in self.form_fields.items())
        return self.json_field is not None and self.json_field.value!=self.json_original

    def select_entity(self,ref):
        if self.form_changed():
            self.page.run_task(self.confirm_navigate,ref);return
        self.session.select(ref);self.document="model";self.expanded.add(ref.kind);self.render()

    async def confirm_navigate(self,ref):
        if await self.confirm("Edição não aplicada","Descartar a edição do formulário e mudar a seleção?"):
            self.session.select(ref);self.document="model";self.expanded.add(ref.kind);self.render()

    def navigate(self,document):
        if self.form_changed():self.page.run_task(self.confirm_document,document);return
        self.document=document
        record=self.record()
        if record and isinstance(record.execution.result,BearingSweep):self.bearing_record=record;self.document="bearings"
        self.render()

    async def confirm_document(self,document):
        if await self.confirm("Edição não aplicada","Descartar a edição do formulário e mudar de documento?"):
            self.form_fields={};self.json_field=None;self.navigate(document)

    def apply_properties(self):
        if self.form_entity is None:return True
        if self.busy:
            self.error("Análise em execução","Aguarde o término antes de aplicar alterações.");return False
        try:
            entity=from_form(self.form_entity,{k:v.value for k,v in self.form_fields.items()}) if self.form_fields else from_json(self.form_entity,self.json_field.value)
            self.session.replace_entity(self.session.selection,entity)
            self.render();return True
        except Exception as e:self.error("Não foi possível aplicar",e);return False
    def apply_clicked(self,e=None):self.apply_properties()
    def undo(self,e=None):
        if not self.may_edit():return
        self.session.undo();self.render()
    def redo(self,e=None):
        if not self.may_edit():return
        self.session.redo();self.render()
    def may_edit(self):
        if self.busy:
            self.error("Análise em execução","Aguarde o término antes de editar o modelo.");return False
        if self.form_changed():
            self.error("Edição pendente","Aplique ou restaure o formulário antes desta ação.");return False
        return True
    def toggle_theme(self,e=None):
        if self.form_changed():
            self.error("Edição pendente","Aplique ou restaure o formulário antes de alternar o tema.");return
        self.dark=not self.dark;self.render()

    def error(self,title,error):
        self.session.log("ERRO",str(error))
        if not self.alive:
            return
        dialog=ft.AlertDialog(title=self.txt(title,18,bold=True),content=ft.Container(ft.Text(str(error),size=13,selectable=True),width=600),
                              actions=[self.button("Fechar",lambda e:self.page.pop_dialog())])
        self.page.show_dialog(dialog)
        if hasattr(self,"message_rows"):self.refresh_messages()

    async def confirm(self,title,message):
        future=asyncio.get_running_loop().create_future()
        def finish(value):
            self.page.pop_dialog()
            if not future.done():future.set_result(value)
        self.page.show_dialog(ft.AlertDialog(modal=True,title=self.txt(title,18,bold=True),content=ft.Text(message,size=13),
                    actions=[self.button("Cancelar",lambda e:finish(False)),self.button("Continuar",lambda e:finish(True),primary=True)]))
        return await future

    async def may_replace_project(self):
        if self.busy:self.error("Análise em execução","Cancele e aguarde o ponto seguro antes de trocar o projeto.");return False
        if self.session.dirty or self.form_changed():
            return await self.confirm("Alterações não salvas","Descartar as alterações e abrir outro projeto?")
        return True

    async def new_project(self,e=None):
        if await self.may_replace_project():self.session.reset(RotorProject("Novo projeto",RotorModel()));self.document="model";self.bearing_record=None;self.bearing_ref=None;self.render()
    async def open_example(self,e=None):
        if await self.may_replace_project():self.session.reset(reference_project());self.document="model";self.bearing_record=None;self.bearing_ref=self.first_bearing();self.render()

    async def open_project(self,e=None):
        if not await self.may_replace_project():return
        try:
            files=await ft.FilePicker().pick_files(dialog_title="Abrir projeto RotorStudio",allow_multiple=False,
                    file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=["json","txt"],with_data=self.page.web)
            if not files:return
            file=files[0]
            if file.path and not self.page.web:self.session.open(file.path)
            elif file.bytes is not None:self.session.open_bytes(file.bytes,Path(file.name).suffix.lower())
            else:raise ValueError("O seletor não retornou os bytes do arquivo.")
            self.document="model";self.bearing_record=None;self.bearing_ref=self.first_bearing();self.render()
        except Exception as exc:self.error("Falha ao abrir projeto",exc)

    async def write_bytes(self,data,name,*,project=False):
        suffix=Path(name).suffix.lstrip('.')
        path=await ft.FilePicker().save_file(dialog_title="Salvar arquivo",file_name=name,
                        file_type=ft.FilePickerFileType.CUSTOM,allowed_extensions=[suffix],src_bytes=data if self.page.web else None)
        if self.page.web:
            self.session.log("EXPORTAÇÃO","Arquivo enviado ao navegador; o download é controlado pelo navegador.")
            return None
        if path:
            if not Path(path).suffix:path=path+"."+suffix
            if project:self.session.save(path)
            else:Path(path).write_bytes(data);self.session.log("EXPORTAÇÃO",path)
        return path

    async def save_project(self,e=None):
        if self.form_changed() and not self.apply_properties():return
        try:
            if self.session.path and not self.page.web:self.session.save(self.session.path)
            else:await self.write_bytes(self.session.as_bytes(),"rotor_project.json",project=True)
            self.render()
        except Exception as exc:self.error("Falha ao salvar",exc)
    async def save_as(self,e=None):
        if self.form_changed() and not self.apply_properties():return
        try:await self.write_bytes(self.session.as_bytes(),"rotor_project.json",project=True);self.render()
        except Exception as exc:self.error("Falha ao salvar",exc)

    async def window_event(self,e):
        if e.type==ft.WindowEventType.CLOSE:
            if self.busy:self.error("Análise em execução","Cancele e aguarde a chamada nativa antes de fechar.");return
            if (self.session.dirty or self.form_changed()) and not await self.confirm("Fechar RotorStudio","Descartar alterações não salvas e fechar?"):return
            self.alive=False;self.animating=False;await self.page.window.destroy()
    def disconnect(self,e=None):
        self.alive=False;self.animating=False
        if self.busy:self.job.cancel()
    async def keyboard(self,e):
        if not (e.ctrl or e.meta):return
        key=e.key.lower()
        if key=="s":await self.save_project()
        elif key=="o":await self.open_project()
        elif key=="z":self.undo()
        elif key=="y":self.redo()

    def close_result(self,key):
        self.session.records=[r for r in self.session.records if r.id!=key]
        if self.bearing_record and self.bearing_record.id==key:self.bearing_record=None
        if self.document==key:self.document="model"
        self.render()

    async def remove_selected(self,e=None):
        if not self.may_edit():return
        ref=self.session.selection
        if ref is None:return
        if not await self.confirm("Remover elemento","Remover a seleção? Referências inválidas serão bloqueadas e a ação pode ser desfeita."):return
        try:self.session.remove_entity(ref);self.render()
        except Exception as exc:self.error("Remoção bloqueada",exc)

    def add_dialog(self,e=None):
        if not self.may_edit():return
        kind=ft.Dropdown(value="nodes",label="Elemento",text_size=12,options=[ft.DropdownOption(k,v) for k,v in NAMES.items() if k in ("nodes","shafts","disks","bearings","advanced_bearings","forces")])
        node=self.field("Nó inicial / nó do componente","1")
        end=self.field("Nó final (eixo)","2")
        z=self.field("Z (novo nó)","0","mm")
        def submit(e):
            try:
                m=self.session.project.model;ni=number(node.value,integer=True);ne=number(end.value,integer=True)
                k=kind.value
                if k=="nodes":value=Node(ni,float(mm_to_m(number(z.value))))
                elif k=="shafts":value=ShaftElement(2,ni,ne,.05,0,7850,210e9,80.77e9)
                elif k=="disks":value=Disk.geometric(ni,7850,.05,.25,.05)
                elif k=="bearings":value=Bearing(3,ni,(1e7,1e7,1500.,1500.))
                elif k=="advanced_bearings":value=CoefficientBearing(ni,1e7,1500.,tag=f"M{len(m.advanced_bearings)+1}")
                else:value=Force(1,(ni,.001,0.))
                self.session.add_entity(k,value);self.page.pop_dialog();self.document="model";self.expanded.add(k);self.render()
            except Exception as exc:self.error("Não foi possível adicionar",exc)
        self.page.show_dialog(ft.AlertDialog(title=self.txt("Adicionar elemento",18,bold=True),content=ft.Container(ft.Column([kind,node,end,z,
               self.notice("Valores iniciais são um ponto de partida explícito. Revise todas as propriedades após adicionar.")],tight=True,spacing=12),width=420),
               actions=[self.button("Cancelar",lambda e:self.page.pop_dialog()),self.button("Adicionar",submit,primary=True)]))

    def analysis_dialog(self,e=None,*,kind="modal_sweep"):
        if self.busy:self.error("Análise em execução","Aguarde ou solicite cancelamento.");return
        if self.form_changed() and not self.apply_properties():return
        if kind=="static" and (self.session.project.model.advanced_bearings or self.session.project.model.rotors or self.session.project.model.bend):
            self.error("Estática fora do escopo do Core", "A1 requer eixo circular simples e apoios radiais clássicos. Mancais avançados, rotores coaxiais e pré-curvatura não serão convertidos ou aproximados automaticamente.");return
        name=self.field("Nome do caso",f"{dict(ANALYSES).get(kind,kind)}_{len(self.session.project.analyses)+1:02d}")
        speed=self.field("Rotação de operação","3600","rpm",key="analysis-speed")
        start=self.field("Rotação inicial","0","rpm")
        end=self.field("Rotação final","6000","rpm")
        count=self.field("Número de pontos","31")
        modal_policy=ft.Dropdown(label="Política dos coeficientes",value="SYNCHRONOUS_COEFFICIENTS",text_size=11,
                     options=[ft.DropdownOption("SYNCHRONOUS_COEFFICIENTS","Síncronos · ω = Ω"),ft.DropdownOption("MATCHED_WHIRL","Whirl casado · Core B17")])
        controls=[name]
        if kind=="modal":controls += [speed,modal_policy]
        elif kind=="modal_sweep":controls += [start,end,count,modal_policy]
        elif kind=="frequency_response":controls += [start,end,count,self.notice("Usa os desbalanceamentos/forças síncronas já definidos no projeto.")]
        elif kind=="critical_speeds":controls += [self.notice(f"Método iterativo {3 if self.session.project.model.advanced_bearings else 2} · ordem 1× · frequências amortecidas · 4 estimativas · tol 1e−6 · 40 iterações. Verifique convergência e eventuais raízes repetidas no resultado.")]
        elif kind=="static":controls += [self.notice("Análise estática nativa do modelo atual.")]
        async def submit(e):
            try:
                if not name.value.strip():raise ValueError("Informe um nome de caso.")
                if kind=="modal":
                    params={"speed_rad_s":rpm_to_rad_s(number(speed.value)),"with_eigenvectors":True,"with_kappa":True,"coefficient_policy":modal_policy.value}
                elif kind in ("modal_sweep","frequency_response"):
                    n=number(count.value,integer=True);a=number(start.value);b=number(end.value)
                    if not 2<=n<=2000 or not 0<=a<b:raise ValueError("Esperado 2–2000 pontos e 0 ≤ rotação inicial < rotação final.")
                    params={"speeds_rad_s":rpm_to_rad_s(np.linspace(a,b,n)).tolist()}
                    if kind=="modal_sweep":params.update(with_eigenvectors=True,with_kappa=True,coefficient_policy=modal_policy.value)
                elif kind=="critical_speeds":params={"NX":1.,"damped":True,"ncrit":4,"method":3 if self.session.project.model.advanced_bearings else 2,"max_iterations":40,"tol":1e-6}
                else:params={}
                case=AnalysisCase(kind,params,name.value.strip())
                self.page.pop_dialog();await self.run_case(case)
            except Exception as exc:self.error("Configuração inválida",exc)
        self.page.show_dialog(ft.AlertDialog(title=self.txt(f"Configurar · {dict(ANALYSES).get(kind,kind)}",18,bold=True),
                       content=ft.Container(ft.Column(controls,tight=True,spacing=12),width=430),
                       actions=[self.button("Cancelar",lambda e:self.page.pop_dialog()),self.button("Executar",submit,ft.Icons.PLAY_ARROW,primary=True)]))

    def advanced_case_dialog(self,e=None):
        kind=self.field("AnalysisCase.kind","general_frf")
        name=self.field("Nome do caso","FRF_01")
        params=self.field("Parâmetros Core · unidades SI",json.dumps({"frequency_rad_s":[10.,50.,100.],"speed":100.},indent=2),multiline=True)
        async def submit(e):
            try:
                data=json.loads(params.value)
                if not isinstance(data,dict):raise ValueError("Parâmetros devem ser um objeto JSON.")
                case=AnalysisCase(kind.value.strip(),data,name.value.strip())
                self.page.pop_dialog();await self.run_case(case)
            except Exception as exc:self.error("Caso avançado inválido",exc)
        self.page.show_dialog(ft.AlertDialog(title=self.txt("Caso avançado · API do Core",18,bold=True),content=ft.Container(ft.Column([kind,name,params,
                 self.notice("Use os nomes e unidades da API do Core. Resultados sem vista específica permanecem disponíveis para exportação integral.")],tight=True,spacing=12),width=590),
                 actions=[self.button("Cancelar",lambda e:self.page.pop_dialog()),self.button("Executar",submit,primary=True)]))

    async def run_case(self,case):
        if not self.alive:
            return None
        if self.busy:
            self.error("Análise em execução", "Já existe uma execução nesta sessão.");return None
        if self.form_changed() and not self.apply_properties():return None
        self.session.set_case(case)
        self.job=NativeJob(self.session.project,case,self.library_path)
        self.session.log("EXECUÇÃO",f"{case.name}: snapshot do modelo enviado ao núcleo.")
        self.render()
        while not self.job.future.done():
            if not self.alive:self.job.cancel();return
            self.refresh_messages();await asyncio.sleep(.12)
        if not self.alive:
            self.job.cancel()
            return None
        try:
            record=self.job.future.result()
            self.session.records.append(record)
            self.speed_index=0;self.mode_ordinal=0
            if isinstance(record.execution.result,BearingSweep):self.bearing_record=record;self.document="bearings"
            else:
                self.document=record.id
                self.subview="modes" if isinstance(record.execution.result,ModalResult) else "campbell"
            self.session.log("CONCLUÍDO",f"{case.name} · hash {record.execution.analysis_hash[:14]} · resultado nativo.")
            self.render()
            return record
        except Exception as exc:
            if self.job.state=="CANCELLED":self.session.log("CANCELADO",str(exc));self.render();return None
            self.render();self.error("Falha na análise",exc);return None

    def cancel(self,e=None):
        if self.busy:
            self.job.cancel();self.session.log("AVISO","Cancelamento solicitado. A chamada nativa em curso não será interrompida à força.");self.refresh_messages()
    async def rerun(self,e=None):
        record=self.record()
        if record:await self.run_case(record.execution.case)

    async def bearing_analysis(self,e=None):
        if self.bearing_ref is None:return
        ref=self.bearing_ref;b=getattr(self.session.project.model,ref.kind)[ref.index]
        if isinstance(b,CoefficientBearing) and len(b.speed_rad_s)>1:
            speeds=np.linspace(b.speed_rad_s[0],b.speed_rad_s[-1],25).tolist()
        else:speeds=rpm_to_rad_s(np.linspace(300,6000,25)).tolist()
        case=AnalysisCase("bearing_matrices",{"speed_rad_s":float(speeds[0])},f"Mancal_{ref.kind}_{ref.index+1}",{
            "flet_scope":"bearing_sweep","bearing_kind":ref.kind,"bearing_index":ref.index,"speeds_rad_s":speeds})
        await self.run_case(case)

    def table_dialog(self,e=None):
        if not self.may_edit():return
        ref=self.bearing_ref
        if ref is None:return
        b=getattr(self.session.project.model,ref.kind)[ref.index]
        if not isinstance(b,CoefficientBearing) or b.frequency_rad_s:
            self.error("Tabela K/C por rotação","Este editor requer CoefficientBearing sem eixo de frequência. Use Editar propriedades para preservar outros tipos ou tabelas 2D.");return
        columns=["rpm","kxx","kxy","kyx","kyy","cxx","cxy","cyx","cyy"]
        speeds=list(b.speed_rad_s) or [0.]
        stream=io.StringIO();writer=csv.writer(stream,delimiter=';',lineterminator='\n');writer.writerow(columns)
        for i,w in enumerate(speeds):
            row=[rad_s_to_rpm(w)]
            for key in columns[1:]:
                v=getattr(b,key)
                if v is None:v=getattr(b,{"kyy":"kxx","cyy":"cxx"}[key])
                arr=np.asarray(v);row.append(float(arr) if arr.ndim==0 else float(arr[i]))
            writer.writerow(row)
        text=self.field("CSV · rpm;Kxx;Kxy;Kyx;Kyy;Cxx;Cxy;Cyx;Cyy",stream.getvalue(),multiline=True,key="bearing-table")
        method=ft.Dropdown(value=b.interpolation,label="Interpolação no Core",options=[ft.DropdownOption("linear"),ft.DropdownOption("pchip")],text_size=12)
        async def import_file(e):
            try:
                files=await ft.FilePicker().pick_files(allow_multiple=False,with_data=self.page.web)
                if not files:return
                file=files[0];raw=file.bytes if self.page.web else Path(file.path).read_bytes()
                text.value=raw.decode("utf-8-sig");text.update()
            except Exception as exc:self.error("Falha ao importar tabela",exc)
        def apply(e):
            try:
                candidate=coefficient_csv(b,text.value,method.value)
                self.session.replace_entity(ref,candidate);self.page.pop_dialog();self.render()
            except Exception as exc:self.error("Tabela inválida — modelo preservado",exc)
        self.page.show_dialog(ft.AlertDialog(title=self.txt("Editar coeficientes tabelados",18,bold=True),content=ft.Container(ft.Column([text,method,
                 self.notice("K em N/m · C em N·s/m · rotação em rpm · decimal com ponto ou vírgula · separador ;. Sem inversão dos sinais cruzados.")],tight=True,spacing=12),width=760),
                 actions=[self.button("Importar CSV",import_file,ft.Icons.UPLOAD_FILE),self.button("Cancelar",lambda e:self.page.pop_dialog()),self.button("Aplicar tabela",apply,primary=True)]))

    async def export_png(self,e=None):await self.export("png")
    async def export_csv(self,e=None):await self.export("csv")
    async def export_npz(self,e=None):await self.export("npz")
    async def export_report(self,e=None):await self.export("zip")
    async def export(self,extension):
        r=self.record()
        if r is None:self.error("Nenhum resultado selecionado","Execute uma análise e abra seu documento antes de exportar.");return
        try:
            if extension=="png":
                if self.plot_png is None:raise ValueError("Nenhuma figura disponível para este resultado.")
                data=self.plot_png
            elif extension=="csv":data=csv_bytes(r)
            elif extension=="npz":data=npz_bytes(r)
            else:data=report_bytes(r,current=self.session.is_current(r),png=self.plot_png)
            await self.write_bytes(data,f"rotorstudio_{r.id[:8]}.{extension}");self.refresh_messages()
        except Exception as exc:self.error("Falha ao exportar",exc)

    def about(self,e=None):
        self.page.show_dialog(ft.AlertDialog(title=self.txt("RotorStudio · Flet",20,bold=True),content=ft.Container(ft.Column([
            ft.Text("Interface Flet 1.0 baseada nos quatro mockups aprovados. Editor, Campbell, mancais K/C e modos 3D.",size=13),
            ft.Text("Modelo, unidades, persistência e cálculos: drm_core → AnalysisService / SolverFacade → Fortran. Nenhum resultado numérico é fabricado pela interface.",size=13),
            ft.Text("As demais telas especializadas do Qt permanecem disponíveis em drm-studio. Esta entrega não declara paridade integral com todos os fluxos Qt nem qualificação de executáveis congelados.",size=13),
            ft.Text("Atalhos: Ctrl+O abrir · Ctrl+S salvar · Ctrl+Z desfazer · Ctrl+Y refazer. No rotor: clique seleciona, arraste desloca. Os modos usam amplitude normalizada.",size=13)],tight=True,spacing=14),width=570),
            actions=[self.button("Fechar",lambda e:self.page.pop_dialog())]))

