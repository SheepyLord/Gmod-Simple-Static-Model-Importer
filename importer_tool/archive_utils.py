from __future__ import annotations

import shutil
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
    if log:
        log(f"Prepared workspace: {workspace}")
    return StagedSource(source_path=src, workspace_path=workspace, extracted=True, cleanup_path=temp_root)



def _normalize_workspace(extracted_root: Path) -> Path:
    children = [p for p in extracted_root.iterdir() if p.name not in {"__MACOSX"}]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extracted_root



def _extract_rar(src: Path, dest: Path, log: LogFn = None) -> None:
    try:
        import rarfile  # type: ignore
    except Exception as exc:  # pragma: no cover - environment dependent
        raise ArchiveError("RAR support requires the 'rarfile' Python package.") from exc

    # rarfile still needs a backend tool such as UnRAR.exe, unar, or 7-Zip.
    try:
        with rarfile.RarFile(src) as rf:
            if log:
                log(f"Extracting RAR: {src.name}")
            rf.extractall(dest)
    except rarfile.RarCannotExec as exc:  # pragma: no cover - environment dependent
        raise ArchiveError(
            "RAR extraction needs an external backend tool. Install UnRAR or 7-Zip, or re-pack the model as ZIP."
        ) from exc
    except rarfile.Error as exc:  # pragma: no cover - environment dependent
        raise ArchiveError(f"Failed to extract RAR archive: {exc}") from exc
