"""Project, results, reports and diagnostic workspaces shared by all screens."""
from __future__ import annotations
import asyncio
import io
import json
from pathlib import Path
import platform
import zipfile
import flet as ft
from .jobs import csv_bytes,npz_bytes,report_bytes,arrays_of


class ProjectActions:
    def flash(self,message):
        self.session.log('INFO',str(message))
        self.page.show_dialog(ft.SnackBar(ft.Text(str(message))))

    def results_view(self):
        body=[self.txt('Resultados',23,bold=True),self.notice('Cada resultado guarda seu próprio modelo de origem. Fechar um documento remove somente o resultado em memória, não o caso salvo.')]
        for record in self.session.records:
            current=self.session.is_current(record)
            body.append(self.card(record.execution.case.name,ft.Container(ft.Column([
                self.kv('Análise',record.execution.case.kind),self.kv('Executado em',record.created_utc),
                self.field('Hash de análise',record.execution.analysis_hash,readonly=True),
                ft.Row([self.chip('ATUAL' if current else 'DESATUALIZADO',self.p.success if current else self.p.warning),
                        self.button('Abrir',lambda e,r=record:self.navigate(r.id),ft.Icons.OPEN_IN_NEW),
                        self.button('Reexecutar',lambda e,c=record.execution.case:self.page.run_task(self.run_case,c),ft.Icons.REFRESH,disabled=self.busy),
                        self.button('Remover resultado',lambda e,r=record:self.page.run_task(self.remove_result_document,r.id),ft.Icons.DELETE_OUTLINE)],wrap=True)
                ],spacing=9),padding=14)))
        if not self.session.records:body.append(self.button('Configurar análise',lambda e:self.navigate('analyses'),ft.Icons.QUERY_STATS,primary=True))
        return ft.Column(body,spacing=14,expand=True,scroll=ft.ScrollMode.AUTO)

    async def remove_result_document(self,key):
        if await self.confirm('Remover resultado','Remover este resultado da sessão? O caso de análise será preservado e poderá ser recalculado.'):
            self.close_result(key)

    def reports_view(self):
        body=[self.txt('Relatórios e exportação',23,bold=True),self.notice('Os arquivos contêm dados reais do Core. O relatório identifica resultados desatualizados e não transforma uma execução numérica em certificação de projeto.')]
        for record in self.session.records:
            async def report(e=None,r=record):
                try:await self.write_bytes(report_bytes(r,current=self.session.is_current(r)),f'rotorstudio_{r.id[:8]}_report.zip')
                except Exception as exc:self.error('Falha de exportação',exc)
            body.append(ft.Row([self.txt(record.execution.case.name,13,bold=True,expand=True),self.chip('ATUAL' if self.session.is_current(record) else 'DESATUALIZADO'),
                self.button('Relatório + dados',report,ft.Icons.DESCRIPTION_OUTLINED),
                self.button('Figura / seleção',lambda e,r=record:self.navigate(r.id))],wrap=True,spacing=8))
        body.extend([ft.Divider(color=self.p.line),self.button('Exportar todos os resultados',self.export_all_results,ft.Icons.FOLDER_ZIP_OUTLINED,disabled=not self.session.records),
                     self.button('Diagnóstico da sessão',lambda e:self.navigate('diagnostics')),self.button('Salvar projeto',self.save_project,ft.Icons.SAVE_OUTLINED)])
        return ft.Column(body,spacing=18,expand=True,scroll=ft.ScrollMode.AUTO)

    async def export_all_results(self,e=None):
        if not self.session.records:return
        try:
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
                z.writestr('project.json',self.session.as_bytes())
                for r in self.session.records:z.writestr(f'{r.id}/report.zip',report_bytes(r,current=self.session.is_current(r)))
                z.writestr('README.txt','Relatórios por identificador de resultado. O projeto contém modelo/casos; abrir o JSON exige recalcular. Os NPZ guardam arrays completos sem pickle.\n')
            await self.write_bytes(out.getvalue(),'RotorStudio_relatorios.zip')
        except Exception as exc:self.error('Não foi possível exportar o conjunto',exc)

    def export_formats_dialog(self,e=None):
        record=self.record()
        if not record:return self.error('Sem resultado','Selecione um resultado calculado.')
        async def choose(ext):
            self.page.pop_dialog();await self.export(ext)
        self.page.show_dialog(ft.AlertDialog(title=self.txt('Exportar figura / dados',17,bold=True),
            content=ft.Container(ft.Column([self.notice('Exporta a vista atual e sua seleção. Os dados completos permanecem disponíveis em CSV/NPZ.'),
                ft.Row([self.button(label,lambda e,x=ext:self.page.run_task(choose,x)) for ext,label in [('png','PNG'),('svg','SVG vetorial'),('pdf','PDF vetorial'),('bundle','Pacote PNG/SVG/PDF')]],wrap=True),
                ft.Row([self.button('CSV',lambda e:self.page.run_task(choose,'csv')),self.button('NPZ',lambda e:self.page.run_task(choose,'npz')),self.button('Relatório',lambda e:self.page.run_task(choose,'zip'))])],tight=True,spacing=14),width=570),
            actions=[self.button('Cancelar',lambda e:self.page.pop_dialog())]))

    def export_bytes(self,extension):
        record=self.record()
        if record is None:raise ValueError('Abra um documento de resultado antes de exportar.')
        if extension=='png':
            if not self.plot_png:raise ValueError('Nenhuma figura disponível.')
            return self.plot_png
        if extension in ('svg','pdf'):
            if self.figure is None:raise ValueError('Nenhuma figura disponível.')
            output=io.BytesIO();self.figure.savefig(output,format=extension,facecolor=self.figure.get_facecolor());return output.getvalue()
        if extension=='csv':return csv_bytes(record)
        if extension=='npz':return npz_bytes(record)
        if extension=='bundle':
            output=io.BytesIO()
            with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
                for ext in ('png','svg','pdf'):z.writestr('plot.'+ext,self.export_bytes(ext))
                z.writestr('selection.json',json.dumps({'analysis_hash':record.execution.analysis_hash,'model_hash':record.model.model_hash(),
                   'current':self.session.is_current(record),'view_selection':getattr(record,'view_selection',{})},ensure_ascii=False,indent=2))
            return output.getvalue()
        if extension=='zip':return report_bytes(record,current=self.session.is_current(record),png=self.plot_png)
        raise ValueError(f'Formato de exportação não suportado: {extension}')

    async def export(self,extension):
        try:
            data=self.export_bytes(extension);r=self.record();suffix='zip' if extension=='bundle' else extension
            await self.write_bytes(data,f'rotorstudio_{r.id[:8]}.{suffix}');self.refresh_messages()
        except Exception as exc:self.error('Falha ao exportar',exc)

    def diagnostics_view(self):
        import importlib.metadata
        from .analysis_catalog import CATALOG
        info={'Python':platform.python_version(),'Plataforma':platform.platform(),'Flet':importlib.metadata.version('flet'),
              'Biblioteca do rotor':str(self.library_path or 'Não localizada'),'Hash do modelo':self.session.project.model.model_hash(),
              'Casos de análise':len(self.session.project.analyses),'Resultados da sessão':len(self.session.records),'Contratos de análise com tela':len(CATALOG)}
        body=[self.txt('Diagnóstico da sessão',23,bold=True),self.notice('Informações de configuração e rastreabilidade; esta tela não executa cálculos nem atribui qualificação automática.')]
        body += [self.field(str(k),str(v),readonly=True) for k,v in info.items()]
        body.append(self.txt('Mensagens e diagnósticos',15,bold=True))
        body += [ft.Text(f'{level}: {text}',size=11,selectable=True,color=self.p.error if level in ('ERRO','VISUALIZAÇÃO') else self.p.text) for level,text in self.session.messages]
        return ft.Column(body,expand=True,spacing=10,scroll=ft.ScrollMode.AUTO)

    def project_properties(self,e=None):
        if not self.may_edit():return
        name=self.field('Nome do projeto',self.session.project.name)
        error=ft.Text('',color=self.p.error)
        def apply(_):
            if not str(name.value).strip():error.value='Nome obrigatório.';self.page.update();return
            self.session.transact('Renomear projeto',lambda p:setattr(p,'name',str(name.value).strip()),validate=False);self.page.pop_dialog();self.render()
        self.page.show_dialog(ft.AlertDialog(modal=True,title=self.txt('Propriedades do projeto',17,bold=True),
              content=ft.Container(ft.Column([name,self.field('Hash do modelo',self.session.project.model.model_hash(),readonly=True),
                 ft.Text(json.dumps(self.session.project.metadata,ensure_ascii=False,indent=2,default=str),size=10,selectable=True),error],scroll=ft.ScrollMode.AUTO),width=600,height=360),
              actions=[self.button('Cancelar',lambda e:self.page.pop_dialog()),self.button('Aplicar',apply,primary=True)]))

    def about(self,e=None):
        self.page.show_dialog(ft.AlertDialog(title=self.txt('RotorStudio · Flet',20,bold=True),
             content=ft.Container(ft.Column([
                ft.Text('Ambiente de engenharia: projeto, modelo, todas as configurações AnalysisService, resultados e mapas de mancais.',size=13),
                ft.Text('Flet → adaptadores de entrada → drm_core → Fortran 2018. A interface não substitui o solver nem altera as hipóteses dos modelos.',size=13),
                ft.Text('Ctrl+O abrir · Ctrl+S salvar · Ctrl+Z desfazer · Ctrl+Y refazer. Os modos 3D têm escala visual normalizada; respostas forçadas mantêm unidades físicas.',size=13),
                ft.Text('O aplicativo Qt continua em drm-studio. A presença de uma tela não amplia a validade física do Core, nem significa qualificação de todas as plataformas ou executáveis congelados.',size=13),
                self.button('Diagnósticos',lambda e:(self.page.pop_dialog(),self.navigate('diagnostics')))],tight=True,spacing=14),width=630),actions=[self.button('Fechar',lambda e:self.page.pop_dialog())]))
