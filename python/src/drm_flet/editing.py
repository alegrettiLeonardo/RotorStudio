"""Explicit form↔Core adapters. Display units never change stored SI values."""
from __future__ import annotations
from dataclasses import dataclass, replace, fields, is_dataclass
import json
import math
import re
from drm_core import (Node, ShaftElement, TaperedShaftElement, AsymmetricShaftElement,
                      Disk, Bearing, CoefficientBearing, Force, BendPoint, RotorDefinition)
from drm_core.units import mm_to_m, m_to_mm, mpa_to_pa, pa_to_mpa, rpm_to_rad_s, rad_s_to_rpm
from drm_core.validation.model import validate_model
from drm_core.domain.bearings import advanced_bearing_from_dict, advanced_bearing_to_dict

@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    unit: str = ""
    integer: bool = False
    section: str = "GEOMETRIA"


def number(text, *, integer=False):
    """Dot or comma decimals; dot+comma requires valid PT thousand grouping."""
    original = str(text)
    s = original.strip().replace("\u00a0", "").replace(" ", "")
    if "," in s and "." in s:
        if not re.fullmatch(r"[+-]?\d{1,3}(?:\.\d{3})+,\d+(?:[eE][+-]?\d+)?", s):
            raise ValueError(f"Recebido {original!r}; use decimal com ponto ou vírgula, sem agrupamento ambíguo.")
        s = s.replace(".", "")
    try: value = float(s.replace(",", "."))
    except ValueError as e: raise ValueError(f"Recebido {original!r}; esperado número finito.") from e
    if not math.isfinite(value): raise ValueError(f"Recebido {original!r}; NaN e infinito não são permitidos.")
    if integer:
        if value != int(value): raise ValueError(f"Recebido {original!r}; esperado inteiro, sem arredondamento.")
        return int(value)
    return value


def display(value, unit):
    fn = {"mm": m_to_mm, "MPa": pa_to_mpa, "rpm": rad_s_to_rpm}.get(unit, float)
    return format(float(fn(value)), ".12g")


def canonical(value, unit):
    return {"mm": mm_to_m, "MPa": mpa_to_pa, "rpm": rpm_to_rad_s}.get(unit, float)(value)


def specs(entity):
    F = FieldSpec
    if isinstance(entity, Node): return [F("number", "Número do nó", integer=True), F("z_m", "Posição axial Z", "mm")]
    if isinstance(entity, ShaftElement):
        return [F("shaft_type", "Tipo DRM (1–8)", integer=True), F("node1", "Nó inicial", integer=True),
                F("node2", "Nó final", integer=True), F("outer_diameter_m", "Diâmetro externo", "mm"),
                F("inner_diameter_m", "Diâmetro interno", "mm"), F("E_pa", "Módulo de Young · E", "MPa", section="MATERIAL"),
                F("G_pa", "Módulo de cisalhamento · G", "MPa", section="MATERIAL"),
                F("rho_kg_m3", "Densidade · ρ", "kg/m³", section="MATERIAL"),
                F("damping_factor", "Amortecimento proporcional", "s", section="CARREGAMENTO"),
                F("axial_force_n", "Força axial", "N", section="CARREGAMENTO"),
                F("torque_nm", "Torque", "N·m", section="CARREGAMENTO")]
    if isinstance(entity, Disk) and entity.disk_type in (1,2,3,4):
        ans = [F("disk_type", "Tipo DRM do disco", integer=True), F("node", "Nó", integer=True)]
        if entity.disk_type in (1,3):
            ans += [F("p3", "Densidade", "kg/m³"), F("p4", "Espessura", "mm"),
                    F("p5", "Diâmetro externo", "mm"), F("p6", "Diâmetro interno", "mm")]
        else:
            ans += [F("p3", "Massa", "kg"), F("p4", "Inércia diametral", "kg·m²"), F("p5", "Inércia polar", "kg·m²")]
        return ans
    if isinstance(entity, Bearing):
        names = {
            1: [], 2: [],
            3: [("Kxx", "N/m"), ("Kyy", "N/m"), ("Cxx", "N·s/m"), ("Cyy", "N·s/m")],
            5: [(k, "N/m" if k.startswith("K") else "N·s/m") for k in ("Kxx","Kxy","Kyx","Kyy","Cxx","Cxy","Cyx","Cyy")],
            7: [("Carga estática", "N"), ("Diâmetro", "mm"), ("Comprimento", "mm"), ("Folga radial", "mm"), ("Viscosidade", "Pa·s")],
            8: [("Diferença de pressão", "Pa"), ("Raio", "mm"), ("Comprimento", "mm"), ("Folga radial", "mm"), ("Velocidade axial", "m/s"), ("Atrito", "")],
        }
        if entity.bearing_type not in names: return []
        return [F("node", "Nó", integer=True)] + [F(f"property_{i}", name, unit, section="COEFICIENTES / GEOMETRIA")
                                                   for i, (name, unit) in enumerate(names[entity.bearing_type])]
    if isinstance(entity, RotorDefinition): return [F("node1", "Nó inicial", integer=True), F("node2", "Nó final", integer=True), F("speed_factor", "Fator de rotação")]
    if isinstance(entity, BendPoint): return [F("node", "Nó", integer=True), F("x_m", "Curvatura X", "mm"), F("y_m", "Curvatura Y", "mm")]
    return []


