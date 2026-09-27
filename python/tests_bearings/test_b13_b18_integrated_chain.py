from drm_studio.b13_b18_qualification import run_b15_b18_integrated_smoke


def test_b13_b18_integrated_product_chain(tmp_path):
    evidence = run_b15_b18_integrated_smoke(tmp_path)
    assert evidence["status"] == "PASS"
    assert evidence["b15"]["mapped_inline_bearing_tables"] == 2
    assert evidence["b16"]["cold_source"] == "GENERATED"
    assert evidence["b16"]["warm_source"] == "L1"
    assert evidence["b16"]["synchronous"] is True
    assert evidence["b17"]["all_converged"] is True
    assert evidence["b18"]["native_abi"] == "rd_runup_coeffmap_legacy"
    assert evidence["b18"]["scope"] == (
        "FULL_ORDER|SYNCHRONOUS_COEFFICIENT_POLICY|MAP_BASED|NO_TEHD_IN_ODE"
    )
