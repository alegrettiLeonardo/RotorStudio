from pathlib import Path
import os
import sys

from drm_core.solver import ffi


class _Handle:
    def __init__(self, path):
        self.path = path


def test_prepare_windows_dll_search_registers_library_explicit_and_path_dirs(
    tmp_path, monkeypatch
):
    lib_dir = tmp_path / "lib"
    explicit_dir = tmp_path / "explicit"
    path_dir = tmp_path / "path"
    for directory in (lib_dir, explicit_dir, path_dir):
        directory.mkdir()

    dll = lib_dir / "libdrmrotor.dll"
    dll.write_bytes(b"")

    seen = []

    def fake_add_dll_directory(path):
        seen.append(os.path.normcase(str(Path(path).resolve())))
        return _Handle(path)

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "add_dll_directory", fake_add_dll_directory, raising=False)
    monkeypatch.setenv("DRMROTOR_DLL_DIRS", str(explicit_dir))
    monkeypatch.setenv("PATH", str(path_dir))

    ffi._dll_directory_handles.clear()
    ffi._dll_directory_paths.clear()

    ffi._prepare_windows_dll_search(dll)

    expected = {
        os.path.normcase(str(lib_dir.resolve())),
        os.path.normcase(str(explicit_dir.resolve())),
        os.path.normcase(str(path_dir.resolve())),
    }
    assert set(seen) == expected
    assert ffi._dll_directory_paths == expected
    assert len(ffi._dll_directory_handles) == 3

    # Re-registering the same paths must not duplicate AddDllDirectory handles.
    ffi._prepare_windows_dll_search(dll)
    assert len(seen) == 3
    assert len(ffi._dll_directory_handles) == 3


def test_prepare_windows_dll_search_skips_inaccessible_path_entries(
    tmp_path, monkeypatch
):
    lib_dir = tmp_path / "lib"
    good_dir = tmp_path / "good"
    denied_dir = tmp_path / "denied"
    for directory in (lib_dir, good_dir, denied_dir):
        directory.mkdir()

    dll = lib_dir / "libdrmrotor.dll"
    dll.write_bytes(b"")

    seen = []

    def fake_add_dll_directory(path):
        seen.append(os.path.normcase(str(Path(path).resolve())))
        return _Handle(path)

    original_is_dir = Path.is_dir

    def fake_is_dir(self):
        if os.path.normcase(str(self.resolve())) == os.path.normcase(
            str(denied_dir.resolve())
        ):
            raise PermissionError("access denied")
        return original_is_dir(self)

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "add_dll_directory", fake_add_dll_directory, raising=False)
    monkeypatch.setattr(Path, "is_dir", fake_is_dir)
    monkeypatch.delenv("DRMROTOR_DLL_DIRS", raising=False)
    monkeypatch.setenv(
        "PATH",
        os.pathsep.join([str(denied_dir), str(good_dir)]),
    )

    ffi._dll_directory_handles.clear()
    ffi._dll_directory_paths.clear()

    ffi._prepare_windows_dll_search(dll)

    expected = {
        os.path.normcase(str(lib_dir.resolve())),
        os.path.normcase(str(good_dir.resolve())),
    }
    assert set(seen) == expected
    assert ffi._dll_directory_paths == expected
    assert len(ffi._dll_directory_handles) == 2
