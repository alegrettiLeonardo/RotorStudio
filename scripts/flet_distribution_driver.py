"""Drive the real client, real FilePicker dialogs and clean extracted executables.

This does not claim manual usability review, pixel equality or physical-machine validation.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import traceback


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def clean_environment(home):
    home.mkdir(parents=True, exist_ok=True)
    keep = ('SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP',
            'DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS', 'LANG', 'LC_ALL')
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env.update(HOME=str(home), USERPROFILE=str(home), MPLBACKEND='Agg',
               LIBGL_ALWAYS_SOFTWARE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    if os.name == 'nt':
        system = Path(os.environ['SYSTEMROOT'])
        env['PATH'] = os.pathsep.join([str(system/'System32'), str(system), str(system/'System32/Wbem')])
        env['APPDATA'] = str(home/'AppData/Roaming'); env['LOCALAPPDATA'] = str(home/'AppData/Local')
    else:
        env['PATH'] = '/usr/bin:/bin'
    return env


def dialog_title(title):
    if os.name == 'nt':
        import ctypes
        user = ctypes.windll.user32
        found = []
        callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def visit(hwnd, _):
            if not user.IsWindowVisible(hwnd):
                return True
            b = ctypes.create_unicode_buffer(512); user.GetWindowTextW(hwnd, b, 512)
            if title in b.value:
                found.append(hwnd)
            return True
        user.EnumWindows(callback(visit), 0)
        if not found:
            return None
        user.SetForegroundWindow(found[-1]); return str(found[-1])
    result = subprocess.run(['xdotool', 'search', '--onlyvisible', '--name', '^'+title+'$'], capture_output=True, text=True)
    if result.returncode or not result.stdout.strip():
        return None
    hwnd = result.stdout.split()[-1]
    subprocess.run(['xdotool', 'windowactivate', '--sync', hwnd], check=True)
    return hwnd


async def drive(args):
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    report_path = out/'all_screens_smoke.json'
    if report_path.exists():
        raise RuntimeError('Evidence directory is not fresh; use a new output directory.')
    command = args.command
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        raise ValueError('An executable command is required after --.')
    command[0] = shutil.which(command[0]) or str(Path(command[0]).resolve())
    env = clean_environment(out/'clean_home') if args.clean else os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    cwd = out/'launch_cwd'; cwd.mkdir()
    if args.clean:
        manifest_path=Path(command[0]).parent/'PACKAGE_MANIFEST.json'
        package=read_json(manifest_path)
        if package.get('source_head') != args.source_head:
            raise RuntimeError('Extracted package does not match the requested source HEAD.')
        probe = subprocess.run(command+['--check'], env=env, cwd=cwd, text=True, capture_output=True, timeout=60)
        (out/'clean_check.stdout').write_text(probe.stdout, encoding='utf-8')
        (out/'clean_check.stderr').write_text(probe.stderr, encoding='utf-8')
        if probe.returncode:
            raise RuntimeError('Clean executable --check failed: '+probe.stderr)
        loaded = json.loads(probe.stdout)
        if not loaded.get('frozen') or not Path(loaded['rotor_library']).resolve().is_relative_to(Path(command[0]).parent):
            raise RuntimeError('Clean probe did not load a native library from the extracted bundle.')
    command += ['--qualification-all-screens', str(out)]
    if args.file_dialogs:
        command += ['--qualification-file-dialogs']
    url = None
    if args.mode == 'web':
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]
        command += ['--web', '--port', str(port)]
        env['FLET_FORCE_WEB_SERVER'] = 'true'
        url = f'http://127.0.0.1:{port}'
    log = (out/'process.log').open('w', encoding='utf-8')
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env,
                               cwd=cwd if args.clean else Path.cwd())
    browser = None; playwright = None; download_tasks = []; driver_checks = []
    js_errors = []; seen = set(); dialog_wait = None; deadline = time.monotonic()+args.timeout
    try:
        if url:
            from playwright.async_api import async_playwright
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True,
                        executable_path=os.environ.get('BROWSER_EXECUTABLE') or None,
                        args=['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
            context = await browser.new_context(viewport={'width': 1800, 'height': 1120}, accept_downloads=True)
            page = await context.new_page()
            page.on('pageerror', lambda e: js_errors.append(str(e)))
            async def downloaded(download):
                await download.save_as(out/('download_'+download.suggested_filename))
            page.on('download', lambda d: download_tasks.append(asyncio.create_task(downloaded(d))))
            async def choose(chooser):
                await chooser.set_files(str(out/'upload_project.json'))
            page.on('filechooser', lambda c: asyncio.create_task(choose(c)))
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('Server exited before the browser connected.')
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=3000)
                    break
                except Exception as exc:
                    if 'ERR_BLOCKED_BY_ADMINISTRATOR' in str(exc):
                        raise RuntimeError('Browser navigation blocked by administrator policy; not retried.') from exc
                    # Retry only the initial server connection while it is starting.
                    if 'ERR_CONNECTION_REFUSED' not in str(exc):
                        raise
                    await asyncio.sleep(.5)
        while time.monotonic() < deadline:
            report = read_json(report_path)
            if report.get('status') in ('FAIL', 'PASS'):
                break
            if process.poll() is not None:
                raise RuntimeError('Client exited before a fresh explicit result.')
            if args.file_dialogs and not url:
                stage = read_json(out/'file_dialog.json')
                action = stage.get('action')
                if action and action not in seen:
                    title = 'Abrir projeto RotorStudio' if action == 'open_project' else 'Salvar arquivo'
                    if dialog_wait is None or dialog_wait[0] != action:
                        dialog_wait = (action, time.monotonic())
                    hwnd = dialog_title(title)
                    if hwnd:
                        import pyautogui
                        await asyncio.sleep(.5)
                        pyautogui.screenshot().save(out/('os_dialog_'+action+'.png'))
                        pyautogui.hotkey('alt', 'n') if os.name == 'nt' else pyautogui.hotkey('ctrl', 'l')
                        await asyncio.sleep(.3)
                        pyautogui.hotkey('ctrl', 'a')
                        pyautogui.write(stage['destination'], interval=.01); pyautogui.press('enter')
                        seen.add(action); driver_checks.append('real_os_dialog_'+action)
                    elif time.monotonic()-dialog_wait[1] > 40:
                        raise TimeoutError('Native file dialog not found: '+title)
            await asyncio.sleep(.2)
        else:
            raise TimeoutError('Client qualification timeout.')
        if report.get('status') != 'PASS' or report.get('sessions_started') != 1:
            raise RuntimeError('Client failed: '+str(report.get('error', report)))
        if len(report.get('checks', [])) < 131 or len(report.get('screenshots', {})) < 199:
            raise RuntimeError('Incomplete screen or check coverage.')
        if args.clean and not report.get('frozen_executable_test'):
            raise RuntimeError('An unfrozen process cannot qualify the frozen package.')
        if url:
            await page.screenshot(path=str(out/'browser_final.png'))
            if download_tasks:
                await asyncio.gather(*download_tasks)
            if args.file_dialogs:
                saved = out/'download_rotor_project.json'
                if saved.read_bytes() != (out/'upload_project.json').read_bytes():
                    raise AssertionError('Browser project download differs from the saved input.')
                if (out/'download_dialog_export.csv').read_bytes() != b'node;value\n1;123.456\n':
                    raise AssertionError('Browser CSV download differs.')
                driver_checks += ['real_browser_file_upload', 'real_browser_project_download', 'real_browser_csv_download']
            if js_errors:
                raise RuntimeError('Browser JavaScript errors: '+repr(js_errors))
        elif args.file_dialogs and seen != {'save_project', 'open_project', 'export'}:
            raise RuntimeError('Not all OS file dialogs were exercised.')
        if not url:
            exit_code = await asyncio.to_thread(process.wait, 25)
            if exit_code:
                raise RuntimeError(f'Client process exited with {exit_code}.')
        payload = {'status': 'PASS', 'mode': args.mode, 'clean_extraction': args.clean,
                   'source_head': args.source_head, 'run_id': report['run_id'],
                   'checks': driver_checks, 'client_checks': len(report['checks']),
                   'screenshots': len(report['screenshots']), 'javascript_errors': js_errors,
                   'file_dialogs': args.file_dialogs, 'clean_path': env.get('PATH'),
                   'client_report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest()}
        (out/'DISTRIBUTION_RESULT.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
        print(json.dumps(payload, indent=2))
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
        if process.poll() is None:
            process.terminate()
            try:
                await asyncio.to_thread(process.wait, 20)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
        log.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--mode', choices=['desktop', 'web'], default='desktop')
    p.add_argument('--clean', action='store_true')
    p.add_argument('--file-dialogs', action='store_true')
    p.add_argument('--source-head', default='LOCAL_UNPUBLISHED')
    p.add_argument('--timeout', type=int, default=900)
    p.add_argument('command', nargs=argparse.REMAINDER)
    args = p.parse_args()
    try:
        asyncio.run(drive(args))
    except BaseException as exc:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out/'DISTRIBUTION_RESULT.json').write_text(json.dumps({
            'status': 'FAIL', 'error': str(exc), 'traceback': traceback.format_exc(),
            'source_head': args.source_head}, indent=2), encoding='utf-8')
        raise


if __name__ == '__main__':
    main()
