from __future__ import annotations

import hashlib
import io
import json
import math
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image

from gmod_locator import GModInstall, normalize_game_root
from pmx_parser import PMXMaterial, PMXModel
from scene_loader import load_supported_model, scan_supported_model_files

LogFn = Callable[[str], object] | None
ResolveMissingTextureFn = Callable[[PMXMaterial, int, PMXModel, Path, set[Path], list[int], bool], Path | None] | None


MESH_MAGIC = b"PMXSM01\0"

DEFAULT_SCALE_BY_EXT: dict[str, float] = {
    ".pmx": 3.6,
    ".fbx": 10.0,
    ".obj": 10.0,
    ".glb": 10.0,
}
DEFAULT_SCALE_FALLBACK: float = 10.0


def default_scale_for_path(path: Path | str) -> float:
    """Return the recommended default import scale for a model file extension."""
    ext = Path(path).suffix.lower()
    return DEFAULT_SCALE_BY_EXT.get(ext, DEFAULT_SCALE_FALLBACK)


@dataclass(slots=True)
class ImportOptions:
    axis_preset: str = "x,-z,y"
    global_scale: float = 3.6
    flip_v: bool = False
    output_model_id: str | None = None
    display_name_override: str | None = None
    resolve_missing_texture: ResolveMissingTextureFn = None
    workspace_root: Path | None = None


@dataclass(slots=True)
class ImportResult:
    model_id: str
    display_name: str
    manifest_path: Path
    mesh_path: Path
    material_dir: Path
    triangle_count: int
    material_count: int


@dataclass(slots=True)
class ImportedModelRecord:
    model_id: str
    display_name: str
    triangle_count: int
    material_count: int
    vertex_count: int
    manifest_path: Path
    data_dir: Path
    material_dir: Path
    updated_timestamp: float


@dataclass(slots=True)
class StaticImportWarning:
    code: str
    value: int
    detail: str = ""


LogFn = Callable[[str], None] | None


_AXIS_PRESETS: dict[str, tuple[str, str, str]] = {
    "x,-z,y": ("x", "-z", "y"),
    "x,z,y": ("x", "z", "y"),
    "-x,-z,y": ("-x", "-z", "y"),
    "x,y,z": ("x", "y", "z"),
}


_SANITIZE_RE = re.compile(r"[^a-z0-9]+")
_DISPLAY_NAME_CLEAN_RE = re.compile(r"[^A-Za-z ]+")
_DISPLAY_NAME_VALIDATE_RE = re.compile(r"^[A-Za-z]+(?: [A-Za-z]+)*$")


class ImportError(RuntimeError):
    """Raised when a supported source model cannot be imported."""



