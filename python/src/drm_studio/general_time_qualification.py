from pathlib import Path
import numpy as np
from PySide6.QtCore import QEventLoop,QTimer
from drm_core import RotorModel,RotorProject,Node,ShaftElement,Disk,CoefficientBearing
from .application import ProjectSession
from .main_window import MainWindow
from .analysis_pages.general_time_setup import GeneralTimeSetupDialog
from .result_views.io import export_record_csv,export_record_native,export_record_report,export_view_plot_bundle,record_data_table

def run_general_time_gui_smoke(output_dir):
    out=Path(output_dir)/'general_time_response';out.mkdir(parents=True,exist_ok=True)
    model=RotorModel([Node(i+1,i*.25) for i in range(4)],
        [ShaftElement(2,i+1,i+2,.05,.01,7810.,211e9,81.2e9) for i in range(3)],
        [Disk.inertial(2,7.,.02,.04)],advanced_bearings=[CoefficientBearing(n,kxx=((1e6,1.3e6),(1.7e6,2.1e6)),kyy=1.6e6,cxx=170.,cyy=230.,kxy=13000.,kyx=-27000.,speed_rad_s=(0.,600.),frequency_rad_s=(0.,600.)) for n in (1,4)])
    w=MainWindow(ProjectSession(RotorProject('General Time qualification',model)));w.show()
    dialog=GeneralTimeSetupDialog(model,w);dialog.stop.setValue(.04);dialog.points.setValue(81);dialog.output_dof.setCurrentIndex(6)
    dialog.speed_values.setText(','.join(map(str,np.linspace(83,583,81))));dialog.weight.setChecked(True);dialog.forces.setRowCount(0)
    dialog.add_force(2,0,'Sine','137,317,0');dialog.add_force(3,1,'Pulse','89,.004,.009');dialog.add_force(2,2,'Constant','17');dialog.add_force(4,3,'Samples',','.join(map(str,np.linspace(-11,7,81))))
    case=dialog.analysis_case();dialog.deleteLater()
    def execute(window,c):
        loop=QEventLoop();records=[];errors=[]
        def done(r):records.append(r);loop.quit()
        def fail(e):errors.append(e.message);loop.quit()
        window.session.resultAdded.connect(done);window.jobs.failed.connect(fail)
        timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit);timer.start(30000)
        try:
            assert window.run_analysis(c),'GUI rejected General Time Response'
            loop.exec();assert records and not errors,f'General Time failed/timed out: {errors}'
            return records[0]
        finally:timer.stop();window.session.resultAdded.disconnect(done);window.jobs.failed.disconnect(fail)
    try:
        first=execute(w,case);r=first.execution.result
        assert r.displacement.shape==(16,81) and max(r.absolute_residual[1:])<1e-6
        np.testing.assert_array_equal(r.force_external,np.asarray(case.parameters['force_real']))
        assert np.max(abs(r.angular_acceleration_rad_s2))>1 and np.any(r.force!=r.force_external)
        view=w._result_tabs[first.key];assert len(view.figure.axes)==7
        for dof in (5,6):
            view.output_dof.setCurrentIndex(dof)
            for kind in ('displacement','velocity','acceleration'):
                view.response.setCurrentText(kind);path=out/f'{kind}_{dof}.csv';export_record_csv(first,path)
                header,data=record_data_table(first);np.testing.assert_array_equal(data[:,5],r.displacement[dof])
                loaded=np.genfromtxt(path,delimiter=',',names=True)
                for col in (4,5,6,7,8,9,10):np.testing.assert_allclose(loaded[header[col]],data[:,col],rtol=1e-14,atol=0)
                assert ('Nm' if dof%4>=2 else '_N') in header[4]
        export_record_native(first,out/'time.npz');export_record_report(first,out/'report');export_view_plot_bundle(view,out/'time')
        with np.load(out/'time.npz') as saved:
            for key,value in vars(r).items():
                if isinstance(value,np.ndarray):np.testing.assert_array_equal(saved[key],value)
        w.grab().save(str(out/'time_gui.png'));w.save_project(out/'time.rds');w.close()
        w=MainWindow();w.session.open_project(out/'time.rds');w.show();second=execute(w,w.session.project.analyses[0])
        for key,value in vars(r).items():
            if isinstance(value,np.ndarray):np.testing.assert_array_equal(value,getattr(second.execution.result,key))
        assert first.execution.analysis_hash==second.execution.analysis_hash
        w.session.project.model.disks.append(Disk.inertial(3,1.,0.,0.));w.session.notify_model_changed();assert second.stale
        w.session.project.model.disks.pop();w.session.notify_model_changed();assert not second.stale
        w.save_project()
        return dict(status='PASS',native_abi='rd_general_time_response_v1',solver='Fortran simple Newmark',path='GUI input -> general_time_response AnalysisCase -> GUI worker -> AnalysisService -> native ABI -> Fortran -> result -> plots',speed='variable; native gradient and alpha*Ksdt',bearing_axes='2-D diagonal Omega/Omega; constant mass',persistence='save-close-reopen-recompute all arrays and analysis hash exact',staleness='PASS',exports='full arrays NPZ; selected SI CSV; report/plots PNG SVG PDF',max_absolute_residual=float(max(r.absolute_residual[1:])),max_scaled_residual=float(max(r.residual[1:])))
    finally:w.session._set_dirty(False);w.close()
