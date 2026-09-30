"""Complete, Qt-independent catalogue of the current Core analysis contracts.

Only input materialization and display-unit conversion live here. All matrices,
eigensystems, time integration and operating-map physics remain in drm_core.
The catalogue is also consumed by the GUI, round-trip tests and coverage audit.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import csv
import io
import json
import math
import re
from typing import Any

import numpy as np
from drm_core import AnalysisCase
from drm_core.units import rpm_to_rad_s, rad_s_to_rpm
from .editing import number

DOFS = ("x", "y", "alpha", "beta")
POLICIES = ("SYNCHRONOUS_COEFFICIENTS", "FIXED_WHIRL", "MATCHED_WHIRL")


@dataclass(frozen=True)
class InputSpec:
    key: str
    label: str
    default: Any = ""
    kind: str = "float"
    unit: str = ""
    choices: tuple = ()
    minimum: float | None = None
    maximum: float | None = None
    optional: bool = False
    section: str = "CONFIGURAÇÃO"
    note: str = ""


@dataclass(frozen=True)
class AnalysisSpec:
    kind: str
    label: str
    group: str
    inputs: tuple[InputSpec, ...]
    qt_screen: str
    result_screen: str
    note: str = ""


def field(key, label, value=0., unit="", **kw):
    return InputSpec(key, label, value, unit=unit, **kw)


def grid(key, label, a, b, count, unit):
    return InputSpec(key, label, (a, b, count), "grid", unit,
                     note="Grade uniforme ou amostras explícitas. Nenhum ponto calculado é interpolado pela tela.")


SPEED = field("speed_rad_s", "Rotação do rotor Ω", 3600., "rpm")
OUTPUT = InputSpec("output_dof", "Resposta · nó e grau de liberdade", 0, "dof", section="VISUALIZAÇÃO")
INPUT = InputSpec("input_dof", "Entrada · nó e grau de liberdade", 0, "dof", section="VISUALIZAÇÃO")
RESPONSE = InputSpec("response", "Grandeza de resposta", "displacement", "select",
                     choices=("displacement", "velocity", "acceleration"), section="VISUALIZAÇÃO")
MODAL = (
    InputSpec("coefficient_policy", "Política dos coeficientes", POLICIES[0], "select", choices=POLICIES),
    field("whirl_frequency_rad_s", "Whirl fixo ω", 60., "Hz"),
    field("whirl_rtol", "Tolerância relativa · whirl casado", .001, minimum=1e-12, maximum=1),
    field("whirl_max_iter", "Iterações máximas · whirl casado", 15, kind="int", minimum=1, maximum=10000),
    InputSpec("with_eigenvectors", "Calcular autovetores", True, "bool"),
    InputSpec("with_kappa", "Calcular precessão κ", True, "bool"),
)
EXCITATION = grid("frequency_rad_s", "Frequência de excitação ω", .1, 140, 71, "Hz")
ROTOR_POLICY = (
    InputSpec("speed_policy", "Rotação do rotor", "fixed", "select", choices=("fixed", "synchronous")),
    field("speed", "Rotação fixa Ω", 3600., "rpm"),
)
SWEEP = grid("speeds_rad_s", "Varredura de rotação", 100, 6000, 31, "rpm")
TOLERANCES = (field("rtol", "Tolerância relativa", .001, minimum=1e-14, maximum=1),
              field("atol", "Tolerância absoluta", 1e-6, minimum=1e-15, maximum=1),
              field("h_init", "Passo inicial (0 = automático)", 0., "s", minimum=0),
              field("h_max", "Passo máximo (0 = automático)", 0., "s", minimum=0))
REDUCTION = field("nr", "GL reduzidos (0 = modelo completo)", 0, kind="int", minimum=0, maximum=100000)

CATALOG = (
    AnalysisSpec("modal", "Modal / raízes características", "Modal", (SPEED, *MODAL), "ModalSetupDialog", "ModalResultView"),
    AnalysisSpec("modal_sweep", "Diagrama de Campbell", "Modal", (
        grid("speeds_rad_s", "Varredura de rotação", 0, 6000, 31, "rpm"), *MODAL,
        field("nx", "Ordem máxima das linhas de excitação", 2., minimum=.1, maximum=20, section="VISUALIZAÇÃO")),
        "CampbellSetupDialog", "CampbellResultView"),
    AnalysisSpec("critical_speeds", "Velocidades críticas", "Modal", (
        field("NX", "Ordem de excitação NX", 1., minimum=.1, maximum=20),
        InputSpec("damped", "Frequências amortecidas", True, "bool"),
        field("ncrit", "Número de críticas", 4, kind="int", minimum=1, maximum=100),
        InputSpec("method", "Método", "2", "select", choices=("auto", "2", "3")),
        field("max_iterations", "Iterações máximas", 40, kind="int", minimum=1, maximum=10000),
        field("tol", "Tolerância de convergência", 1e-6, minimum=1e-14, maximum=1),
        InputSpec("initial_estimates", "Estimativas iniciais · método 3", "", "vector", "rpm", optional=True),
        InputSpec("with_mode_shapes", "Recuperar formas modais (métodos 2/3)", False, "bool")),
        "CriticalSpeedSetupDialog", "CriticalSpeedResultView",
        "Método 3 exige uma estimativa por crítica. A lista pode conter raízes repetidas; confira convergência e Campbell."),
    AnalysisSpec("static", "Análise estática", "Estática", (), "StaticSetupDialog", "StaticResultView",
        "Escopo A1 do Core: gravidade, eixo circular simples e apoios radiais clássicos. Não converte mancais físicos em constantes."),
    AnalysisSpec("frequency_response", "Resposta síncrona", "Resposta harmônica", (SWEEP, OUTPUT),
        "SynchronousResponseSetupDialog", "FrequencyResponseResultView", "Usa os desbalanceamentos e a pré-curvatura definidos no modelo."),
    AnalysisSpec("auxiliary_frequency_response", "FRF · apoio auxiliar / spinner", "Resposta harmônica", (
        field("rotor_speed_rad_s", "Rotação do rotor Ω", 3600., "rpm"),
        grid("omega_rad_s", "Frequência independente de excitação", .1, 140, 71, "Hz"),
        InputSpec("direction", "Sentido do spinner", "1", "select", choices=("1", "-1")), OUTPUT),
        "FrequencyResponseSetupDialog", "FrequencyResponseResultView", "Requer força tipo 6 ou 7 no modelo. ω é independente de Ω."),
    AnalysisSpec("foundation_frequency_response", "Excitação da fundação · frequência", "Fundação", (
        field("rotor_speed_rad_s", "Rotação do rotor Ω", 3600., "rpm"),
        grid("omega_rad_s", "Frequência da fundação", .1, 140, 71, "Hz"), OUTPUT),
        "FrequencyResponseSetupDialog", "FrequencyResponseResultView", "Requer excitação de base tipo 4 no modelo."),
    AnalysisSpec("general_frf", "FRF geral · matriz de transferência", "Resposta harmônica", (
        EXCITATION, *ROTOR_POLICY, InputSpec("free_free", "Modelo livre-livre", False, "bool"), INPUT, OUTPUT, RESPONSE),
        "GeneralFrfSetupDialog", "GeneralFrfResultView", "Matriz completa 4 GL/nó. Entradas em N ou N·m; saídas em m ou rad e derivadas."),
    AnalysisSpec("forced_response", "Resposta forçada · forças e momentos", "Resposta harmônica", (
        EXCITATION, *ROTOR_POLICY, InputSpec("loads", "Forças e momentos complexos", (), "harmonic_loads", section="CARREGAMENTO"), OUTPUT, RESPONSE),
        "ForcedResponseSetupDialog", "ForcedResponseResultView", "Forças repetidas no mesmo GL são somadas. Não acrescenta desbalanceamento automaticamente."),
    AnalysisSpec("general_time_response", "Resposta temporal geral · F(t)", "Transiente", (
        grid("time_s", "Grade temporal", 0., .04, 81, "s"),
        InputSpec("speed", "Ω(t): constante ou uma amostra por instante", "3600", "vector", "rpm"),
        field("gamma", "Newmark γ", .5, minimum=1e-12), field("beta", "Newmark β", .25, minimum=1e-12),
        field("tol", "Tolerância absoluta do resíduo", 1e-6, minimum=1e-15),
        InputSpec("weight", "Incluir gravidade do Core", False, "bool"),
        InputSpec("loads", "Históricos de forças e momentos", (), "time_loads", section="CARREGAMENTO"), OUTPUT, RESPONSE),
        "GeneralTimeSetupDialog", "GeneralTimeResultView", "Newmark nativo. Estado inicial q=v=a=0; sem equilíbrio estático inicial implícito."),
    AnalysisSpec("foundation_time_response", "Pulso na fundação · tempo", "Fundação", (
        field("rotor_speed_rad_s", "Rotação do rotor Ω", 3600., "rpm"), field("dt", "Passo de saída", .0001, "s", minimum=1e-9),
        field("npts", "Pontos de saída", 2001, kind="int", minimum=2, maximum=2000000), REDUCTION, *TOLERANCES, OUTPUT),
        "FoundationTimeSetupDialog", "TransientResultView", "Pulso de meia-senoide: amplitudes e duração vêm da força tipo 5."),
    AnalysisSpec("runup", "Run-up / run-down", "Transiente", (
        InputSpec("alpha", "Coeficientes [α₂; α₁; α₀] de φ(t)", "10;0;0", "triple", "rad/s²; rad/s; rad",
                  note="φ(t)=α₂t²+α₁t+α₀. A aceleração angular é 2α₂, não α₂."),
        InputSpec("tspan", "Intervalo [início; fim]", "0;1", "pair", "s"), REDUCTION, *TOLERANCES,
        field("max_points", "Máximo de pontos adaptativos", 200000, kind="int", minimum=2, maximum=2000000), OUTPUT),
        "RunupSetupDialog", "TransientResultView", "Dormand–Prince nativo; as restrições dos mancais e da redução são verificadas pelo Core."),
    AnalysisSpec("coaxial_modal", "Coaxial · análise modal", "Rotores especiais", (SPEED,), "SpecialRotorSetupDialog", "SpecialRotorResultView",
        "Cadastre definições de rotor e acoplamentos tipo 20. Os fatores de rotação podem ser negativos."),
    AnalysisSpec("coaxial_frequency_response", "Coaxial · resposta síncrona", "Rotores especiais", (SWEEP, OUTPUT),
        "SpecialRotorSetupDialog", "SpecialRotorResultView", "A resposta usa os fatores e a convenção de rotação de referência do Core."),
    AnalysisSpec("asymmetric_modal", "Assimétrico · modal no referencial girante", "Rotores especiais", (
        SPEED, InputSpec("with_eigenvectors", "Calcular autovetores", True, "bool")),
        "SpecialRotorSetupDialog", "SpecialRotorResultView", "Os autovalores pertencem ao referencial girante. Apoios incompatíveis são rejeitados, não aproximados."),
    AnalysisSpec("asymmetric_frequency_response", "Assimétrico · resposta no referencial girante", "Rotores especiais", (SWEEP, OUTPUT),
        "SpecialRotorSetupDialog", "SpecialRotorResultView", "Usa o contrato nativo freq_asym; mantenha as restrições de isotropia do Core."),
    AnalysisSpec("ucs", "UCS · mapa de velocidades críticas", "Estabilidade / API", (
        InputSpec("stiffness_range_exponents", "Expoentes de rigidez [mínimo; máximo]", "6;11", "pair", "log10(N/m)"),
        field("num", "Pontos de rigidez", 20, kind="int", minimum=2, maximum=256),
        field("num_modes", "Autovalores modais solicitados", 16, kind="int", minimum=4, maximum=1024),
        InputSpec("bearing_speed_range", "Faixa do mancal [início; fim] · vazio = eixo nativo", "", "pair", "rpm", optional=True),
        InputSpec("synchronous", "Formulação síncrona de Rouch", False, "bool")),
        "UCSSetupDialog", "UCSResultView", "Rigidez por expoentes base 10. Interseções e modais críticos são calculados pelo Core."),
    AnalysisSpec("level1", "Estabilidade · Level 1", "Estabilidade / API", (
        field("rotor_speed_rad_s", "Rotação do rotor Ω", 3600., "rpm"),
        field("cross_coupling_node", "Nó do acoplamento cruzado", 1, kind="int", minimum=1),
        InputSpec("stiffness_range_n_m", "Faixa de Q [início; fim]", "0;2500000", "pair", "N/m"),
        field("num", "Pontos de Q", 7, kind="int", minimum=2, maximum=4096)),
        "Level1SetupDialog", "Level1ResultView", "Kxy=+Q e Kyx=−Q. Seleção modal e decremento logarítmico são fornecidos pelo Core."),
    AnalysisSpec("api617_unbalance", "API 617 · posicionamento de desbalanceamento", "Estabilidade / API", (
        field("mode", "Modo direto (1 = primeiro)", 1, kind="int", minimum=1, maximum=32),
        field("maximum_continuous_speed_rad_s", "Rotação máxima contínua Nmc", 9000, "rpm", minimum=1e-9),
        field("num_modes", "Autovalores solicitados (par)", 12, kind="int", minimum=4, maximum=64)),
        "API617UnbalanceSetupDialog", "API617UnbalanceResultView", "Apresenta o resultado A7 existente; não é uma certificação normativa da máquina."),
    AnalysisSpec("clearance", "API 617 · análise de folgas", "Estabilidade / API", (
        grid("speed_range_rad_s", "Varredura síncrona de rotação", 0, 10000, 101, "rpm"),
        field("minimum_allowable_speed_rad_s", "Rotação mínima admissível Nma", 7000., "rpm", minimum=0),
        field("maximum_continuous_speed_rad_s", "Rotação máxima contínua Nmc", 9000., "rpm", minimum=1e-9),
        InputSpec("probe_nodes", "Nós das sondas radiais", "1;3", "nodes", section="SONDAS RADIAIS"),
        InputSpec("probe_angles_rad", "Ângulos das sondas", "45;-45", "vector", "deg", section="SONDAS RADIAIS"),
        InputSpec("probe_tags", "Nomes das sondas · separados por ;", "DE-45;NDE-45", "tags", section="SONDAS RADIAIS"),
        InputSpec("clearance_nodes", "Nós das folgas", "1;2;3", "nodes", section="FOLGAS DE OPERAÇÃO"),
        InputSpec("radial_clearance_m", "Folgas radiais · não diametrais", "100;250;120", "vector", "µm", section="FOLGAS DE OPERAÇÃO"),
        InputSpec("clearance_tags", "Nomes das folgas · separados por ;", "DE;centro;NDE", "tags", section="FOLGAS DE OPERAÇÃO"),
        field("mode", "Modo direto (1 = primeiro)", 1, kind="int", minimum=1, maximum=32, section="ESCALA / DESBALANCEAMENTO"),
        field("num_modes", "Autovalores solicitados (par)", 12, kind="int", minimum=4, maximum=64, section="ESCALA / DESBALANCEAMENTO"),
        field("scale_factor_cap", "Limite do fator de escala · vazio = sem limite", "", optional=True, minimum=1e-12, section="ESCALA / DESBALANCEAMENTO"),
        InputSpec("explicit_unbalance", "Usar desbalanceamento explícito em vez do posicionamento A7", False, "bool", section="ESCALA / DESBALANCEAMENTO"),
        InputSpec("unbalance_nodes", "Nós do desbalanceamento explícito", "2", "nodes", section="ESCALA / DESBALANCEAMENTO"),
        InputSpec("unbalance_magnitude_kg_m", "Magnitudes explícitas", "0.00002", "vector", "kg·m", section="ESCALA / DESBALANCEAMENTO"),
        InputSpec("unbalance_phase_rad", "Fases explícitas", "0", "vector", "deg", section="ESCALA / DESBALANCEAMENTO")),
        "ClearanceSetupDialog", "ClearanceResultView",
        "A8 nativo: Nma/Nmc são inseridas no eixo calculado. Amplitudes pico a pico; limite de 75% da folga diametral. "
        "O limite do fator de escala só se aplica quando preenchido. Igualdade no limite de folga reprova. "
        "Escopo: linha única circular de 4 GL/nó; não certifica conformidade normativa integral."),
    AnalysisSpec("bearing_matrices", "Mancais · matrizes globais", "Mancais", (SPEED,),
        "BearingPerformancePage", "BearingPerformancePage", "M, C, K, máscara de restrições e excentricidade da montagem nativa."),
)
BY_KIND = {s.kind: s for s in CATALOG}


def unit_to_core(value, unit):
    if unit == "rpm": return rpm_to_rad_s(value)
    if unit == "Hz": return rpm_to_rad_s(np.asarray(value, float) * 60.)
    if unit == "deg": return np.deg2rad(value)
    if unit == "µm": return np.asarray(value, float) * 1e-6
    return value


def unit_to_display(value, unit):
    if unit == "rpm": return rad_s_to_rpm(value)
    if unit == "Hz": return np.asarray(rad_s_to_rpm(value)) / 60.
    if unit == "deg": return np.rad2deg(value)
    if unit == "µm": return np.asarray(value, float) * 1e6
    return value


def numeric_array(value, *, ndim=None, allow_empty=False):
    """Parse numeric vectors/matrices; reject bool, ragged, NaN and Inf."""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            if allow_empty: return np.asarray([], float)
            raise ValueError("Informe ao menos um valor numérico.")
        if text[0] == "[":
            value = json.loads(text)
        else:
            # Semicolon is the unambiguous PT list separator; a decimal comma
            # is accepted inside each item only when semicolons separate items.
            pieces = text.split(";") if ";" in text else re.split(r"[,\s]+", text)
            value = [number(x) for x in pieces if x.strip()]
    def reject_booleans(x):
        if isinstance(x, (bool, np.bool_)): raise ValueError("Booleano não é coeficiente numérico.")
        if isinstance(x, (list, tuple, np.ndarray)):
            for y in x: reject_booleans(y)
    reject_booleans(value)
    try: result = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc: raise ValueError("Esperado vetor/matriz numérico retangular.") from exc
    if not np.isfinite(result).all(): raise ValueError("NaN e infinito não são permitidos.")
    if not allow_empty and not result.size: raise ValueError("Vetor vazio não é permitido.")
    if ndim is not None and result.ndim != ndim: raise ValueError(f"Esperado {ndim} dimensão(ões); recebido {result.shape}.")
    return result


def materialize_grid(value):
    if isinstance(value, dict):
        if value.get("mode") == "explicit":
            result = numeric_array(value.get("values", ""), ndim=1)
        else:
            n = number(value["count"], integer=True)
            if not 1 <= n <= 10000: raise ValueError("Grade: esperado 1–10000 pontos.")
            a, b = number(value["start"]), number(value["stop"])
            if (n > 1 and b <= a) or (n == 1 and b != a):
                raise ValueError("Grade: fim > início, ou início = fim para um único ponto.")
            result = np.linspace(a, b, n)
    else: result = numeric_array(value, ndim=1)
    if not 1 <= result.size <= 10000 or (result.size > 1 and np.any(np.diff(result) <= 0)):
        raise ValueError("A grade deve conter 1–10000 amostras finitas e estritamente crescentes.")
    return result


def default_values(kind, model):
    values = {}
    for spec in BY_KIND[kind].inputs:
        value = deepcopy(spec.default)
        if spec.kind == "grid":
            value = dict(mode="uniform", start=value[0], stop=value[1], count=value[2], values="")
        elif spec.kind.endswith("loads"):
            node = model.nodes[0].number if model.nodes else 1
            value = [dict(node=node, dof=0, shape="Constant", real="1", imag="0", values="1")]
        values[spec.key] = value
    if kind == "critical_speeds" and model.advanced_bearings:
        values["method"] = "3"
        values["initial_estimates"] = "1000;2000;3000;4000"
    if kind == "clearance" and model.nodes:
        nodes = [n.number for n in model.nodes]
        values.update(probe_nodes=f"{nodes[0]};{nodes[-1]}",
                      clearance_nodes=f"{nodes[0]};{nodes[len(nodes)//2]};{nodes[-1]}",
                      unbalance_nodes=str(nodes[len(nodes)//2]))
    return values


def loads_matrix(entries, axis, model, *, temporal=False):
    """Materialize user-specified loads, not a mechanical response."""
    if not entries: raise ValueError("Cadastre uma força explícita, inclusive zero quando intencional.")
    n = 4 * len(model.nodes)
    if n < 4: raise ValueError("Cadastre nós antes de definir forças.")
    count = len(axis)
    result = np.zeros((n, count), dtype=float if temporal else complex)
    index = {node.number: i for i, node in enumerate(model.nodes)}
    for row, entry in enumerate(entries, 1):
        node = number(entry["node"], integer=True); dof = number(entry["dof"], integer=True)
        if node not in index or not 0 <= dof < 4: raise ValueError(f"Força {row}: selecione nó existente e GL x/y/alpha/beta.")
        if temporal:
            x = numeric_array(entry.get("values", ""), ndim=1)
            shape = entry.get("shape", "Constant")
            expected = {"Constant": 1, "Sine": 3, "Pulse": 3, "Samples": count}.get(shape)
            if expected is None or x.size != expected: raise ValueError(f"Força {row} · {shape}: esperado {expected} valores.")
            if shape == "Sine": y = x[0] * np.sin(x[1] * axis + x[2])
            elif shape == "Pulse":
                if x[2] < x[1]: raise ValueError(f"Força {row}: fim do pulso anterior ao início.")
                y = np.where((axis >= x[1]) & (axis <= x[2]), x[0], 0.)
            else: y = x
        else:
            real = numeric_array(entry.get("real", "0"), ndim=1)
            imag = numeric_array(entry.get("imag", "0"), ndim=1)
            if real.size not in (1, count) or imag.size not in (1, count):
                raise ValueError(f"Força {row}: parte real e imaginária exigem 1 ou {count} amostras.")
            y = real + 1j * imag
        result[4 * index[node] + dof] += y
    if not np.isfinite(result).all(): raise ValueError("Soma de forças não finita; reduza os valores.")
    return result


def build_case(kind, values, model, name, *, original=None):
    """Validate a complete form before constructing a persistent AnalysisCase."""
    if kind not in BY_KIND: raise ValueError(f"Análise sem contrato de tela: {kind}")
    if not str(name).strip(): raise ValueError("Informe o nome do caso.")
    if not model.nodes: raise ValueError("O modelo precisa de nós antes de configurar uma análise.")
    p = {}; options = deepcopy(original.options) if original is not None else {}
    # All current API parameters have explicit controls. Preserve additional
    # forward-compatible arguments from a saved case rather than dropping them.
    extras = deepcopy(original.parameters) if original is not None else {}
    for f in BY_KIND[kind].inputs:
        raw = values.get(f.key, f.default)
        try:
            if f.kind.endswith("loads"): continue
            if kind == "clearance" and f.key.startswith("unbalance_") and not values.get("explicit_unbalance", False): continue
            if f.optional and (raw is None or (isinstance(raw, str) and not raw.strip())):
                value = None
            elif f.kind == "bool":
                if not isinstance(raw, bool): raise ValueError("Esperado verdadeiro/falso.")
                value = raw
            elif f.kind == "select":
                value = str(raw)
                if value not in f.choices: raise ValueError(f"Escolha um de {f.choices}.")
            elif f.kind == "tags":
                value = [x.strip() for x in str(raw).split(";")]
                if any(not x for x in value): raise ValueError("Nomes vazios não são permitidos.")
            elif f.kind == "nodes":
                a = numeric_array(raw, ndim=1)
                if not np.all(a == np.floor(a)): raise ValueError("Números de nós devem ser inteiros.")
                value = a.astype(int).tolist()
                if not set(value).issubset({n.number for n in model.nodes}): raise ValueError("Há nó inexistente no modelo.")
            elif f.kind == "dof":
                value = number(raw, integer=True)
                if not 0 <= value < 4 * len(model.nodes): raise ValueError("GL fora do modelo.")
            elif f.kind in ("pair", "triple", "vector", "grid"):
                value = materialize_grid(raw) if f.kind == "grid" else numeric_array(raw, ndim=1)
                if f.kind in ("pair", "triple") and len(value) != {"pair": 2, "triple": 3}[f.kind]:
                    raise ValueError("Quantidade incorreta de valores.")
                value = np.asarray(unit_to_core(value, f.unit)).tolist()
            else:
                value = number(raw, integer=f.kind == "int")
                if f.minimum is not None and value < f.minimum: raise ValueError(f"Mínimo: {f.minimum}.")
                if f.maximum is not None and value > f.maximum: raise ValueError(f"Máximo: {f.maximum}.")
                value = unit_to_core(value, f.unit)
            if f.section == "VISUALIZAÇÃO": options[f.key] = value
            else: p[f.key] = value
        except (ValueError, TypeError, KeyError) as exc: raise ValueError(f"{f.label}: {exc}") from exc
    if kind in ("modal", "modal_sweep"):
        p["with_eigenvectors"] = p["with_eigenvectors"] or p["with_kappa"]
        if p["coefficient_policy"] != "FIXED_WHIRL": p.pop("whirl_frequency_rad_s")
    if kind == "critical_speeds":
        if p["method"] == "auto":
            if p["with_mode_shapes"]: raise ValueError("Formas críticas exigem método 2 ou 3 explicitamente.")
            for key in ("method", "initial_estimates", "max_iterations", "tol"): p.pop(key)
            p["return_diagnostics"] = False
        else:
            p["method"] = int(p["method"]); p["return_diagnostics"] = True
            if p["method"] == 3:
                if p["initial_estimates"] is None or len(p["initial_estimates"]) != p["ncrit"]:
                    raise ValueError("Método 3 exige uma estimativa inicial por crítica solicitada.")
            else: p.pop("initial_estimates")
    if kind in ("general_frf", "forced_response"):
        if p.pop("speed_policy") == "synchronous": p["speed"] = None
    if kind == "auxiliary_frequency_response": p["direction"] = float(p["direction"])
    if kind == "forced_response":
        a = np.asarray(p["frequency_rad_s"])
        force = loads_matrix(values["loads"], a, model)
        p.update(force_real=force.real.tolist(), force_imag=force.imag.tolist())
    if kind == "general_time_response":
        t = np.asarray(p["time_s"]); speed = p["speed"]; n = 4 * len(model.nodes)
        if len(t) < 2 or t[0] < 0: raise ValueError("Tempo: pelo menos duas amostras não negativas.")
        if len(speed) not in (1, len(t)): raise ValueError("Ω(t): informe uma constante ou uma amostra por instante.")
        if not 8 <= n <= 512 or 320 * n * len(t) + 240 * n * n > 512 * 1024 ** 2:
            raise ValueError("Orçamento de memória do contrato temporal excedido; reduza nós/amostras.")
        p["speed"] = speed[0] if len(speed) == 1 else speed
        p["force_real"] = loads_matrix(values["loads"], t, model, temporal=True).tolist()
    if kind == "runup" and p["tspan"][1] <= p["tspan"][0]: raise ValueError("Tempo final deve ser maior que o inicial.")
    if kind == "ucs":
        if p["stiffness_range_exponents"][1] <= p["stiffness_range_exponents"][0]: raise ValueError("Expoentes UCS devem ser crescentes.")
        if p["bearing_speed_range"] is not None and p["bearing_speed_range"][1] <= p["bearing_speed_range"][0]:
            raise ValueError("Faixa de rotação do mancal deve ser crescente.")
    if kind == "level1":
        if p["cross_coupling_node"] not in {n.number for n in model.nodes}: raise ValueError("Nó de acoplamento não existe no modelo.")
        if p["stiffness_range_n_m"][1] <= p["stiffness_range_n_m"][0]: raise ValueError("Faixa de Q deve ser crescente.")
    if kind == "clearance":
        if p["minimum_allowable_speed_rad_s"] > p["maximum_continuous_speed_rad_s"]:
            raise ValueError("Esperado 0 ≤ Nma ≤ Nmc e Nmc > 0.")
        if len(p["speed_range_rad_s"]) < 2 or min(p["speed_range_rad_s"]) < 0:
            raise ValueError("Varredura de folgas exige ao menos duas velocidades não negativas.")
        for keys in (("probe_nodes", "probe_angles_rad", "probe_tags"),
                     ("clearance_nodes", "radial_clearance_m", "clearance_tags")):
            if len({len(p[k]) for k in keys}) != 1: raise ValueError("Quantidades devem coincidir: " + ", ".join(keys))
        if min(p["radial_clearance_m"]) <= 0: raise ValueError("Folgas radiais devem ser positivas.")
        explicit = p.pop("explicit_unbalance")
        keys = ("unbalance_nodes", "unbalance_magnitude_kg_m", "unbalance_phase_rad")
        if explicit:
            if len({len(p[k]) for k in keys}) != 1: raise ValueError("Nós, magnitudes e fases devem ter a mesma quantidade.")
            if min(p["unbalance_magnitude_kg_m"]) < 0: raise ValueError("Magnitude de desbalanceamento não pode ser negativa.")
        else:
            for key in keys: p.pop(key, None)
    if kind in ("api617_unbalance", "clearance"):
        p["mode"] -= 1
        if p["num_modes"] % 2: raise ValueError("Número de autovalores deve ser par.")
    if "output_dof" in options:
        j = options["output_dof"]; out = model.nodes[j // 4].number + (j % 4 + 1) / 10.
        options.update(outnodes=[out], outnode=out)
    known = {f.key for f in BY_KIND[kind].inputs} | {"force_real", "force_imag", "return_diagnostics"}
    for key, value in extras.items():
        if key not in known: p[key] = value
    return AnalysisCase(kind, p, str(name).strip(), options)


def values_from_case(case, model):
    values = default_values(case.kind, model)
    p = case.parameters
    for f in BY_KIND[case.kind].inputs:
        source = case.options if f.section == "VISUALIZAÇÃO" else p
        if f.key not in source: continue
        value = source[f.key]
        if value is None: values[f.key] = "" if f.optional else values[f.key]; continue
        if f.kind == "tags": values[f.key] = "; ".join(value); continue
        value = unit_to_display(value, f.unit)
        if f.kind == "grid": values[f.key] = dict(mode="explicit", values=format_vector(value), start=0, stop=1, count=2)
        elif f.kind in ("vector", "pair", "triple", "nodes"): values[f.key] = format_vector(np.atleast_1d(value))
        elif f.kind == "select": values[f.key] = str(value)
        else: values[f.key] = value
    if case.kind in ("api617_unbalance", "clearance"): values["mode"] = int(p["mode"]) + 1
    if case.kind == "clearance": values["explicit_unbalance"] = p.get("unbalance_nodes") is not None
    if case.kind in ("general_frf", "forced_response"): values["speed_policy"] = "synchronous" if p.get("speed") is None else "fixed"
    if case.kind == "critical_speeds": values["method"] = str(p.get("method", "auto"))
    if case.kind in ("forced_response", "general_time_response"):
        real = np.asarray(p["force_real"]); imag = np.asarray(p.get("force_imag", np.zeros_like(real)))
        entries = []
        for j in range(len(real)):
            if np.any(real[j]) or np.any(imag[j]):
                entries.append(dict(node=model.nodes[j // 4].number, dof=j % 4, shape="Samples",
                                    real=format_vector(real[j]), imag=format_vector(imag[j]), values=format_vector(real[j])))
        values["loads"] = entries or [dict(node=model.nodes[0].number, dof=0, shape="Constant", real="0", imag="0", values="0")]
    return values


def format_vector(value):
    return "; ".join(format(float(x), ".17g") for x in value)


def import_history_csv(text, model):
    expected = ["time_s", "speed_rad_s"] + [f"F{i}" for i in range(4 * len(model.nodes))]
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    if not rows or rows[0] != expected: raise ValueError("Cabeçalho SI esperado: " + ",".join(expected))
    if any(len(row) != len(expected) for row in rows[1:]): raise ValueError("Número incorreto de colunas no histórico.")
    data = numeric_array(rows[1:], ndim=2)
    if not 2 <= len(data) <= 10000 or np.any(np.diff(data[:, 0]) <= 0): raise ValueError("Tempo deve conter 2–10000 amostras crescentes.")
    case = AnalysisCase("general_time_response", dict(time_s=data[:, 0].tolist(), speed=data[:, 1].tolist(),
                        force_real=data[:, 2:].T.tolist(), gamma=.5, beta=.25, tol=1e-6, weight=False), "Histórico importado")
    return values_from_case(case, model)
