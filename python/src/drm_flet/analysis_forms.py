"""Typed Flet configuration forms for every AnalysisService entry point."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import flet as ft

from .analysis_catalog import (BY_KIND, CATALOG, DOFS, InputSpec, build_case,
    default_values, values_from_case, import_history_csv, format_vector)


class AxisControl:
    """Uniform or explicitly sampled independent variable, in labelled units."""
    def __init__(self, app, spec, value):
        self.app, self.spec = app, spec
        value = dict(value)
        self.mode = ft.Dropdown(value=value.get("mode", "uniform"), label="Grade",
            options=[ft.DropdownOption("uniform", "Uniforme"), ft.DropdownOption("explicit", "Amostras explícitas")],
            text_size=11, dense=True, width=155, on_select=self.sync)
        self.start = app.field("Início", value.get("start", 0), spec.unit, width=140)
        self.stop = app.field("Fim", value.get("stop", 1), spec.unit, width=140)
        self.count = app.field("Pontos", value.get("count", 31), width=110)
        self.explicit = app.field("Valores separados por ;", value.get("values", ""), spec.unit)
        self.uniform = ft.Row([self.start, self.stop, self.count], wrap=True, spacing=8)
        self.root = ft.Column([app.txt(spec.label, 12, bold=True), self.mode, self.uniform, self.explicit], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.sync()

    def sync(self, event=None):
        self.uniform.visible = self.mode.value == "uniform"
        self.explicit.visible = not self.uniform.visible
        if event is not None: self.root.update()

    @property
    def value(self):
        return dict(mode=self.mode.value, start=self.start.value, stop=self.stop.value,
                    count=self.count.value, values=self.explicit.value)


class LoadRows:
    """Engineering table: physical node, force/moment DOF and explicit samples."""
    def __init__(self, app, model, values, *, temporal=False):
        self.app, self.model, self.temporal = app, model, temporal
        self.rows = []
        self.body = ft.Column(spacing=8)
        self.root = ft.Column([app.notice(
            "x/y em N; alpha/beta em N·m. Constant: valor. Sine: amplitude;ω [rad/s];fase [rad]. "
            "Pulse: amplitude;início [s];fim [s]. Samples: um valor por instante."
            if temporal else "x/y em N; alpha/beta em N·m. Parte real em fase; parte imaginária em quadratura. "
            "Cada parte pode ser uma constante ou uma amostra por frequência; use ; como separador."),
            self.body, app.button("Adicionar força / momento", lambda e: self.add(), ft.Icons.ADD)], spacing=10)
        for value in values: self.add(value, update=False)

    def add(self, value=None, *, update=True):
        a = self.app
        value = value or dict(node=self.model.nodes[0].number, dof=0, shape="Constant", real="1", imag="0", values="1")
        node = ft.Dropdown(label="Nó", value=str(value["node"]), width=100, text_size=11, dense=True,
            options=[ft.DropdownOption(str(n.number)) for n in self.model.nodes])
        dof = ft.Dropdown(label="GL / unidade", value=str(value["dof"]), width=145, text_size=11, dense=True,
            options=[ft.DropdownOption(str(i), f"{d} · {'N' if i < 2 else 'N·m'}") for i, d in enumerate(DOFS)])
        kind = ft.Dropdown(label="Histórico", value=value.get("shape", "Constant"), width=125, text_size=11, dense=True,
            options=[ft.DropdownOption(x) for x in ("Constant", "Sine", "Pulse", "Samples")])
        real = a.field("Real", value.get("real", "0")); real.expand = True
        imag = a.field("Imaginária", value.get("imag", "0")); imag.expand = True
        samples = a.field("Parâmetros / amostras", value.get("values", "1")); samples.expand = True
        row = dict(node=node, dof=dof, shape=kind, real=real, imag=imag, values=samples)
        box = ft.Container(ft.Column([
            ft.Row([node, dof, *([kind] if self.temporal else []),
                    a.ib(ft.Icons.DELETE_OUTLINE, "Remover linha", lambda e: self.remove(row))], wrap=True, spacing=6),
            ft.Row([samples] if self.temporal else [real, imag], spacing=8)], spacing=8),
            padding=9, border=ft.Border.all(1, a.p.line), border_radius=8)
        row["box"] = box
        self.rows.append(row); self.body.controls.append(box)
        if update: self.body.update()

    def remove(self, row):
        self.rows.remove(row); self.body.controls.remove(row["box"]); self.body.update()

    @property
    def value(self):
        return [{k: v.value for k, v in row.items() if k != "box"} for row in self.rows]


class AnalysisForm:
    def __init__(self, app, kind, case=None):
        self.app, self.kind, self.original = app, kind, case
        self.spec = BY_KIND[kind]
        self.model = deepcopy(app.session.project.model)
        self.model_hash = self.model.model_hash()
        self.name = app.field("Nome do caso", case.name if case else self.unique_name())
        self.controls = {}
        self.error = ft.Text("", color=app.p.error, size=12, selectable=True)
        values = values_from_case(case, self.model) if case else default_values(kind, self.model)
        self.values = values
        sections = {}; labels = []
        for f in self.spec.inputs:
            if f.section not in sections: sections[f.section] = []; labels.append(f.section)
            c = self.make_control(f, values[f.key]); self.controls[f.key] = c
            sections[f.section].append(c.root if hasattr(c, "root") else c)
            if f.note: sections[f.section].append(app.notice(f.note))
        content = [ft.Container(self.name, padding=ft.Padding.only(top=8))]
        if self.spec.note: content.append(app.notice(self.spec.note))
        for label in labels:
            content.extend([app.txt(label, 10, muted=True, bold=True), *sections[label], ft.Divider(color=app.p.line)])
        if kind == "general_time_response":
            content.insert(1, app.button("Importar histórico CSV (SI)", self.import_history, ft.Icons.UPLOAD_FILE))
        if kind.startswith("coaxial"):
            content.append(app.button("Editar definições de rotor", lambda e: self.rotor_definitions()))
        content.append(self.error)
        self.root = ft.Column(content, spacing=12, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.dialog = ft.AlertDialog(modal=True, title=app.txt(self.spec.label, 18, bold=True),
            content=ft.Container(self.root, width=790, height=590, padding=ft.Padding.only(top=8)),
            actions=[app.button("Cancelar", lambda e: app.page.pop_dialog()),
                     app.button("Salvar caso", self.save),
                     app.button("Executar", self.run, ft.Icons.PLAY_ARROW, primary=True)])
        self.baseline = self.read_values()
        self.apply_visibility()

    def unique_name(self):
        existing = {c.name for c in self.app.session.project.analyses}
        i = 1
        while f"{self.spec.label}_{i:02d}" in existing: i += 1
        return f"{self.spec.label}_{i:02d}"

    def make_control(self, f, value):
        app = self.app
        if f.kind == "grid": return AxisControl(app, f, value)
        if f.kind.endswith("loads"): return LoadRows(app, self.model, value, temporal=f.kind == "time_loads")
        if f.kind == "bool": return ft.Checkbox(label=f.label, value=bool(value), label_style=ft.TextStyle(size=12), on_change=lambda e: self.apply_visibility(update=True))
        if f.kind in ("select", "dof"):
            choices = [ft.DropdownOption(str(i), f"Nó {n.number} · {DOFS[j]}")
                       for i, (n, j) in enumerate((n, j) for n in self.model.nodes for j in range(4))] if f.kind == "dof" else [ft.DropdownOption(str(x)) for x in f.choices]
            return ft.Dropdown(label=f.label, value=str(value), options=choices, text_size=12, dense=True,
                key=f"analysis-{f.key}", on_select=lambda e: self.apply_visibility(update=True))
        return app.field(f.label, value, f.unit, key=f"analysis-{f.key}")

    def read_values(self):
        return {k: c.value for k, c in self.controls.items()}

    def apply_visibility(self, update=False):
        c = self.controls
        if "coefficient_policy" in c:
            fixed = c["coefficient_policy"].value == "FIXED_WHIRL"
            matched = c["coefficient_policy"].value == "MATCHED_WHIRL"
            c["whirl_frequency_rad_s"].disabled = not fixed
            c["whirl_rtol"].disabled = c["whirl_max_iter"].disabled = not matched
        if "method" in c:
            c["initial_estimates"].disabled = c["method"].value != "3"
            c["max_iterations"].disabled = c["tol"].disabled = c["method"].value == "auto"
        if "speed_policy" in c: c["speed"].disabled = c["speed_policy"].value == "synchronous"
        if "explicit_unbalance" in c:
            for key in ("unbalance_nodes", "unbalance_magnitude_kg_m", "unbalance_phase_rad"):
                c[key].disabled = not c["explicit_unbalance"].value
        if update: self.root.update()

    def build(self):
        if self.app.session.project.model.model_hash() != self.model_hash:
            raise ValueError("O modelo mudou com o diálogo aberto. Cancele e reabra para atualizar nós/GL.")
        values = self.read_values()
        if self.original is not None and values == self.baseline:
            if not self.name.value.strip(): raise ValueError("Informe o nome do caso.")
            return replace(self.original, name=self.name.value.strip())
        return build_case(self.kind, values, self.model, self.name.value, original=self.original)

    def commit(self, case):
        app = self.app
        if app.busy: raise ValueError("Aguarde o término da execução antes de editar casos.")
        current = app.session.project.analyses
        original_name = self.original.name if self.original else None
        if any(c.name == case.name and c.name != original_name for c in current):
            raise ValueError("Já existe um caso com esse nome. Edite-o ou escolha outro nome.")
        def mutation(p):
            if original_name is not None:
                index = next((i for i, c in enumerate(p.analyses) if c.name == original_name), None)
                if index is None: raise ValueError("O caso original não existe mais.")
                p.analyses[index] = case
            else: p.analyses.append(case)
        app.session.transact(f"Configurar caso {case.name}", mutation, validate=False)

    def show_error(self, exc):
        self.error.value = str(exc); self.error.update()

    def save(self, event=None):
        try:
            case = self.build(); self.commit(case)
            self.app.page.pop_dialog(); self.app.render()
            return case
        except Exception as exc: self.show_error(exc); return None

    async def run(self, event=None):
        try:
            case = self.build(); self.commit(case)
            self.app.page.pop_dialog()
        except Exception as exc: self.show_error(exc); return None
        return await self.app.run_case(case)

    async def import_history(self, event=None):
        try:
            files = await ft.FilePicker().pick_files(allow_multiple=False, with_data=self.app.page.web)
            if not files: return
            f = files[0]; data = f.bytes if self.app.page.web else Path(f.path).read_bytes()
            values = import_history_csv(data.decode("utf-8-sig"), self.model)
            axis = self.controls["time_s"]; axis.mode.value = "explicit"; axis.explicit.value = values["time_s"]["values"]; axis.sync()
            self.controls["speed"].value = values["speed"]
            rows = self.controls["loads"]; rows.rows.clear(); rows.body.controls.clear()
            for row in values["loads"]: rows.add(row, update=False)
            self.root.update()
        except Exception as exc: self.show_error(exc)

    def rotor_definitions(self):
        # Close the analysis draft before editing the authoritative model.
        self.app.page.pop_dialog(); self.app.entity_collection_dialog("rotors")


class AnalysisActions:
    def analysis_dialog(self, event=None, *, kind="modal_sweep", case=None):
        if self.busy: self.error("Análise em execução", "Aguarde ou solicite cancelamento."); return
        if self.form_changed() and not self.apply_properties(): return
        if case and case.options.get("flet_scope") in ("bearing_fields","operating_map"):
            return self.bearing_job_dialog(case=case)
        if kind not in BY_KIND: self.error("Tipo sem tela", f"AnalysisCase.kind={kind!r}"); return
        try:
            form = AnalysisForm(self, kind, case)
            self.active_analysis_form = form
            self.page.show_dialog(form.dialog)
        except Exception as exc: self.error("Não foi possível configurar", exc)

    def advanced_case_dialog(self, event=None):
        # Former raw JSON entry point becomes the complete typed catalogue.
        self.navigate("analyses")

    def analyses_view(self):
        controls = [self.txt("Análises", 23, bold=True), self.notice("Todos os tipos do AnalysisService possuem formulário próprio. A execução usa o modelo atual e preserva as restrições numéricas do Core.")]
        for group in dict.fromkeys(s.group for s in CATALOG):
            controls.append(self.txt(group.upper(), 10, muted=True, bold=True))
            controls.append(ft.Row([self.button(s.label, lambda e, k=s.kind: self.analysis_dialog(kind=k), ft.Icons.QUERY_STATS)
                                   for s in CATALOG if s.group == group], wrap=True, spacing=8, run_spacing=8))
        controls.extend([ft.Divider(color=self.p.line), self.txt("Casos salvos", 15, bold=True)])
        for c in self.session.project.analyses:
            controls.append(ft.Row([self.txt(c.name, 12, expand=True), self.chip(c.kind),
                self.button("Editar", lambda e, case=c: self.analysis_dialog(kind=case.kind, case=case)),
                self.button("Executar", lambda e, case=c: self.page.run_task(self.run_case, case), disabled=self.busy),
                self.ib(ft.Icons.DELETE_OUTLINE, "Remover caso", lambda e, name=c.name: self.page.run_task(self.delete_case, name))], spacing=6))
        return ft.Column(controls, spacing=13, expand=True, scroll=ft.ScrollMode.AUTO)

    async def delete_case(self, name):
        if not self.may_edit(): return
        if not await self.confirm("Remover caso", f"Remover {name}? Os resultados já calculados continuarão disponíveis."): return
        self.session.transact(f"Remover caso {name}", lambda p: setattr(p, "analyses", [c for c in p.analyses if c.name != name]), validate=False)
        self.render()
