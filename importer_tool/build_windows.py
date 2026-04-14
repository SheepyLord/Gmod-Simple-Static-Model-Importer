from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


APP_NAME = "PMXStaticImporter"
THIS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
SEP = ";" if os.name == "nt" else ":"



def _find_first_existing(candidates: list[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None



def _find_tcl_tk_binaries(base_prefix: Path) -> list[tuple[Path, str]]:
    search_dirs = [
        base_prefix,
        base_prefix / "DLLs",
        base_prefix / "Library" / "bin",
    ]
    patterns = {
        "tcl": re.compile(r"^tcl\d+(?:t)?\.dll$", re.IGNORECASE),
        "tk": re.compile(r"^tk\d+(?:t)?\.dll$", re.IGNORECASE),
    }

    binaries: list[tuple[Path, str]] = []
    for key, pattern in patterns.items():
        matches: list[Path] = []
        for directory in search_dirs:
            if not directory.exists():
                continue
            for candidate in directory.glob(f"{key}*.dll"):
                if pattern.match(candidate.name):
                    matches.append(candidate)
        matches.sort(key=lambda path: (0 if path.parent.name.lower() == "dlls" else 1, len(path.name), path.name.lower()))
        if matches:
            binaries.append((matches[0], "."))
    return binaries



def _find_tcl_tk_data(base_prefix: Path) -> list[tuple[Path, str]]:
    candidates = [
        (base_prefix / "tcl" / "tcl8.6", "_tcl_data"),
        (base_prefix / "tcl" / "tcl8.7", "_tcl_data"),
        (base_prefix / "Library" / "lib" / "tcl8.6", "_tcl_data"),
        (base_prefix / "Library" / "lib" / "tcl8.7", "_tcl_data"),
        (base_prefix / "tcl" / "tk8.6", "_tk_data"),
        (base_prefix / "tcl" / "tk8.7", "_tk_data"),
        (base_prefix / "Library" / "lib" / "tk8.6", "_tk_data"),
        (base_prefix / "Library" / "lib" / "tk8.7", "_tk_data"),
    ]
    return [(path, dest) for path, dest in candidates if path.exists()]



def _dedupe_pairs(items: list[tuple[Path, str]]) -> list[tuple[Path, str]]:
    output: list[tuple[Path, str]] = []
    seen: set[tuple[str, str]] = set()
    for src, dest in items:
        key = (str(src.resolve()).lower(), dest.lower())
        if key in seen:
            continue
        seen.add(key)
        output.append((src, dest))
    return output



def _ensure_tk_assets_present(base_prefix: Path) -> tuple[list[tuple[Path, str]], list[tuple[Path, str]]]:
    binaries = _dedupe_pairs(_find_tcl_tk_binaries(base_prefix))
    datas = _dedupe_pairs(_find_tcl_tk_data(base_prefix))

    if len(binaries) < 2:
        raise SystemExit(
            "Could not find both Tcl/Tk DLLs in the active Python installation. "
            "Run `python -m tkinter` first to verify this Python build includes tkinter."
        )
    if len(datas) < 2:
        raise SystemExit(
            "Could not find both Tcl/Tk data directories in the active Python installation."
        )
    return binaries, datas



def _find_extra_dlls(base_prefix: Path) -> list[tuple[Path, str]]:
    """Find conda/system DLLs that PyInstaller fails to resolve automatically."""
    needed = [
        "libcrypto-3-x64.dll",
        "libssl-3-x64.dll",
        "libexpat.dll",
        "liblzma.dll",
        "libbz2.dll",
        "ffi-8.dll",
    ]
    search_dirs = [
        base_prefix / "Library" / "bin",
        base_prefix / "DLLs",
        base_prefix,
    ]
    binaries: list[tuple[Path, str]] = []
    seen: set[str] = set()
    for name in needed:
        for directory in search_dirs:
            candidate = directory / name
            if candidate.exists() and name.lower() not in seen:
                seen.add(name.lower())
                binaries.append((candidate, "."))
                break
    return binaries



def _find_7z_tool() -> list[tuple[Path, str]]:
    """Find 7z.exe (and 7z.dll) from a local 7-Zip installation to bundle."""
    candidates = []
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        pf = os.environ.get(env_var)
        if pf:
            candidates.append(Path(pf) / "7-Zip")

    for directory in candidates:
        exe = directory / "7z.exe"
        dll = directory / "7z.dll"
        if exe.is_file():
            result: list[tuple[Path, str]] = [(exe, ".")]
            if dll.is_file():
                result.append((dll, "."))
            return result
    return []



def _build_pyinstaller_args(onefile: bool, console: bool) -> list[str]:
    base_prefix = Path(sys.base_prefix).resolve()
    tk_binaries, tk_datas = _ensure_tk_assets_present(base_prefix)

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_NAME,
        "--runtime-hook",
        str(THIS_DIR / "pyi_rth_tk_paths.py"),
        "--hidden-import",
        "tkinter",
        "--hidden-import",
        "_tkinter",
        "--collect-submodules",
        "tkinter",
        "--collect-all",
        "PIL",
        "--hidden-import",
        "PIL.ImageTk",
        "--hidden-import",
        "trimesh",
        "--collect-submodules",
        "trimesh",
        "--hidden-import",
        "rarfile",
        "--exclude-module",
        "matplotlib",
        "--add-data",
        f"{(PROJECT_DIR / 'gmod_addon').resolve()}{SEP}gmod_addon",
    ]

    if onefile:
        args.append("--onefile")
    else:
        args.append("--onedir")

    args.append("--console" if console else "--windowed")

    for src, dest in tk_binaries:
        args.extend(["--add-binary", f"{src}{SEP}{dest}"])
    for src, dest in tk_datas:
        args.extend(["--add-data", f"{src}{SEP}{dest}"])

    extra_dlls = _find_extra_dlls(base_prefix)
    for src, dest in extra_dlls:
        args.extend(["--add-binary", f"{src}{SEP}{dest}"])

    sevenz = _find_7z_tool()
    for src, dest in sevenz:
        args.extend(["--add-binary", f"{src}{SEP}{dest}"])
    if not sevenz:
        print("WARNING: 7-Zip not found. RAR extraction will require 7-Zip or UnRAR on the target machine.")

    args.append("main.py")
    return args



def _print_summary(args: list[str]) -> None:
    print("PyInstaller command:")
    print(" ".join(f'"{value}"' if " " in value else value for value in args))
    print()



def main() -> int:
    parser = argparse.ArgumentParser(description="Build the PMX Static Importer Windows executable.")
    parser.add_argument("--onefile", action="store_true", help="Build a onefile executable instead of onedir.")
    parser.add_argument("--console", action="store_true", help="Build with a console window for debugging.")
    parser.add_argument("--keep-build", action="store_true", help="Do not remove the existing build/dist folders first.")
    args = parser.parse_args()

    if not args.keep_build:
        shutil.rmtree(THIS_DIR / "build", ignore_errors=True)
        if args.onefile:
            shutil.rmtree(THIS_DIR / "dist", ignore_errors=True)
        else:
            shutil.rmtree(THIS_DIR / "dist" / APP_NAME, ignore_errors=True)

    command = _build_pyinstaller_args(onefile=args.onefile, console=args.console)
    _print_summary(command)

    # Write compile date so the app can check for updates
    compile_date_file = THIS_DIR / "_compile_date.py"
    compile_date_file.write_text(
        f'COMPILE_DATE = "{datetime.now(timezone.utc).strftime("%Y-%m-%d")}"\n',
        encoding="utf-8",
    )

    subprocess.check_call(command, cwd=THIS_DIR)

    if args.onefile:
        print(f"\nBuild finished: {THIS_DIR / 'dist' / f'{APP_NAME}.exe'}")
    else:
        print(f"\nBuild finished: {THIS_DIR / 'dist' / APP_NAME / f'{APP_NAME}.exe'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
