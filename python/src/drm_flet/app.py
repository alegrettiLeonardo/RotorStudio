"""Separate entry point; the existing drm-studio Qt application is untouched."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform


def resolve_library(explicit: Path | None = None, *, roots=None) -> Path | None:
    """Prefer an explicit path/environment; never replace a broken explicit path.

    Discovery is confined to conventional local build folders. It does not
    download binaries, select an unrelated installed solver, or compile code.
    """
    given = explicit or os.environ.get("DRMROTOR_LIB")
    if given:
        candidate = Path(given).expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"Biblioteca informada não existe: {candidate}")
        return candidate
    if roots is None:
        roots = [Path.cwd(), Path(__file__).resolve().parents[3]]
    names = ("libdrmrotor.so", "drmrotor.dll", "libdrmrotor.dll", "libdrmrotor.dylib")
    for root in roots:
        for directory in ("build-release", "build-flet", "build"):
            for subdir in (Path(directory), Path(directory) / "Release"):
                for name in names:
                    candidate = Path(root) / subdir / name
                    if candidate.is_file():
                        return candidate.resolve()
    return None


def configure_native(library: Path | None) -> None:
    if library is None:
        return
    os.environ["DRMROTOR_LIB"] = str(library)
    if not os.environ.get("DRMBEARINGS_LIB"):
        for name in ("libdrmbearings.so", "drmbearings.dll", "libdrmbearings.dll", "libdrmbearings.dylib"):
            bearing = library.parent / name
            if bearing.is_file():
                os.environ["DRMBEARINGS_LIB"] = str(bearing)
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="RotorStudio · interface Flet de engenharia")
    parser.add_argument("--project", type=Path, help="Projeto JSON do Core ou importação iRdin .txt")
    parser.add_argument("--library", type=Path, help="Biblioteca compartilhada do solver drmrotor existente")
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--web", action="store_true", help="Servidor local Python; não é Pyodide nem aplicação web estática")
    parser.add_argument("--port", type=int, default=8550)
    parser.add_argument("--check", action="store_true", help="Verificar carregamento do núcleo sem abrir a interface")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("A porta deve estar entre 1 e 65535.")
    try:
        library = resolve_library(args.library)
        configure_native(library)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.check:
        if library is None:
            parser.error("Solver não encontrado. Compile o núcleo ou informe --library / DRMROTOR_LIB.")
        from drm_core.solver.facade import SolverFacade
        facade = SolverFacade(str(library))
        print(json.dumps({"status": "LOADED", "python": platform.python_version(),
                          "rotor_library": str(library),
                          "bearing_library": os.environ.get("DRMBEARINGS_LIB"),
                          "note": "Carregamento, não qualificação numérica ou de executável congelado."}, indent=2))
        del facade
        return
    import flet as ft
    from .session import StudioSession
    from .ui import StudioApp

    # Resolve invalid project files before starting the desktop client.
    session = StudioSession()
    if args.project:
        try:
            session.open(args.project)
        except Exception as exc:
            parser.error(f"Não foi possível abrir {args.project}: {exc}")

    async def start(page):
        # A web client must receive an independent session, including undo/redo.
        instance = StudioSession(session.project)
        instance.path, instance.saved_hash = session.path, session.saved_hash
        if library is None:
            instance.log("AVISO", "Núcleo não encontrado: edição disponível; cálculos exigem a biblioteca Fortran.")
        StudioApp(page, instance, library_path=str(library) if library else None, dark=args.dark)

    ft.run(start, view=ft.AppView.WEB_BROWSER if args.web else ft.AppView.FLET_APP,
           host="127.0.0.1", port=args.port if args.web else 0, no_cdn=True)


if __name__ == "__main__":
    main()
