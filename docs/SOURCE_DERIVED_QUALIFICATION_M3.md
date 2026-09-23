# Source-derived qualification — M3

These tests use the preserved MATLAB V2 source as the formula/algorithm specification but do **not** execute MATLAB. They are therefore not a substitute for the MATLAB↔Fortran numerical-equivalence gates.

## Evidence executed

- `bearmtx` types 1/2: constrained DOF masks.
- `bearmtx` types 3/4: exact diagonal K/C placement.
- `bearmtx` type 5: exact 2x2 cross-coupled K/C placement.
- `bearmtx` type 6: exact 4x4 K/C mapping.
- `bearmtx` type 7: quartic eccentricity root and K/C coefficients against an independent NumPy oracle.
- `bearmtx` type 7 nonlinear flag: K/C suppressed while eccentricity remains available.
- `bearmtx` type 8: seal M/C/K formulas against an independent oracle.
- `freq_rsp`: combined force types 1, 2, 3 and 8 against a separately assembled Python dynamic-stiffness solve.
- `freq_rsp`: constrained DOF zero restoration and zero-speed unbalance response.
- `crit_spd` direct: damped and undamped results against an independent complex state-space construction.
- `crit_spd` method 2: independent source-equation iteration with a type-7 bearing, including iteration-limit status.
- `crit_spd` method 3: independent replication of the V2 closest-to-initial-estimate rule.
- `shftasym` types 11..18: M/C1/K0/K2 against an independent transcription of the source formulas.
- `rotorasym`: circular-shaft conversion agrees with the equivalent explicit asymmetric-element definition.
- `bearasym` type 4: V2 index defect is asserted numerically.
- `chr_asym`: output-count-dependent K1b path is asserted numerically.
- `freq_asym`: rotating-frame static response equation is independently reconstructed.
- `chr_root_coax`: all-speed-factor-one reduction and independent RelSpd/type-20-link state matrix checks.
- `freq_rsp_coax`: independent reference-speed bearing / rotor-specific excitation-speed response equation check.

## Numerical matching in offline qualification

For coaxial eigenvalue comparisons between NumPy and LAPACK, conjugate pairs may appear in opposite order because tiny solver-level magnitude differences affect sorting ties. Qualification therefore matches each computed eigenvalue to the nearest remaining reference eigenvalue offline. This does not alter the production solver, mode ordering, or Campbell behaviour.

## Test counts

M3 release evidence records 36 Python tests and 4 CTest tests. Exact test names are stored in `validation/reports/pytest_collection_M3.txt`.
