"""Design tokens transcribed from the approved RotorStudio Flet mockups."""
from dataclasses import dataclass
import flet as ft

@dataclass(frozen=True)
class Palette:
    background: str = "#EDF3FA"
    surface: str = "#FFFFFF"
    subtle: str = "#F6F9FE"
    text: str = "#24364C"
    muted: str = "#70839F"
    line: str = "#DFE7F2"
    primary: str = "#245FC4"
    selected: str = "#E4EDFC"
    cyan: str = "#C8F0F6"
    success: str = "#237A52"
    warning: str = "#AF720B"
    error: str = "#B3261E"

LIGHT = Palette()
DARK = Palette("#111A24", "#18232F", "#141E29", "#E4EDF7", "#93A8C0", "#2C3A4B",
               "#91BEFF", "#263F5B", "#274D59", "#7AD6A3", "#F1C46E", "#FFB4AB")

def make_theme(dark: bool = False) -> ft.Theme:
    p = DARK if dark else LIGHT
    return ft.Theme(color_scheme_seed=p.primary, use_material3=True,
                    visual_density=ft.VisualDensity.COMPACT,
                    font_family="Roboto",
                    color_scheme=ft.ColorScheme(primary=p.primary, surface=p.surface,
                                                on_surface=p.text, outline=p.line))
