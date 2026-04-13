from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path


APP_TITLE = "PMX Static Importer"
_STARTUP_DLL_HANDLES: list[object] = []


def _append_startup_log(message: str) -> None:
    try:
        if os.name == "nt":
            base = Path(os.environ.get("LOCALAPPDATA", Path.cwd())) / "PMXStaticImporter"
        else:
            base = Path.home() / ".pmx_static_importer"
        base.mkdir(parents=True, exist_ok=True)
        log_path = base / "startup.log"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip() + "\n")
    except Exception:
        pass



def _iter_runtime_base_dirs() -> list[Path]:
    dirs: list[Path] = []

    def _append_candidate(value: object, *, treat_as_file: bool = False) -> None:
        if not value:
            return
        try:
            candidate = Path(str(value)).resolve()
            if treat_as_file:
                candidate = candidate.parent
            dirs.append(candidate)
        except Exception:
            pass

    _append_candidate(__file__, treat_as_file=True)
    _append_candidate(getattr(sys, "_MEIPASS", None))
    _append_candidate(getattr(sys, "executable", None), treat_as_file=True)
    _append_candidate(getattr(sys, "_base_executable", None), treat_as_file=True)

    # When running from source inside a virtual environment or an IDE, some optional
    # extension modules (notably _ctypes) may rely on DLLs that live in the *base*
    # Python installation rather than alongside the venv launcher. Probe both the
    # active prefixes and the base prefixes so Windows can resolve those dependencies.
    _append_candidate(getattr(sys, "prefix", None))
    _append_candidate(getattr(sys, "exec_prefix", None))
    _append_candidate(getattr(sys, "base_prefix", None))
    _append_candidate(getattr(sys, "base_exec_prefix", None))

    expanded: list[Path] = []
    seen: set[str] = set()
    for directory in dirs:
        for candidate in (
            directory,
            directory / "DLLs",
            directory / "Library" / "bin",
            directory / "tcl",
            directory / "lib",
            directory.parent,
            directory.parent / "DLLs",
            directory.parent / "Library" / "bin",
            directory.parent / "tcl",
            directory.parent / "lib",
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



def _prepend_path_entries(entries: list[Path]) -> None:
    valid = [str(path) for path in entries if path.exists()]
    if not valid:
        return

    existing = os.environ.get("PATH", "")
    existing_parts = existing.split(os.pathsep) if existing else []
    merged: list[str] = []
    seen: set[str] = set()
    for value in valid + existing_parts:
        normalized = value.lower()
        if not value or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(value)
    os.environ["PATH"] = os.pathsep.join(merged)



def _configure_frozen_windows_paths() -> None:
    if os.name != "nt":
        return

    runtime_dirs = _iter_runtime_base_dirs()
    _prepend_path_entries(runtime_dirs)

    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is not None:
        handles: list[object] = []
        for candidate in runtime_dirs:
            if not candidate.exists():
                continue
            try:
                # Keep returned handles alive for the lifetime of the process.
                handles.append(add_dll_directory(str(candidate)))
            except OSError:
                pass
        if handles:
            _STARTUP_DLL_HANDLES.extend(handles)
            setattr(sys, "_pmx_startup_dll_handles", _STARTUP_DLL_HANDLES)

    tcl_candidates: list[Path] = []
    tk_candidates: list[Path] = []
    for base in runtime_dirs:
        tcl_candidates.extend(
            [
                base / "tcl8.6",
                base / "tcl8.7",
                base / "tcl" / "tcl8.6",
                base / "tcl" / "tcl8.7",
                base / "lib" / "tcl8.6",
                base / "lib" / "tcl8.7",
                base / "_tcl_data",
            ]
        )
        tk_candidates.extend(
            [
                base / "tk8.6",
                base / "tk8.7",
                base / "tcl" / "tk8.6",
                base / "tcl" / "tk8.7",
                base / "lib" / "tk8.6",
                base / "lib" / "tk8.7",
                base / "_tk_data",
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



def _show_startup_error(message: str) -> None:
    _append_startup_log(message)
    if os.name == "nt":
        try:
            import ctypes

            MB_ICONERROR = 0x00000010
            MB_TOPMOST = 0x00040000
            ctypes.windll.user32.MessageBoxW(None, message, APP_TITLE, MB_ICONERROR | MB_TOPMOST)
            return
        except Exception:
            pass
    print(message, file=sys.stderr)



def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import static PMX / FBX / OBJ / GLB meshes into Garry's Mod.")
    parser.add_argument("--source", help="Folder, ZIP, or RAR containing one or more supported model files.")
    parser.add_argument("--pmx", help="Selected model file name or relative path inside --source (kept for backward compatibility).")
    parser.add_argument("--pmx-file", help="Exact PMX / FBX / OBJ / GLB file path to import directly.")
    parser.add_argument("--gmod", help="Garry's Mod install folder.")
    parser.add_argument("--display-name", help="Override display name (English letters and spaces).")
    parser.add_argument("--output-id", help="Override output model id.")
    parser.add_argument("--axis", default="x,-z,y", choices=["x,-z,y", "x,z,y", "-x,-z,y", "x,y,z"], help="Axis preset.")
    parser.add_argument("--scale", type=float, default=None, help="Global import scale (auto-detected from file type if omitted).")
    parser.add_argument("--flip-v", action="store_true", help="Flip V texture coordinate.")
    parser.add_argument(
        "--no-install-runtime-addon",
        action="store_true",
        help="Do not install/update the Garry's Mod runtime addon during import.",
    )
    parser.add_argument(
        "--install-runtime-addon-only",
        action="store_true",
        help="Only install/update the Garry's Mod runtime addon and exit.",
    )
    return parser



def _run_cli(args: argparse.Namespace) -> int:
    from archive_utils import stage_input
    from importer_core import ImportOptions, default_scale_for_path, import_pmx_model, install_runtime_addon
    from scene_loader import scan_supported_model_files

    if args.install_runtime_addon_only:
        if not args.gmod:
            raise SystemExit("--gmod is required with --install-runtime-addon-only")
        addon_path = install_runtime_addon(args.gmod, log=print)
        print(f"Runtime addon installed to: {addon_path}")
        return 0

    if not args.gmod:
        raise SystemExit("--gmod is required for CLI import")

    if args.pmx_file:
        pmx_path = Path(args.pmx_file).expanduser().resolve()
        if not pmx_path.is_file():
            raise SystemExit(f"Model file not found: {pmx_path}")
        scale = args.scale if args.scale is not None else default_scale_for_path(pmx_path)
        result = import_pmx_model(
            pmx_path,
            args.gmod,
            options=ImportOptions(
                axis_preset=args.axis,
                global_scale=scale,
                flip_v=bool(args.flip_v),
                install_runtime_addon=not args.no_install_runtime_addon,
                output_model_id=args.output_id,
                display_name_override=args.display_name,
            ),
            log=print,
        )
        print(f"Imported {result.display_name} as {result.model_id}")
        return 0

    if not args.source:
        raise SystemExit("--source or --pmx-file is required for CLI import")

    staged = stage_input(args.source, log=print)
    try:
        pmx_files = scan_supported_model_files(staged.workspace_path)
        if not pmx_files:
            raise SystemExit("No supported model files (.pmx, .fbx, .obj, .glb) were found in the selected source")

        selected: Path | None = None
        if args.pmx:
            wanted = args.pmx.replace("\\", "/").strip().lower()
            for pmx_file in pmx_files:
                relative_name = pmx_file.relative_to(staged.workspace_path).as_posix().lower()
                if relative_name == wanted or pmx_file.name.lower() == wanted:
                    selected = pmx_file
                    break
        elif len(pmx_files) == 1:
            selected = pmx_files[0]

        if selected is None:
            names = "\n".join(f" - {path.relative_to(staged.workspace_path).as_posix()}" for path in pmx_files)
            raise SystemExit(f"Select a model with --pmx. Available files:\n{names}")

        scale = args.scale if args.scale is not None else default_scale_for_path(selected)
        result = import_pmx_model(
            selected,
            args.gmod,
            options=ImportOptions(
                axis_preset=args.axis,
                global_scale=scale,
                flip_v=bool(args.flip_v),
                install_runtime_addon=not args.no_install_runtime_addon,
                output_model_id=args.output_id,
                display_name_override=args.display_name,
            ),
            log=print,
        )
        print(f"Imported {result.display_name} as {result.model_id}")
        return 0
    finally:
        staged.cleanup()



def _run_gui() -> int:
    _configure_frozen_windows_paths()

    try:
        from pmx_importer_app import launch
    except Exception as exc:
        _show_startup_error(
            "Failed to start the graphical interface.\n\n"
            f"Reason: {exc}\n\n"
            "A startup log was also written to the PMXStaticImporter folder under LocalAppData."
        )
        return 1

    try:
        launch()
    except Exception:
        _show_startup_error(
            "The graphical interface crashed during startup.\n\n"
            + traceback.format_exc()
        )
        return 1
    return 0



def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    wants_cli = bool(args.install_runtime_addon_only or args.source or args.pmx_file)
    if wants_cli:
        return _run_cli(args)
    return _run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
