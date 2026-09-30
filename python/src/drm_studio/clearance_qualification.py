from pathlib import Path
import json
import numpy as np
from PySide6.QtCore import QEventLoop,QTimer

from drm_core import Bearing,Disk,Node,RotorModel,RotorProject,ShaftElement
from .application import ProjectSession
from .main_window import MainWindow
from .analysis_pages.clearance_setup import ClearanceSetupDialog
from .result_views.io import (
    export_record_csv,export_record_native,export_record_report,export_view_plot_bundle
)


def _model():
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i+1,i+2,.05,0.,7810.,211e9,81.2e9) for i in range(6)]
    disks=[Disk.geometric(3,7810.,.07,.28,.05),Disk.geometric(5,7810.,.07,.28,.05)]
    props=(1e6,0.,0.,.8e6,1e3,0.,0.,1e3)
    return RotorModel(nodes,shafts,disks,[Bearing(5,1,props),Bearing(5,7,props)])


def run_clearance_gui_smoke(output_dir):
    out=Path(output_dir)/"clearance";out.mkdir(parents=True,exist_ok=True)
    model=_model()
    window=MainWindow(ProjectSession(RotorProject("A8 clearance qualification",model)))
    window.show()
    dialog=ClearanceSetupDialog(model,window)
    dialog.speed_start.setValue(0.0);dialog.speed_stop.setValue(1047.197551)
    dialog.speed_points.setValue(101);dialog.nma.setValue(733.038286);dialog.nmc.setValue(942.477796)
    dialog.probe_nodes.setText("1,7");dialog.probe_angles.setText("45,-45");dialog.probe_tags.setText("DE-45,NDE-45")
    dialog.clear_nodes.setText("1,4,7");dialog.clear_radial_um.setText("100,250,120");dialog.clear_tags.setText("DE,eye,NDE")
    dialog.mode.setValue(1);dialog.num_modes.setValue(12)
    case=dialog.analysis_case();dialog.deleteLater()

    def execute(w,c):
        loop=QEventLoop();records=[];errors=[]
        def done(record):records.append(record);loop.quit()
        def fail(error):errors.append(error.message);loop.quit()
        w.session.resultAdded.connect(done);w.jobs.failed.connect(fail)
        timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit);timer.start(90000)
        try:
            assert w.run_analysis(c),"GUI rejected A8 clearance"
            loop.exec();assert records and not errors,f"A8 failed/timed out: {errors}"
            return records[0]
        finally:
            timer.stop();w.session.resultAdded.disconnect(done);w.jobs.failed.disconnect(fail)

    try:
        first=execute(window,case);r=first.execution.result
        assert r.metadata["native_abi"]=="rd_clearance_v1"
        assert r.metadata["ross_authority"]=="6320eab9f890f1b3cc1710d508b446fe063ca68d"
        assert list(r.clearance_nodes)==[1,4,7] and r.clearance_response_m_pp.shape[0]==3
        assert np.isfinite(r.scale_factor) and r.scale_factor>0
        view=window._result_tabs[first.key];assert len(view.figure.axes)==1
        view.location.setCurrentIndex(1);assert "75% limit" in view.detail.text()

        csv_path=export_record_csv(first,out/"clearance.csv")
        data=np.genfromtxt(csv_path,delimiter=",",names=True)
        assert np.atleast_1d(data).size==3 and "max_scaled_response_m_pp" in data.dtype.names
        response_path=out/"clearance_response.csv"
        assert response_path.exists() and response_path.stat().st_size>0

        native=export_record_native(first,out/"clearance.npz")
        with np.load(native) as saved:
            for key,value in vars(r).items():
                if isinstance(value,np.ndarray):np.testing.assert_array_equal(saved[key],value)
            assert saved["analysis_hash"].item()==first.execution.analysis_hash

        report=export_record_report(first,out/"report")
        payload=json.loads(report["json"].read_text())
        assert payload["case"]["kind"]=="clearance" and payload["status"]=="COMPLETED"
        plots=export_view_plot_bundle(view,out/"clearance_plot")
        for path in plots.values():assert path.exists() and path.stat().st_size>0
        window.grab().save(str(out/"clearance_gui.png"))

        project=out/"clearance.rds";window.save_project(project);window.close()
        window=MainWindow();window.session.open_project(project);window.show()
        second=execute(window,window.session.project.analyses[0]);r2=second.execution.result
        for key,value in vars(r).items():
            if isinstance(value,np.ndarray):np.testing.assert_array_equal(value,getattr(r2,key))
        assert first.execution.analysis_hash==second.execution.analysis_hash
        window.session.project.model.disks.append(Disk.inertial(4,1.,0.,0.))
        window.session.notify_model_changed();assert second.stale
        window.session.project.model.disks.pop();window.session.notify_model_changed();assert not second.stale
        window.save_project()
        return {
            "status":"PASS","native_abi":"rd_clearance_v1",
            "ross_authority":"6320eab9f890f1b3cc1710d508b446fe063ca68d",
            "path":"GUI -> AnalysisCase -> worker -> AnalysisService -> native ABI -> Fortran -> ClearanceResult -> plot",
            "persistence":"save-close-reopen-recompute exact arrays/hash",
            "staleness":"PASS","exports":"CSV summary + response CSV / NPZ / report / PNG/SVG/PDF",
        }
    finally:
        window.session._set_dirty(False);window.close()
