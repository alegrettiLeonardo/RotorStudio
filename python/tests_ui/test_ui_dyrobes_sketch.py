from pathlib import Path

from PySide6.QtGui import QColor, QImage

from drm_studio.application.session import ProjectSession
from drm_studio.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples" / "legacy" / "EST-12735185-CRYOSTAR_V2.txt"


def _tag_counts(view):
    counts = {}
    for item in view.scene_obj.items():
        tag = item.data(1)
        if tag:
            counts[str(tag)] = counts.get(str(tag), 0) + 1
    return counts


def test_real_cryostar_opens_as_dyrobes_reference_sketch_without_binding_save_path(qtbot):
    session = ProjectSession()
    window = MainWindow(session=session)
    qtbot.addWidget(window)

    window.open_project(FIXTURE)
    window.show()
    qtbot.wait(50)

    assert session.project.name == "12735185-CRYOSTAR_V2"
    assert session.path is None
    assert window.model_page.dyrobes_check.isChecked()
    assert window.model_page.view.dyrobes_style is True

    counts = _tag_counts(window.model_page.view)
    assert counts["shaft"] == 16
    assert counts["mass"] == 3
    assert counts["bearing"] == 2
    assert counts["unbalance"] == 2
    assert counts["probe"] == 2  # grouped r2/r1 and r4/r3 stations
    assert counts["station"] == 17

    checks = [window.messages_dock.checks.item(i).text() for i in range(window.messages_dock.checks.count())]
    assert any("BLOCKED_FOR_NUMERICAL_ANALYSIS" in text for text in checks)


def test_real_cryostar_reference_sketch_renders_mass_shaft_unbalance_and_probe_colors(qtbot):
    session = ProjectSession()
    window = MainWindow(session=session)
    qtbot.addWidget(window)
    window.open_project(FIXTURE)
    window.resize(1440, 900)
    window.show()
    qtbot.wait(50)
    window.model_page.view.fit_view()
    qtbot.wait(20)

    image = QImage(window.model_page.view.viewport().size(), QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    window.model_page.view.viewport().render(image)
    assert not image.isNull()

    # Antialiasing changes exact edge pixels across Qt/platform builds, so
    # validate the authoritative QGraphicsScene presentation properties rather
    # than depending on an exact raster sample of one-pixel-wide symbols.
    tagged = {}
    for item in window.model_page.view.scene_obj.items():
        tag = item.data(1)
        if tag and str(tag) not in tagged:
            tagged[str(tag)] = item

    assert tagged["mass"].brush().color().name().lower() == "#19c9d2"
    assert tagged["unbalance"].pen().color().name().lower() == "#e13d43"
    assert tagged["probe"].pen().color().name().lower() == "#2f9e44"


def test_imported_cryostar_analysis_button_is_blocked_before_job_submission(qtbot):
    session = ProjectSession()
    window = MainWindow(session=session)
    qtbot.addWidget(window)
    window.open_project(FIXTURE)

    submitted = []
    window.jobs.submit = lambda *args, **kwargs: submitted.append((args, kwargs))

    from drm_core import AnalysisCase

    accepted = window.run_analysis(
        AnalysisCase("modal", {"speed_rad_s": 0.0}, "Imported sketch modal")
    )
    assert accepted is False
    assert submitted == []
