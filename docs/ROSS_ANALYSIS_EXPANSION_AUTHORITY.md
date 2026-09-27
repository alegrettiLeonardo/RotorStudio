# ROSS analysis expansion — source authority and pre-implementation audit

Audit date: 2026-09-27. Live GitHub refs were queried through the repository API.

| Repository/ref | Observed SHA | Difference from requested baseline |
|---|---|---|
| alegrettiLeonardo/RotorStudio main | e2a8b57003edf4b407ea089e92160ce86b30c35c | Identical; no delta |
| petrobras/ross main | 6320eab9f890f1b3cc1710d508b446fe063ca68d | Identical to frozen authority |
| petrobras/ross frozen commit | 6320eab9f890f1b3cc1710d508b446fe063ca68d | Commit exists; ROSS source version 3.1.0.dev0 |

RotorStudio base tree: `ceadc45f8f398a4485dba9905bc8117eb9aad87b`.
There are no AGENTS.md entries in the recursively returned repository tree.
Existing qualification claims in documentation are historical evidence; a query
for workflow runs associated with the baseline SHA returned no runs during this
audit. That does not disprove ancestral qualification, and this PR does not
relabel it. New qualification must use actual results at the new commit.

## Reusable native inventory

| Existing module | Reuse decision |
|---|---|
| rd_kinds, rd_status | Native kinds and status conventions |
| rd_lapack | solve_real/dgesv, solve_complex/zgesv, eig_real, eig_complex, generalized_eig_real; preserve wrappers |
| rd_shaft_circular, rd_shaft_tapered, rd_shaft_asymmetric | Existing element candidates; validate entries against ROSS before claiming interchangeability |
| rd_assembly_stationary | assemble_rotor gives M,C0,C1,K0,K1; 4 DOFs/node; use separate support policy for static |
| rd_assembly_rotating | Preserve rotating/asymmetric assembly; not A1 scope |
| rd_eigensystem | Modal foundation for A5/A6/A7; do not replace qualified branches |
| rd_frequency_response, rd_external_response | Synchronous/auxiliary/foundation paths; useful boundary references for A2/A3 |
| rd_critical_speed | Existing critical solvers; UCS is a distinct analysis |
| rd_reduction, rd_dp45, rd_transient | Preserve qualified reduction/DP45; add Newmark separately in A4 |
| rd_coaxial_solver, rd_rotating_solver | Preserve; ROSS MultiRotor is not automatically equivalent |
| fortran/bearings/src/rb_* | Separate drmbearings library; B13–B18 policies remain untouched |

`rd_assemble_legacy` already returns `C0 + Cb + speed*C1`. A2 must not
add `Omega*G` a second time. It also includes dynamic bearing contributions,
so it cannot be used unchanged as the ROSS static auxiliary matrix.

## Existing C ABI inventory

All following symbols are present in `fortran/src/rd_c_api.f90`:

- rd_version
- rd_element_circular_legacy, rd_element_tapered_legacy, rd_element_asymmetric_legacy
- rd_bearings_legacy, rd_assemble_legacy
- rd_modal_legacy, rd_modal_legacy_vectors
- rd_freq_rsp_legacy, rd_freq_aux_legacy, rd_freq_fdn_legacy
- rd_time_fdn_legacy, rd_runup_legacy, rd_runup_coeffmap_legacy
- rd_crit_spd_legacy, rd_crit_spd_legacy_ex
- rd_coax_modal_legacy, rd_coax_freq_rsp_legacy
- rd_asym_assemble_legacy, rd_bearasym_legacy, rd_asym_modal_legacy, rd_asym_freq_rsp_legacy

ISO_C_BINDING uses C int/double, status returns, column-major flattened outputs,
and separate real/imaginary buffers where needed. Existing input tables are
shaft(11,nshaft), disc(6,ndisc), bear(34,nbear). Preserve their node numbering
and convert only at an explicit new boundary. Static ABI is absent.
The separate bearing ABI in rb_c_api is outside the new rotor-ABI change scope.

## Actual application dispatch

`python/src/drm_core/analysis/service.py` and `domain/analysis_cases.py` only
re-export from `drm_core/stage1.py`. The actual `AnalysisService.execute` lives
in that file. It dispatches modal, modal_sweep, frequency_response,
auxiliary_frequency_response, foundation_frequency_response, critical_speeds,
coaxial_modal, coaxial_frequency_response, asymmetric_modal,
asymmetric_frequency_response, foundation_time_response, runup and
bearing_matrices. Unsupported kinds raise ValueError. Project readiness gates
are checked before dispatch. Hashing, build metadata and save/load are already
implemented. Static dispatch and facade method are absent.

## Phase 1 source mapping

All methods below were found in frozen `ross/rotor_assembly.py`. Proposed
modules/ABIs are NOT existing implementations or evidence of qualification.

