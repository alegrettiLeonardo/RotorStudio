from __future__ import annotations

from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QApplication, QStyle

try:
    import qtawesome as qta
except ImportError:  # Core/headless installs remain QtAwesome-independent.
    qta = None


_ICON_NAMES = {
    "new": "fa6s.file",
    "open": "fa6s.folder-open",
    "save": "fa6s.floppy-disk",
    "model": "fa6s.gears",
    "analysis": "fa6s.play",
    "results": "fa6s.chart-column",
    "repeat": "fa6s.rotate-right",
    "report": "fa6s.file-lines",
    "zoom_in": "fa6s.magnifying-glass-plus",
    "zoom_out": "fa6s.magnifying-glass-minus",
    "fit": "fa6s.expand",
    "pan": "fa6s.hand",
    "help": "fa6s.circle-question",
    "modal": "fa6s.wave-square",
    "campbell": "fa6s.chart-line",
    "critical": "fa6s.gauge-high",
    "synchronous": "fa6s.arrows-rotate",
    "frequency": "fa6s.signal",
    "foundation": "fa6s.building-columns",
    "runup": "fa6s.arrow-trend-up",
    "coaxial": "fa6s.bullseye",
    "asymmetric": "fa6s.circle-half-stroke",
    "bearing": "fa6s.gear",
    "seal": "fa6s.droplet",
    "cancel": "fa6s.circle-stop",
    "export": "fa6s.file-export",
    "delete": "fa6s.trash",
}


_FALLBACKS = {
    "new": QStyle.SP_FileIcon,
    "open": QStyle.SP_DialogOpenButton,
    "save": QStyle.SP_DialogSaveButton,
    "analysis": QStyle.SP_MediaPlay,
    "help": QStyle.SP_DialogHelpButton,
    "cancel": QStyle.SP_BrowserStop,
    "zoom_in": QStyle.SP_ArrowUp,
    "zoom_out": QStyle.SP_ArrowDown,
}


def studio_icon(name: str, color: str = "#1261a6") -> QIcon:
    """Return a consistent RotorStudio icon with a safe Qt fallback."""
    if qta is not None:
        icon_name = _ICON_NAMES.get(name)
        if icon_name:
            try:
                return qta.icon(icon_name, color=QColor(color))
            except Exception:
                pass
    app = QApplication.instance()
    if app is None:
        return QIcon()
    enum = _FALLBACKS.get(name, QStyle.SP_FileIcon)
    return app.style().standardIcon(enum)