def import_pmx_model(
    pmx_path: str | Path,
    gmod_root: str | Path,
    options: ImportOptions | None = None,
    log: LogFn = None,
) -> ImportResult:
    options = options or ImportOptions()
    install = normalize_game_root(gmod_root)
    model = load_supported_model(pmx_path, log=log, boundary=options.workspace_root)

    if log:
        log(f"Parsed model: {Path(pmx_path).name} ({model.source_format.upper()})")
        log(
            "Vertices: "
            f"{len(model.vertices):,} | Triangles: {model.triangle_count:,} | Materials: {len(model.materials):,}"
        )

    if not model.vertices or not model.indices or not model.materials:
        raise ImportError("The selected model file does not contain the mesh/material data required for static import.")

    display_name = pick_display_name(model)
    if options.display_name_override is not None:
        display_name = normalize_display_name(options.display_name_override)
        if not is_valid_display_name(display_name):
            raise ImportError(
                "Display Name must use English letters and spaces only. Example: 'Fu Xuan'."
            )

    model_id = build_model_id(model, explicit_id=options.output_model_id, display_name=display_name)

    mod_root = install.mod_root
    data_dir = mod_root / "data" / "pmx_static_importer" / "models" / model_id
    materials_dir = mod_root / "materials" / "pmx_static_importer" / model_id
    data_dir.mkdir(parents=True, exist_ok=True)
    materials_dir.mkdir(parents=True, exist_ok=True)

    texture_lookup = build_texture_lookup(
        model.source_path.parent if model.source_path else Path.cwd(),
        boundary=options.workspace_root,
    )
    bake_flip_winding = axis_flips_winding(options.axis_preset)

    bounds_mins = [float("inf"), float("inf"), float("inf")]
    bounds_maxs = [float("-inf"), float("-inf"), float("-inf")]

    texture_output_cache: dict[str, tuple[str, str]] = {}
    submesh_entries: list[dict[str, object]] = []

    mesh_buffer = io.BytesIO()
    mesh_buffer.write(MESH_MAGIC)
    mesh_buffer.write(struct.pack("<I", len(model.materials)))

    index_cursor = 0
    for material_index, material in enumerate(model.materials):
        raw_sub_indices = model.indices[index_cursor : index_cursor + max(0, material.surface_count)]
        index_cursor += max(0, material.surface_count)
        sub_indices = maybe_flip_triangle_winding(raw_sub_indices, bake_flip_winding)

        texture_rel_path, texture_source_label = export_material_texture(
            materials_dir=materials_dir,
            model_dir=model.source_path.parent if model.source_path else Path.cwd(),
            texture_lookup=texture_lookup,
            material=material,
            material_index=material_index,
            model=model,
            model_id=model_id,
            texture_output_cache=texture_output_cache,
            log=log,
            resolve_missing_texture=options.resolve_missing_texture,
            sub_indices=raw_sub_indices,
            flip_v=options.flip_v,
        )

        safe_material_name = build_material_id(material, material_index)
        pmx_double_sided = bool(material.draw_flags & 0x01)
        runtime_no_cull = True
        translucent = bool(material.diffuse[3] < 0.999)

        vertex_count = len(sub_indices)
        mesh_buffer.write(struct.pack("<I", vertex_count))

        for vertex_index in sub_indices:
            try:
                vertex = model.vertices[vertex_index]
            except IndexError as exc:
                raise ImportError(f"Triangle index {vertex_index} is out of range for the vertex list.") from exc

            pos = transform_vector(vertex.position, options.axis_preset, options.global_scale)
            normal = normalize_vector(transform_vector(vertex.normal, options.axis_preset, 1.0))
            uv = transform_uv(vertex.uv, options.flip_v)

            mesh_buffer.write(struct.pack("<8f", pos[0], pos[1], pos[2], normal[0], normal[1], normal[2], uv[0], uv[1]))
            update_bounds(bounds_mins, bounds_maxs, pos)

        submesh_entries.append(
            {
                "index": material_index,
                "name": pick_material_display_name(material, material_index),
                "safe_name": safe_material_name,
                "image_path": texture_rel_path,
                "texture_source": texture_source_label,
                "vertex_count": vertex_count,
                "triangle_count": vertex_count // 3,
                "double_sided": pmx_double_sided,
                "pmx_double_sided": pmx_double_sided,
                "no_cull": runtime_no_cull,
                "translucent": translucent,
                "alpha": round(float(material.diffuse[3]), 6),
                "diffuse": [round(float(v), 6) for v in material.diffuse],
            }
        )

    if index_cursor < len(model.indices) and log:
        leftover = len(model.indices) - index_cursor
        log(f"Warning: {leftover} leftover indices were not assigned to a PMX material block.")

    mesh_bytes = mesh_buffer.getvalue()
    mesh_hash = hashlib.sha1(mesh_bytes).hexdigest()[:12]

    warnings = collect_static_import_warnings(model)
    manifest = {
        "format": 2,
        "build_id": mesh_hash,
        "model_id": model_id,
        "display_name": display_name,
        "safe_display_name": model_id,
        "source_file": Path(pmx_path).name,
        "source_format": model.source_format,
        "source_name_local": model.name_local,
        "source_name_en": model.name_en,
        "axis_preset": options.axis_preset,
        "scale": options.global_scale,
        "flip_v": options.flip_v,
        "triangle_count": len(model.indices) // 3,
        "vertex_count": len(model.vertices),
        "render_vertex_count": len(model.indices),
        "material_count": len(model.materials),
        "pmx_bone_count": model.bone_count,
        "pmx_morph_count": model.morph_count,
        "static_only_warning": bool(warnings),
        "mesh_file": f"pmx_static_importer/models/{model_id}/mesh.json",
        "runtime_no_cull": True,
        "winding_flipped_baked": bake_flip_winding,
        "bounds": {
            "mins": [round(v, 6) for v in finalize_bounds_min(bounds_mins)],
            "maxs": [round(v, 6) for v in finalize_bounds_max(bounds_maxs)],
        },
        "submeshes": submesh_entries,
    }

    manifest_bytes = json.dumps(manifest, ensure_ascii=True, indent=2).encode("utf-8")
    manifest_hash = hashlib.sha1(manifest_bytes).hexdigest()[:12]
    manifest["manifest_hash"] = manifest_hash
    manifest_bytes = json.dumps(manifest, ensure_ascii=True, indent=2).encode("utf-8")

    mesh_path = data_dir / "mesh.json"
    manifest_path = data_dir / "manifest.json"
    mesh_path.write_bytes(mesh_bytes)
    manifest_path.write_bytes(manifest_bytes)

    if log:
        log(f"Wrote mesh: {mesh_path}")
        log(f"Wrote manifest: {manifest_path}")
        log(f"Wrote/updated textures in: {materials_dir}")

    return ImportResult(
        model_id=model_id,
        display_name=display_name,
        manifest_path=manifest_path,
        mesh_path=mesh_path,
        material_dir=materials_dir,
        triangle_count=len(model.indices) // 3,
        material_count=len(model.materials),
    )



