# I17 — API 541 torsional input contract

I17 starts the torsional scope as a separate engineering model. It does not
reuse or reinterpret the ST41 lateral iRdin file as a torsional train.

The explicit contract requires:

- polar inertia for every torsional station;
- torsional stiffness for every serial connection;
- optional nonnegative torsional damping;
- explicit motor and driven-equipment stations;
- explicit coupling connection;
- driven-equipment identification;
- one or more pulsating/electromagnetic torque excitations;
- provenance for every inertia, connection and excitation.

An excitation declares exactly one frequency reference:

- order relative to operating speed; or
- explicit frequency in Hz.

The initial qualified topology is a serial adjacent-station train. More general
branched gear trains are outside I17.

## Fail-closed rule

`torsional_model_from_irdin()` always rejects automatic construction. The
lateral source does not provide enough authority to infer the driven machine,
coupling stiffness, complete station inertias or torsional excitation spectrum.

## Gate

A successful validation returns:

`API541_TORSIONAL_INPUT_READY`

This means input completeness only. It does not mean:

- torsional eigensolver qualified;
- forced/transient torsional response qualified;
- fatigue/stress assessment qualified;
- whole-standard API 541 compliance.

The next stage is I18: native torsional M/C/K assembly and natural-frequency
analysis using this explicit contract.