def form_values(entity):
    out = {}
    for s in specs(entity):
        v = entity.properties[int(s.key.split("_")[1])] if s.key.startswith("property_") else getattr(entity, s.key)
        out[s.key] = display(v, s.unit)
    return out


def from_form(entity, values):
    updated, properties = {}, list(getattr(entity, "properties", ()))
    for s in specs(entity):
        try: v = canonical(number(values[s.key], integer=s.integer), s.unit)
        except (KeyError, ValueError) as e: raise ValueError(f"{s.label}: {e}") from e
        if s.integer: v = int(v)
        if s.key.startswith("property_"): properties[int(s.key.split("_")[1])] = v
        else: updated[s.key] = v
    if isinstance(entity, Bearing): updated["properties"] = tuple(properties)
    if isinstance(entity, Disk) and updated.get("disk_type") not in ((1,3) if entity.disk_type in (1,3) else (2,4)):
        raise ValueError("Não reinterpretar geometria como inércia: crie um novo disco do tipo desejado.")
    return replace(entity, **updated)


def entity_json(entity):
    data = advanced_bearing_to_dict(entity) if hasattr(entity, "model_family") else vars(entity)
    return json.dumps(data, ensure_ascii=False, indent=2)


def from_json(entity, text):
    data = json.loads(text, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"Valor não finito: {x}")))
    if hasattr(entity, "model_family"): return advanced_bearing_from_dict(data)
    allowed = {f.name for f in fields(entity) if f.init}
    if set(data) != allowed: raise ValueError(f"Campos esperados: {', '.join(sorted(allowed))}")
    for key in ("properties", "values"):
        if key in data: data[key] = tuple(data[key])
    return type(entity)(**data)


