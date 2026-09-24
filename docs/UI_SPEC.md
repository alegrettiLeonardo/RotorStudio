# Stage 2 Desktop UI Specification

## Authority and scope

This specification is derived from the three Stage 2 mockups supplied on 2026-09-24 and from the qualified Stage 1 public Python API at `STAGE2_BASE_HEAD=168f53047125b71ea2b5c5a0602ce7f0aa88bd20`.

Visual authority:
1. **Rotor Model mockup** — main window, Project Explorer, QGraphics-style rotor editor, element-property inspector, analysis-module launcher row, Messages & Results dock, status bar.
2. **Bearing Performance mockup** — bearing editor workspace, geometry/operating-condition form, central schematic, result table and plot region.
3. **Results Analysis mockup** — tabbed Campbell/root-locus/modes/orbits/FRF workspace, results-property inspector, summary table and export/report actions.

Numerical authority remains Stage 1:
`drm_core -> AnalysisService -> SolverFacade -> ctypes -> Fortran 2018 -> BLAS/LAPACK`.

The UI must never add a substitute rotor solver or change the qualified Stage 1 algorithms.

## Visual language

The desktop application uses a dense scientific/CAE layout matching the mockups:
- native Qt menu bar and toolbar;
- pale blue window/dock headers;
- white engineering canvas and plotting surfaces;
- blue selection/accent treatment;
- compact 10–11 pt desktop typography;
- thin neutral separators and dock borders;
- left Project Explorer, central workspace, right inspector, bottom Messages & Results;
- persistent dock sizes/visibility through `QSettings`.

Qt standard/theme icons or project-owned SVGs are used. No Dyrobes assets are copied.

## Main-window map

| Mockup component | Stage 1 capability | Stage 2 API/view-model | Qt implementation |
|---|---|---|---|
| Project / Model / Analysis / Bearings / Results / Tools / Help menus | project, analyses, reports, post-processing | `MainWindow` actions | `QMenuBar` |
| New / Open / Save | `RotorProject`, `save_project`, `load_project` | `ProjectSession` | `QToolBar` |
| Units selector | canonical SI + unit helpers | `UnitSystem` display adapter | `QComboBox` |
| Project Explorer | real `RotorProject` | `ProjectTreeModel` | `QTreeView` / `QAbstractItemModel` |
| Rotor Model editor | nodes, shafts, disks, bearings, seals/forces | scene items bound to domain IDs | `QGraphicsView/QGraphicsScene` |
| Element Properties | typed domain entities | selection-aware property editor | form widgets in `QDockWidget` |
| Analysis Modules | `AnalysisCase` + `AnalysisService` | case commands | push/tool buttons |
| Messages & Results | validation/execution diagnostics | structured application log | tabbed bottom dock |
| Status bar | project/model counts, units, job state | session/job state | `QStatusBar` |

## Project Explorer

The tree is a projection of the current `RotorProject`; it is not an independent data store.

Required groups:
- Model: Nodes, Shaft Elements, Disks, Bearings, Seals, Forces, Constraints, Rotor Definitions.
- Analysis: named persistent analysis cases, plus capability groups for Modal/Characteristic Roots, Campbell, Critical Speeds, Synchronous Response, Frequency Response, Foundation Excitation, Time Response, Run-up/Run-down, Coaxial Rotor and Asymmetric Rotor.
- Results: completed result records.

Selection identity is represented by a stable `EntityRef(kind, index/id)` shared by tree, canvas and inspector.

## Rotor Model editor

The geometric editor uses `QGraphicsScene`, not Matplotlib.

M1 renders:
- shaft line and stepped circular shaft outer/inner-diameter proportions;
- nodes and optional node numbers;
- disks;
- bearing/support symbols;
- rotation annotation;
- selected-element outline.

Tools: Select, Pan, Zoom In, Zoom Out, Fit View. Display toggles: node numbers, element numbers, bearings.

Later slices add force/seal/coaxial-specific graphics without changing the domain model.

## Property Inspector

M1 Shaft Element fields are mapped directly to `ShaftElement`:
- shaft type;
- node 1 / node 2;
- length (read-only, from node axial positions);
- outside diameter;
- inside diameter;
- Young modulus;
- shear modulus;
- density;
- damping factor;
- axial force;
- torque.

Edits create undoable commands and replace the frozen dataclass in `RotorModel.shafts`. No widget stores a second physical value.

Disk, bearing, seal, force and analysis-case editors are enabled only for properties represented by Stage 1.

Derived section properties (area, I, J, element mass) are not computed inside UI widgets. They remain hidden/read-only until exposed by a Core-side non-solver helper.

## Units

Internal/domain/Fortran values remain canonical SI.

