"""Prove the promoted core is byte-identical after stripping the additive A2 ABIs."""
from pathlib import Path
import subprocess,re
BASE='1560b7da158b22079a46832f199ae95dd85ee5d6'
def git(*args):return subprocess.check_output(['git',*args])
paths=git('ls-tree','-r','--name-only',BASE,'fortran/src','fortran/tests').decode().splitlines()
for path in paths:
    before=git('show',f'{BASE}:{path}').decode().replace('\r\n','\n')
    after=Path(path).read_text()
    if path=='fortran/src/rd_c_api.f90':
        after=after.replace(' use rd_dynamic_stiffness, only: build_dynamic_stiffness\n','').replace(' use rd_frf_general, only: general_frf,frf_size_valid\n','').replace(' public :: rd_frf_general_v1,rd_dynamic_stiffness_v1\n','')
        for symbol in ['rd_frf_general_v1','rd_dynamic_stiffness_v1']:
            after,n=re.subn(r" integer\(c_int\) function "+symbol+r"\(.*?\n end function\n\n",'',after,count=1,flags=re.S)
            assert n==1,'Missing or malformed additive ABI: '+symbol
    assert after==before,f'Promoted legacy source changed: {path}'
extra=set(git('ls-files','--cached','--others','--exclude-standard','fortran/src','fortran/tests').decode().splitlines())-set(paths)
allowed_additive={
 'fortran/src/rd_dynamic_stiffness.f90','fortran/src/rd_frf_general.f90','fortran/tests/test_frf_general.f90',
 'fortran/src/rd_forced_response.f90','fortran/src/rd_forced_response_c_api.f90','fortran/tests/test_forced_response.f90',
 'fortran/src/rd_newmark.f90','fortran/src/rd_transient_stiffness.f90','fortran/src/rd_time_response_general.f90',
 'fortran/src/rd_time_response_c_api.f90','fortran/tests/test_newmark.f90','fortran/tests/time_probe.f90',
 # A5 is additive and has no edits to the promoted legacy/A1 implementation.
 'fortran/src/rd_intersections.f90','fortran/src/rd_rouch.f90','fortran/src/rd_ucs.f90',
 'fortran/src/rd_ucs_c_api.f90','fortran/tests/test_ucs.f90',
 # A6 Level 1 remains additive to the promoted A5 implementation.
 'fortran/src/rd_level1.f90','fortran/src/rd_level1_c_api.f90','fortran/tests/test_level1.f90',
 # A7 API 617 unbalance remains additive to the promoted A6 implementation.
 'fortran/src/rd_api617_unbalance.f90','fortran/src/rd_api617_unbalance_c_api.f90','fortran/tests/test_api617_unbalance.f90',
}
assert extra==allowed_additive,extra
print('PASS: legacy source and tests unchanged; A1 unchanged; only additive A2/A3/A4/A5/A6/A7 modules/ABIs/tests added')

exec(Path("scripts/verify_a2_preservation.py").read_text())

exec(Path("scripts/verify_a3_preservation.py").read_text())
