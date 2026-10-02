# I15 — experimental lateral correlation

I15 implements the correlation layer from the staged iRdin/API 541 plan.
It does not create or infer experimental measurements.

## Canonical CSV

The initial file contract is UTF-8 CSV:

```text
speed_rpm,DE-H_amplitude_um,DE-H_phase_deg,DE-V_amplitude_um,DE-V_phase_deg,...
```

Each measurement channel must provide amplitude in micrometres and phase in
degrees. Channel names are arbitrary engineering labels; mapping from each
measurement channel to one qualified iRdin `ResponseProbe` is explicit and
one-to-one.

## Quantities

At each measured speed I15 evaluates the same I9 native expanded synchronous
solver and reports:

- amplitude difference;
- relative amplitude error;
- wrapped phase difference;
- optional explicitly paired critical-speed error.

A separate MAC utility is provided when measured modal vectors are available.

## Status policy

Raw comparison always returns:

`MODEL_NOT_CORRELATED`

with `acceptance_evaluated=false`.

The model can become:

`MODEL_CORRELATED_FOR_LATERAL_SCOPE`

only after caller-supplied project criteria are supplied for amplitude and
phase and, when requested, critical-speed error. No API 541 correlation
tolerance is invented.

Experimental correlation does not establish whole-standard API 541 compliance.
Torsional analysis remains a separate gate.
