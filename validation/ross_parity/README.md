# Frozen ROSS analysis parity infrastructure (PR-A0)

Authority: `petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d`.
This directory is validation-only. Production code must never import it.

The checked-in `authority.json` is a source pin, not a generated reference or a
PASS certificate. Each generated bundle contains a separate `authority.json`
with actual Python/NumPy/SciPy/ROSS versions, OS, UTC generation time, full
installed package versions, source hashes, Git tree and payload hashes.

```bash
python -m unittest discover -s validation/ross_parity/tests -v
python validation/ross_parity/generate_reference.py --ross-root _ross_ref --out reference_run1
python validation/ross_parity/generate_reference.py --ross-root _ross_ref --out reference_run2
python validation/ross_parity/compare_references.py reference_run1 reference_run2
```

Install ROSS from a clean checkout of the exact commit, with Python >=3.12.
`--out` must not exist. There is no overwrite switch or fallback physics.
Generation executes `Rotor.run_static()` directly. Four candidate A1 fixtures
cover the official example, changed dynamic support stiffness, seal exclusion,
and an asymmetric disk. Full numerical JSON is deterministic for identical
values; environment/timestamp metadata is deliberately separate from cases.
NaN/Inf is rejected on write and comparison. No screenshot is numerical evidence.

The reproducibility comparator's 2e-12 relative/1e-12 absolute defaults are
candidate ROSS-to-ROSS thresholds, not frozen cross-platform A1 tolerances.
They must be reviewed against CI errors. A1 must use quantity-specific scales
and conditioning analysis before freezing its production acceptance thresholds.

Generated candidates are CI artifacts. They must be reviewed and frozen by an
explicit commit before A1 uses them. Never regenerate on a failed parity test,
never derive golden data from RotorStudio, and never call two ROSS runs
Fortran parity. No numerical candidate has been checked in by this PR.

Layout reserved by roadmap: static, frf, forced, transient, ucs, level1, api617,
sixdof, faults, harmonic_balance, stochastic, multirotor, amb. Future feature
directories are created with real content, not empty qualification placeholders.

Qualification remains BLOCKED until real generation, source/CI regressions and
same-head platform evidence are reviewed. No new GUI feature is enabled by A0.