def collect_static_import_warnings(model: PMXModel) -> list[StaticImportWarning]:
    warnings: list[StaticImportWarning] = []
    if model.bone_count > 50:
        warnings.append(StaticImportWarning(code="bones", value=model.bone_count))
    if len(model.vertices) > 50_000:
        warnings.append(StaticImportWarning(code="vertices", value=len(model.vertices)))
    if model.morph_count > 0:
        warnings.append(StaticImportWarning(code="morphs", value=model.morph_count))
    for mat_index, material in enumerate(model.materials):
        vert_count = max(0, material.surface_count)
        if vert_count > 65535:
            mat_name = pick_material_display_name(material, mat_index)
            warnings.append(StaticImportWarning(code="submesh_vertices", value=vert_count, detail=mat_name))
    return warnings



def build_model_id(model: PMXModel, explicit_id: str | None = None, display_name: str | None = None) -> str:
    if explicit_id:
        cleaned = sanitize_ascii_name(explicit_id, fallback="model")
        if cleaned:
            return cleaned

    if display_name:
        cleaned = sanitize_ascii_name(display_name, fallback="model")
        if cleaned:
            return cleaned

    candidates = [model.name_en, model.name_local, (model.source_path.stem if model.source_path else "")]
    for candidate in candidates:
        cleaned = sanitize_ascii_name(candidate, fallback="")
        if cleaned:
            return cleaned

    seed = (model.source_path.name if model.source_path else "model").encode("utf-8", errors="ignore")
    return f"model_{hashlib.sha1(seed).hexdigest()[:10]}"



def ensure_unique_model_id(base_id: str, existing_ids: Iterable[str]) -> str:
    cleaned_base = sanitize_ascii_name(base_id, fallback="model")
    existing = {sanitize_ascii_name(item, fallback="") for item in existing_ids if item}
    if cleaned_base not in existing:
        return cleaned_base

    counter = 2
    while True:
        candidate = f"{cleaned_base}_{counter}"
        if candidate not in existing:
            return candidate
        counter += 1



def build_material_id(material: PMXMaterial, material_index: int) -> str:
    candidates = [material.name_en, material.name_local]
    for candidate in candidates:
        cleaned = sanitize_ascii_name(candidate, fallback="")
        if cleaned:
            return f"mat_{material_index:03d}_{cleaned}"
    seed = f"{material_index}:{material.name_local}:{material.name_en}".encode("utf-8", errors="ignore")
    return f"mat_{material_index:03d}_{hashlib.sha1(seed).hexdigest()[:8]}"



def pick_display_name(model: PMXModel) -> str:
    return first_nonempty(
        suggest_display_name(model),
        model.name_en,
        model.name_local,
        model.source_path.stem if model.source_path else "Imported Model",
    )



def suggest_display_name(model: PMXModel) -> str:
    candidates = [
        model.name_en,
        model.name_local,
        model.source_path.stem if model.source_path else "",
        build_model_id(model),
    ]
    for candidate in candidates:
        suggestion = suggest_display_name_from_text(candidate)
        if suggestion:
            return suggestion
    return "Imported Model"



