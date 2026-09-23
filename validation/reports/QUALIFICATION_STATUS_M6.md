# Qualification status — Stage 1 M6

| Gate | Status | M6 evidence |
|---|---|---|
| G1 source integrity | PASS | M5 authority tree retained |
| G2 Fortran Release build | PASS | 5/5 CTest |
| G3 Fortran Debug build | PASS | 5/5 CTest |
| G4 Python package tests | PASS | 51/51 pytest |
| G5 element matrices | BLOCKED | formal MATLAB exporter + qualification ABI ready; authority output unavailable |
| G6 global M/C/G/K | BLOCKED | formal comparator ready; authority output unavailable |
| G7 modal equivalence | BLOCKED | eig/frequency/MAC/kappa comparator ready; authority output unavailable |
| G8 harmonic response | BLOCKED | freq_rsp/freq_aux/freq_fdn comparator ready; authority output unavailable |
| G9 critical speeds | BLOCKED | direct + iterative comparator ready; authority output unavailable |
| G10 transient overall | BLOCKED | M5 implementation/source-oracle PASS; MATLAB tolerance freeze blocked |
| G11 coaxial | BLOCKED | formal eig/MAC/response comparator ready; authority output unavailable |
| G12 asymmetric rotor | BLOCKED | formal nargout/eig/MAC/response comparator ready; authority output unavailable |
| G13 22 examples | PASS | 33/33 campaign runs, 22 unique examples |
| G14 book problem regression | NOT_EXECUTED | downstream |
| G15 Python↔Fortran ABI | PASS | all M5 paths plus element qualification ABI exercised |
| G16 Linux execution | PASS | Release/Debug/pytest/campaign |
| G17 Windows execution | BLOCKED | unavailable |
| G18 clean package validation | PASS | exact M6 ZIP rebuilt/tested: 5/5 CTest, 51/51 pytest, 33/33 campaign; formal status correctly BLOCKED |
