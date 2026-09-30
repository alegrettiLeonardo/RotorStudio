# iRdin / API 541 staged campaign

## Baseline

- campaign branch: `feature/irdin-api541-dynamics`
- starting promoted `main`: `d44ad24590f984e3f0655c427fcbf39be94a6da6`
- sentinel: `ST41_1000_B3_60HZ_1675_63536.txt`
- current implementation stage: **I0 — import/source authority**

This campaign is intentionally separate from B1. I0 does not add rotor physics,
remove numerical-readiness blockers, create API 541 analysis cases, or reinterpret
legacy fields whose original semantics have not yet been proven.

## I0 frozen-source contract

The ST41 source is stored with Git text normalization disabled because its
CP1252/CRLF bytes are part of the authority.

Expected source identity:

- SHA256: `b7f14fd34ccce55f2c00c3915725097c12eda9be4161b91ce7ee84c56530f0fc`
- bytes: `3688`
- source records: `171`
- assignments: `161`

Committed/generated authority:

- `authority/parsed_source.json` — ordered source record identity;
- `authority/field_inventory.json` — exactly one inventory entry per assignment;
- `authority/source_sha256.json` — byte identity;
- `i0_authority.py` — deterministic writer/verifier.

Verification:

```bash
python validation/irdin/i0_authority.py --verify
```

The verifier fails on source hash change, missing/duplicate inventory entries,
unparsed nonempty source lines, or any mismatch with regenerated authority.

## Production importer behavior in I0

I0 extends imported project metadata only:

- `source_sha256`;
- `source_size_bytes`;
- `legacy_irdin_raw`, containing every parsed section/key/value.

Save/reopen must preserve these values exactly. Existing shaft and inline-bearing
mappings remain unchanged. Distributed mass/package, concentrated mass and
flexible-support blockers remain fail-closed.

Inventory status means:

- `MAPPED`: the current importer already gives the field an explicit target;
- `PRESERVED_ONLY`: the raw value is retained, but I0 makes no numerical-physics claim.

`numerical_mapping` separately distinguishes `MODEL`, `METADATA`,
`SKETCH_ONLY`, and `NONE`.

## Staged continuation

The next gate is **I1 semantic authority**. Before implementing new physics,
original iRdin source/manual/results must establish the meaning and units of
`[Massas]`, `[Suporte]`, `[Desbal]`, and `[Respo]`.

Then:

I1 semantic authority → I2 mass/inertia → I3 flexible-support M/C/K →
I4 bearing range/envelope → I5 unbalance/probes/automatic cases →
legacy numerical parity → API 541 lateral dynamics → experimental correlation →
torsional extension.
