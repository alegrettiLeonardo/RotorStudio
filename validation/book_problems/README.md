# G14 - 83 DRM book-problem regression

The supplied problem set is treated as an independent authority. inventory.py hashes and classifies all 83 Problem_*.m files.

- Class A: 15 cases. The original script calls a Rotor_Software_v2 numerical solver/matrix routine. The untouched case is executed in GNU Octave 7.1.0 and a final numerical result is re-evaluated through the existing Python to Fortran production API.
- Class B: 68 cases. Analytical/educational cases with no V2 numerical-solver call. They execute independently in GNU Octave 7.1.0.
- Plot/post-only calls do not make a case Class A.
- The G14 harness contains no alternate rotor solver and does not duplicate Fortran physics.

The full runtime inventory, per-file SHA256, detected calls and pass/fail evidence are emitted under validation/reports/.
