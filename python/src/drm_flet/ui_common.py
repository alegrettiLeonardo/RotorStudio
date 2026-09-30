"""Shared Flet control vocabulary and Core adapters for the presentation layer."""
from __future__ import annotations
import asyncio
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import csv
import io
import json
import math
import os
import numpy as np
import flet as ft
from drm_core import (AnalysisCase, RotorProject, RotorModel, Node, ShaftElement, Disk,
                      Bearing, CoefficientBearing, Force, parse_coefficient_table)
from drm_core.analysis.modal import ModalResult
from drm_core.units import rpm_to_rad_s, rad_s_to_rpm, m_to_mm, mm_to_m
from .session import StudioSession, EntityRef, reference_project
from .editing import specs, form_values, from_form, from_json, entity_json, number, coefficient_csv
from .jobs import NativeJob, BearingSweep, csv_bytes, npz_bytes, report_bytes
from .plotting import (rotor_svg, campbell_figure, modal_figure, bearing_figure, generic_figure,
                       positive_modes, whirl_label, png_bytes, base_figure)
from .theme import LIGHT, DARK, make_theme

NAMES = {"nodes":"Nós", "shafts":"Elementos do eixo", "disks":"Discos", "bearings":"Mancais clássicos",
         "advanced_bearings":"Mancais K/C e avançados", "forces":"Forças", "bend":"Curvatura", "rotors":"Definições do rotor"}
ICONS = {"nodes":ft.Icons.SCATTER_PLOT_OUTLINED, "shafts":ft.Icons.LINEAR_SCALE,
         "disks":ft.Icons.ALBUM_OUTLINED, "bearings":ft.Icons.SETTINGS_INPUT_COMPONENT,
         "advanced_bearings":ft.Icons.SETTINGS_INPUT_COMPONENT, "forces":ft.Icons.ARROW_FORWARD,
         "bend":ft.Icons.WAVES, "rotors":ft.Icons.VIEW_IN_AR}
ANALYSES = [("modal","Modal"),("modal_sweep","Campbell"),("critical_speeds","Vel. críticas"),
            ("frequency_response","Síncrona"),("static","Estática")]