def suggest_display_name_from_text(text: str | None) -> str:
    if text is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.replace("_", " ").replace("-", " ")
    ascii_text = _DISPLAY_NAME_CLEAN_RE.sub(" ", ascii_text)
    ascii_text = " ".join(part for part in ascii_text.split() if part)
    if not ascii_text:
        return ""
    return ascii_text.title()[:64]



def normalize_display_name(text: str) -> str:
    return " ".join(str(text or "").strip().split())[:64]



def is_valid_display_name(text: str) -> bool:
    normalized = normalize_display_name(text)
    return bool(normalized and _DISPLAY_NAME_VALIDATE_RE.fullmatch(normalized))



def pick_material_display_name(material: PMXMaterial, material_index: int) -> str:
    return first_nonempty(material.name_en, material.name_local, f"Material {material_index}")



def first_nonempty(*values: str) -> str:
    for value in values:
        if value and str(value).strip():
            return str(value).strip()
    return ""



def sanitize_ascii_name(text: str | None, fallback: str = "item") -> str:
    if text is None:
        text = ""
    normalized = unicodedata.normalize("NFKD", str(text))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = _SANITIZE_RE.sub("_", ascii_text).strip("_")
    if ascii_text:
        return ascii_text[:64]
    if fallback:
        fallback_clean = _SANITIZE_RE.sub("_", fallback.lower()).strip("_") or "item"
    else:
        fallback_clean = "item"
    seed = hashlib.sha1(str(text).encode("utf-8", errors="ignore")).hexdigest()[:8]
    return f"{fallback_clean}_{seed}"[:64]



def get_import_storage_paths(install: GModInstall | str | Path, model_id: str) -> tuple[Path, Path]:
    if not isinstance(install, GModInstall):
        install = normalize_game_root(install)
    safe_id = sanitize_ascii_name(model_id, fallback="model")
    data_dir = install.mod_root / "data" / "pmx_static_importer" / "models" / safe_id
    material_dir = install.mod_root / "materials" / "pmx_static_importer" / safe_id
    return data_dir, material_dir



def list_imported_models(install: GModInstall | str | Path) -> list[ImportedModelRecord]:
    if not isinstance(install, GModInstall):
        install = normalize_game_root(install)

    models_root = install.mod_root / "data" / "pmx_static_importer" / "models"
    if not models_root.exists():
        return []

    records: list[ImportedModelRecord] = []
    for manifest_path in models_root.glob("*/manifest.json"):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        model_id = str(data.get("model_id") or manifest_path.parent.name)
        display_name = str(data.get("display_name") or model_id)
        triangle_count = int(data.get("triangle_count") or 0)
        material_count = int(data.get("material_count") or 0)
        vertex_count = int(data.get("vertex_count") or 0)
        updated_timestamp = manifest_path.stat().st_mtime
        _, material_dir = get_import_storage_paths(install, model_id)

        records.append(
            ImportedModelRecord(
                model_id=model_id,
                display_name=display_name,
                triangle_count=triangle_count,
                material_count=material_count,
                vertex_count=vertex_count,
                manifest_path=manifest_path,
                data_dir=manifest_path.parent,
                material_dir=material_dir,
                updated_timestamp=updated_timestamp,
            )
        )

    records.sort(key=lambda item: (-item.updated_timestamp, item.display_name.lower(), item.model_id.lower()))
    return records



def remove_imported_model(install: GModInstall | str | Path, model_id: str) -> None:
    if not isinstance(install, GModInstall):
        install = normalize_game_root(install)
    data_dir, material_dir = get_import_storage_paths(install, model_id)
    if data_dir.exists():
        shutil.rmtree(data_dir)
    if material_dir.exists():
        shutil.rmtree(material_dir)



