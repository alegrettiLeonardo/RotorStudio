# I9 — expanded modal and synchronous response

I9 consumes the I8 expanded rotor/bearing/support matrices and adds two native
solves:

- `rd_irdin_support_modal_v1`: second-order damped eigenproblem;
- `rd_irdin_support_synchronous_v1`: synchronous unbalance response.

No A0-A8 ABI or production solver path is modified.

## Legacy response authority

The force and probe conventions are taken from the frozen historical source
`alegrettiLeonardo/frontend_rotordin@647d600bc1d32a05de62ee457942e00285b572e3`.

For one unbalance value `U` and phase `phi`, `resp_f.f90` builds

`P = U * omega^2 * exp(i*phi)`

and applies

`Fx = -i*P`

`Fz = +P`.

The iRdin Z axis is the modern RotorStudio Y axis by name only; no coefficient
sign is changed.

The frozen `matfun.f90:vrotate` convention is

`x' = x*cos(theta) + z*sin(theta)`

`z' = z*cos(theta) - x*sin(theta)`.

Probe coordinate 1 selects `x'`; coordinate 2 selects `z'`.

## Scope

I9 is still a qualification path, not a general AnalysisCase. It validates:

1. expanded M/C/K modal solution;
2. synchronous legacy unbalance forcing;
3. complex rotor response;
4. exact probe rotation and channel extraction;
5. ST41 finite end-to-end solves with native bearing interpolation.

The project remains `BLOCKED_FOR_NUMERICAL_ANALYSIS` until I9 and the
following automatic-case/legacy-parity gate are closed on Linux and Windows.
