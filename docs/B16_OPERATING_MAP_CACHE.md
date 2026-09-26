# B16 — Advanced Bearing Operating-Point Map / Cache

BASE_HEAD = af165254866212d9c48f2bacd0473f3e487ebc7b
B15_GATE = B15_IRDIN_COEFFICIENT_BEARING_IMPORT PASS at workflow run 36248681356
STATUS = AWAITING_SAME_HEAD_QUALIFICATION

## Contract

B16 materializes expensive advanced-bearing evaluations as coefficient-only
operating maps:

- synchronous 1-D: omega = Omega;
- independent 2-D: Omega and omega are separate axes.

`BearingOperatingMap` stores K/C, interpolation, source-bearing SHA256,
solver fingerprint, source qualification and convergence summaries. Full
pressure/temperature/deformation fields are deliberately not part of the
coefficient cache.

## Deterministic key

The SHA256 key includes the complete canonical physical bearing payload,
family, Omega/omega axes, interpolation, native ABI, native library
fingerprint, frozen ROSS authority and cache schema. Mesh, solver controls,
thermal and deformation settings are part of the physical bearing payload and
therefore invalidate the key automatically.

## Cache

L1 is an in-memory LRU. L2 is:

`<cache-root>/<sha256>/manifest.json`
`<cache-root>/<sha256>/coefficients.npz`

L2 writes use a temporary sibling directory followed by atomic rename. The
manifest carries the NPZ SHA256; incomplete or corrupt entries are rejected and
the normal get-or-generate path invalidates/recomputes them. Cancellation occurs
before cache promotion and cannot create a valid partial cache.

## Async generation

`OperatingMapJobManager` follows the B14 serialized QThreadPool/JobState
contract. Progress is emitted at physical operating-point boundaries. A cancel
request also reaches the B14 native cooperative-cancel mailbox so an in-flight
Reynolds/THD/TEHD point can leave at a safe native boundary.

## Qualification

B16 gates compare direct physical evaluation with map values at tabulated
points, exercise a narrow asynchronous TiltingPad 2-D cell with Omega != omega,
test L1/L2 reuse, all required invalidation inputs, cache corruption,
cancellation/no-promotion, model-hash isolation and direct/cold/warm timing.

Known exclusions remain: matched-whirl (B17), advanced-bearing run-up (B18),
general transient advanced bearings, coaxial/rotating advanced bearings and
nonzero bearing-M assembly.
