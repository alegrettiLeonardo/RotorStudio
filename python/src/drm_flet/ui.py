"""Application shell: lifecycle, navigation and shared desktop controls."""
from .ui_common import *
from .ui_views import WorkspaceViews
from .ui_properties import PropertiesViews
from .ui_actions import EditorActions


from .analysis_forms import AnalysisActions
from .entity_forms import EntityActions
from .ui_results import AllResultsViews
from .ui_bearings import BearingWorkspaces
from .ui_project import ProjectActions

class StudioApp(BearingWorkspaces, AllResultsViews, AnalysisActions, EntityActions, ProjectActions, WorkspaceViews, PropertiesViews, EditorActions):
    def __init__(self, page: ft.Page, session=None, *, library_path=None, dark=False):
        self.page = page
        self.session = session if session is not None else StudioSession()
        self.library_path = library_path or os.environ.get("DRMROTOR_LIB")
        self.dark = dark
        self.document = "model"
        self.subview = "campbell"
        self.mode_ordinal = 0
        self.speed_index = 0
        self.phase, self.amplitude, self.elev, self.azim = 0.0, 1.0, 20.0, -62.0
        self.show_orbits = self.show_reference = self.show_markers = True
        self.show_forward = self.show_backward = self.show_excitation = True
        self.damped_frequency = False
        self.campbell_modes = 6
        self.show_nodes = self.show_elements = self.show_bearings = self.show_dimensions = True
        self.zoom, self.pan = 1.0, 0.0
        self.model_width, self.model_height = 960.0, 330.0
        self.hitboxes = []
        self.filter_text = ""
        self.expanded = {"shafts", "advanced_bearings"}
        self.form_fields = {}
        self.form_original = {}
        self.form_entity = None
        self.json_field = None
        self.json_original = ""
        self.bearing_ref = self.first_bearing()
        self.bearing_record = None
        self.bearing_damping = False
        self.job = None
        self.animating = False
        self.alive = True
        self.plot_png = None
        self.figure = None
        self.plot_image = None
        self.table_pages = {}
        self.root = ft.Container(expand=True)
        page.title = "RotorStudio · Flet"
        page.padding = 0
        page.spacing = 0
        page.theme = make_theme(False); page.dark_theme = make_theme(True)
        page.window.width = 1580; page.window.height = 1000
        page.window.min_width = 1120; page.window.min_height = 780
        page.window.prevent_close = True
        page.window.on_event = self.window_event
        page.on_keyboard_event = self.keyboard
        page.on_disconnect = self.disconnect
        page.on_close = self.disconnect
        page.add(self.root)
        self.render()

    @property
    def p(self): return DARK if self.dark else LIGHT
    @property
    def busy(self): return self.job is not None and not self.job.future.done()

    def first_bearing(self):
        for kind in ("advanced_bearings","bearings"):
            if getattr(self.session.project.model,kind): return EntityRef(kind,0)
        return None

    def record(self):
        if self.document == "bearings": return self.bearing_record
        return next((r for r in self.session.records if r.id == self.document),None)

    def txt(self,value,size=12,*,muted=False,bold=False,expand=False,color=None):
        return ft.Text(str(value),size=size,color=color or (self.p.muted if muted else self.p.text),
                       weight=ft.FontWeight.W_600 if bold else ft.FontWeight.NORMAL,
                       expand=expand,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS)

    def icon(self,name,size=18): return ft.Icon(name,size=size,color=self.p.muted)

    def button(self,label,callback=None,icon=None,*,primary=False,disabled=False,key=None):
        return ft.Button(label,icon=icon,on_click=callback,disabled=disabled,height=34,key=key,
                         color=("#FFFFFF" if not self.dark else "#12223A") if primary else self.p.primary,
                         bgcolor=self.p.primary if primary else self.p.selected,elevation=0,
                         style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=18),
                                             padding=ft.Padding.symmetric(horizontal=14,vertical=4),text_style=ft.TextStyle(size=11)))

    def ib(self,icon,tooltip,fn=None,*,disabled=False):
        return ft.IconButton(icon,tooltip=tooltip,on_click=fn,disabled=disabled,icon_size=18,
                             icon_color=self.p.muted,width=34,height=32)

    def field(self,label,value="",unit="",*,width=None,readonly=False,key=None,multiline=False):
        return ft.TextField(label=label,value=str(value),suffix=ft.Text(unit, size=10, color=self.p.muted) if unit else None,
                            text_size=12,label_style=ft.TextStyle(size=11,color=self.p.muted),
                            color=self.p.text,border_color=self.p.line,focused_border_color=self.p.primary,
                            bgcolor=self.p.surface,border_radius=7,dense=True,read_only=readonly,
                            content_padding=ft.Padding.symmetric(horizontal=11,vertical=12),
                            height=None if multiline else 42,width=width,key=key,multiline=multiline,
                            min_lines=8 if multiline else None,max_lines=15 if multiline else 1)

    def chip(self,text,color=None):
        return ft.Container(self.txt(text,10,color=color or self.p.muted),padding=ft.Padding.symmetric(horizontal=8,vertical=4),
                            border=ft.Border.all(1,self.p.line),border_radius=5,bgcolor=self.p.subtle)

    def card(self,title,content,actions=None,*,expand=False,height=None):
        head=ft.Container(ft.Row([self.txt(title,12,bold=True,expand=True),*(actions or [])],spacing=5),
                          padding=ft.Padding.symmetric(horizontal=14,vertical=8),height=42,
                          border=ft.Border(bottom=ft.BorderSide(1,self.p.line)))
        return ft.Container(ft.Column([head,content],spacing=0,expand=expand),bgcolor=self.p.surface,
                            border=ft.Border.all(1,self.p.line),border_radius=10,clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            expand=expand,height=height)

    def notice(self,text,*,warning=False):
        return ft.Container(ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE,size=16,color=self.p.warning if warning else self.p.primary),
                                   ft.Text(text,size=11,color=self.p.muted,expand=True)],spacing=9),
                            padding=10,bgcolor=self.p.subtle,border_radius=7)

    def kv(self,label,value):
        return ft.Row([self.txt(label,10,muted=True,expand=True),self.txt(value,11,bold=True)],spacing=8)

    def table(self, headers, rows, *, selected=None, select=None, height=175):
        """Compact native Flet grid with a stationary, unit-labelled header."""
        def cells(values, *, header=False):
            return ft.Row([
                ft.Container(
                    ft.Text(str(value), size=10 if header else 11,
                            color=self.p.muted if header else self.p.text,
                            weight=ft.FontWeight.W_600 if header else ft.FontWeight.NORMAL,
                            max_lines=2 if header else 1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            tooltip=str(value)),
                    expand=1, padding=ft.Padding.symmetric(horizontal=5),
                    alignment=ft.Alignment.CENTER_LEFT,
                ) for value in values
            ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        header = ft.Container(
            cells(headers, header=True), height=36, bgcolor=self.p.subtle,
            padding=ft.Padding.symmetric(horizontal=7),
            border=ft.Border(bottom=ft.BorderSide(1, self.p.line)),
        )
        # Declarative pagination avoids a delayed scroll_to() response targeting
        # a table that has already been unmounted by a document/theme change.
        # No asynchronous client method is invoked on a disposable table.
        page_size = max(1, int(((height or 320) - 63) / 29))
        key = (self.document, tuple(headers))
        previous = self.table_pages.get(key)
        page_count = max(1, math.ceil(len(rows) / page_size))
        current_page = previous[0] if previous else 0
        if selected is not None and (previous is None or previous[1] != selected):
            current_page = selected // page_size
        current_page = max(0, min(page_count - 1, current_page))
        self.table_pages[key] = (current_page, selected)
        body = ft.ListView(expand=True, spacing=0, item_extent=29, padding=0)
        page_label = self.txt("", 9, muted=True, expand=True)

        def show_page(index, update=False):
            index = max(0, min(page_count - 1, index))
            self.table_pages[key] = (index, selected)
            first = index * page_size
            body.controls = [
                ft.Container(
                    cells(row), height=29,
                    padding=ft.Padding.symmetric(horizontal=7),
                    bgcolor=self.p.selected if i == selected else self.p.surface,
                    border=ft.Border(bottom=ft.BorderSide(.5, self.p.line)),
                    on_click=(lambda e, i=i: select(i)) if select else None,
                ) for i, row in enumerate(rows[first:first + page_size], first)
            ]
            page_label.value = f"{first + 1 if rows else 0}–{min(first + page_size, len(rows))} de {len(rows)} · página {index + 1}/{page_count}"
            back.disabled = index == 0
            forward.disabled = index >= page_count - 1
            if update:
                body.update(); footer.update()

        back = self.ib(ft.Icons.CHEVRON_LEFT, "Página anterior",
                       lambda e: show_page(self.table_pages[key][0] - 1, True))
        forward = self.ib(ft.Icons.CHEVRON_RIGHT, "Próxima página",
                          lambda e: show_page(self.table_pages[key][0] + 1, True))
        footer = ft.Container(ft.Row([page_label, back, forward], spacing=2),
                              height=27, padding=ft.Padding.only(left=10, right=6),
                              border=ft.Border(top=ft.BorderSide(1, self.p.line)))
        show_page(current_page)
        return ft.Container(
            ft.Column([header, body, footer], spacing=0, expand=True),
            height=height, expand=height is None,
        )

    def render(self):
        if not self.alive:
            return
        self.animating = False
        self.page.theme_mode = ft.ThemeMode.DARK if self.dark else ft.ThemeMode.LIGHT
        self.page.bgcolor = self.p.background
        self.form_fields = {}; self.form_original = {}; self.form_entity = None
        self.json_field = None; self.json_original = ""
        self.figure = None; self.plot_png = None; self.plot_image = None
        explorer=self.explorer()
        inspector=self.inspector()
        central=self.workspace()
        body=ft.Row([self.rail(),explorer,ft.Column([self.tabs(),central,self.messages()],spacing=0,expand=True),inspector],
                    spacing=0,expand=True,vertical_alignment=ft.CrossAxisAlignment.STRETCH)
        self.status_text=self.txt(self.status(),10,muted=True,expand=True)
        status=ft.Container(ft.Row([self.status_text,self.txt("FLET 1.0  ·  SI canônico  ·  Fortran",10,muted=True)],spacing=12),
                            bgcolor=self.p.subtle,padding=ft.Padding.symmetric(horizontal=14,vertical=4),height=25,
                            border=ft.Border(top=ft.BorderSide(1,self.p.line)))
        self.root.content=ft.Column([self.header(),self.menu(),body,status],spacing=0,expand=True)
        self.page.title=f"RotorStudio · {self.session.project.name}{' *' if self.session.dirty else ''}"
        self.page.update()

    def status(self):
        m=self.session.project.model
        s=f"{len(m.nodes)} nós · {len(m.shafts)} elementos · {len(m.disks)} discos · {len(m.bearings)+len(m.advanced_bearings)} mancais"
        return ("Executando no núcleo…" if self.busy else "Pronto")+"   |   "+s+('   |   Alterações não salvas' if self.session.dirty else '')

    def header(self):
        brand=ft.Container(ft.Icon(ft.Icons.SETTINGS_INPUT_COMPONENT,size=23,color="#FFFFFF"),bgcolor="#245FC4",border_radius=12,padding=8)
        name=ft.Column([self.txt("RotorStudio",20,bold=True),self.txt("ROTOR DYNAMICS",8,muted=True)],spacing=0)
        return ft.Container(ft.Row([brand,name,ft.VerticalDivider(width=22,color=self.p.line),
                                   self.txt(self.session.project.name,12,bold=True,expand=True),self.chip("FLET"),
                                   self.ib(ft.Icons.FOLDER_OPEN,"Abrir projeto · Ctrl+O",self.open_project),
                                   self.ib(ft.Icons.SAVE_OUTLINED,"Salvar · Ctrl+S",self.save_project),
                                   self.ib(ft.Icons.UNDO,"Desfazer · Ctrl+Z",self.undo,disabled=self.busy or not self.session.can_undo),
                                   self.ib(ft.Icons.REDO,"Refazer · Ctrl+Y",self.redo,disabled=self.busy or not self.session.can_redo),
                                   ft.VerticalDivider(width=12,color=self.p.line),
                                   self.button("Cancelar" if self.busy else "Executar análise",self.cancel if self.busy else self.analysis_dialog,
                                               ft.Icons.STOP if self.busy else ft.Icons.PLAY_ARROW_OUTLINED,primary=True,key="run-analysis")],spacing=10),
                            bgcolor=self.p.surface,padding=ft.Padding.symmetric(horizontal=18,vertical=9),height=65)

    def menu(self):
        def item(text,fn,icon=None):return ft.MenuItemButton(content=self.txt(text,11),leading=self.icon(icon) if icon else None,on_click=fn)
        controls=[ft.SubmenuButton(content=self.txt("Projeto",11),controls=[
                    item("Novo projeto",self.new_project,ft.Icons.ADD),item("Abrir…",self.open_project,ft.Icons.FOLDER_OPEN),
                    item("Abrir rotor de exemplo",self.open_example),item("Propriedades do projeto",self.project_properties),item("Salvar",self.save_project,ft.Icons.SAVE),item("Salvar como…",self.save_as)]),
                  ft.SubmenuButton(content=self.txt("Modelo",11),controls=[item("Adicionar elemento",self.add_dialog),
                    item("Editar seleção · formulário completo",self.entity_dialog),item("Remover seleção",self.remove_selected),
                    item("Definições de rotores coaxiais",lambda e:self.entity_collection_dialog("rotors")),
                    item("Curvatura do rotor",lambda e:self.entity_collection_dialog("bend")),item("Desfazer",self.undo),item("Refazer",self.redo)]),
                  ft.SubmenuButton(content=self.txt("Análises",11),controls=[
                    item(label,lambda e,k=kind:self.analysis_dialog(kind=k)) for kind,label in ANALYSES]+[
                    item("Catálogo e casos salvos",self.advanced_case_dialog)]),
                  ft.SubmenuButton(content=self.txt("Mancais",11),controls=[item("Desempenho / coeficientes",lambda e:self.navigate("bearings")),
                    item("Ponto de operação e campos",self.bearing_job_dialog),item("Mapa operacional e cache",lambda e:self.bearing_job_dialog(scope="operating_map"))]),
                  ft.SubmenuButton(content=self.txt("Resultados",11),controls=[item("Gerenciar resultados",lambda e:self.navigate("results")),
                    item("Exportar figura PNG/SVG/PDF",self.export_formats_dialog),item("Exportar PNG",self.export_png),
                    item("Exportar CSV",self.export_csv),item("Exportar NPZ",self.export_npz),item("Relatório e dados",self.export_report)]),
                  ft.SubmenuButton(content=self.txt("Ajuda",11),controls=[item("Diagnósticos",lambda e:self.navigate("diagnostics")),item("Sobre esta interface",self.about)])]
        return ft.Container(ft.Row([ft.MenuBar(controls=controls,style=ft.MenuStyle(bgcolor=self.p.surface)),
                                     ft.Container(expand=True),self.txt("SI · mm, N, kg, rpm",10,muted=True),
                                     self.ib(ft.Icons.DARK_MODE_OUTLINED if not self.dark else ft.Icons.LIGHT_MODE_OUTLINED,"Alternar tema",self.toggle_theme)],spacing=6),
                            height=32,bgcolor=self.p.surface,border=ft.Border(bottom=ft.BorderSide(1,self.p.line)),padding=ft.Padding.only(right=12))

    def rail(self):
        index={"model":0,"analyses":1,"bearings":2,"reports":4}.get(self.document,3)
        return ft.Container(ft.Column([ft.NavigationRail(selected_index=index,min_width=62,
                       label_type=ft.NavigationRailLabelType.ALL,bgcolor=self.p.subtle,indicator_color=self.p.selected,
                       selected_label_text_style=ft.TextStyle(size=9,color=self.p.primary),unselected_label_text_style=ft.TextStyle(size=9,color=self.p.muted),
                       destinations=[ft.NavigationRailDestination(icon=ft.Icons.SETTINGS_INPUT_COMPONENT,label="Modelo"),
                           ft.NavigationRailDestination(icon=ft.Icons.QUERY_STATS,label="Análises"),
                           ft.NavigationRailDestination(icon=ft.Icons.TOLL_OUTLINED,label="Mancais"),
                           ft.NavigationRailDestination(icon=ft.Icons.INSIGHTS_OUTLINED,label="Resultados"),
                           ft.NavigationRailDestination(icon=ft.Icons.DESCRIPTION_OUTLINED,label="Relatórios")],
                       on_change=self.rail_changed,expand=True),
                       self.ib(ft.Icons.BRIGHTNESS_6_OUTLINED,"Tema claro / escuro",self.toggle_theme),
                       self.ib(ft.Icons.HELP_OUTLINE,"Ajuda",self.about)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=10,expand=True),
                       width=64,bgcolor=self.p.subtle,padding=ft.Padding.only(top=10,bottom=10),
                       border=ft.Border(right=ft.BorderSide(1,self.p.line)))

    def rail_changed(self,e):
        i=e.control.selected_index
        if i==0:self.navigate("model")
        elif i==1:self.navigate("analyses")
        elif i==2:self.navigate("bearings")
        elif i==3:self.navigate("results")
        else:self.navigate("reports")

    def explorer(self):
        self.tree=ft.Column(spacing=2,scroll=ft.ScrollMode.AUTO,expand=True)
        self.fill_tree()
        search=self.field("Filtrar entidades…",self.filter_text)
        search.height=39;search.on_change=self.filter_changed
        return ft.Container(ft.Column([ft.Container(ft.Row([self.txt("Explorador do projeto",12,bold=True,expand=True),self.ib(ft.Icons.ADD,"Adicionar",self.add_dialog)],spacing=0),height=40),
                 ft.Row([self.icon(ft.Icons.FOLDER_OUTLINED),self.txt(self.session.project.name,11,bold=True,expand=True)],spacing=9),
                 search,self.tree,self.notice("Modelo e resultados vinculados ao núcleo. Sem dados simulados pela interface.")],spacing=12,expand=True),
                 width=235,padding=ft.Padding.symmetric(horizontal=12,vertical=8),bgcolor=self.p.subtle,
                 border=ft.Border(right=ft.BorderSide(1,self.p.line)))

    def label_entity(self,kind,i,entity):
        if kind=="nodes":return f"Nó {entity.number} · {m_to_mm(entity.z_m):g} mm"
        if kind=="shafts":return f"E{i+1:02d} · Nó {entity.node1} → {entity.node2}"
        if kind=="disks":return f"D{i+1} · Nó {entity.node}"
        if kind in ("bearings","advanced_bearings"):return f"{getattr(entity,'tag','') or 'M'+str(i+1)} · Nó {entity.node}"
        return f"{NAMES[kind]} {i+1}"

    def fill_tree(self):
        controls=[self.txt("MODELO",10,bold=True,muted=True)]
        for kind,label in NAMES.items():
            values=getattr(self.session.project.model,kind)
            visible=[]
            for i,entity in enumerate(values):
                name=self.label_entity(kind,i,entity)
                if self.filter_text.lower() not in (name+label).lower():continue
                ref=EntityRef(kind,i);selected=self.session.selection==ref
                visible.append(ft.Container(ft.Row([self.icon(ICONS[kind],13),self.txt(name,10,color=self.p.primary if selected else self.p.muted,expand=True)],spacing=7),
                       bgcolor=self.p.selected if selected else None,border_radius=6,padding=ft.Padding.symmetric(horizontal=9,vertical=6),
                       on_click=lambda e,r=ref:self.select_entity(r)))
            controls.append(ft.Container(ft.Row([self.icon(ft.Icons.EXPAND_MORE if kind in self.expanded else ft.Icons.CHEVRON_RIGHT,13),
                         self.txt(label,10,expand=True),self.txt(len(values),9,muted=True)],spacing=4),padding=4,
                         on_click=lambda e,k=kind:self.expand_group(k)))
            if kind in self.expanded or self.filter_text:controls.extend(visible)
        controls.extend([ft.Container(height=8),self.txt("ANÁLISES",10,bold=True,muted=True)])
        for kind,label in ANALYSES:
            controls.append(ft.Container(ft.Row([self.icon(ft.Icons.QUERY_STATS,15),self.txt(label,10,muted=True)],spacing=8),padding=6,
                            on_click=lambda e,k=kind:self.analysis_dialog(kind=k)))
        for case in self.session.project.analyses:
            controls.append(ft.Container(ft.Row([self.icon(ft.Icons.PLAY_CIRCLE_OUTLINE,14),
                self.txt(case.name,10,expand=True)],spacing=7),padding=6,tooltip=f"Editar caso salvo: {case.kind}",
                on_click=lambda e,c=case:self.analysis_dialog(kind=c.kind,case=c)))
        controls.extend([ft.Container(height=8),self.txt("RESULTADOS",10,bold=True,muted=True)])
        for r in self.session.records:
            current=self.session.is_current(r)
            controls.append(ft.Container(ft.Row([self.icon(ft.Icons.INSERT_CHART_OUTLINED,14),
                self.txt(r.execution.case.name,10,expand=True),self.txt("●",10,color=self.p.success if current else self.p.warning)],spacing=6),
                bgcolor=self.p.selected if self.document==r.id else None,padding=6,border_radius=6,on_click=lambda e,r=r:self.navigate(r.id)))
        self.tree.controls=controls

    def filter_changed(self,e):
        self.filter_text=e.control.value;self.fill_tree();self.tree.update()
    def expand_group(self,kind):
        self.expanded.symmetric_difference_update({kind});self.fill_tree();self.tree.update()

    def tabs(self):
        docs=[("model","Modelo do rotor",ft.Icons.SETTINGS_INPUT_COMPONENT),("bearings","Mancais",ft.Icons.TOLL_OUTLINED)]
        if self.document in ("analyses","results","reports","diagnostics"):
            docs.append((self.document,{"analyses":"Análises","results":"Resultados","reports":"Relatórios","diagnostics":"Diagnósticos"}[self.document],ft.Icons.DASHBOARD_OUTLINED))
        docs += [(r.id,r.execution.case.name,ft.Icons.QUERY_STATS) for r in self.session.records]
        items=[]
        for key,label,icon in docs:
            row=[ft.Icon(icon,size=15,color=self.p.primary if key==self.document else self.p.muted),self.txt(label,11)]
            if key not in ("model","bearings","analyses","results","reports","diagnostics"):
                row.append(self.ib(ft.Icons.CLOSE,"Fechar documento de resultado",lambda e,k=key:self.close_result(k)))
            items.append(ft.Container(ft.Row(row,spacing=8),padding=ft.Padding.symmetric(horizontal=13,vertical=4),height=39,
                        bgcolor=self.p.surface if key==self.document else self.p.subtle,
                        border=ft.Border(bottom=ft.BorderSide(2,self.p.primary if key==self.document else self.p.line)),
                        on_click=lambda e,k=key:self.navigate(k)))
        items.append(self.ib(ft.Icons.ADD,"Nova análise",self.analysis_dialog))
        return ft.Container(ft.Row(items,spacing=0,scroll=ft.ScrollMode.AUTO),height=40,bgcolor=self.p.subtle)

    def workspace(self):
        if self.document=="model":body=self.model_view()
        elif self.document=="bearings":body=self.bearing_view()
        elif self.document=="analyses":body=self.analyses_view()
        elif self.document in ("results","empty_results"):body=self.results_view()
        elif self.document=="reports":body=self.reports_view()
        elif self.document=="diagnostics":body=self.diagnostics_view()
        elif self.record():body=self.result_view()
        else:body=ft.Column([self.txt("Resultados",23,bold=True),self.notice("Nenhuma análise executada. Configure um caso e execute o núcleo."),self.button("Configurar análise",self.analysis_dialog)],spacing=18)
        return ft.Container(body,padding=15,bgcolor=self.p.background,expand=True)