def validate_editable_model(model):
    """Keep Core validation authoritative, adding finite/form checks before it."""
    def check(value):
        if is_dataclass(value):
            for f in fields(value): check(getattr(value, f.name))
        elif isinstance(value, dict):
            for v in value.values(): check(v)
        elif isinstance(value, (list, tuple)):
            for v in value: check(v)
        elif isinstance(value, (int,float)) and not math.isfinite(value):
            raise ValueError("Valor não finito no modelo. Corrija NaN/Inf antes de aplicar.")
    check(model)
    if not model.nodes:
        if any(getattr(model, k) for k in ("shafts", "disks", "bearings", "advanced_bearings", "forces", "bend", "rotors")):
            raise ValueError("Modelo sem nós contém entidades dependentes. Remova as referências antes de excluir o último nó.")
        return
    node_ids = {n.number for n in model.nodes}
    for collection in (model.shafts, model.disks, model.bearings, model.advanced_bearings, model.bend, model.rotors):
        for entity in collection:
            for attr in ("node", "node1", "node2"):
                if hasattr(entity, attr):
                    value = getattr(entity, attr)
                    if isinstance(value, bool) or int(value) != value or value not in node_ids:
                        raise ValueError(f"{type(entity).__name__}.{attr}: recebido {value}; esperado número de nó inteiro existente.")
    for force in model.forces:
        if force.force_type in (1, 2, 6, 7):
            if not force.values or force.values[0] not in node_ids or int(force.values[0]) != force.values[0]:
                raise ValueError("Força/desbalanceamento aponta para nó inexistente. Corrija a referência antes de aplicar.")
    for n in model.nodes:
        if int(n.number) != n.number or n.number < 1: raise ValueError("Número do nó deve ser inteiro >= 1.")
    for d in model.disks:
        if d.disk_type in (1,3) and not (d.p3 > 0 and d.p4 > 0 and d.p5 > d.p6 >= 0):
            raise ValueError("Disco geométrico: esperado ρ>0, espessura>0 e Ø externo > Ø interno >= 0.")
        if d.disk_type in (2,4) and not (d.p3 > 0 and d.p4 >= 0 and d.p5 >= 0):
            raise ValueError("Disco inercial: esperado massa>0 e inércias >= 0.")
    frame = "rotating" if any(isinstance(s, AsymmetricShaftElement) for s in model.shafts) else ("coaxial" if model.rotors else "stationary")
    validate_model(model, analysis=frame)


def coefficient_csv(bearing: CoefficientBearing, text: str, interpolation: str) -> CoefficientBearing:
    """Edit K/C through the Core table importer, retaining M and provenance.

    The supported text is explicitly semicolon-delimited and speed-based. A
    frequency axis is never silently flattened or interpreted as shaft speed.
    """
    import csv
    import io
    import numpy as np
    from drm_core import parse_coefficient_table
    if not isinstance(bearing, CoefficientBearing) or bearing.frequency_rad_s:
        raise ValueError("O editor CSV requer CoefficientBearing sem eixo de frequência.")
    columns = ["rpm", "kxx", "kxy", "kyx", "kyy", "cxx", "cxy", "cyx", "cyy"]
    lines = list(csv.reader(io.StringIO(text.strip()), delimiter=";"))
    if not lines or [v.strip().lower() for v in lines[0]] != columns:
        raise ValueError("Cabeçalho esperado: " + ";".join(columns))
    data = []
    for i, row in enumerate(lines[1:], 2):
        if len(row) != 9:
            raise ValueError(f"Linha {i}: esperado exatamente nove colunas.")
        data.append("|".join(str(number(v)) for v in row))
    raw = "TABLE§" + "|".join(columns) + "§" + "§".join(data)
    imported = parse_coefficient_table(raw, node=bearing.node, speed_unit="rpm",
        stiffness_unit="N/m", damping_unit="N*s/m", coordinate_convention="X/Y",
        cross_coupling_convention="force-row/displacement-column", source_format="Flet CSV")
    typed = imported.to_coefficient_bearing(interpolation=interpolation, tag=bearing.tag)
    if tuple(typed.speed_rad_s) != tuple(bearing.speed_rad_s) and any(
        np.asarray(getattr(bearing, k)).ndim > 0 for k in ("mxx", "myy", "mxy", "myx")
        if getattr(bearing, k) is not None
    ):
        raise ValueError("Eixo alterado com massa dependente de velocidade. Edite K/C/M conjuntamente no editor SI.")
    candidate = replace(bearing, **{k: getattr(typed, k) for k in columns[1:]},
        speed_rad_s=typed.speed_rad_s, interpolation=interpolation,
        provenance={**dict(bearing.provenance), "last_editor": "RotorStudio Flet CSV", "sign_transform": "NONE"})
    from drm_core.domain.bearings import validate_advanced_bearing
    validate_advanced_bearing(candidate)
    return candidate
