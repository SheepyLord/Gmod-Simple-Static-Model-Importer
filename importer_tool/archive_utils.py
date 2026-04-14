from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class ArchiveError(RuntimeError):
    """Raised when an archive cannot be extracted."""


@dataclass(slots=True)
class StagedSource:
    source_path: Path
    workspace_path: Path
    extracted: bool
    cleanup_path: Path | None = None

    def cleanup(self) -> None:
        if self.cleanup_path and self.cleanup_path.exists():
            shutil.rmtree(self.cleanup_path, ignore_errors=True)


LogFn = Callable[[str], None] | None


def stage_input(source: str | Path, log: LogFn = None) -> StagedSource:
    src = Path(source).expanduser().resolve()
    if not src.exists():
        raise ArchiveError(f"Source does not exist: {src}")

    if src.is_dir():
        if log:
            log(f"Using folder directly: {src}")
        return StagedSource(source_path=src, workspace_path=src, extracted=False, cleanup_path=None)

    suffix = src.suffix.lower()
    temp_root = Path(tempfile.mkdtemp(prefix="pmx_static_importer_"))
    extracted_root = temp_root / "workspace"
    extracted_root.mkdir(parents=True, exist_ok=True)

    try:
        if suffix == ".zip":
            if log:
                log(f"Extracting ZIP: {src.name}")
            with zipfile.ZipFile(src, "r") as zf:
                zf.extractall(extracted_root)
        elif suffix == ".rar":
            _extract_rar(src, extracted_root, log=log)
        else:
            raise ArchiveError("Only folders, .zip files, and optionally .rar files are supported.")
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise

    workspace = _normalize_workspace(extracted_root)
    _extract_nested_archives(workspace, log=log)
    workspace = _normalize_workspace(workspace)
    if log:
        log(f"Prepared workspace: {workspace}")
    return StagedSource(source_path=src, workspace_path=workspace, extracted=True, cleanup_path=temp_root)



def _normalize_workspace(extracted_root: Path) -> Path:
    children = [p for p in extracted_root.iterdir() if p.name not in {"__MACOSX"}]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extracted_root



def _extract_nested_archives(root: Path, log: LogFn = None, _depth: int = 0) -> None:
    """Recursively extract .zip and .rar archives found inside *root*."""
    if _depth >= 3:
        return
    for archive in list(root.rglob("*")):
        if not archive.is_file():
            continue
        suffix = archive.suffix.lower()
        if suffix not in {".zip", ".rar"}:
            continue
        dest = archive.parent / archive.stem
        dest.mkdir(parents=True, exist_ok=True)
        try:
            if suffix == ".zip":
                if log:
                    log(f"Extracting nested ZIP: {archive.name}")
                with zipfile.ZipFile(archive, "r") as zf:
                    zf.extractall(dest)
            elif suffix == ".rar":
                _extract_rar(archive, dest, log=log)
        except Exception:
            shutil.rmtree(dest, ignore_errors=True)
            continue
        archive.unlink(missing_ok=True)
        nested_workspace = _normalize_workspace(dest)
        if nested_workspace != dest:
            # Move contents up so the workspace is flat
            for child in list(nested_workspace.iterdir()):
                target = dest / child.name
                if not target.exists():
                    child.rename(target)
        _extract_nested_archives(dest, log=log, _depth=_depth + 1)



def _find_rar_tool() -> str | None:
    """Search for 7z.exe or UnRAR.exe — bundled first, then common install paths."""
    candidates: list[Path] = []

    # Bundled with PyInstaller (frozen)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "7z.exe")
        candidates.append(Path(meipass) / "UnRAR.exe")

    # Next to the running script / executable
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
    else:
        exe_dir = Path(__file__).resolve().parent
    candidates.append(exe_dir / "7z.exe")
    candidates.append(exe_dir / "UnRAR.exe")

    # Common Windows install locations
    for env_var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        pf = os.environ.get(env_var)
        if not pf:
            continue
        candidates.append(Path(pf) / "7-Zip" / "7z.exe")
        candidates.append(Path(pf) / "WinRAR" / "UnRAR.exe")

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def _extract_rar(src: Path, dest: Path, log: LogFn = None) -> None:
    if log:
        log(f"Extracting RAR: {src.name}")

    # Prefer calling 7z directly — the rarfile native reader cannot
    # decompress most RAR files and fails with truncated-read errors.
    tool = _find_rar_tool()
    if tool and "7z" in tool.lower():
        try:
            subprocess.run(
                [tool, "x", str(src), f"-o{dest}", "-y", "-bso0", "-bsp0"],
                check=True,
                capture_output=True,
            )
            return
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors="replace").strip() if exc.stderr else ""
            raise ArchiveError(f"7-Zip failed to extract RAR archive: {stderr}") from exc

    # Fallback: try the rarfile library (works for UnRAR-backed setups
    # or simple/uncompressed RAR files).
    try:
        import rarfile  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ArchiveError(
            "RAR support requires 7-Zip (https://7-zip.org) or the 'rarfile' Python package."
        ) from exc

    if tool:
        rarfile.UNRAR_TOOL = tool

    try:
        with rarfile.RarFile(src) as rf:
            rf.extractall(dest)
    except rarfile.RarCannotExec as exc:  # pragma: no cover
        raise ArchiveError(
            "RAR extraction needs an external backend tool. Install 7-Zip (https://7-zip.org) or re-pack the model as ZIP."
        ) from exc
    except rarfile.Error as exc:  # pragma: no cover
        raise ArchiveError(f"Failed to extract RAR archive: {exc}") from exc
