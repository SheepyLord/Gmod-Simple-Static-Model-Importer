from __future__ import annotations

import os
import sys
from pathlib import Path


_DLL_HANDLES: list[object] = []


def _iter_candidates() -> list[Path]:
    roots: list[Path] = []

    try:
        roots.append(Path(__file__).resolve().parent)
    except Exception:
        pass

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        try:
            roots.append(Path(meipass).resolve())
        except Exception:
            pass

    executable = getattr(sys, "executable", None)
    if executable:
        try:
            roots.append(Path(executable).resolve().parent)
        except Exception:
            pass

    seen: set[str] = set()
    expanded: list[Path] = []
    for root in roots:
        for candidate in (
            root,
            root / "DLLs",
            root / "Library" / "bin",
            root / "tcl",
            root / "lib",
            root.parent,
            root.parent / "DLLs",
            root.parent / "Library" / "bin",
            root.parent / "tcl",
            root.parent / "lib",
        ):
            try:
                key = str(candidate.resolve()).lower()
            except Exception:
                key = str(candidate).lower()
            if key in seen:
                continue
            seen.add(key)
            expanded.append(candidate)
    return expanded



def _prepend_path(entries: list[Path]) -> None:
    valid = [str(path) for path in entries if path.exists()]
    if not valid:
        return

    existing = os.environ.get("PATH", "")
    current_parts = existing.split(os.pathsep) if existing else []
    merged: list[str] = []
    seen: set[str] = set()
    for value in valid + current_parts:
        normalized = value.lower()
        if not value or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(value)
    os.environ["PATH"] = os.pathsep.join(merged)



def _set_tcl_env(runtime_dirs: list[Path]) -> None:
    tcl_candidates: list[Path] = []
    tk_candidates: list[Path] = []

    for base in runtime_dirs:
        tcl_candidates.extend(
            [
                base / "_tcl_data",
                base / "tcl8.6",
                base / "tcl8.7",
                base / "tcl" / "tcl8.6",
                base / "tcl" / "tcl8.7",
                base / "lib" / "tcl8.6",
                base / "lib" / "tcl8.7",
            ]
        )
        tk_candidates.extend(
            [
                base / "_tk_data",
                base / "tk8.6",
                base / "tk8.7",
                base / "tcl" / "tk8.6",
                base / "tcl" / "tk8.7",
                base / "lib" / "tk8.6",
                base / "lib" / "tk8.7",
            ]
        )

    for candidate in tcl_candidates:
        if candidate.exists():
            os.environ["TCL_LIBRARY"] = str(candidate)
            break

    for candidate in tk_candidates:
        if candidate.exists():
            os.environ["TK_LIBRARY"] = str(candidate)
            break



def _install() -> None:
    if os.name != "nt":
        return

    runtime_dirs = _iter_candidates()
    _prepend_path(runtime_dirs)

    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is not None:
        for candidate in runtime_dirs:
            if not candidate.exists():
                continue
            try:
                _DLL_HANDLES.append(add_dll_directory(str(candidate)))
            except OSError:
                pass
        if _DLL_HANDLES:
            setattr(sys, "_pmx_tk_dll_handles", _DLL_HANDLES)

    _set_tcl_env(runtime_dirs)


_install()
