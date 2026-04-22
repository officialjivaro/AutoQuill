# AutoQuill.spec
# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path


# PyInstaller executes a spec file as Python code, but __file__ is not available here.
# Use the PyInstaller-provided SPEC global instead.
SPEC_FILE = Path(SPEC).resolve() if "SPEC" in globals() else (Path.cwd() / "AutoQuill.spec")

PROJECT_ROOT = SPEC_FILE.parent
MAIN_SCRIPT = PROJECT_ROOT / "AutoQuill.py"

APPDATA_DIR = PROJECT_ROOT / "appdata"
RESOURCES_DIR = APPDATA_DIR / "resources"
IMAGES_DIR = RESOURCES_DIR / "images"

ICON_ICO = IMAGES_DIR / "icon.ico"
ICON_PNG = IMAGES_DIR / "icon.png"

HOOKS_DIR = APPDATA_DIR / "hooks"


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label}: {path}")


def _collect_tree_as_datas(src_root: Path, dest_root: str) -> list[tuple[str, str]]:
    """
    Recursively collect files under src_root and map them into dest_root.

    Returns a list of (source_file, destination_dir) tuples for Analysis(datas=...).
    """
    root = Path(src_root)
    if not root.exists():
        return []

    datas: list[tuple[str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue

        rel_parent = path.parent.relative_to(root)
        if rel_parent == Path("."):
            dest_dir = dest_root
        else:
            dest_dir = os.path.join(dest_root, str(rel_parent))

        datas.append((str(path), dest_dir))

    return datas


def _dedup_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """
    Remove duplicate (src, dest) pairs while preserving order.
    """
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []

    for src, dest in pairs:
        key = (os.path.normcase(os.path.abspath(src)), dest)
        if key in seen:
            continue
        seen.add(key)
        out.append((src, dest))

    return out


_require_file(MAIN_SCRIPT, "entry script")
_require_file(ICON_ICO, "Windows icon (.ico)")

# Bundle project resources so one-file builds can still load them at runtime.
project_datas = _collect_tree_as_datas(RESOURCES_DIR, "appdata/resources")

# Keep the icon files explicit as well; dedupe handles duplicates cleanly.
for icon_path in (ICON_ICO, ICON_PNG):
    if icon_path.is_file():
        project_datas.append((str(icon_path), os.path.join("appdata", "resources", "images")))

datas = _dedup_pairs(project_datas)

# Keep the build lean:
# - let PyInstaller's built-in Qt hooks collect the required PySide6 pieces
# - explicitly exclude other Qt bindings if they exist in the build environment
qt_excludes = ["PyQt5", "PyQt6", "PySide2"]

hook_paths = [str(HOOKS_DIR)] if HOOKS_DIR.is_dir() else []

a = Analysis(
    [str(MAIN_SCRIPT)],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=hook_paths,
    hooksconfig={},
    runtime_hooks=[],
    excludes=qt_excludes,
    noarchive=False,
    optimize=1,
)

# Keep compatibility with current PyInstaller templates.
_pyz_args = [a.pure]
if hasattr(a, "zipped_data"):
    _pyz_args.append(a.zipped_data)
pyz = PYZ(*_pyz_args)

_exe_args = [pyz, a.scripts, a.binaries]
if hasattr(a, "zipfiles"):
    _exe_args.append(a.zipfiles)
_exe_args.append(a.datas)
_exe_args.append([])

exe = EXE(
    *_exe_args,
    name="AutoQuill",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_ICO),
)