M1 display system mirrors the mockup:
- length: mm;
- elastic moduli: MPa;
- density: kg/m³;
- force: N;
- torque: N·m;
- rotational speed: rpm.

All display↔canonical conversions call `drm_core.units`. Stage 2 may add backward-compatible unit helpers to that Core module; conversion constants are not duplicated through widgets.

Changing the display unit does not modify the model hash.

## Analysis cases and real Stage 1 mapping

| UI analysis | `AnalysisCase.kind` / API | Stage 1 result |
|---|---|---|
| Modal / characteristic roots | `modal` | `ModalResult` |
| Campbell / natural-frequency map | `modal_sweep` | list of `ModalResult` |
| Critical speeds | `critical_speeds` | `CriticalSpeedResult` |
| Synchronous response | `frequency_response` | `FrequencyResponseResult` |
| Auxiliary FRF | `auxiliary_frequency_response` | `FrequencyResponseResult` |
| Foundation FRF | `foundation_frequency_response` | `FrequencyResponseResult` |
| Foundation time response | `foundation_time_response` | `TransientResult` |
| Run-up / run-down | `runup` | `TransientResult` |
| Coaxial modal | `coaxial_modal` | `CoaxialModalResult` |
| Coaxial response | `coaxial_frequency_response` | `CoaxialFrequencyResponseResult` |
| Asymmetric modal | `asymmetric_modal` | `AsymmetricModalResult` |
| Asymmetric response | `asymmetric_frequency_response` | `AsymmetricFrequencyResponseResult` |
| Bearing coefficients | `bearing_matrices` | existing Fortran-backed bearing matrices |

## Modal / Campbell results workspace

The results mockup is implemented as central document tabs.

M1 Modal tab:
- modal frequency/damping table from `ModalResult`;
- selected mode/speed context;
- mode-shape plot from existing `drm_core.post.plot_mode`;
- orbit plot from existing `drm_core.post.plot_orbits`.

Campbell slice:
- speed vs natural frequency from the ordered Stage 1 modal sweep;
- integer excitation lines requested by the case;
- kappa-based FW/BW display only when kappa is present;
- critical-speed markers only from `CriticalSpeedResult` or explicit Stage 1 data.

No MAC/Hungarian/new branch tracking is introduced.

## Jobs and responsiveness

A dedicated `QThreadPool` with maximum thread count 1 executes `AnalysisService`.
States: QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED.

No synthetic progress percentage is shown. Cancellation is cooperative between safe calls only; a LAPACK call is never killed mid-call.

## Result staleness

Each stored result records the `analysis_hash` and model hash emitted by Stage 1.
When a model/case edit changes the current hash, the existing result remains visible and is marked **OUTDATED**. Re-run and delete actions are explicit.

## Bearing mockup capability boundary

Stage 1 supports:
- rigid short / pinned;
- rigid long / clamped;
- constant diagonal/full K/C variants;
- hydrodynamic short-width bearing;
- seal;
- coaxial coupling bearing type 20 where applicable.

The following controls visible in the conceptual bearing mockup are **not Stage 2 functional capabilities** unless later proven to exist in the frozen Core:
- tilting-pad bearing solver;
- floating-ring solver;
- gas-bearing solver;
- thrust-bearing solver;
- thermal bearing FEA;
- a new Reynolds solver;
- synthetic pressure/temperature/power-loss results.

They must be hidden or clearly disabled as `FUTURE / NOT AVAILABLE`, never populated with fictitious results.

## M1 vertical slice — Example_05_08_01

Acceptance chain:
1. start `drm-studio`;
2. create/open a project built from the existing `examples/chapter05/example_05_08_01.py` model;
3. draw the rotor in the QGraphics canvas;
4. select a shaft in canvas or tree and synchronize selection;
5. edit a sentinel diameter through the property inspector;
6. convert display units through `drm_core.units`;
7. validate before solver execution;
8. execute a `modal` case through `AnalysisService` on the worker pool;
9. call the real `SolverFacade -> Fortran` path;
10. display `ModalResult` frequencies/damping;
11. display mode shape and orbit from existing post-processing;
12. save project;
13. close/reopen;
14. confirm the same physical model;
15. recompute and compare the deterministic analysis contract.

M1 does not receive PASS if a mock solver is used for the end-to-end path.

## Intentional initial deviations from mockups

- The full Bearing Performance screen is deferred until its existing bearing contracts are mapped; unsupported BePerf concepts are not implemented.
- Calculated shaft section properties are deferred rather than duplicated in UI.
- No results are persisted in the Stage 1 project JSON because the current persistence contract stores model, analyses and metadata only.
- Constraints have no typed Stage 1 domain collection and therefore appear only as a disabled/zero-count group until a qualified non-numerical representation exists.
