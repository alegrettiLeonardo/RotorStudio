from __future__ import annotations
import pytest
from validation.b1.native_preservation import (
    ROOT,BASE,NEW_FILES,ADAPTED_FILES,approve_change,expected_adaptation,git,verify,
)

@pytest.mark.parametrize('path',[
    'fortran/src/rd_shaft_circular.f90',
    'fortran/src/rd_c_api.f90',
    'python/src/drm_core/solver/ffi.py',
    'validation/ross_parity/6dof_elements/tolerances.json',
    'validation/ross_parity/6dof_elements/authority.json',
    'validation/ross_parity/6dof_elements/SHA256SUMS.json',
    'validation/b1/element_cases.json',
    '.github/workflows/stage1-final-qualification.yml',
])
def test_historical_changes_are_not_permitted_by_native_allowlist(path):
    before=git(ROOT,'show',f'{BASE}:{path}')
    with pytest.raises(ValueError,match='Historical file changed'):
        approve_change(path,before,before+b'\n# unauthorized\n')
    with pytest.raises(ValueError,match='Removal'):
        approve_change(path,before,None)


@pytest.mark.parametrize('path',[
    'fortran/src/arbitrary.f90',
    'python/src/drm_core/solver/sixdof_backdoor.py',
    'python/tests_6dof_elements/../../src/drm_core/solver/ffi.py',
    'reference/new_golden.npz',
    '.github/workflows/unreviewed.yml',
])
def test_new_path_requires_exact_membership(path):
    with pytest.raises(ValueError,match='Unapproved new path'):
        approve_change(path,None,b'new content')


@pytest.mark.parametrize('path',sorted(NEW_FILES))
def test_new_file_permission_does_not_allow_replacing_a_historical_file(path):
    approve_change(path,None,b'new additive file')
    with pytest.raises(ValueError,match='Historical file changed'):
        approve_change(path,b'hypothetical historical content',b'replacement')


@pytest.mark.parametrize('path',sorted(ADAPTED_FILES))
def test_only_exact_preservation_adaptations_are_allowed(path):
    before=git(ROOT,'show',f'{BASE}:{path}')
    allowed=expected_adaptation(path,before)
    approve_change(path,before,allowed)
    with pytest.raises(ValueError,match='exact permitted patch'):
        approve_change(path,before,allowed+b'\n# additional unauthorized change\n')


def test_cmake_cannot_redirect_legacy_or_change_optimization():
    path='fortran/CMakeLists.txt'; before=git(ROOT,'show',f'{BASE}:{path}')
    correct=expected_adaptation(path,before)
    for mutant in [correct.replace(b'src/rd_shaft_circular.f90',b'src/rd_shaft_6dof.f90',1),
                   correct.replace(b'-O2',b'-Ofast',1),correct+ b'\nset(BUILD_TESTING OFF)\n']:
        assert mutant!=correct
        with pytest.raises(ValueError,match='exact permitted patch'):
            approve_change(path,before,mutant)


def test_complete_actual_source_tree_and_frozen_inventory_are_preserved():
    result=verify()
    assert result['status']=='PASS'
    assert result['authority']['frozen_file_count']==194
    assert result['authority']['sha256sums_sha256']=='86e80775aab32b904ba48a7d7ba64954a3cfabad79cf835e808bf49077ffe847'
