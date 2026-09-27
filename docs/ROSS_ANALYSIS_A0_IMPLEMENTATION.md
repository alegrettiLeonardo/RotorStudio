# PR-A0 implementation and qualification record

## 1. Baseline

Branch: feature/ross-analysis-a0-20260927. Base:
e2a8b57003edf4b407ea089e92160ce86b30c35c. Final SHA is the current PR #23 head;
qualification must reference that immutable SHA, not the branch name alone.
ROSS authority: 6320eab9f890f1b3cc1710d508b446fe063ca68d.

## 2. Scope

Implemented: pre-implementation audit, dependency plan, immutable source pin,
environment/provenance capture, candidate ROSS static reference generator,
strict comparison/integrity utilities, 16 local infrastructure tests and CI.
Not implemented: A1 Fortran static solver or any later solver/GUI feature.
Blocked: engineering qualification and A1 start until A0 gates/reference review.

## 3. Source authority

| ROSS source | ROSS method/class | RotorStudio Fortran implementation |
|---|---|---|
| ross/rotor_assembly.py | Rotor.run_static; rotor_example | None in A0; rd_static.f90 proposed for A1 |
| ross/bearing_seal_element.py | BearingElement; SealElement | No new port |
| ross/disk_element.py | DiskElement | No new port |
| ross/results.py | StaticResults | Reference outputs only |

## 4. Files changed

Fortran/C ABI/production Python/GUI: none.
Validation Python: infrastructure.py, generate_reference.py,
compare_references.py and validation package init.
Tests: validation/ross_parity/tests/test_infrastructure.py.
Docs/data: authority.json, parity README, authority audit, bearing ABI inventory,
roadmap, this record, third-party notice/license.
CI: .github/workflows/ross-analysis-a0.yml.

## 5. Numerical formulation

No new numerical equation is implemented in A0. The generator calls the exact
ROSS run_static method and exports its outputs. The audited A1 equation is
K_aux*q=F_gravity, with ROSS support replacement and 4-DOF reduction, not a
new Python solver. The generic comparator only measures output differences.

## 6. Golden parity

| Case | Quantities | ROSS | RotorStudio | Error/tolerance | Status |
|---|---|---|---|---|---|
| rotor_example | deformation, reactions, weights, Vx, Bm, axes | Pending real generation | Not implemented | Not measured | BLOCKED |
| soft_supports | Same; static support invariance | Pending | Not implemented | Not measured | BLOCKED |
| seal_exclusion | Same; seal exclusion | Pending | Not implemented | Not measured | BLOCKED |
| asymmetric_disk | Same; asymmetric reactions | Pending | Not implemented | Not measured | BLOCKED |

Candidate reproducibility limits are 2e-12 relative and 1e-12 absolute for two
ROSS runs. They are not A1 parity limits. No golden output is fabricated.

## 7. Independent physics gates

A1 sum-F, sum-M, matrix-entry parity, residual and conditioning gates are
specified in the audit but not executed. A0 tests cover exact-SHA enforcement,
dirty/untracked-source rejection, import provenance, checksums, shape/schema,
sign, finite values, tolerances, deterministic JSON and refusal to overwrite.
Synthetic unit-test data is never presented as physics evidence.

## 8. Regression

Local: 16 unittest tests passed; compileall passed. No production files changed.
Release/CTest, Stage1, Stage2, B13–B18 and relevant existing workflows require
remote results at the PR head; pending runs are not PASS. Existing historical
qualification is not reopened by changing production equations.

## 9. Platform

Local Linux infrastructure tests executed. Native Linux, native Windows, frozen
Linux and frozen Windows have no new completed evidence in this record.
A0 releases no GUI feature. A1 release requires both frozen-platform gates.

## 10. Limitations

The local environment lacks gfortran/cmake on PATH and several ROSS dependencies;
the live repository API was available but direct clone did not complete.
Candidate reference generation must run on CI. Candidate artifacts must be
reviewed and explicitly committed before they become A1 golden authority.
No scope is inferred for unsupported static topology/element types.

## 11. Qualification verdict

**BLOCKED** pending actual reference execution and required CI evidence.
Infrastructure implementation/testing is not engineering qualification.

## 12. Next permitted PR

Complete A0 qualification and reference freezing first. Then A1 Static Analysis.
A2 General FRF may not start until A1 is fully qualified.
