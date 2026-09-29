from pathlib import Path
import json
import numpy as np
from PySide6.QtCore import QEventLoop, QTimer

from drm_core import (
    Bearing, Disk, Node, RotorModel, RotorProject, ShaftElement
)
from .application import ProjectSession
from .main_window import MainWindow
from .analysis_pages.ucs_setup import UCSSetupDialog
from .result_views.io import (
    export_record_csv, export_record_native, export_record_report,
    export_view_plot_bundle,
)


def _qualification_model():
    z=[0.0,0.21,0.48,0.67]
    shafts=[]
    for i,(length,od) in enumerate(zip((0.21,0.27,0.19),(0.054,0.061,0.049)),1):
        shafts.append(
            ShaftElement(
                2,i,i+1,od,0.014,7810.0,211e9,81.2e9,
                2.5e-3,0.0,0.0
            )
        )
    return RotorModel(
        [Node(i+1,x) for i,x in enumerate(z)],
        shafts,
        [Disk.inertial(3,19.0,0.083,0.151)],
        [
            Bearing(3,1,(1.25e7,1.25e7,230.0,230.0)),
            Bearing(3,4,(1.25e7,1.25e7,230.0,230.0)),
        ],
    )


def run_ucs_gui_smoke(output_dir):
    """Exact GUI→service→ABI→Fortran→export→persistence A5 product gate."""
    out=Path(output_dir)/"ucs"
    out.mkdir(parents=True,exist_ok=True)
    model=_qualification_model()
    window=MainWindow(ProjectSession(RotorProject("A5 UCS qualification",model)))
    window.show()

    dialog=UCSSetupDialog(model,window)
    dialog.exp_min.setValue(6.0)
    dialog.exp_max.setValue(10.0)
    dialog.points.setValue(7)
    dialog.num_modes.setValue(16)
    dialog.synchronous.setChecked(True)
    case=dialog.analysis_case()
    dialog.deleteLater()

    def execute(w,c):
        loop=QEventLoop()
        records=[]
        errors=[]
        def done(record):
            records.append(record);loop.quit()
        def fail(error):
            errors.append(error.message);loop.quit()
        w.session.resultAdded.connect(done)
        w.jobs.failed.connect(fail)
        timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit);timer.start(60000)
        try:
            assert w.run_analysis(c),"GUI rejected A5 UCS"
            loop.exec()
            assert records and not errors,f"A5 UCS failed/timed out: {errors}"
            return records[0]
        finally:
            timer.stop()
            w.session.resultAdded.disconnect(done)
            w.jobs.failed.disconnect(fail)

    try:
        first=execute(window,case)
        result=first.execution.result
        assert result.natural_frequency_rad_s.shape==(4,7)
        assert result.synchronous is True
        assert len(result.intersection_speed_rad_s)>0
        assert result.metadata["native_abi"]=="rd_ucs_v1"
        assert result.metadata["backend"]=="Fortran2018/ctypes"
        assert result.metadata["ross_authority"]=="6320eab9f890f1b3cc1710d508b446fe063ca68d"

        view=window._result_tabs[first.key]
        assert len(view.figure.axes)==1
        view.speed_units.setCurrentText("RPM")
        view.intersection.setCurrentIndex(min(1,view.intersection.count()-1))
        assert "kcrit=" in view.detail.text()

        csv_path=export_record_csv(first,out/"ucs_branches.csv")
        intersection_path=out/"ucs_branches_intersections.csv"
        assert csv_path.exists() and csv_path.stat().st_size>0
        assert intersection_path.exists() and intersection_path.stat().st_size>0
        branch_csv=np.genfromtxt(csv_path,delimiter=",",names=True)
        assert branch_csv.size==4*7
        assert set(branch_csv.dtype.names)=={
            "branch_index","stiffness_N_per_m","natural_frequency_rad_s",
            "natural_frequency_rpm","synchronous_rouch"
        }
        text=intersection_path.read_text()
        assert "coefficient" in text and "stiffness_N_per_m" in text

        native=export_record_native(first,out/"ucs.npz")
        with np.load(native) as saved:
            for key,value in vars(result).items():
                if isinstance(value,np.ndarray):
                    np.testing.assert_array_equal(saved[key],value)
            assert saved["analysis_hash"].item()==first.execution.analysis_hash
            assert saved["bearing_speed_policy"].item()==result.bearing_speed_policy

        reports=export_record_report(first,out/"report")
        report_json=json.loads(reports["json"].read_text())
        assert report_json["status"]=="COMPLETED"
        assert report_json["case"]["kind"]=="ucs"
        assert report_json["result"]["metadata"]["ross_authority"]=="6320eab9f890f1b3cc1710d508b446fe063ca68d"
        assert report_json["result"]["synchronous"] is True

        plots=export_view_plot_bundle(view,out/"ucs_map")
        for path in plots.values():
            assert path.exists() and path.stat().st_size>0

        window.grab().save(str(out/"ucs_gui.png"))
        saved_project=out/"ucs.rds"
        window.save_project(saved_project)
        window.close()

        window=MainWindow()
        window.session.open_project(saved_project)
        window.show()
        assert len(window.session.project.analyses)==1
        reopened_case=window.session.project.analyses[0]
        assert reopened_case.kind=="ucs"
        second=execute(window,reopened_case)
        result2=second.execution.result
        for key,value in vars(result).items():
            if isinstance(value,np.ndarray):
                np.testing.assert_array_equal(value,getattr(result2,key))
        assert first.execution.analysis_hash==second.execution.analysis_hash

        window.session.project.model.disks.append(Disk.inertial(2,1.0,0.0,0.0))
        window.session.notify_model_changed()
        assert second.stale
        window.session.project.model.disks.pop()
        window.session.notify_model_changed()
        assert not second.stale
        window.save_project()

        return {
            "status":"PASS",
            "native_abi":"rd_ucs_v1",
            "solver":"Fortran 2018 UCS + LAPACK",
            "ross_authority":"6320eab9f890f1b3cc1710d508b446fe063ca68d",
            "path":"GUI input -> UCS AnalysisCase -> GUI worker -> AnalysisService -> native ABI -> Fortran -> result -> plot",
            "synchronous_rouch":True,
            "temporary_system":"undamped / isotropic sweep supports / seals excluded",
            "intersections":int(len(result.intersection_speed_rad_s)),
            "persistence":"save-close-reopen-recompute exact arrays and analysis hash",
            "staleness":"PASS",
            "exports":"long-form branch CSV + separate intersections CSV + complete NPZ + report + PNG/SVG/PDF",
        }
    finally:
        window.session._set_dirty(False)
        window.close()
