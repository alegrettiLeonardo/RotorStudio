from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="drm-studio", description="Rotor Dynamics Studio desktop UI")
    p.add_argument("project", nargs="?", help="RotorStudio .rds/.json project")
    p.add_argument("--qualification-smoke", metavar="OUTDIR", help=argparse.SUPPRESS)
    p.add_argument("--qualification-project", metavar="PROJECT", help=argparse.SUPPRESS)
    return p


def _configure_frozen_solver():
    if not getattr(sys, "frozen", False):
        return
    root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    libraries = {
        "DRMROTOR_LIB": (
            "libdrmrotor.so", "drmrotor.dll", "libdrmrotor.dll", "libdrmrotor.dylib"
        ),
        "DRMBEARINGS_LIB": (
            "libdrmbearings.so", "drmbearings.dll", "libdrmbearings.dll", "libdrmbearings.dylib"
        ),
    }
    for variable, names in libraries.items():
        for name in names:
            candidate = root / name
            if candidate.is_file():
                os.environ.setdefault(variable, str(candidate))
                break
    os.environ.setdefault("DRMROTOR_DLL_DIRS", str(root))
    if os.environ.get("DRMBEARINGS_LIB"):
        os.environ.setdefault("DRMBEARINGS_DLL_DIRS", str(root))


def _bundled_smoke_project():
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    return root / "examples" / "Stage2_Smoke.rds"


def main(argv=None) -> int:
    if sys.version_info < (3, 12):
        raise RuntimeError("Rotor Dynamics Studio requires Python 3.12 or newer")
    args = build_parser().parse_args(argv)
    _configure_frozen_solver()
    QCoreApplication.setOrganizationName("RotorStudio")
    QCoreApplication.setApplicationName("Rotor Dynamics Studio")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    win = MainWindow()
    if args.qualification_smoke:
        app.setQuitOnLastWindowClosed(False)
        from .qualification import PackagedQualification
        project = Path(args.qualification_project) if args.qualification_project else _bundled_smoke_project()
        runner = PackagedQualification(app, win, args.qualification_smoke, project)
        win._qualification_runner = runner
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, runner.start)
        return app.exec()
    if args.project:
        win.open_project(args.project)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
