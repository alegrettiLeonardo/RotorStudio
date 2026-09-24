# Stage 2 desktop packaging

## Toolchain

- Python 3.12
- PySide6 / Qt 6 from the `studio` extra
- PyInstaller 6.x from the `package` extra
- qualified Fortran 2018 shared library built by CMake
- BLAS/LAPACK runtime used by that library
- Matplotlib runtime/data collected by PyInstaller

The core-only install remains independent of PySide6; Qt is an optional package extra.

## Build command

Linux example:

```bash
python -m pip install -e './python[test,studio,ui-test,package]'
cmake -S fortran -B build-stage2-final -DCMAKE_BUILD_TYPE=Release
cmake --build build-stage2-final
python scripts/package_stage2.py \
  --solver build-stage2-final/libdrmrotor.so \
  --dist-dir dist/stage2 \
  --work-dir build-stage2-pyinstaller
```

Windows uses a real Windows runner and the same script after the UCRT64 Fortran build. `DRMROTOR_DLL_DIRS` / `UCRT64_BIN` identify dependent MinGW/OpenBLAS DLLs.

## Package content

The one-directory frozen application contains:
- Python runtime;
- drm_studio;
- drm_core;
- PySide6 and Qt plugins;
- Matplotlib and required data;
- `libdrmrotor.so` or `drmrotor.dll`;
- required non-system Fortran/BLAS runtime libraries detected at package time;
- `examples/Stage2_Smoke.rds`;
- `STAGE2_BUILD_MANIFEST.json`.

At frozen startup `drm_studio.app` resolves the bundled solver and, on Windows, registers its directory for dependent DLL lookup. No developer path is required.

## Artifacts

`scripts/package_stage2.py` produces:
- `RotorDynamicsStudio-linux-<12sha>.zip` on Linux;
- `RotorDynamicsStudio-win32-<12sha>.zip` on Windows;
- `PACKAGE_linux.json` / `PACKAGE_win32.json` with archive SHA256, size, solver SHA256 and bundled runtime inventory.

Exact names, sizes and hashes are final-workflow artifacts and must not be copied into this document by hand.

## Clean-install procedure

The final workflow:
1. creates a new runner-temporary directory;
2. extracts only the generated ZIP there;
3. removes `PYTHONPATH`, `DRMROTOR_LIB` and `DRMROTOR_DLL_DIRS`;
4. launches the frozen executable with its internal qualification mode;
5. opens the packaged example project;
6. runs a real modal analysis;
7. runs a real Campbell sweep;
8. exports PNG, SVG and PDF from the Campbell view;
9. saves the project;
10. closes the application window;
11. creates a new MainWindow and reopens the saved project;
12. recomputes modal analysis with the packaged Fortran library;
13. writes `PACKAGED_SMOKE.json` only after all checks pass.

A build finishing successfully is not sufficient for UI17/UI18/UI19.