def export_models_as_gma(
    install: GModInstall | str | Path,
    model_ids: list[str],
    output_path: str | Path,
    addon_title: str = "exported_PSIP_models",
    log: LogFn = None,
) -> Path:
    """Assemble selected imported models into a .gma addon using gmad.exe.

    Creates a temporary addon folder matching the trial_addon structure
    (data_static/ for mesh data, materials/ for textures), writes addon.json,
    then invokes gmad.exe create to produce the .gma file.
    """
    if not isinstance(install, GModInstall):
        install = normalize_game_root(install)

    gmad_exe = install.game_root / "bin" / "gmad.exe"
    if not gmad_exe.exists():
        raise ImportError(f"gmad.exe not found at: {gmad_exe}")

    output_path = Path(output_path)

    with tempfile.TemporaryDirectory(prefix="psip_gma_") as tmp_str:
        addon_dir = Path(tmp_str) / "addon"
        addon_dir.mkdir()

        addon_json = {
            "title": addon_title,
            "type": "model",
            "tags": ["build", "movie"],
        }
        (addon_dir / "addon.json").write_text(
            json.dumps(addon_json, indent="\t"), encoding="utf-8"
        )

        for model_id in model_ids:
            data_dir, material_dir = get_import_storage_paths(install, model_id)

            if not data_dir.exists():
                raise ImportError(f"Model data directory not found for '{model_id}': {data_dir}")

            dest_data = addon_dir / "data_static" / "pmx_static_importer" / "models" / model_id
            dest_data.mkdir(parents=True, exist_ok=True)
            for src_file in data_dir.iterdir():
                if src_file.is_file():
                    shutil.copy2(src_file, dest_data / src_file.name)

            if material_dir.exists():
                dest_mat = addon_dir / "materials" / "pmx_static_importer" / model_id
                dest_mat.mkdir(parents=True, exist_ok=True)
                for src_file in material_dir.iterdir():
                    if src_file.is_file():
                        shutil.copy2(src_file, dest_mat / src_file.name)

            if log:
                log(f"Packed model: {model_id}")

        if log:
            log(f"Running gmad.exe to create GMA...")

        result = subprocess.run(
            [str(gmad_exe), "create", "-folder", str(addon_dir), "-out", str(output_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise ImportError(f"gmad.exe failed (exit code {result.returncode}): {detail}")

        if log:
            log(f"GMA created: {output_path}")

    return output_path



def transform_vector(value: tuple[float, float, float], axis_preset: str, scale: float) -> tuple[float, float, float]:
    axes = _AXIS_PRESETS.get(axis_preset)
    if axes is None:
        raise ImportError(f"Unsupported axis preset: {axis_preset}")
    src = {"x": float(value[0]), "y": float(value[1]), "z": float(value[2])}
    out: list[float] = []
    for token in axes:
        if token.startswith("-"):
            out.append(-src[token[1:]] * scale)
        else:
            out.append(src[token] * scale)
    return out[0], out[1], out[2]



def axis_flips_winding(axis_preset: str) -> bool:
    axes = _AXIS_PRESETS.get(axis_preset)
    if axes is None:
        raise ImportError(f"Unsupported axis preset: {axis_preset}")

    matrix: list[list[int]] = []
    for token in axes:
        row = [0, 0, 0]
        sign = -1 if token.startswith("-") else 1
        axis_name = token[1:] if token.startswith("-") else token
        axis_index = {"x": 0, "y": 1, "z": 2}[axis_name]
        row[axis_index] = sign
        matrix.append(row)

    determinant = (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )
    return determinant < 0



def maybe_flip_triangle_winding(indices: list[int], should_flip: bool) -> list[int]:
    if not should_flip or len(indices) < 3:
        return list(indices)

    flipped: list[int] = []
    whole_triangle_count = len(indices) // 3
    for triangle_index in range(whole_triangle_count):
        base = triangle_index * 3
        flipped.extend((indices[base], indices[base + 2], indices[base + 1]))

    leftover = len(indices) % 3
    if leftover:
        flipped.extend(indices[-leftover:])

    return flipped



def transform_uv(value: tuple[float, float], flip_v: bool) -> tuple[float, float]:
    u = float(value[0])
    v = float(value[1])
    if flip_v:
        v = 1.0 - v
    return u, v



def normalize_vector(value: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = value
    length = math.sqrt((x * x) + (y * y) + (z * z))
    if length <= 1e-9:
        return 0.0, 0.0, 1.0
    return x / length, y / length, z / length



def update_bounds(mins: list[float], maxs: list[float], pos: tuple[float, float, float]) -> None:
    for i in range(3):
        mins[i] = min(mins[i], float(pos[i]))
        maxs[i] = max(maxs[i], float(pos[i]))



def finalize_bounds_min(mins: list[float]) -> tuple[float, float, float]:
    if any(math.isinf(v) for v in mins):
        return -1.0, -1.0, -1.0
    return mins[0], mins[1], mins[2]



def finalize_bounds_max(maxs: list[float]) -> tuple[float, float, float]:
    if any(math.isinf(v) for v in maxs):
        return 1.0, 1.0, 1.0
    return maxs[0], maxs[1], maxs[2]



def build_texture_lookup(root: Path, boundary: Path | None = None) -> dict[str, Path]:
    lookup: dict[str, Path] = {}
    search_roots = [root]
    if boundary is None:
        parent = root.parent
        if parent.exists() and parent != root:
            search_roots.append(parent)
    else:
        # Walk up but stay strictly within the boundary
        boundary_resolved = boundary.resolve()
        try:
            root.resolve().relative_to(boundary_resolved)
        except ValueError:
            # root is outside boundary – fall back to boundary itself
            search_roots = [boundary_resolved]
        else:
            current = root.parent
            while current != root and current.exists():
                try:
                    current.resolve().relative_to(boundary_resolved)
                except ValueError:
                    break
                if current not in search_roots:
                    search_roots.append(current)
                parent = current.parent
                if parent == current:
                    break
                current = parent
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for file_path in search_root.rglob("*"):
            if not file_path.is_file():
                continue
            try:
                relative = file_path.relative_to(search_root).as_posix().lower()
                if relative not in lookup:
                    lookup[relative] = file_path
            except ValueError:
                pass
            name_lower = file_path.name.lower()
            if name_lower not in lookup:
                lookup[name_lower] = file_path
    return lookup



def resolve_texture_path(model_dir: Path, texture_lookup: dict[str, Path], raw_path: str) -> Path | None:
    if not raw_path:
        return None

    stripped = raw_path.replace("\\", "/").strip().strip('"')
    direct_path = Path(stripped)
    if direct_path.is_absolute() and direct_path.exists() and direct_path.is_file():
        return direct_path.resolve()

    candidate_key = stripped.lstrip("./").lower()
    if candidate_key in texture_lookup:
        return texture_lookup[candidate_key]

    candidate = (model_dir / candidate_key).resolve()
    if candidate.exists() and candidate.is_file():
        return candidate

    basename = Path(candidate_key).name.lower()
    if basename in texture_lookup:
        return texture_lookup[basename]

    normalized_basename = re.sub(r"[^a-z0-9]+", "", basename)
    if normalized_basename:
        for key, value in texture_lookup.items():
            if re.sub(r"[^a-z0-9]+", "", Path(key).name.lower()) == normalized_basename:
                return value

    # Strip trailing extension-like suffixes from the name (e.g. _dds, _png)
    stem = Path(candidate_key).stem.lower()
    for ext_suffix in ('_dds', '_png', '_jpg', '_jpeg', '_bmp', '_tga'):
        if stem.endswith(ext_suffix):
            clean_stem = stem[:len(stem) - len(ext_suffix)]
            for key, value in texture_lookup.items():
                if Path(key).stem.lower() == clean_stem:
                    return value
            break

    return None



def export_material_texture(
    *,
    materials_dir: Path,
    model_dir: Path,
    texture_lookup: dict[str, Path],
    material: PMXMaterial,
    material_index: int,
    model: PMXModel,
    model_id: str,
    texture_output_cache: dict[str, tuple[str, str]],
    log: LogFn,
    resolve_missing_texture: ResolveMissingTextureFn = None,
    sub_indices: list[int] | None = None,
    flip_v: bool = False,
) -> tuple[str, str]:
    safe_material_name = build_material_id(material, material_index)

    texture_path: Path | None = None
    texture_source_label = "generated"
    embedded_texture_bytes: bytes | None = None
    if 0 <= material.texture_index < len(model.textures):
        raw_texture_ref = model.textures[material.texture_index]
        texture_source_label = raw_texture_ref or "generated"
        if raw_texture_ref in model.embedded_textures:
            embedded_texture_bytes = model.embedded_textures[raw_texture_ref]
        else:
            texture_path = resolve_texture_path(model_dir, texture_lookup, raw_texture_ref)
            if texture_path is None:
                # Try matching the material name as a texture reference
                for fallback_name in (material.name_en, material.name_local):
                    if fallback_name:
                        texture_path = resolve_texture_path(model_dir, texture_lookup, fallback_name)
                        if texture_path is not None:
                            break
            if texture_path is None and log:
                log(f"Texture missing for material {material_index}: {raw_texture_ref!r}. Using diffuse-color fallback PNG.")

    if embedded_texture_bytes is not None:
        cache_key = f"embedded::{hashlib.sha1(embedded_texture_bytes).hexdigest()}"
        if cache_key in texture_output_cache:
            return texture_output_cache[cache_key]
        image_rel_path = convert_image_bytes_to_png(embedded_texture_bytes, materials_dir, safe_material_name)
        image_rel = f"pmx_static_importer/{model_id}/{image_rel_path.name}"
        texture_output_cache[cache_key] = (image_rel, texture_source_label)
        return texture_output_cache[cache_key]

    if texture_path is not None:
        cache_key = f"file::{texture_path.resolve()}"
        if cache_key in texture_output_cache:
            return texture_output_cache[cache_key]
        image_rel_path = convert_source_image_to_png(texture_path, materials_dir, safe_material_name)
        image_rel = f"pmx_static_importer/{model_id}/{image_rel_path.name}"
        texture_output_cache[cache_key] = (image_rel, str(texture_path.name))
        return texture_output_cache[cache_key]

    # Ask the user to pick a texture before falling back to diffuse color
    if resolve_missing_texture is not None:
        # Collect paths already assigned to other materials
        used_paths: set[Path] = set()
        for cache_key in texture_output_cache:
            if cache_key.startswith("file::"):
                try:
                    used_paths.add(Path(cache_key[6:]))
                except Exception:
                    pass
        user_picked = resolve_missing_texture(material, material_index, model, model_dir, used_paths, sub_indices or [], flip_v)
        if user_picked is not None:
            cache_key = f"file::{user_picked.resolve()}"
            if cache_key in texture_output_cache:
                return texture_output_cache[cache_key]
            image_rel_path = convert_source_image_to_png(user_picked, materials_dir, safe_material_name)
            image_rel = f"pmx_static_importer/{model_id}/{image_rel_path.name}"
            texture_output_cache[cache_key] = (image_rel, str(user_picked.name))
            return texture_output_cache[cache_key]

    fallback_rgba = tuple(max(0, min(255, int(round(component * 255.0)))) for component in material.diffuse)
    cache_key = f"rgba::{fallback_rgba}"
    if cache_key in texture_output_cache:
        return texture_output_cache[cache_key]

    image_name = f"{safe_material_name}_fallback_{hashlib.sha1(str(fallback_rgba).encode('ascii')).hexdigest()[:8]}.png"
    out_path = materials_dir / image_name
    image = Image.new("RGBA", (4, 4), fallback_rgba)
    image.save(out_path, format="PNG")
    image_rel = f"pmx_static_importer/{model_id}/{out_path.name}"
    texture_output_cache[cache_key] = (image_rel, "generated-diffuse-color")
    return texture_output_cache[cache_key]



def convert_source_image_to_png(source_path: Path, materials_dir: Path, safe_material_name: str) -> Path:
    source_bytes = source_path.read_bytes()
    return convert_image_bytes_to_png(source_bytes, materials_dir, safe_material_name)



def convert_image_bytes_to_png(source_bytes: bytes, materials_dir: Path, safe_material_name: str) -> Path:
    content_hash = hashlib.sha1(source_bytes).hexdigest()[:10]
    output_name = f"{safe_material_name}_{content_hash}.png"
    out_path = materials_dir / output_name

    if out_path.exists():
        return out_path

    with Image.open(io.BytesIO(source_bytes)) as img:
        converted = img.convert("RGBA")
        converted = _clamp_image_size(converted, 4096)
        converted.save(out_path, format="PNG")
    return out_path



def _clamp_image_size(image: Image.Image, max_side: int) -> Image.Image:
    """Resize the image so neither side exceeds *max_side* pixels."""
    w, h = image.size
    if w <= max_side and h <= max_side:
        return image
    scale = min(max_side / w, max_side / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return image.resize((new_w, new_h), Image.LANCZOS)



def resource_path(relative: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base_path / relative
