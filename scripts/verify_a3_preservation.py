"""A4 is additive: exact promoted native A0/A1/A2/A3 sources, tests and goldens."""
from pathlib import Path
import subprocess
BASE='e2b4a346faf55d5bdb66c826934b829532410fae'
def git(*a):return subprocess.check_output(['git',*a])
paths=git('ls-tree','-r','--name-only',BASE,'fortran/src','fortran/tests','validation/ross_parity/static','validation/ross_parity/static_extended','validation/ross_parity/frf','validation/ross_parity/forced').decode().splitlines()
for p in paths:
    before=git('show',f'{BASE}:{p}')
    after=Path(p).read_bytes()
    if not p.endswith('.npz'):before=before.replace(b'\r\n',b'\n');after=after.replace(b'\r\n',b'\n')
    assert before==after,f'Promoted A0/A1/A2/A3 source/golden changed: {p}'
print('PASS: promoted native legacy/A1/A2/A3 implementations and immutable authorities unchanged')
