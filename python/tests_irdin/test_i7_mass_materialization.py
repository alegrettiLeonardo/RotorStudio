from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from drm_core import RotorModel, load_irdin_project, load_project, save_project
from drm_core.importers.irdin_mass import all_mass_slices, mass_audit
from drm_core.solver.facade import SolverFacade

ROOT=Path(__file__).resolve().parents[2]
CASE=ROOT/"validation/irdin/cases/ST41_1000_B3_60HZ_1675_63536.txt"


def _project():
    return load_irdin_project(CASE)


def test_i7_st41_materializes_all_eight_slices_at_exact_nodes():
    p=_project()
    slices=all_mass_slices(p.model.mass_spans)
    assert len(slices)==8
    assert len(p.model.disks)==8
    z={n.number:n.z_m for n in p.model.nodes}
    for piece,disk in zip(slices,p.model.disks):
        assert z[disk.node]==pytest.approx(piece.z_center_m,abs=1e-12)
        assert disk.disk_type==2
        assert disk.p3==pytest.approx(piece.mass_kg,rel=0,abs=0)
        assert disk.p4==pytest.approx(piece.diametral_inertia_kgm2,rel=0,abs=0)
        assert disk.p5==pytest.approx(piece.polar_inertia_kgm2,rel=0,abs=0)


def test_i7_mass_conservation_and_readiness_remove_only_mass_blocker():
    p=_project()
    audit=p.metadata["legacy_irdin"]["mass_audit"]
    assert audit==mass_audit(p.model.mass_spans)
    assert audit["mass_kg"]==pytest.approx(10680.0)
    assert sum(d.p3 for d in p.model.disks)==pytest.approx(10680.0)
    r=p.metadata["numerical_readiness"]
    assert r["components"]["mass_native_materialization"]=="PASS_I7_DISK_MATERIALIZATION"
    codes={x["code"] for x in r["blockers"]}
    assert "IRDIN_DISTRIBUTED_MASS_UNMAPPED" not in codes
    assert "IRDIN_FLEXIBLE_SUPPORT_UNMAPPED" in codes
    assert r["status"]=="BLOCKED_FOR_NUMERICAL_ANALYSIS"


def test_i7_materialized_disks_survive_save_reopen_exactly(tmp_path):
    p=_project(); target=tmp_path/"st41-i7.json"; save_project(p,target)
    reopened=load_project(target)
    assert reopened.model.disks==p.model.disks
    assert reopened.model.mass_spans==p.model.mass_spans
    assert reopened.model.model_hash()==p.model.model_hash()


def test_i7_materialized_disks_enter_existing_native_rotor_assembly():
    p=_project()
    base=RotorModel(nodes=p.model.nodes,shafts=p.model.shafts)
    full=RotorModel(nodes=p.model.nodes,shafts=p.model.shafts,disks=p.model.disks)
    facade=SolverFacade()
    M0,C0,K0,G0=facade.assemble(base,0.0)
    M1,C1,K1,G1=facade.assemble(full,0.0)
    assert np.linalg.norm(M1-M0)>0
    assert np.trace(M1-M0)>0
    np.testing.assert_allclose(C1,C0,rtol=0,atol=0)
    np.testing.assert_allclose(K1,K0,rtol=0,atol=0)
    assert np.linalg.norm(G1-G0)>0


def test_i7_ump_case_remains_unmaterialized_and_blocked():
    fixture=ROOT/"examples/legacy/EST-12735185-CRYOSTAR_V2.txt"
    p=load_irdin_project(fixture)
    assert p.model.mass_spans==[]
    assert p.model.disks==[]
    r=p.metadata["numerical_readiness"]
    assert r["components"]["mass_native_materialization"]=="BLOCKED"
    assert "IRDIN_DISTRIBUTED_MASS_UNMAPPED" in {x["code"] for x in r["blockers"]}
