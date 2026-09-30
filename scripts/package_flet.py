"""Build an onedir Flet distribution on the target OS, including native solvers."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_dependencies(libraries):
    found = {}
    if os.name == 'nt':
        roots = [Path(p) for k in ('DRMROTOR_DLL_DIRS', 'DRMBEARINGS_DLL_DIRS', 'UCRT64_BIN')
                 for p in os.environ.get(k, '').split(os.pathsep) if p]
        patterns = ('libgfortran*.dll', 'libquadmath*.dll', 'libgcc_s*.dll',
                    'libwinpthread*.dll', 'libopenblas*.dll', 'libblas*.dll',
                    'liblapack*.dll', 'libgomp*.dll')
        for root in roots:
            for pattern in patterns:
                for p in root.glob(pattern):
                    found[p.name.lower()] = p
    else:
        for library in libraries:
            output = subprocess.check_output(['ldd', str(library)], text=True)
            if 'not found' in output:
                raise RuntimeError(output)
            for line in output.splitlines():
                if '=>' not in line:
                    continue
                name, rest = line.split('=>', 1)
                p = Path(rest.strip().split()[0])
                if p.is_file() and any(k in name for k in ('gfortran', 'quadmath', 'blas', 'lapack', 'libgcc_s', 'libgomp')):
                    found[p.name] = p
    if not found:
        raise RuntimeError('Native runtime dependencies were not identified; refusing incomplete bundle.')
    return list(found.values())


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--solver', type=Path, required=True)
    a.add_argument('--bearing-solver', type=Path, required=True)
    a.add_argument('--out', type=Path, default=ROOT/'dist/flet')
    a.add_argument('--work', type=Path, default=ROOT/'build-flet-package')
    a.add_argument('--client-archive', type=Path)
    a.add_argument('--source-head', required=True)
    args = a.parse_args()
    if sys.platform not in ('linux', 'win32'):
        a.error('The declared distribution targets are Linux x86-64 and Windows x86-64.')
    import flet_desktop
    import importlib.metadata as md
    if md.version('flet') != '1.0.0' or md.version('flet-desktop') != '1.0.0':
        raise RuntimeError('This qualification requires the pinned Flet 1.0.0 runtime.')
    libraries = [args.solver.resolve(), args.bearing_solver.resolve()]
    if not all(p.is_file() for p in libraries):
        a.error('Both compiled native libraries must exist.')
    out, work = args.out.resolve(), args.work.resolve()
    out.mkdir(parents=True, exist_ok=True); work.mkdir(parents=True, exist_ok=True)
    filename = flet_desktop.get_artifact_filename()
    client = args.client_archive.resolve() if args.client_archive else work/filename
    if not client.is_file():
        urllib.request.urlretrieve('https://github.com/flet-dev/flet/releases/download/v1.0.0/'+filename, client)
    staging = work/'client'; staging.mkdir(exist_ok=True)
    shutil.copy2(client, staging/filename)
    name = 'RotorStudioFlet'
    cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
           '--name', name, '--distpath', str(out), '--workpath', str(work/'pyinstaller'),
           '--specpath', str(work), '--paths', str(ROOT/'python/src'), '--paths', str(ROOT),
           '--hidden-import', 'scripts.flet_all_screens_smoke',
           '--hidden-import', 'scripts.flet_screen_cases',
           '--collect-all', 'flet', '--collect-all', 'flet_desktop', '--collect-all', 'flet_web',
           '--collect-submodules', 'drm_flet', '--collect-submodules', 'drm_core',
           '--copy-metadata', 'flet', '--copy-metadata', 'flet-desktop', '--copy-metadata', 'flet-web',
           '--exclude-module', 'PySide6', '--exclude-module', 'PyQt5', '--exclude-module', 'drm_studio',
           '--add-data', str(staging)+os.pathsep+'flet_desktop/app']
    native = libraries + native_dependencies(libraries)
    for p in native:
        cmd += ['--add-binary', str(p)+os.pathsep+'native']
    cmd += [str(ROOT/'scripts/flet_entry.py')]
    subprocess.run(cmd, check=True, cwd=ROOT)
    bundle = out/name
    manifest = {'schema': 1, 'source_head': args.source_head, 'platform': sys.platform,
                'flet': md.version('flet'), 'pyinstaller': md.version('pyinstaller'),
                'client': {'name': filename, 'sha256': digest(client)},
                'native': {p.name: digest(p) for p in native},
                'files': {str(p.relative_to(bundle)).replace('\\', '/'): digest(p)
                          for p in sorted(bundle.rglob('*')) if p.is_file()}}
    (bundle/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    archive = shutil.make_archive(str(out/(name+'-'+sys.platform+'-'+args.source_head[:12])),
                                  'zip' if os.name == 'nt' else 'gztar', root_dir=out, base_dir=name)
    result = {'source_head': args.source_head, 'archive': Path(archive).name,
              'sha256': digest(archive), 'bytes': Path(archive).stat().st_size,
              'status': 'BUILT_NOT_YET_QUALIFIED'}
    (out/'PACKAGE.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
