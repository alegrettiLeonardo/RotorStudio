# I13 — composed API 541 lateral assessment

I13 combines the previously qualified pieces into one engineering result:

- I11 modal tracking, critical crossings, separation checks, legacy probe peaks
  and support-stiffness sensitivity;
- I12 API 541 analytical-unbalance construction and scaled native response;
- deterministic JSON and Markdown engineering reports.

The dynamic solvers remain the native I9 expanded rotor-bearing-support path.

## Declared result

A successful I13 result is labeled:

`PASS_I13_API541_LATERAL_ASSESSMENT`

and the report scope is:

`API 541 lateral dynamics analysis for the declared imported iRdin scope`

This is intentionally **not** a whole-standard compliance statement.

## Required report content

The Markdown/JSON report contains:

- tracked critical speeds and damping;
- separation fraction, required fraction and individual PASS/FAIL;
- analytical-unbalance planes, journal loads, minimum and applied g.mm;
- API 541 vibration limit and resulting peak-to-peak probe motion;
- support-sensitivity evidence;
- explicit limitations.

## Remaining gates

I13 does not include:

- experimental correlation;
- torsional train analysis;
- general multi-support journal-load allocation;
- overhung-load substitution unless explicitly qualified;
- a whole-machine API 541 conformity decision.

The importer/AnalysisService readiness is not changed by this implementation
until the I12 and I13 cross-platform gates are green on the same final HEAD.
