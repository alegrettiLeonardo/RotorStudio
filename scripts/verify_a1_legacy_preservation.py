"""Prove the promoted core is byte-identical after stripping the additive A1 ABI."""
from pathlib import Path
import subprocess,re
BASE='a44c5aa3f521a84785f9b020db9e119e9d1e25a2'
def git(*args):return subprocess.check_output(['git',*args])
paths=git('ls-tree','-r','--name-only',BASE,'fortran/src','fortran/tests').decode().splitlines()
for path in paths:
    before=git('show',f'{BASE}:{path}').decode().replace('\r\n','\n')
    after=Path(path).read_text()
    if path=='fortran/src/rd_c_api.f90':
        after=after.replace(' use rd_static, only: static_solve\n','').replace(' public :: rd_static_v1\n','')
        after,n=re.subn(r" integer\(c_int\) function rd_static_v1\(.*?\n end function\n\n",'',after,count=1,flags=re.S)
        assert n==1,'Missing or malformed additive ABI'
    assert after==before,f'Promoted legacy source changed: {path}'
extra=set(git('ls-files','--cached','--others','--exclude-standard','fortran/src','fortran/tests').decode().splitlines())-set(paths)
assert extra=={'fortran/src/rd_static.f90','fortran/tests/test_static.f90'},extra
print('PASS: legacy source and tests unchanged; only rd_static_v1/module/test added')
