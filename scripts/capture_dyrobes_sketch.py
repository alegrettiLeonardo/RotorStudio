from __future__ import annotations

import argparse
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from drm_studio.application.session import ProjectSession
from drm_studio.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "examples" / "legacy" / "EST-12735185-CRYOSTAR_V2.txt"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--outdir", default="validation/reports/dyrobes_sketch")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    QCoreApplication.setOrganizationName("RotorStudio-CI")
    QCoreApplication.setApplicationName("RotorStudio DyRoBeS Sketch Capture")
    app = QApplication.instance() or QApplication([])

    window = MainWindow(session=ProjectSession())
    window.resize(1440, 900)
    window.open_project(args.source)
    window.show()
    app.processEvents()
    window.model_page.view.fit_view()
    app.processEvents()

    full = outdir / "cryostar_rotorstudio.png"
    sketch = outdir / "cryostar_dyrobes_sketch.png"
    assert window.grab().save(str(full))
    assert window.model_page.view.viewport().grab().save(str(sketch))
    assert full.stat().st_size > 0
    assert sketch.stat().st_size > 0

    print(full)
    print(sketch)
    window.close()


if __name__ == "__main__":
    main()
