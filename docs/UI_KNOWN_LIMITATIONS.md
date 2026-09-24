# Stage 2 known limitations

These are explicit scope boundaries, not hidden solver capabilities.

1. **No new bearing physics.** There is no new tilting-pad, floating-ring, gas-bearing, thrust-bearing, thermal-bearing FEA or Reynolds solver. The bearing editor exposes only Stage 1 types 1–8 and coaxial coupling type 20.
2. **No synthetic BePerf results.** Pressure distribution, thermal rise, power loss and other values visible in the conceptual bearing mockup are not shown unless a qualified Core result exists.
3. **No new Campbell mode tracking.** No MAC, Hungarian assignment or new branch tracker is introduced. The UI displays the Stage 1 modal-sweep ordering and kappa where available.
4. **Cancellation is deliberately conservative.** Queued jobs can be removed before solver start. `modal_sweep` can cancel between its Python-level speed points. Monolithic FRF, critical-speed, transient, run-up, coaxial and asymmetric Fortran/LAPACK calls are not killed mid-call; a request is shown as CANCELLING and the call is allowed to return safely, after which its real result is retained.
5. **Project JSON does not persist numerical Result objects.** The existing Stage 1 persistence contract stores the physical model, analysis cases and metadata. In-memory results remain viewable and stale-aware during a session, but are not silently embedded in a second project format.
6. **Constraints have no independent typed Stage 1 collection.** The Project Explorer therefore does not invent editable constraint entities beyond what bearings/support contracts already represent.
7. **Derived shaft section properties are not recomputed by widgets.** Values such as A/I/J/element mass are only appropriate for display when exposed by a qualified Core helper; Stage 2 does not duplicate those calculations for presentation.
8. **Frozen Linux portability follows the runner/toolchain ABI.** The Linux ZIP is qualified by clean extraction on the declared Ubuntu runner. It is not claimed as a universal manylinux/AppImage binary.
