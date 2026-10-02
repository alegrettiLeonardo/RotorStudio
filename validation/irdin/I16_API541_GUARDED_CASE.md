# I16 — guarded API 541 lateral AnalysisCase

I16 connects the qualified I11/I12/I13 implementation to the application
dispatcher without weakening imported-project safeguards.

A freshly imported ST41 project remains:

`LEGACY_NUMERIC_READY`

and cannot execute `api541_lateral`.

The caller must first provide an I14 declaration:

- explicit `HalfCoupling` entity, or
- explicit `NOT_APPLICABLE` with engineering justification.

The caller must also declare exactly one operating reference:

- fixed operating speed, or
- operating speed range.

Only then `enable_api541_lateral_analysis()` returns a copied project with:

`API541_LATERAL_READY`

and one guarded `AnalysisCase("api541_lateral")`.

The generated case uses the qualified legacy Campbell/response grids, the I9
native expanded solver, I11 separation/support-sensitivity logic, I12
analytical unbalance and I13 reporting result.

Generic RotorStudio 4-DOF analysis kinds remain blocked for this imported
project state. The readiness label describes the declared lateral-analysis
scope only and is not a whole-standard API 541 compliance statement.

Experimental correlation and torsional analysis remain separate gates.
