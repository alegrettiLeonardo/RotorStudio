# M7 authority integrity audit — G1 reopening and correction

Date: 2026-09-24

## Scope

This audit reopens G1 after a clean Windows checkout of `main@3c3837c7856ffd8c9517aa9eb709580f28c0b7b2` reported 16 of 19 required MATLAB authority sources with canonical-LF SHA256 mismatches.

No Fortran numerical physics, formal thresholds, or authority hashes were changed to obtain PASS.

## Authority provenance

The authoritative archive supplied for this audit is:

- file: `Rotor_Software_v2.zip`
- SHA256: `bc42d18020013a537da6e7785a3d6b15533cd881939410c5e2a58c8563db5344`
- archive contents: 28 real `.m` sources after excluding AppleDouble `__MACOSX/._*.m` entries

The archive SHA256 was recomputed directly from the supplied ZIP during this audit and matches the value already frozen in `authority_source_manifest.json`.

The manifest's required-source hashes are SHA256 values after canonicalizing CRLF/CR to LF. The checked examples below match the supplied ZIP exactly under that rule:

- `bearmtx.m`: `89becb4738ac30b39c0b07783d209d2ae21277f3655c029d313abae77ae19a50`
- `chr_root.m`: `ab4ecb954dc552e7b8a95fb2dcc021ee38f5c032fae31045bc36de39b24b1482`
- `crit_spd.m`: `6b2a2eeeb0abaaf2fbfe146f055b257ef6199379d341230f321de4fddf8a53bb`
- `runup.m`: `81ad102dcc7e1cdd14d3d15b8f2c612449151918b05574fadfe1d24ce0cb2117`
- `shftasym.m`: `6d766e90cc091dbb8d84dace86ea7fdceb39e728be9f093a017ffaa5ea47fdd2`
- `time_fdn.m`: `fa3eebfa55ca4219191346ac8dc0534f98310169bc01d239a75739f0489bbc4c`

Therefore the manifest was not corrected to match the repository. The repository sources were corrected to match the authority.

## Root cause 1 — incorrect MATLAB files were committed during M7

The M7 branch history contains commits named as authority-source restoration, but multiple restored files were compact/minified source variants rather than the byte-equivalent files from the authoritative ZIP.

For example, commit `325e3d8828f5d0430a15bcd1354a3a1729e9c4a6` ("m7: restore V2 authority source crit_spd.m") added the compact source that later appears in `main`; its canonical-LF content does not match the authoritative ZIP hash.

At `main@3c3837c...`, 16 required files therefore differed from the ZIP authority. The three sources that happened to match were `bearasym.m`, `freq_fdn.m`, and `whirl.m`.

This was a source-provenance defect, not a Windows line-ending defect.

## Root cause 2 — the M7 CI masked verifier failure

GitHub Actions run #8 / ID `35982543106` checked out PR #6 merge ref `f4364c2be8baa3f00fb5290b1f0d4952c60fc850`.

Its Linux Release job log explicitly printed:

```text
"required_source_count": 19,
"overall": "FAIL",
```

but the workflow step was written as:

```bash
python validation/equivalence/verify_authority_sources.py | tee ...
```

without `set -o pipefail`. The verifier exited nonzero, while `tee` exited zero, so GitHub marked the step and job successful. The formal Octave job used the same vulnerable pipeline.

Thus the earlier M7 CI success was a false-positive for G1/G19. It did not demonstrate source integrity.

## Correction branch

Correction branch:

`fix/m7-authority-integrity-windows-g17`

PR:

`#8 — G17 Windows qualification: authority integrity and DLL loader hardening`

The branch restores the 19 required numerical authority files to the content represented by the existing manifest and adds `.gitattributes` so those authority files remain LF-stable across platforms.

GitHub Actions run #16 / ID `35992129380` on PR #8 explicitly printed `"overall": "PASS"` and listed all 19 required files as PASS in both Linux Release and formal Octave jobs.

The workflow has additionally been hardened so piped qualification commands use `set -o pipefail`; a future verifier failure can no longer be hidden by `tee`.

## Gate interpretation

- G1 on `main@3c3837c...`: **FAIL**
- G19 historical M7 claim on run #8: **REOPENED / INVALID AS G1 EVIDENCE**
- G1 on the correction branch after exact source restoration: **PASS on Linux CI**
- Windows G1: independently observed PASS on the correction branch; final G17 remains gated by the complete Windows Release/Python/examples/Debug/ABI sequence.
- G5–G12 numerical thresholds and previously qualified Fortran physics are unchanged.

Do not merge the correction branch until G17 is fully closed and the hardened CI is green.
