# Formal equivalence closure — M7

M7 turns the local M6 formal-equivalence harness into repository-owned, reproducible qualification.

## Authority and ordering

`Rotor_Software_v2` remains the numerical and behavioural authority. M7 stores the numerical V2 source subset required by the formal campaign in `reference/matlab_v2` and freezes their canonical LF SHA256 values in `authority_source_manifest.json`.

Verify source integrity first:

```bash
python validation/equivalence/verify_authority_sources.py
```

The original V2 ZIP SHA256 is:

```text
bc42d18020013a537da6e7785a3d6b15533cd881939410c5e2a58c8563db5344
```

## Formal sequence

The order is intentionally one-way:

1. generate independent transient source references;
2. execute untouched V2 with GNU Octave 7.1.0;
3. freeze transient tolerances using only Octave-vs-independent-oracle discrepancy;
4. run the Fortran/Python comparator;
5. report G5–G12 as PASS/FAIL.

The transient tolerance script refuses overwrite. The comparator also verifies that the source-reference hashes match the frozen policy.

No Fortran result is used to set or relax a threshold.

## Manual reproduction

Build the production core first:

```bash
cmake -S fortran -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release -j
ctest --test-dir build-release --output-on-failure

export PYTHONPATH="$PWD/python/src:$PWD"
export DRMROTOR_LIB="$PWD/build-release/libdrmrotor.so"
python -m pip install -e './python[test]'
```

Generate the independent transient references:

```bash
python validation/baseline/transient/generate_source_baseline.py
```

Generate the authority baseline with GNU Octave 7.1.0:

```bash
mkdir -p validation/baseline/matlab_authority
docker run --rm \
  -v "$PWD:/work" \
  -w /work \
  gnuoctave/octave:7.1.0 \
  octave --no-gui --quiet --eval \
  "addpath('/work/validation/equivalence/matlab'); generate_authority_baseline('/work','/work/validation/baseline/matlab_authority');"
```

Freeze transient tolerances before the formal Fortran comparison:

```bash
python validation/equivalence/freeze_transient_tolerances.py \
  --matlab-baseline validation/baseline/matlab_authority/authority_baseline.mat \
  --source-reference-dir validation/baseline/transient \
  --output validation/baseline/matlab_authority/TRANSIENT_TOLERANCES.json
```

Run the fixed formal gates:

```bash
python validation/equivalence/run_formal_equivalence.py \
  --matlab-baseline validation/baseline/matlab_authority/authority_baseline.mat \
  --transient-tolerances validation/baseline/matlab_authority/TRANSIENT_TOLERANCES.json \
  --output validation/reports/FORMAL_EQUIVALENCE.json
```

## G7 semantics

At repeated/degenerate eigenvalues an individual eigenvector is not unique. M7 therefore applies individual-vector MAC only to isolated modes while retaining eigenvalue/frequency gates for all modes.

The fixed `kappa_absrel=1e-10` criterion qualifies the legacy V2 `whirl` transformation on the same authority eigenvectors. End-to-end kappa remains a diagnostic because near-circular local orbits amplify tiny cross-LAPACK eigenvector perturbations.

## CI

`.github/workflows/stage1-m7-qualification.yml` reproduces the full Linux regression and the formal Octave 7.1.0 G5–G12 closure on every relevant push/PR. Formal evidence is uploaded as a workflow artifact.
