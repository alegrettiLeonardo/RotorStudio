from pathlib import Path
import numpy as np
from PySide6.QtCore import QEventLoop,QTimer
from drm_core import RotorModel,RotorProject,Node,ShaftElement,Disk,CoefficientBearing
from .application import ProjectSession
from .main_window import MainWindow
from .analysis_pages.general_frf_setup import GeneralFrfSetupDialog
from .result_views.io import export_record_csv,export_record_native,export_record_report,export_view_plot_bundle

def run_general_frf_gui_smoke(output_dir):
    out=Path(output_dir)/'general_frf';out.mkdir(parents=True,exist_ok=True)
    model=RotorModel([Node(i+1,i*.25) for i in range(4)],
        [ShaftElement(2,i+1,i+2,.05,.01,7810.,211e9,81.2e9) for i in range(3)],
        [Disk.inertial(2,7.,.02,.04)],advanced_bearings=[CoefficientBearing(n,kxx=((1e6,1.3e6),(1.7e6,2.1e6)),kyy=1.6e6,cxx=170.,cyy=230.,kxy=13000.,kyx=-27000.,speed_rad_s=(0.,300.),frequency_rad_s=(0.,600.)) for n in (1,4)])
    w=MainWindow(ProjectSession(RotorProject('General FRF qualification',model)));w.show()
    dialog=GeneralFrfSetupDialog(model,w);dialog.policy.setCurrentIndex(1);dialog.speed.setValue(183.);dialog.start.setValue(43.);dialog.stop.setValue(503.);dialog.points.setValue(7);dialog.input_dof.setCurrentIndex(4);dialog.output_dof.setCurrentIndex(5)
    case=dialog.analysis_case();dialog.deleteLater()
    def execute(window,c):
        loop=QEventLoop();records=[];errors=[]
        def done(r):records.append(r);loop.quit()
        def fail(e):errors.append(e.message);loop.quit()
        window.session.resultAdded.connect(done);window.jobs.failed.connect(fail)
        timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit);timer.start(30000)
        try:
            assert window.run_analysis(c),'GUI rejected General FRF'
            loop.exec()
            assert records and not errors,f'General FRF failed/timed out: {errors}'
            return records[0]
        finally:
            timer.stop();window.session.resultAdded.disconnect(done);window.jobs.failed.disconnect(fail)
    try:
        first=execute(w,case);r=first.execution.result
        assert r.H_disp.shape==(16,16,7) and max(r.residual)<1e-12
        view=w._result_tabs[first.key];assert len(view.figure.axes)==3
        for kind in ['displacement','velocity','acceleration']:
            view.response.setCurrentText(kind);export_record_csv(first,out/f'{kind}.csv')
        export_record_native(first,out/'frf.npz');export_record_report(first,out/'report');export_view_plot_bundle(view,out/'frf')
        with np.load(out/'frf.npz') as saved:np.testing.assert_array_equal(saved['H_disp'],r.H_disp)
        w.grab().save(str(out/'frf_gui.png'));w.save_project(out/'frf.rds');w.close()
        w=MainWindow();w.session.open_project(out/'frf.rds');w.show();second=execute(w,w.session.project.analyses[0])
        for key in ['H_disp','H_vel','H_acc']:np.testing.assert_array_equal(getattr(r,key),getattr(second.execution.result,key))
        assert first.execution.analysis_hash==second.execution.analysis_hash
        w.session.project.model.disks.append(Disk.inertial(3,1.,0.,0.));w.session.notify_model_changed();assert second.stale
        w.session.project.model.disks.pop();w.session.notify_model_changed();assert not second.stale
        w.save_project()
        return dict(status='PASS',native_abi='rd_frf_general_v1',policy='fixed',bearing_axes='independent 2-D native interpolation',persistence='save-close-reopen-recompute exact',staleness='PASS',exports='complex NPZ/selected CSV/report/Bode/polar PNG SVG PDF',max_residual=float(max(r.residual)))
    finally:
        w.session._set_dirty(False);w.close()
