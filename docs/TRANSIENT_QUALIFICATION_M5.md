# Transient qualification — Stage 1 M5

## Qualification layers

### 1. Source integrity
V2 `time_fdn.m`, `runup.m` and the corresponding book examples are SHA256-frozen.

### 2. Fortran primitive tests
CTest `transient_dp45_reduction` verifies the DP5(4) integrator against an analytic undamped oscillator at `pi/2`, plus `DGGEV` modal truncation on a known diagonal `(K,M)` system.

### 3. Independent source-derived oracle
The production result is compared to an independent implementation using `scipy.linalg.eig(K,M)` and `solve_ivp(method="DOP853")` at `rtol=2e-11`, `atol=2e-13`.

Canonical 10-mode `time_fdn`:
```text
max absolute response difference = 2.9704856645187266e-09 m
reference peak response          = 1.8667050378352941e-03 m
max difference / reference peak  = 1.5912988952788282e-06
```

Canonical 4-mode `runup`, 0–3 s:
```text
max absolute response difference = 2.5818612682916922e-11 m
reference peak response          = 1.9511129405022653e-04 m
max difference / reference peak  = 1.3232761746877946e-07
```

These are **source-derived qualification results**, not MATLAB-equivalence results.

### 4. Supplied book examples
`Example_06_05_01` case (b): full model `dt=0.00006,npts=65536,nr=0`; reduced `dt=0.001,npts=16384,nr=10`; PASS.

`Example_06_11_01`: case 1 `alpha=[0.05*2*pi,8*pi,0],tspan=[0,70],nr=4`; case 2 `alpha=[0.20*2*pi,8*pi,0],tspan=[0,20],nr=4`; PASS for both.

## MATLAB gate
```text
MATLAB_ODE45_BASELINE = BLOCKED
G10_TRANSIENT_OVERALL = BLOCKED
G10a_IMPLEMENTATION   = PASS
G10b_SOURCE_ORACLE    = PASS
G10c_MATLAB_EQUIV     = BLOCKED
```

The authoritative transient tolerance will be defined only against real MATLAB `ode45` output once MATLAB/Octave can be executed.
