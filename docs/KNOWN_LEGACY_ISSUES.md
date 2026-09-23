# Known legacy issues — preserved/gated in M2

Execution-based classification against MATLAB is **BLOCKED** because neither MATLAB nor GNU Octave is installed. The following are therefore source-audit observations unless explicitly described as an ABI guard.

- `shftasym.m`: the defaulting condition for `AxialForce` appears inconsistent with the function argument count; the nonzero axial-force branch writes into `Kre`, which is not defined in that routine. M2 preserves the executable zero-axial source equations, and any nonzero axial force returns `RD_ERR_LEGACY_DEFECT (40)` instead of inventing a formula. This is a gate, not a silent correction.
- `shftasym.m`: the source constructs `Cs` and then overwrites it with a scaled `Ms` expression. The translated element keeps the V2 expression pending an authoritative MATLAB behavior test.
- `bearasym.m`: suspected `K1b1` indexing issue remains unmodified because rotating-frame bearing assembly is not yet migrated.
- `chr_asym.m`: numerical path can depend on `nargout`; rotating-frame implementation remains NOT_EXECUTED.
- `time_fdn.m` / `freq_fdn.m`: the bearing-selection condition `type > 2 | type < 9` appears true for nearly every numeric bearing type. No silent correction has been made.
- `runup.m`: source mixes explicitly defined `jot` with implicit MATLAB `j`. No silent correction has been made.
- `bearmtx.m` type 7 at exactly zero speed enters source expressions containing division by speed. The C ABI returns `RD_ERR_INPUT` for that undefined point rather than returning NaN/Inf. This is documented as an ABI safety guard and is **not** claimed MATLAB-equivalent.

Required future classification remains: minimal MATLAB case -> execute -> classify `LEGACY_BEHAVIOR`, `LEGACY_DEFECT`, `DOCUMENTATION_MISMATCH` or `LEGACY_DEFECT_FIXED` -> preserve/fix only with regression evidence.
