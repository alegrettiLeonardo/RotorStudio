from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from drm_core import load_irdin_project,load_project,save_project
from drm_core.analysis.irdin_lateral import build_expanded_state
from drm_core.analysis.api541_analytical_unbalance import journal_static_loads_kg
from drm_core.importers.irdin_half_coupling import (
    I14_EXPLICIT,I14_NOT_APPLICABLE,
    declare_half_coupling,declare_half_coupling_not_applicable,
    require_half_coupling_declaration,
)
from validation.irdin.i0_authority import CASE_PATH


def test_i14_import_never_infers_half_coupling_from_mass_rows():
    p=load_irdin_project(CASE_PATH)
    assert p.model.half_couplings==[]
    assert p.metadata["numerical_readiness"]["components"]["half_coupling"]=="NOT_DECLARED"
    with pytest.raises(ValueError,match="explicit I14"):
        require_half_coupling_declaration(p)


def test_i14_explicit_half_coupling_persists_and_enters_native_i9_mass(tmp_path):
    p=load_irdin_project(CASE_PATH)
    before=build_expanded_state(p,0.0)
    q=declare_half_coupling(
        p,node=len(p.model.nodes),
        mass_kg=125.0,
        diametral_inertia_kgm2=3.5,
        polar_inertia_kgm2=6.0,
        provenance={"source":"engineering drawing HC-001"},
    )
    assert p.model.half_couplings==[]
    assert q.metadata["numerical_readiness"]["components"]["half_coupling"]==I14_EXPLICIT
    require_half_coupling_declaration(q)
    after=build_expanded_state(q,0.0)
    rotor_nd=4*len(q.model.nodes)
    # Added disk mass lives only on rotor DOFs; support rows are unchanged by declaration.
    assert np.trace(after.M[:rotor_nd,:rotor_nd]-before.M[:rotor_nd,:rotor_nd])>0.0
    np.testing.assert_allclose(
        after.M[rotor_nd:,rotor_nd:],
        before.M[rotor_nd:,rotor_nd:],
        rtol=0,atol=0,
    )
    path=tmp_path/"st41-i14.rds";save_project(q,path);r=load_project(path)
    assert r.model.half_couplings==q.model.half_couplings
    assert r.model.model_hash()==q.model.model_hash()
    assert require_half_coupling_declaration(r)==I14_EXPLICIT


def test_i14_half_coupling_mass_enters_api541_static_journal_loads():
    p=load_irdin_project(CASE_PATH)
    base=sum(x.static_load_kg for x in journal_static_loads_kg(p))
    q=declare_half_coupling(
        p,node=len(p.model.nodes),
        mass_kg=125.0,
        diametral_inertia_kgm2=3.5,
        polar_inertia_kgm2=6.0,
    )
    updated=sum(x.static_load_kg for x in journal_static_loads_kg(q))
    assert updated-base==pytest.approx(125.0,rel=2e-13,abs=1e-9)


def test_i14_not_applicable_is_explicit_and_does_not_create_mass():
    p=load_irdin_project(CASE_PATH)
    q=declare_half_coupling_not_applicable(
        p,reason="Motor configuration explicitly has no separate half coupling in assessed scope"
    )
    assert q.model.half_couplings==[]
    assert require_half_coupling_declaration(q)==I14_NOT_APPLICABLE
    assert q.metadata["api541_half_coupling_declaration"]["applicable"] is False


def test_i14_rejects_missing_node_and_nonphysical_values():
    p=load_irdin_project(CASE_PATH)
    with pytest.raises(ValueError,match="does not exist"):
        declare_half_coupling(p,node=999,mass_kg=1,diametral_inertia_kgm2=1,polar_inertia_kgm2=1)
    with pytest.raises(ValueError,match="mass>0"):
        declare_half_coupling(p,node=1,mass_kg=0,diametral_inertia_kgm2=1,polar_inertia_kgm2=1)
    with pytest.raises(ValueError,match="nonempty"):
        declare_half_coupling_not_applicable(p,reason=" ")
