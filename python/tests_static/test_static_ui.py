def test_real_gui_persistence_exports(qapp,tmp_path):
    from drm_studio.static_qualification import run_static_gui_smoke
    assert run_static_gui_smoke(tmp_path)['status']=='PASS'
