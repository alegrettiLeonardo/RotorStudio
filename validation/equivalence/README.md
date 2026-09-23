# Formal equivalence closure

M6 separates authority generation, transient-threshold freeze, and Fortran comparison.

1. `matlab/generate_authority_baseline.m` executes untouched V2.
2. `freeze_transient_tolerances.py` uses only MATLAB-vs-independent-oracle discrepancy, never Fortran output, and refuses overwrite.
3. `run_formal_equivalence.py` applies the original fixed gates.

Missing authority data always returns `BLOCKED`, never PASS.

```bash
export PYTHONPATH="$PWD/python/src:$PWD"
export DRMROTOR_LIB="$PWD/build-release/libdrmrotor.so"
validation/equivalence/run_authority.sh
python validation/equivalence/freeze_transient_tolerances.py   --matlab-baseline validation/baseline/matlab_authority/authority_baseline.mat   --source-reference-dir validation/baseline/transient   --output validation/baseline/matlab_authority/TRANSIENT_TOLERANCES.json
python validation/equivalence/run_formal_equivalence.py   --matlab-baseline validation/baseline/matlab_authority/authority_baseline.mat   --transient-tolerances validation/baseline/matlab_authority/TRANSIENT_TOLERANCES.json
```
