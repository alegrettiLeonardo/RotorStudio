# ROSS analysis parity infrastructure (A0)

Validation only. No production dependency on ROSS. Frozen authority:
`petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d` (Apache-2.0).
The ROSS authors retain authorship of the authority algorithms. The generator
calls their API; no solver is ported in A0. See the upstream LICENSE.md and
tracked hashes in static/authority.json.

Run from the repository root:

```sh
python -m pip install -e /path/to/clean/pinned/ross
python validation/ross_parity/generate_reference.py --ross-root /path/to/clean/pinned/ross --out /new/directory
python validation/ross_parity/verify_reference.py validation/ross_parity/static --candidate /new/directory
python -m pytest validation/ross_parity/tests -q
```

The generator refuses existing output directories, dirty authority checkouts and
wrong SHAs. CI regenerates in a separate directory and never updates golden files.
JSON records all case inputs in SI. NPZ contains finite numeric arrays only.
Metadata records environment, source hashes and output hashes. The hashes are
integrity evidence, not a digital signature or a substitute for pinned source.
Reference manifest timestamps are intentionally not byte-reproducible; numeric
arrays are compared at rtol=atol=1e-12 for same-source ROSS reproduction.
This is distinct from the provisional Fortran static rtol=1e-8 gate.

Static reference scope: circular Euler-Bernoulli shafts (no shear, no rotary
inertia), rigid disks, simple supports, single shaft, no housing links. The three
cases deliberately include a stepped overhung shaft and a statically
indeterminate three-support shaft. No general static capability is claimed.
A1 must add seals/support-invariance, invalid/singular input, consistent K/F and
matrix parity cases before release, and separately justify broader scope.

Reserved future suites: frf, forced, transient, ucs, level1, api617, sixdof,
faults, harmonic_balance, stochastic, multirotor, amb. They are not implemented.
