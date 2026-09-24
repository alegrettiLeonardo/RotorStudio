# Headless plot stubs for G14

The 83 book-problem scripts include legacy calls to `picrotor`, `plotcamp`, `plotmode`, and `plotresp`. G14 validates problem runtime and numerical solver behavior, not MATLAB figure rendering. These four plot-only functions therefore become no-ops only inside the G14 Octave runner.

No numerical V2 routine is stubbed, replaced, or reimplemented. All routines used to construct matrices, eigensystems, responses, critical speeds, coaxial results, asymmetric results, or transients resolve to the frozen `reference/matlab_v2` authority.
