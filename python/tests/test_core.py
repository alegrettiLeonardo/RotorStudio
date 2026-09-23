import ast, pathlib, sys
import numpy as np
from drm_core.domain.model import RotorModel,Node,ShaftElement,Disk,Bearing
from drm_core.validation.model import validate_model,ModelValidationError
from drm_core.units import rpm_to_rad_s

def test_no_gui_imports():
    root=pathlib.Path(__file__).parents[1]/'src'/'drm_core'; forbidden={'PySide6','PyQt5','PyQt6','tkinter','wx'}
    for f in root.rglob('*.py'):
        tree=ast.parse(f.read_text())
        for n in ast.walk(tree):
            if isinstance(n,(ast.Import,ast.ImportFrom)):
                names=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else [str(n.module).split('.')[0]]
                assert not forbidden.intersection(names), f'{f} imports GUI library'
def test_units(): assert abs(rpm_to_rad_s(60)-2*np.pi)<1e-15
def test_validation_message():
    m=RotorModel([Node(1,0),Node(2,0)],[ShaftElement(2,1,2,.1,0,7800,2e11,8e10)],[],[])
    try: validate_model(m)
    except ModelValidationError as e: assert 'Le=0' in str(e) and 'expected Le > 0' in str(e)
    else: assert False

def test_tapered_validation_and_legacy_mapping():
    from drm_core.domain.model import TaperedShaftElement
    m=RotorModel.from_legacy_arrays([[1,0],[2,.2]],[[22,1,2,.08,.07,.02,.01,7800,2e11,8e10,0]],[],[])
    assert isinstance(m.shafts[0],TaperedShaftElement)
    validate_model(m)