| Feature | ROSS method / supporting source | Proposed Fortran | Proposed ABI | Python / tests | Status |
|---|---|---|---|---|---|
| A1 Static | run_static, gravitational_force, _remove_housing_bearings; utils.remove_dofs; results.StaticResults | rd_static.f90 | rd_static_v1 | analysis/static.py; direct ABI + static golden suite | BLOCKED |
| A2 FRF | run_freq_response, _run_freq_response, transfer_matrix | rd_dynamic_stiffness.f90; rd_frf_general.f90 | rd_frf_general_v1 | thin binding; D/H/residual suite | BLOCKED |
| A3 Forced | run_forced_response | rd_forced_response.f90 | rd_forced_response_v1 | direct vs H*F vs ROSS | BLOCKED |
| A4 Time | run_time_response; integration helpers | rd_newmark.f90; rd_force_provider.f90; rd_time_response.f90 | rd_time_response_v1 | SDOF + ROSS + timestep convergence | BLOCKED |
| A5 UCS | run_ucs; utils intersections and 6-to-4 conversion | rd_ucs.f90; rd_intersections.f90 | rd_ucs_v1 | log stiffness grid + intersections | BLOCKED |
| A6 Level1 | run_level1; modal whirl/log decrement | rd_level1.f90 | rd_level1_v1 | Q sweep + mode classification | BLOCKED |
| A7 Unbalance | api617_unbalance; orbit/antinode helpers | rd_orbit.f90; rd_antinode.f90; rd_api617.f90 | rd_api617_unbalance_v1 | nodes, loads, phases, units | BLOCKED |
| A8 Clearance | run_clearance_analysis; results probe magnitude | rd_api617_clearance.f90 | rd_api617_clearance_v1 | pk-pk + scale + clearance | BLOCKED |

`shaft_element.py`, `disk_element.py`, `bearing_seal_element.py`, `materials.py`,
`point_mass.py`, `results.py`, `units.py` and `utils.py` are supporting sources.
The complete commit is pinned; generated manifests hash selected source files.

## Semantic findings and risks

1. ROSS static excludes SealElement, removes housing bearings, replaces support
   stiffness with **1e20 N/m**, constructs zero-stiffness auxiliary bearings,
   reduces matrices to 4 DOFs and uses **g=-9.8065 m/s²**. It is not static
   equilibrium on the original frequency-dependent bearing stiffness.
2. Static force is ROSS gravitational_force applied to the auxiliary mass
   matrix; reactions use `K_without_support*q - weight`. Disk force dictionaries
   report positive weights. Preserve signed internal loads and diagram axes.
3. The 1e20 penalty makes conditioning a real risk. Do not substitute exact
   constraints silently or choose an absolute tolerance without scales.
4. Existing circular/tapered element formulations cannot be declared ROSS-equal
   from frequency agreement. A1 needs a documented lateral DOF/sign map and
   entry-by-entry K/M comparison for each admitted element type.
5. ROSS is internally 6-DOF here but run_static explicitly reduces to 4-DOF.
   That permits A1; it does not authorize 4-DOF fault-model parity.
6. ROSS FRF supports fixed spin independent of excitation frequency. Existing
   assembly already includes gyro damping; avoid double-counting it.
7. UCS uses a log stiffness grid; Level1 uses **np.linspace** on its stiffness
   range. Its default range derives from log10(k) yet is passed to linspace.
   Preserve that source behavior initially; do not silently normalize it.
8. Level1 selects first non-backward log decrement, not an arbitrary sorted
   eigenvalue. API617 unbalance uses modal selection, static loads and unit
   conversions; 6350 and 3.937 cannot be applied to an unexamined load unit.
9. Clearance unions Nma/Nmc with the speed grid, filters radial probes and uses
   pk-pk response. Peak, RMS, radius and diameter must remain distinct.
10. Housing/link supports, multiple disks at one node, concentrated masses,
    tapered shafts, overhung topology and unsupported legacy rows require
    explicit scope decisions. Reject unsupported cases rather than approximate.
11. A0 environment has no gfortran/cmake on PATH and lacks ROSS dependencies.
    Direct GitHub clone did not supply a checkout; repository API reads worked.
    Local unittest is executable; native/golden/platform gates require CI.

## Proposed A0 and A1 changes and acceptance

A0 files: validation/ross_parity/{authority.json,infrastructure.py,
generate_reference.py,compare_references.py,README.md,tests/test_infrastructure.py},
this authority audit, roadmap, third-party attribution/license and a dedicated
CI workflow. No production, legacy ABI, bearing physics or GUI changes.

A0 acceptance: exact clean ROSS source/import verification; actual environment
and source/payload hashes; deterministic full numeric references; two independent
ROSS generations; strict schema/finite/integrity comparisons; wrong-SHA/dirty
source rejection; no overwrites; Linux/Windows CI at the same commit; Release
build/CTest, Stage1 and relevant bearing/UI regressions. Existing Stage2/G14 and
frozen workflows remain required where their release gates apply. A0 does not
release a product feature. Candidate reference artifacts require review and
explicit freezing before A1 consumes them.

A1 files proposed: fortran/src/rd_static.f90; additive rd_static_v1 in rd_c_api;
fortran/tests/test_static.f90; fortran/CMakeLists.txt; solver/ffi.py, backend.py,
facade.py; analysis/static.py; result model; stage1.py dispatch;
python/tests_static/; validation/ross_parity/static/; GUI static setup/results
only after numerical gates; docs/ROSS_STATIC_FORTRAN_IMPLEMENTATION.md; A1 CI.

A1 acceptance: audited DOF/material/unit mapping; K/F and matrix-entry tests;
Fortran static solve and full output diagrams; direct ABI invalid-input/layout
tests; ROSS displacement/reaction/shear/moment parity; independent sum-F and
sum-M equilibrium; scaled residual/conditioning study; seal-exclusion and
support-policy tests; thin wrapper + AnalysisService + save/reopen/recompute;
GUI flow; preserved previous regressions; frozen Linux and Windows on the same
final SHA. No A2 start until A1 actually passes. No A1 physics is implemented by A0.

## Attribution

ROSS is Apache-2.0, copyright ROSS developers. See
docs/third_party/ROSS_ANALYSIS_NOTICE.md and ROSS_LICENSE.txt. A0 calls the
authority and records outputs; it does not port solver equations. Every later
port must identify the original method, source SHA and modifications.
