from __future__ import annotations

from pathlib import Path
import math

import pytest

from drm_core import load_irdin_project, save_project, load_project
from drm_core.domain.model import Node
from drm_core.importers.irdin_excitation import (
    GMM_TO_KGM,
    IrdinExcitationMappingError,
    build_response_probes,
)

ROOT=Path(__file__).resolve().parents[2]
CASE=ROOT/"validation/irdin/cases/ST41_1000_B3_60HZ_1675_63536.txt"


def _node_at(project,z_m):
    matches=[n for n in project.model.nodes if abs(n.z_m-z_m)<=1e-10]
    assert len(matches)==1
    return matches[0].number


def test_st41_unbalance_materializes_exact_legacy_force_contract():
    project=load_irdin_project(CASE)
    assert len(project.model.forces)==2
    assert [_node_at(project,z) for z in (1.3709,3.0459)] == [
        int(force.values[0]) for force in project.model.forces
    ]
    for force in project.model.forces:
        assert force.force_type==1
        assert float(force.values[1]) == pytest.approx(110175.3*GMM_TO_KGM,rel=0,abs=1e-15)
        assert float(force.values[2]) == 0.0
    audit=project.metadata["legacy_irdin"]["excitation_probe_audit"]
    assert audit["status"]=="PASS"
    assert audit["unbalance_count"]==2
    assert audit["unbalance_unit_conversion"]=="g.mm -> kg.m"
    assert project.metadata["numerical_readiness"]["components"]["unbalance"]=="PASS_I6_LEGACY_UNBALANCE"


def test_st41_probes_are_exact_nodes_with_axis_and_orientation_preserved():
    project=load_irdin_project(CASE)
    probes=project.model.probes
    assert len(probes)==4
    assert [p.node for p in probes] == [
        _node_at(project,.550),_node_at(project,.550),
        _node_at(project,3.977),_node_at(project,3.977),
    ]
    assert [p.coordinate for p in probes]==[1,2,1,2]
    assert all(p.orientation_rad==0.0 for p in probes)
    assert project.metadata["numerical_readiness"]["components"]["probes"]=="PASS_I6_RESPONSE_PROBES"


def test_i6_keeps_global_readiness_blocked_until_mass_support_global_physics():
    project=load_irdin_project(CASE)
    readiness=project.metadata["numerical_readiness"]
    assert readiness["status"]=="BLOCKED_FOR_NUMERICAL_ANALYSIS"
    codes={x["code"] for x in readiness["blockers"]}
    assert "IRDIN_DISTRIBUTED_MASS_UNMAPPED" not in codes
    assert readiness["components"]["mass_native_materialization"]=="PASS_I7_DISK_MATERIALIZATION"
    assert "IRDIN_FLEXIBLE_SUPPORT_UNMAPPED" in codes
    assert "IRDIN_EXCITATION_PROBE_UNMAPPED" not in codes


def test_i6_save_reopen_preserves_force_probe_contract(tmp_path):
    project=load_irdin_project(CASE)
    before=project.model.model_hash()
    target=tmp_path/"st41.json"
    save_project(project,target)
    reopened=load_project(target)
    assert reopened.model.model_hash()==before
    assert reopened.model.forces==project.model.forces
    assert reopened.model.probes==project.model.probes


def test_probe_negative_support_reference_remains_fail_closed():
    with pytest.raises(IrdinExcitationMappingError,match="negative"):
        build_response_probes(
            [{"index":1,"position_mm":-1.0,"coordinate":1,"orientation_deg":0.0}],
            [Node(1,0.0),Node(2,1.0)],
        )


def test_probe_unknown_coordinate_fails_closed():
    with pytest.raises(IrdinExcitationMappingError,match="coordinate"):
        build_response_probes(
            [{"index":1,"position_mm":0.0,"coordinate":3,"orientation_deg":0.0}],
            [Node(1,0.0),Node(2,1.0)],
        )
