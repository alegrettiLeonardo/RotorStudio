# Stage 2 UI Architecture

## Dependency rule

```text
drm_studio (PySide6)
        |
        v
drm_core (GUI independent)
        |
        v
AnalysisService -> SolverFacade -> ctypes -> Fortran 2018
```

`drm_core` must never import `PySide6`. CI includes an explicit dependency-boundary test.

## Package layout

```text
python/src/drm_studio/
  app.py
  main_window.py
  style.py
  application/
    session.py
    jobs.py
    selection.py
  commands/
    model_commands.py
  models/
    project_tree.py
  docks/
    project_explorer.py
    property_inspector.py
    messages.py
  widgets/
    rotor_view.py
    analysis_modules.py
  analysis_pages/
    modal_setup.py
  result_views/
    modal_view.py
  plotting/
  resources/
```

The exact tree may grow by vertical slice, but domain and numerical code remain outside `drm_studio`.

## ProjectSession

`ProjectSession` is the single application-level state holder:
- current `RotorProject`;
- optional project path;
- dirty flag;
- current display-unit configuration;
- selected `EntityRef`;
- result records and stale status;
- undo stack.

Qt widgets bind to signals from this session. They do not own cloned rotor entities.

## Selection

A selection controller publishes one `EntityRef`. Project tree, scene and property inspector update from the same identity in both directions.

## Editing

Domain entities are frozen dataclasses. Commands use `dataclasses.replace` and replace the entity in the corresponding `RotorModel` list. Every command:
1. validates the candidate domain value;
2. applies exactly one logical model mutation;
3. emits one model-changed event;
4. updates tree/scene/inspector;
5. marks previous analysis records stale when their model hash no longer matches.

`QUndoStack` owns undo/redo history.

## Execution

`SolverJobManager` owns a dedicated `QThreadPool(maxThreadCount=1)`. A worker calls only:
`AnalysisService.execute(project, case)`.

The worker returns `AnalysisExecution`; the GUI thread then updates result models/views. Errors are transferred as structured failure records and original tracebacks are retained in the Console.

## Validation

Before an analysis job is submitted, the application calls `drm_core.validation.model.validate_model` using the analysis family (stationary/coaxial/rotating). A validation failure blocks solver submission.

UI widgets may provide immediate range hints, but Core validation remains authoritative.

## Plotting

The geometric editor is native Qt graphics.

Scientific result plots embed existing Stage 1 Matplotlib post-processing via `FigureCanvasQTAgg`. A result view may format axes and annotations, but it may not assemble matrices or solve an analysis.

## Core changes permitted in Stage 2

The preferred numerical change count is zero. Backward-compatible, non-solver API additions are allowed only when needed by the UI, for example:
- unit conversion helpers;
- metadata enumeration;
- progress callbacks around safe outer loops.

Any `drm_core`, `SolverFacade` or Fortran change triggers proportional Stage 1 regression. No Stage 2 change may relax a Stage 1 numerical threshold.


## Cancellation boundary

Cancellation is an orchestration feature, not a numerical interruption mechanism. `SolverJobManager` has one worker thread and six terminal/transition states: QUEUED, RUNNING, CANCELLING, CANCELLED, COMPLETED and FAILED.

A queued `QRunnable` may be removed before execution. The only current cooperative running boundary is `modal_sweep`, whose existing Python outer loop checks a cancellation callback between complete calls to `run_modal`. No LAPACK or Fortran call is interrupted. Monolithic analyses acknowledge CANCELLING but finish their real call and retain the completed result.

## Result lifecycle

`ResultRecord` stores the source model hash. Model edits recompute stale state; if undo restores the original physical model hash the result becomes current again. Results may be viewed while stale, rerun or removed explicitly.

Exports consume result objects only:
- plots use `drm_core.post.export_figure`;
- CSV uses explicit real-valued result columns and `export_csv`;
- native numeric data uses `export_npz`;
- reports call `write_analysis_report`.

None of these paths calls a solver merely because the user changes visualization or exports data.

## Frozen application

The PyInstaller one-directory build packages `drm_studio`, `drm_core`, Qt plugins, Matplotlib, the qualified Fortran shared library and its required non-system runtime dependencies. Frozen startup resolves the bundled solver path. Qualification executes from a clean extracted directory with source/developer environment variables removed.
