"""Source and frozen qualification through the real GUI job/persistence path."""
from pathlib import Path
import numpy as np
from PySide6.QtCore import QEventLoop,QTimer
from drm_core import RotorModel,RotorProject,Node,ShaftElement,Disk,Bearing
from .application import ProjectSession
from .main_window import MainWindow
from .analysis_pages.static_setup import StaticSetupDialog
from .result_views.io import export_record_csv,export_record_native,export_record_report,export_view_plot_bundle

def run_static_gui_smoke(output_dir):
    out=Path(output_dir)/'static';out.mkdir(parents=True,exist_ok=True)
    model=RotorModel([Node(i+1,i*.25) for i in range(5)],
        [ShaftElement(2,i+1,i+2,.05,.01,7810.,211e9,81.2e9) for i in range(4)],
        [Disk.inertial(3,8.,.03,.06)],[Bearing(1,1),Bearing(1,5)])
    window=MainWindow(ProjectSession(RotorProject('Static qualification',model)))
    window.show()
    dialog=StaticSetupDialog(window);case=dialog.analysis_case();dialog.deleteLater()
    def execute(w,c):
        loop=QEventLoop();records=[];failures=[]
        def done(record):records.append(record);loop.quit()
        def failed(failure):failures.append(failure.message);loop.quit()
        w.session.resultAdded.connect(done);w.jobs.failed.connect(failed)
        timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit);timer.start(30000)
        try:
            if not w.run_analysis(c):raise AssertionError('Static GUI input rejected')
            loop.exec()
            if failures or not records:raise AssertionError(f'Static GUI failed/timed out: {failures}')
            return records[0]
        finally:
            timer.stop();w.session.resultAdded.disconnect(done);w.jobs.failed.disconnect(failed)
    try:
        first=execute(window,case);r=first.execution.result
        assert max(abs(r.diagnostics[:2]))<1e-8 and r.diagnostics[2]<1e-14
        view=window._result_tabs[first.key]
        assert view.table.rowCount()>0 and len(view.figure.axes)==4
        export_record_csv(first,out/'static.csv');export_record_native(first,out/'static.npz')
        export_record_report(first,out/'report');export_view_plot_bundle(view,out/'static')
        window.grab().save(str(out/'static_gui.png'))
        window.save_project(out/'static.rds');window.close()
        window=MainWindow();window.session.open_project(out/'static.rds');window.show()
        second=execute(window,window.session.project.analyses[0])
        for key,value in vars(r).items():
            if isinstance(value,np.ndarray):np.testing.assert_array_equal(value,getattr(second.execution.result,key))
        assert first.execution.analysis_hash==second.execution.analysis_hash
        window.session.project.model.disks.append(Disk.inertial(2,1.,0.,0.))
        window.session.notify_model_changed();assert second.stale
        window.session.project.model.disks.pop();window.session.notify_model_changed();assert not second.stale
        window.save_project()
        return {'status':'PASS','native_abi':'rd_static_v1','persistence':'save-close-reopen-recompute exact','staleness':'PASS','exports':'CSV/NPZ/report/PNG/SVG/PDF','diagnostics':r.diagnostics.tolist()}
    finally:
        window.session._set_dirty(False);window.close()
