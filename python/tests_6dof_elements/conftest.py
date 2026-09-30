from __future__ import annotations
import os
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'python/src'))

@pytest.fixture(scope='session')
def native_reports(tmp_path_factory):
    from validation.b1.native_validation import qualify
    from validation.b1.tests.test_frozen_authority import locked_integrity
    from validation.ross_parity.verify_6dof_elements_candidate import snapshot
    root=ROOT/'validation/ross_parity/6dof_elements'
    locked_integrity(root)
    before=snapshot(root)
    library=os.environ.get('DRMROTOR_LIB')
    if not library or not Path(library).is_file():
        pytest.fail('Real DRMROTOR_LIB must identify the built B1 shared library; native tests cannot be skipped')
    value=os.environ.get('B1_NATIVE_EVIDENCE')
    out=Path(value) if value else tmp_path_factory.mktemp('b1-native-evidence')
    reports,summary=qualify(out,library)
    yield reports,summary
    assert snapshot(root)==before, 'Native qualification modified frozen authority'
