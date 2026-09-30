"""Presentation of native A8 arrays; no clearance/response calculation here."""
from __future__ import annotations
import numpy as np
from drm_core.analysis.clearance import ClearanceResult
from drm_core.units import rad_s_to_rpm
from .plotting import base_figure

CLEARANCE_TABS = [('clearance', 'Resposta / folga'), ('probes', 'Sondas radiais'),
                  ('summary', 'Resumo das folgas'), ('unbalance', 'Desbalanceamento aplicado')]


def present_clearance(result: ClearanceResult, selection: dict, dark: bool = False):
    from .result_presenter import Presented
    r = result
    view = selection.get('view', 'clearance')
    index = max(0, min(int(selection.get('selected_clearance_index', 0)), len(r.clearance_nodes)-1))
    probe = max(0, min(int(selection.get('probe_index', 0)), len(r.probe_nodes)-1))
    rpm = np.asarray(rad_s_to_rpm(r.speed_range_rad_s))
    fig, ax = base_figure(dark)
    limit = np.asarray(r.clearance_limit_m) * 1e6
    if view == 'clearance':
        response = np.asarray(r.clearance_response_m_pp[index]) * 1e6
        ax.plot(rpm, response, label=r.clearance_tags[index] + ' · escalada')
        ax.axhline(limit[index], linestyle='--', label='75% da folga diametral')
        ax.scatter([rad_s_to_rpm(r.speed_at_max_response_rad_s[index])],
                   [r.max_clearance_response_m_pp[index]*1e6], marker='x', s=70, label='Máximo nativo')
        headers = ['Rotação [rpm]', 'Resposta escalada [µm p-p]', 'Limite [µm p-p]']
        rows = [[float(x), float(y), float(limit[index])] for x,y in zip(rpm,response)]
    elif view == 'probes':
        response = np.asarray(r.probe_response_m_pp[probe]) * 1e6
        ax.plot(rpm, response, label=r.probe_tags[probe] + ' · não escalada')
        ax.axhline(r.vibration_limit_m_pp*1e6, linestyle='--', label='Avl')
        headers = ['Rotação [rpm]', 'Sonda não escalada [µm p-p]']
        rows = [[float(x), float(y)] for x,y in zip(rpm,response)]
    elif view == 'summary':
        x = np.arange(len(r.clearance_nodes))
        ax.bar(x, r.percent_of_limit, label='Resposta máxima / limite')
        ax.axhline(100., linestyle='--', label='Limite estrito')
        ax.set_xticks(x, r.clearance_tags); ax.set_ylabel('Utilização do limite [%]')
        headers = ['Local', 'Nó', 'Radial [µm]', 'Diametral [µm]', 'Limite [µm p-p]',
                   'Máximo [µm p-p]', 'Rotação no máximo [rpm]', 'Status nativo']
        rows = [[tag,int(node),float(d*.5e6),float(d*1e6),float(l),float(y*1e6),float(rad_s_to_rpm(w)),
                 'PASS' if bool(passed) else 'EXCEDIDO']
                for tag,node,d,l,y,w,passed in zip(r.clearance_tags,r.clearance_nodes,r.diametral_clearance_m,
                    limit,r.max_clearance_response_m_pp,r.speed_at_max_response_rad_s,r.passed)]
    else:
        ax.bar(r.unbalance_nodes, r.unbalance_magnitude_kg_m)
        ax.set_xlabel('Nó'); ax.set_ylabel('Desbalanceamento [kg·m]')
        headers = ['Nó', 'Magnitude [kg·m]', 'Fase [deg]']
        rows = [[int(n),float(u),float(np.rad2deg(p))] for n,u,p in
                zip(r.unbalance_nodes,r.unbalance_magnitude_kg_m,r.unbalance_phase_rad)]
    if view in ('clearance','probes'):
        ax.axvspan(rad_s_to_rpm(r.minimum_allowable_speed_rad_s),rad_s_to_rpm(r.maximum_continuous_speed_rad_s),
                   alpha=.08,label='Nma–Nmc')
        ax.set_xlabel('Rotação [rpm]');ax.set_ylabel('Amplitude [µm pico a pico]')
    if ax.get_legend_handles_labels()[0]: ax.legend(fontsize=8)
    ax.set_title(dict(CLEARANCE_TABS)[view], fontsize=12)
    fig.subplots_adjust(left=.13,right=.95,bottom=.18,top=.89)
    cap = 'sem limite' if r.scale_factor_cap is None else f'{r.scale_factor_cap:.7g}'
    status = 'PASS' if np.all(r.passed) else 'EXCEDIDO'
    note = (f'A8 · {status}. Avl={r.vibration_limit_m_pp*1e6:.7g} µm p-p; '
            f'Amax em Nma–Nmc={r.max_probe_amplitude_m_pp*1e6:.7g} µm p-p; '
            f'Scc={r.scale_factor:.7g}; cap={cap}. Limite estrito: resposta < 75% da folga diametral; '
            'igualdade reprova. Sondas não escaladas, folgas escaladas. Não é certificação normativa integral.')
    return Presented(fig,headers,rows,note)
