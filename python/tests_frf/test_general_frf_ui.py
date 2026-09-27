def test_real_general_frf_gui(qapp,tmp_path):
    from drm_studio.general_frf_qualification import run_general_frf_gui_smoke
    assert run_general_frf_gui_smoke(tmp_path)['status']=='PASS'
