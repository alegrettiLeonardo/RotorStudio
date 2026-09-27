from pathlib import Path
import numpy as np
from PySide6.QtCore import QEventLoop,QTimer
from drm_core import RotorModel,RotorProject,Node,ShaftElement,Disk,CoefficientBearing
from .application import ProjectSession
from .main_window import MainWindow
from .analysis_pages.forced_response_setup import ForcedResponseSetupDialog
from .result_views.forced_response_view import orbit_xy
from .result_views.io import export_record_csv,export_record_native,export_record_report,export_view_plot_bundle,record_data_table

def run_forced_response_gui_smoke(output_dir):
    out=Path(output_dir)/'forced_response';out.mkdir(parents=True,exist_ok=True)
    model=RotorModel([Node(i+1,i*.25) for i in range(4)],
        [ShaftElement(2,i+1,i+2,.05,.01,7810.,211e9,81.2e9) for i in range(3)],
        [Disk.inertial(2,7.,.02,.04)],advanced_bearings=[CoefficientBearing(n,kxx=((1e6,1.3e6),(1.7e6,2.1e6)),kyy=1.6e6,cxx=170.,cyy=230.,kxy=13000.,kyx=-27000.,speed_rad_s=(0.,300.),frequency_rad_s=(0.,600.)) for n in (1,4)])
    w=MainWindow(ProjectSession(RotorProject('Forced Response qualification',model)));w.show()
    dialog=ForcedResponseSetupDialog(model,w);dialog.policy.setCurrentIndex(1);dialog.speed.setValue(183.);dialog.start.setValue(43.);dialog.stop.setValue(503.);dialog.points.setValue(7);dialog.output_dof.setCurrentIndex(6)
    dialog.forces.setRowCount(0)
    dialog.add_force(2,0,'137,149,121,193,17,41,61','41,-11,29,53,71,19,-7')
    dialog.add_force(3,1,'-23','89');dialog.add_force(2,2,'17','-31');dialog.add_force(4,3,'-11','-7')
    case=dialog.analysis_case();dialog.deleteLater()
    def execute(window,c):
        loop=QEventLoop();records=[];errors=[]
        def done(r):records.append(r);loop.quit()
        def fail(e):errors.append(e.message);loop.quit()
        window.session.resultAdded.connect(done);window.jobs.failed.connect(fail)
        timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit);timer.start(30000)
        try:
            assert window.run_analysis(c),'GUI rejected Forced Response'
            loop.exec();assert records and not errors,f'Forced Response failed/timed out: {errors}'
            return records[0]
        finally:timer.stop();window.session.resultAdded.disconnect(done);window.jobs.failed.disconnect(fail)
    try:
        first=execute(w,case);r=first.execution.result
        assert r.displacement.shape==(16,7) and max(r.residual)<1e-12
        assert not hasattr(r,'H_disp') and np.linalg.matrix_rank(r.force_complex)>1
        np.testing.assert_array_equal(r.force_complex.real,np.asarray(case.parameters['force_real']))
        np.testing.assert_array_equal(r.force_complex.imag,np.asarray(case.parameters['force_imag']))
        view=w._result_tabs[first.key];assert len(view.figure.axes)==4
        for dof in (5,6):
            view.output_dof.setCurrentIndex(dof)
            for kind in ['displacement','velocity','acceleration']:
                view.response.setCurrentText(kind);path=out/f'{kind}_{dof}.csv';export_record_csv(first,path)
                header,data=record_data_table(first);np.testing.assert_allclose(data[:,5],abs(getattr(r,kind)[dof]),rtol=0,atol=0)
                assert ('Nm' if dof%4>=2 else '_N') in header[3]
                loaded=np.genfromtxt(path,delimiter=',',names=True);np.testing.assert_allclose(loaded[header[5]],data[:,5],rtol=1e-14)
        export_record_native(first,out/'forced.npz');export_record_report(first,out/'report');export_view_plot_bundle(view,out/'forced')
        with np.load(out/'forced.npz') as saved:
            for key,value in [('F',r.force_complex),('q',r.displacement),('v',r.velocity),('a',r.acceleration)]:np.testing.assert_array_equal(saved[key+'_real']+1j*saved[key+'_imag'],value)
        xy=orbit_xy(r,1,2,[0.,np.pi/2]);np.testing.assert_allclose(xy[:,0],r.displacement[4:6,2].real,rtol=0,atol=0);np.testing.assert_allclose(xy[:,1],-r.displacement[4:6,2].imag,atol=1e-18)
        w.grab().save(str(out/'forced_gui.png'));w.save_project(out/'forced.rds');w.close()
        w=MainWindow();w.session.open_project(out/'forced.rds');w.show();second=execute(w,w.session.project.analyses[0])
        for key in ['force_complex','displacement','velocity','acceleration','residual','condition_estimate']:np.testing.assert_array_equal(getattr(r,key),getattr(second.execution.result,key))
        assert first.execution.analysis_hash==second.execution.analysis_hash
        w.session.project.model.disks.append(Disk.inertial(3,1.,0.,0.));w.session.notify_model_changed();assert second.stale
        w.session.project.model.disks.pop();w.session.notify_model_changed();assert not second.stale
        w.save_project()
        return dict(status='PASS',native_abi='rd_forced_response_v1',solver='direct Dq=F in Fortran; no H materialized',force='arbitrary complex spectrum; force and moment; nonproportional frequency samples',policy='fixed',bearing_axes='independent 2-D native interpolation',persistence='save-close-reopen-recompute exact',staleness='PASS',exports='F/q/v/a real-imag NPZ; selected unit-labelled CSV; report/Bode/polar/orbit PNG SVG PDF',max_residual=float(max(r.residual)),max_condition_estimate=float(max(r.condition_estimate)))
    finally:w.session._set_dirty(False);w.close()
