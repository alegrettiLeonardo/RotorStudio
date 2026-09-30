# iRdin Semantic Contract — ST41 declared lateral scope

## Status

`IRDIN_SEMANTIC_AUTHORITY_ST41 = PASS`

This gate establishes legacy field meaning only. It does **not** remove the
RotorStudio numerical-readiness blockers and does not yet add mass/support
physics.

## Authority chain

The primary source available for the historical numerical contract is the
current migrated RotorDin frontend and the native RotorDin source archived in
`alegrettiLeonardo/frontend_rotordin@647d600bc1d32a05de62ee457942e00285b572e3`.

The exact Git blobs are frozen in `semantic_contract.json`. The key evidence
is:

- `legacy_import.py`: explicit INI grid-column mapping;
- `domain.py`: typed Xi/LC, support, force and probe contract;
- `mass_properties.py` + `solver_disks.py`: physical mass geometry,
  package expansion, and the predad-compatible inertia convention;
- `physical_parity.py`: legacy/display unbalance is g·mm, converted once to
  kg·m; phase and response orientation are degrees;
- `entrada.f90`: SI native input and the SUPPORT row contract
  `bearing,Kxx,Kxz,Kzz,Kzx,Cxx,Cxz,Czz,Czx,mass`;
- `predad.f90`: disk/inertia preparation and response locations as mandatory
  stations;
- `resp_f.f90`: unbalance force uses `U*omega^2`; response coordinate
  1 = horizontal/X, 2 = vertical/Z after rotation by the probe angle.

The archived repository does not contain the original VB6 form source in the
current tree. Consequently this gate claims the demonstrated RotorDin/iRdin
numerical contract, not provenance from a specific VB6 control declaration.

## [Massas]

| Column | Qualified meaning | Unit | Status |
|---:|---|---|---|
| 0 | Xi: start of the logical mass span | mm | PASS |
| 1 | LC: axial span length | mm | PASS |
| 2 | explicit mass | kg | PASS |
| 3 | physical outer diameter | mm | PASS |
| 4 | package flag | boolean | PASS |
| 5 | UMP enable flag | boolean | PARTIAL |
| 6 | physical inner diameter/bore | mm | PASS |

The logical center is `Xi + LC/2`. A package is split into `p_div` equal
axial rigid-disk slices, conserving total mass, axial extent and centroid.

For a cylindrical annular disk, the historical/native inertia convention is

```text
Ip = m/8 * (De^2 + Di^2)
Id = 0.5*Ip + m*L^2/12
```

with SI geometry at the native boundary.

The producer-side unit/scale of historical `ump_crg` remains unproven.
ST41 has UMP disabled on all three mass rows, so this does not block the ST41
declared scope. It remains a blocker for a general UMP import claim.

## [Suporte]

One row represents one bearing housing/support and references a 1-based bearing
number.

The historical lateral axes are X/Z. RotorStudio's modern lateral domain uses
X/Y, therefore the import must perform a **coordinate-name mapping only**:

```text
legacy X -> RotorStudio X
legacy Z -> RotorStudio Y
```

Coefficient values and cross-coupling signs are not swapped or negated.

| Column | Native meaning | Unit |
|---:|---|---|
| 0 | bearing number | — |
| 1 | Kxx | N/m |
| 2 | Kzz | N/m |
| 3 | Kxz | N/m |
| 4 | Kzx | N/m |
| 5 | Cxx | N·s/m |
| 6 | Czz | N·s/m |
| 7 | Cxz | N·s/m |
| 8 | Czx | N·s/m |
| 9 | housing/support mass | kg |
| 10 | description/type | — |

The native reader requires support mass > 0 and rejects more than one support
for the same bearing.

## [Desbal]

For the legacy default force kind 0:

- column 0: axial position [mm];
- column 1: phase [degrees];
- column 2: mass-unbalance U [g·mm].

The solver boundary converts `g·mm -> kg·m` exactly once with factor
`1e-6`. Native synchronous force amplitude is proportional to
`U*omega^2`.

ST41 therefore preserves the two source values `110175.3 g·mm` without
rescaling them in persisted project metadata.

## [Respo]

- column 0: response position [mm];
- column 1: coordinate selector;
- column 2: orientation [degrees].

The native response solver rotates the complex X/Z response by the orientation
angle and then selects:

- coordinate 1: horizontal/X;
- coordinate 2: vertical/Z.

Positive response positions are physical mandatory FE stations. Negative
positions retain the historical support-reference convention; ST41 uses only
positive positions.

## ST41 sentinels

The source contract requires:

- 3 mass rows; total explicit mass = 10680 kg;
- package row: Xi=1370.9 mm, LC=1675 mm, mass=10090 kg, OD=1140 mm;
- 2 support rows; each mass=415 kg; Kxx=2.73e9 N/m; Kzz=3.41e9 N/m;
- 2 unbalance rows at 1370.9 and 3045.9 mm; each 110175.3 g·mm;
- 4 response rows: X/Z at 550 mm and X/Z at 3977 mm.

## Next gate

I2 may now implement the mass/inertia domain for ST41, but must keep numerical
readiness blocked until support dynamics, bearing range policy, unbalance/probe
materialization and the complete legacy numerical-parity gates are closed.
