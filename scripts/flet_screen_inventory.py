"""Audit every Qt presentation class and native analysis dispatch against Flet.

This is a coverage inventory, not a substitute for native/UI execution tests.
Frozen comparison scope: main fcdac252974aeeded6961dbe3310677e234a6495.
"""
from __future__ import annotations
import argparse
import ast
import json
from pathlib import Path
from drm_flet.analysis_catalog import CATALOG

BASE_HEAD = 'fcdac252974aeeded6961dbe3310677e234a6495'
AUXILIARY = {
    'MainWindow': ('ui.StudioApp', 'menus, abas, navegação, ciclo de vida e execução'),
    'AdvancedBearingEditor': ('entity_forms.EntityForm', '14 famílias; parâmetros físicos / coeficientes / proveniência'),
    'BearingInspectorWidget': ('ui_properties.PropertiesViews', 'mancais clássicos 1–8 e acoplamento 20'),
    'DiskInspectorWidget': ('ui_properties.PropertiesViews', 'discos 1–6'),
    'MessagesDock': ('ui.StudioApp.messages', 'mensagens estruturadas / falhas / progresso'),
    'ProjectExplorerDock': ('ui.StudioApp.explorer', 'entidades, casos e resultados'),
    'PropertyInspectorDock': ('ui_properties.PropertiesViews', 'propriedades por entidade / resultado'),
    'AnalysisModulesBar': ('analysis_forms.AnalysisActions', 'catálogo e formulários de todos os contratos'),
    '_FieldCanvas': ('ui_bearings.field_present', 'campos nativos; indisponibilidade explícita quando ausentes'),
    'BearingPerformancePage': ('ui_bearings.BearingWorkspaces', 'K/C/M, campos, mapas, cache e aplicação transacional'),
    'RotorView': ('plotting.rotor_svg', 'desenho gerado do modelo / seleção / zoom / deslocamento'),
    'RotorModelPage': ('ui_views.WorkspaceViews', 'modelo e tabela de entidades'),
}


def inventory(root: Path):
    qt = root/'python/src/drm_studio'
    files = [qt/'main_window.py']
    for folder in ('analysis_pages','result_views','docks','widgets'):
        files.extend(sorted((qt/folder).glob('*.py')))
    records=[]
    for file in files:
        for cls in ast.parse(file.read_text(encoding='utf-8')).body:
            if not isinstance(cls,ast.ClassDef):continue
            analyses=[s.kind for s in CATALOG if cls.name in (s.qt_screen,s.result_screen)]
            if cls.name in AUXILIARY:
                target,scope=AUXILIARY[cls.name]
            elif analyses:
                target='analysis_forms.AnalysisForm' if file.parent.name=='analysis_pages' else 'ui_results.AllResultsViews / ui_views.WorkspaceViews'
                scope=', '.join(analyses)
            else:raise AssertionError(f'Tela Qt sem mapeamento Flet: {file.name}:{cls.name}')
            records.append(dict(qt_path=str(file.relative_to(root)),qt_class=cls.name,
                flet_target=target,scope=scope,analysis_kinds=analyses))
    from drm_core import stage1
    kinds=set()
    for n in ast.walk(ast.parse(Path(stage1.__file__).read_text(encoding='utf-8'))):
        if isinstance(n,ast.Compare) and ast.unparse(n.left)=='k':
            kinds.update(x.value for x in n.comparators if isinstance(x,ast.Constant) and isinstance(x.value,str))
    assert kinds=={s.kind for s in CATALOG},kinds.symmetric_difference(s.kind for s in CATALOG)
    return dict(schema=1,comparison_base=BASE_HEAD,status='MAPPED',
        scope='Qt presentation classes and AnalysisService contracts at the frozen comparison base',
        qt_presentation_classes=len(records),native_contracts=len(kinds),
        analyses=[dict(kind=s.kind,label=s.label,setup=s.qt_screen,result=s.result_screen) for s in CATALOG],screens=records,
        excluded_claims=['pixel-perfect Qt equality','Windows desktop rendering','web qualification','frozen executables','normative API certification'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path);args=parser.parse_args()
    data=inventory(Path(__file__).resolve().parents[1]);text=json.dumps(data,ensure_ascii=False,indent=2)
    if args.out:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(text+'\n',encoding='utf-8')
    print(text)
