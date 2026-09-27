"""A3 is additive: exact promoted native A0/A1/A2 sources, tests and goldens."""
from pathlib import Path
import subprocess
BASE='7b87c422691153fc4be3c1d134af4ffcc0af1678'
def git(*a):return subprocess.check_output(['git',*a])
paths=git('ls-tree','-r','--name-only',BASE,'fortran/src','fortran/tests','validation/ross_parity/static','validation/ross_parity/static_extended','validation/ross_parity/frf').decode().splitlines()
for p in paths:
    before=git('show',f'{BASE}:{p}')
    after=Path(p).read_bytes()
    if not p.endswith('.npz'):before=before.replace(b'\r\n',b'\n');after=after.replace(b'\r\n',b'\n')
    assert before==after,f'Promoted A0/A1/A2 source/golden changed: {p}'
print('PASS: promoted native legacy/A1/A2 implementations and immutable authorities unchanged')
