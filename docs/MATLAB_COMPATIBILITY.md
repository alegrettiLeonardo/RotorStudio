# MATLAB V2 compatibility contract

`Rotor_Software_v2` is the numerical and behavioral authority. The migration preserves DOF ordering, matrix ordering, signs, phases, SI values delivered to Fortran, zero-DOF treatment, FW/BW conventions and legacy output ordering.

Formal covered functions include `shftelem`, `taper`, `shftasym`, `rotormtx`, `rotorasym`, `bearmtx`, `bearasym`, `chr_root`, `chr_asym`, `chr_root_coax`, `crit_spd`, `freq_rsp`, `freq_aux`, `freq_fdn`, `freq_rsp_coax`, `freq_asym`, `time_fdn`, `runup` and `whirl`.

Manual/V2 mismatch: transient reduction uses V2 modal truncation `eig(K,M)`, not Guyan/static reduction.

Known V2 defects are characterized explicitly in `KNOWN_LEGACY_ISSUES.md`; they are not silently repaired in the translation. The offline qualification harness may associate modes for comparison, but production solver ordering is not replaced by Hungarian or new tracking logic.
