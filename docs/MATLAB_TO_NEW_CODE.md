# MATLAB V2 -> Stage 1 M2 mapping

| MATLAB V2 | New owner | M2 status |
|---|---|---|
| `shftelem.m` | `fortran/src/rd_shaft_circular.f90` | IMPLEMENTED; CTest/internal invariants executed; MATLAB equivalence BLOCKED |
| `taper.m` | `fortran/src/rd_shaft_tapered.f90` | IMPLEMENTED; types 21–28; constant-section axial=0 source relation tested; MATLAB equivalence BLOCKED |
| `shftasym.m` | `fortran/src/rd_shaft_asymmetric.f90` | ELEMENT IMPLEMENTED; types 11–18; V2 axial-force defect explicitly gated; rotating-frame integration NOT_EXECUTED |
| `rotormtx.m` | `rd_assembly_stationary.f90` | IMPLEMENTED for circular+tapered shafts and disks 1–4; MATLAB equivalence BLOCKED |
| `bearmtx.m` | `rd_bearings.f90` | IMPLEMENTED types 1–8 plus type-20 stationary no-op; MATLAB equivalence BLOCKED |
| `chr_root.m` | `rd_eigensystem.f90` + `rd_c_api.f90` | IMPLEMENTED stationary eigenvalues/eigenvectors/eccentricity; MATLAB equivalence BLOCKED |
| `freq_rsp.m` | `rd_frequency_response.f90` | IMPLEMENTED, including force types handled by V2 source; MATLAB equivalence BLOCKED |
| `crit_spd.m` | `rd_critical_speed.f90` | IMPLEMENTED direct, iterative-index, iterative-nearest; MATLAB equivalence BLOCKED |
| `whirl.m` | `drm_core/post/whirl.py` | IMPLEMENTED geometric post-processing |
| `picrotor.m`, `plotcamp.m` | Python headless post layer | initial implementation retained |
| `rotorasym.m`, `bearasym.m`, `chr_asym.m`, `freq_asym.m` | future Fortran rotating-frame modules | NOT_EXECUTED |
| `chr_root_coax.m`, `freq_rsp_coax.m` | future Fortran coaxial modules | NOT_EXECUTED |
| `freq_aux.m`, `freq_fdn.m` | future Fortran frequency-domain modules | NOT_EXECUTED |
| `time_fdn.m`, `runup.m` | future Fortran transient module | NOT_EXECUTED |
| `fftscale.m`, remaining plots | Python post-processing | NOT_EXECUTED |

Internal tests are evidence of implementation consistency only. They do not change any MATLAB-equivalence gate to PASS while MATLAB/Octave execution is unavailable.

## Example translations executed in M2

- `Example_05_08_01`: re-executed M1 milestone.
- `Example_06_03_01`: translated with deterministic `--case`; case 1 executed through `freq_rsp`.
- `Example_06_08_01`: translated with deterministic `--lh-case/--rh-case`; LH1/RH1 executed through modal/Campbell/critical-speed paths.

These examples are execution smoke evidence only until MATLAB/Octave reference output is generated.
