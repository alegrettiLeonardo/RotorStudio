ROSS (petrobras/ross), Copyright ROSS developers. Apache License 2.0.
Source authority: 6320eab9f890f1b3cc1710d508b446fe063ca68d.
The gravity, replacement-support and repeated-station recovery algorithms in
fortran/src/rd_static.f90 are adapted from ross/rotor_assembly.py Rotor.run_static.
Result semantics follow ross/results.py StaticResults; lateral DOF selection
follows ross/utils.py remove_dofs. The implementation is a Fortran adaptation,
with explicit validation and independent equilibrium/residual diagnostics.
See ROSS_LICENSE.md for the license. Validation reference data is generated
from that unmodified source. Existing legacy element formulas remain unchanged.

A2: fortran/src/rd_dynamic_stiffness.f90 and rd_frf_general.f90 adapt the full-order
Rotor.transfer_matrix / run_freq_response / _run_freq_response conventions from
the same pinned ROSS authority. Complex multiple-RHS LAPACK solves replace the
Python LU orchestration. Singular/nonfinite responses fail closed instead of
replacing NaNs by zero. Golden models are converted before solving through
ross.utils.convert_6dof_to_4dof. Bearing interpolation reuses the existing native
ROSS-derived coefficient provider. No A1 or legacy physics was replaced.
