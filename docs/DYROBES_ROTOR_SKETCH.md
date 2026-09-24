# DyRoBeS Rotor Sketch in RotorStudio

## Scope

This change implements the **model sketch conventions** of DyRoBeS/iRdin in the
RotorStudio desktop application. It is a presentation and import-boundary feature;
it does not add or modify rotor-dynamics physics in the qualified Fortran core.

The implementation is based on the supplied DyRoBeS Rotor manual and on the real
iRdin fixture `EST-12735185-CRYOSTAR_V2.txt`.

## Reference conventions implemented

The sketch follows these engineering conventions:

- axial rotor topology is dominant and uses a compact radial scale;
- shaft sections are stepped/tapered along the spin axis;
- finite-element stations appear at section boundaries;
- distributed rotor masses/packages are cyan envelopes painted behind the shaft so
  the shaft remains visually continuous through the component;
- package center markers are retained for large active-stack masses;
- bearings are compact triangular supports labelled A, B, ...;
- unbalance locations are red circular/stem symbols labelled u1, u2, ...;
- response channels at a common axial station are grouped into a green Y/V probe
  symbol, e.g. r2/r1 and r4/r3;
- section/station numbering can be shown or hidden;
- the Stage 2.1 engineering sketch can be toggled with `DyRoBeS Sketch`.

The legacy cyan Stage 2.1 rotor drawing remains available by unchecking the sketch
toggle.

## iRdin import

RotorStudio now opens historical `*.txt` iRdin/VB6 files directly.

Import rules are deliberately conservative:

1. **Exact numerical shaft geometry**
   - `[Secoes]` length and diameter data are converted to SI RotorModel nodes and
     shaft elements.
   - E, density and Poisson ratio are preserved from `[Dados]`.
   - no geometric rescaling is performed.

2. **Engineering-sketch metadata**
   - `[Massas]`, `[Mancais]`, `[Desbal]`, `[Respo]`, `[Concent]` and
     `[Suporte]` are preserved in `RotorProject.metadata["sketch"]`.
   - inline `TABLE§...` bearing data are parsed into rpm + 8 K/C coefficients.

3. **Numerical safety gate**
   - current Stage 1 RotorStudio does not expose an equivalent qualified
     speed-dependent bearing-table contract;
   - distributed iRdin mass/package records are not silently approximated into a
     different DISK contract;
   - imported projects are therefore marked
     `BLOCKED_FOR_NUMERICAL_ANALYSIS` when those records exist;
   - both the UI and `AnalysisService.execute(RotorProject,...)` block solver
     execution before Fortran is called.

4. **Save safety**
   - opening an iRdin text file does not bind RotorStudio Save to the legacy source;
   - the first save is explicitly a RotorStudio `.rds`/JSON Save As.

## Real Cryostar qualification fixture

`examples/legacy/EST-12735185-CRYOSTAR_V2.txt`

Imported sketch inventory:

- 16 shaft sections;
- 17 stations;
- total shaft length: 2585.55 mm;
- 3 distributed masses/packages;
- 2 bearing stations;
- 2 speed-dependent bearing tables, 8 speed points each from 1000 to 4500 rpm;
- 2 unbalance locations;
- 4 response channels grouped into two probe stations;
- nominal speed 3600 rpm;
- 2 poles / 60 Hz;
- material: E = 207 GPa, density = 7850 kg/m3, Poisson = 0.3.

## Qualification

Workflow: `DyRoBeS Rotor Sketch Qualification`

Required gates:

- zero `fortran/` diff from the qualified main baseline;
- frozen Stage 1 suite remains exactly 57 tests and passes 57/57;
- complete desktop UI regression with real Fortran backend;
- iRdin importer tests use the real Cryostar fixture;
- visual scene tests verify shaft/mass/bearing/unbalance/probe entity counts;
- screenshot evidence:
  - `cryostar_rotorstudio.png`
  - `cryostar_dyrobes_sketch.png`

## Deliberate limitation

This change does **not** claim that the Cryostar iRdin project is numerically
equivalent to a complete RotorStudio Stage 1 model. The shaft geometry is exact;
legacy distributed-mass and speed-dependent bearing semantics are retained as
source data and visualized, but remain blocked from numerical execution until an
explicit qualified mapping is added.
