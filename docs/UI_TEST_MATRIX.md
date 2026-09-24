# Stage 2 UI test matrix

The Stage 2 acceptance rule is evidence based. A page existing in the application is not a PASS. The authoritative aggregate is produced by `.github/workflows/stage2-final-qualification.yml` as `STAGE2_FINAL_QUALIFICATION.json`; individual rows below identify the concrete test path that must pass with the real Fortran library where numerical work is involved.

| Feature | GUI input | Domain | Units | Validation | Solver / result | GUI output | Save/reopen | Linux | Windows | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| Project open/save | MainWindow | RotorProject | canonical SI | loader/schema | N/A | model canvas/tree | yes | required | required | `test_ui_model_editing.py::test_project_save_reopen_preserves_physical_model` + packaged smoke |
| Shaft elements | Property Inspector | ShaftElement | mm/MPa ↔ SI | validate_model | modal consumers | QGraphics + inspector | yes | required | required | `test_ui_model_editing.py` sentinel 53.217 mm |
| Disks | Project Explorer / command | Disk | SI-domain | validate_model | existing Core | canvas/tree | yes | required | required | UI behavior suite; no new disk physics |
| Bearings | Bearing tab | Bearing | mm display for geometry, SI domain | bearing contracts | existing bearing matrices/analyses | type-sensitive table | yes | required | required | `test_ui_bearing_seal.py` |
| Seals | Bearing tab type 8 | Bearing type 8 / Seal contract | mm display geometry, SI domain | type-8 contract | existing Stage 1 seal path | type-sensitive table | yes | required | required | `test_ui_bearing_seal.py`; unsupported BePerf types absent |
| Modal | modal dialog | AnalysisCase | rpm → rad/s | stationary model validation | ModalResult / Fortran | table + mode/orbit | case persists | required | required | `test_ui_e2e_modal.py` |
| Campbell | Campbell dialog | modal_sweep | rpm → rad/s | stationary validation | ordered list[ModalResult] / Fortran | Campbell/root locus/modes/orbits | case persists | required | required | `test_ui_e2e_modal.py::test_campbell_workspace_uses_real_modal_sweep` |
| Critical speeds | setup dialog | critical_speeds | rpm display / rad/s result | Core validation | CriticalSpeedResult / Fortran | table | case persists | required | required | `test_ui_e2e_modal.py::test_critical_speed_workspace_uses_real_fortran` |
| Synchronous response | response dialog | frequency_response | rpm → rad/s | forcing type 1/2/3 required | FrequencyResponseResult / Fortran | response plot | case persists | required | required | `test_ui_e2e_responses.py::test_synchronous_response_e2e` |
| Auxiliary FRF | FRF dialog | auxiliary_frequency_response | Hz → rad/s | forcing type 6/7 required | FrequencyResponseResult / Fortran | amplitude/phase | case persists | required | required | `test_ui_e2e_responses.py::test_auxiliary_frequency_response_e2e` |
| Foundation FRF | foundation dialog | foundation_frequency_response | Hz → rad/s | forcing type 4 required | FrequencyResponseResult / Fortran | amplitude/phase | case persists | required | required | `test_ui_e2e_responses.py::test_foundation_frequency_and_time_response_e2e` |
| Foundation time | time dialog | foundation_time_response | SI time/rpm | forcing type 5 required | TransientResult / Fortran | time + FFT | case persists | required | required | same E2E response test |
| Run-up/down | run-up dialog | runup | SI/rpm display | constant-bearing solver contract | TransientResult / Fortran | time/speed + FFT | case persists | required | required | `test_ui_e2e_responses.py::test_runup_e2e` |
| Coaxial | rotor table + setup | RotorDefinition / AnalysisCase | rpm → rad/s; signed speed factor | coaxial coverage/type20 | Coaxial*Result / Fortran | eigen/response workspace | yes | required | required | `test_ui_special_rotors.py` |
| Asymmetric | setup | AsymmetricShaftElement / AnalysisCase | rpm → rad/s | rotating-frame restrictions | Asymmetric*Result / Fortran | eigen/response workspace | case persists | required | required | `test_ui_special_rotors.py` |
| Stale results | model edit/undo | ResultRecord model hash | unchanged | hash comparison | no recalculation | OUTDATED marker; rerun/delete | N/A | required | required | `test_ui_exports_reports.py::test_stale_then_undo_returns_result_to_current` |
| Exports | Results menu | Result object | explicit columns | type mapping | no solver rerun | PNG/SVG/PDF/CSV/NPZ | files | required | required | `test_ui_exports_reports.py::test_real_modal_exports_and_report` |
| Reports | Results menu | AnalysisExecution | canonical SI documented | N/A | existing write_analysis_report | JSON + Markdown | files | required | required | same export/report test |
| Cancellation | Analysis menu | AnalysisCase/job | N/A | safe-boundary policy | modal_sweep cooperative only | QUEUED/RUNNING/CANCELLING/CANCELLED/COMPLETED/FAILED | N/A | required | required | `test_ui_jobs.py` cases A/B/C |
| GUI independence | package boundary | drm_core | N/A | import scan | CLI/Core without Qt | N/A | N/A | required | required | `test_ui_core_boundary.py` |

## End-to-end map

The final workflow executes all of `python/tests_ui` with `DRMROTOR_LIB` pointing to a freshly built real Fortran library on both Linux and Windows. It rejects skipped real-Fortran tests.

- E2E-1 Modal: `test_ui_e2e_modal.py`.
- E2E-2 Campbell + critical speeds: `test_ui_e2e_modal.py`.
- E2E-3 Synchronous / auxiliary FRF: `test_ui_e2e_responses.py`.
- E2E-4 Foundation FRF + foundation transient: `test_ui_e2e_responses.py`.
- E2E-5 Run-up: `test_ui_e2e_responses.py`.
- E2E-6 Coaxial modal/response: `test_ui_special_rotors.py`.
- E2E-7 Asymmetric modal/response and rotating-frame rejection: `test_ui_special_rotors.py`.
- E2E-8 Bearing/seal editing + real modal after bearing edit: `test_ui_bearing_seal.py`.

The frozen-application smoke adds a second independent chain outside the source tree: packaged launch → packaged example → real modal → real Campbell → PNG/SVG/PDF export → save → close → reopen → real modal recompute.
