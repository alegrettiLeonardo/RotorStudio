from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="drm-studio", description="Rotor Dynamics Studio desktop UI")
    p.add_argument("project", nargs="?", help="RotorStudio .rds/.json project")
    return p


def main(argv=None) -> int:
    if sys.version_info < (3, 12):
        raise RuntimeError("Rotor Dynamics Studio requires Python 3.12 or newer")
    args = build_parser().parse_args(argv)
    QCoreApplication.setOrganizationName("RotorStudio")
    QCoreApplication.setApplicationName("Rotor Dynamics Studio")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    win = MainWindow()
    if args.project:
        win.open_project(args.project)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
