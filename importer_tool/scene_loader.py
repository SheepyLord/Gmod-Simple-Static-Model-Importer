from __future__ import annotations

import difflib
import hashlib
import io
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Callable

import numpy as np
import trimesh
from PIL import Image

from pmx_parser import PMXMaterial, PMXModel, PMXParser, PMXVertex


SUPPORTED_MODEL_SUFFIXES = {'.pmx', '.fbx', '.obj', '.glb', '.gltf'}
_IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.bmp', '.tga', '.tif', '.tiff', '.webp'}

LogFn = Callable[[str], None] | None


class SceneLoadError(RuntimeError):
    """Raised when a supported source model cannot be converted to the internal mesh form."""


@dataclass(slots=True)
class _ObjMaterialOverride:
    name: str
    texture_ref: str | None = None
    resolved_texture: Path | None = None
    diffuse: tuple[float, float, float, float] = (0.8, 0.8, 0.8, 1.0)


@dataclass(slots=True)
class _MaterialContext:
    name: str
    geometry_name: str
    node_name: str
    texture_ref: str | None
    embedded_image_bytes: bytes | None
    diffuse: tuple[float, float, float, float]
    double_sided: bool



def is_supported_model_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_MODEL_SUFFIXES



def scan_supported_model_files(root: Path) -> list[Path]:
    results = [path for path in root.rglob('*') if path.is_file() and path.suffix.lower() in SUPPORTED_MODEL_SUFFIXES]
    results.sort(key=lambda item: item.as_posix().lower())
    return results



def load_supported_model(path: str | Path, log: LogFn = None) -> PMXModel:
    source_path = Path(path).expanduser().resolve()
    suffix = source_path.suffix.lower()
    if suffix == '.pmx':
        model = PMXParser().parse(source_path)
        model.source_format = 'pmx'
        return model
    if suffix == '.obj':
        return _load_obj_model(source_path, log=log)
    if suffix in {'.glb', '.gltf'}:
        return _load_trimesh_scene_model(source_path, source_format=suffix.lstrip('.'), log=log)
    if suffix == '.fbx':
        return _load_fbx_model(source_path, log=log)
    raise SceneLoadError(f'Unsupported model format: {source_path.suffix}')



def _load_fbx_model(source_path: Path, log: LogFn = None) -> PMXModel:
    sibling = _find_sibling_scene_variant(source_path)
    if sibling is not None:
        if log:
            log(f"FBX fallback: using sibling scene file '{sibling.name}' for '{source_path.name}'.")
        model = load_supported_model(sibling, log=log)
        model.source_format = 'fbx'
        if not model.name_en:
            model.name_en = source_path.stem
        if not model.name_local:
            model.name_local = source_path.stem
        return model

    blender_path = _find_blender_executable()
    if blender_path is None:
        raise SceneLoadError(
            "FBX import needs either Blender installed or a sibling .glb/.gltf/.obj file with the same base name."
        )

    if log:
        log(f"FBX conversion: using Blender at '{blender_path}'.")

    with tempfile.TemporaryDirectory(prefix='pmx_importer_fbx_') as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        glb_path = temp_dir / f'{source_path.stem}.glb'
        _convert_fbx_to_glb_with_blender(source_path, glb_path, blender_path)
        model = _load_trimesh_scene_model(glb_path, source_format='fbx', log=log)
        model.source_format = 'fbx'
        if not model.name_en:
            model.name_en = source_path.stem
        if not model.name_local:
            model.name_local = source_path.stem
        return model



def _find_sibling_scene_variant(source_path: Path) -> Path | None:
    for suffix in ('.glb', '.gltf', '.obj'):
        candidate = source_path.with_suffix(suffix)
        if candidate.exists():
            return candidate
    return None



def _find_blender_executable() -> Path | None:
    env_value = os.environ.get('BLENDER_PATH')
    if env_value:
        candidate = Path(env_value).expanduser()
        if candidate.exists():
            return candidate.resolve()

    which_value = shutil.which('blender')
    if which_value:
        return Path(which_value).resolve()

    if os.name == 'nt':
        blender_root = Path('C:/Program Files/Blender Foundation')
        if blender_root.exists():
            candidates = sorted(blender_root.glob('Blender*/*/blender.exe')) + sorted(blender_root.glob('Blender*/blender.exe'))
            if candidates:
                return candidates[-1].resolve()
    return None



def _convert_fbx_to_glb_with_blender(source_path: Path, glb_path: Path, blender_path: Path) -> None:
    python_script = (
        'import bpy, sys; '
        'src = sys.argv[-2]; dst = sys.argv[-1]; '
        'bpy.ops.wm.read_factory_settings(use_empty=True); '
        'bpy.ops.import_scene.fbx(filepath=src); '
        "bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_texcoords=True, export_normals=True, export_materials='EXPORT')"
    )
    command = [
        str(blender_path),
        '--background',
        '--factory-startup',
        '--python-expr',
        python_script,
        '--',
        str(source_path),
        str(glb_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0 or not glb_path.exists():
        raise SceneLoadError(
            'Blender failed to convert the FBX file to GLB.\n\n'
            f'STDOUT:\n{completed.stdout}\n\nSTDERR:\n{completed.stderr}'
        )



def _load_obj_model(source_path: Path, log: LogFn = None) -> PMXModel:
    obj_overrides = _parse_obj_material_overrides(source_path)
    return _load_trimesh_scene_model(source_path, source_format='obj', log=log, obj_material_overrides=obj_overrides)



def _load_trimesh_scene_model(
    source_path: Path,
    *,
    source_format: str,
    log: LogFn = None,
    obj_material_overrides: dict[str, _ObjMaterialOverride] | None = None,
) -> PMXModel:
    try:
        scene = trimesh.load(source_path, force='scene', process=False)
    except NotImplementedError as exc:
        raise SceneLoadError(str(exc)) from exc
    except Exception as exc:
        raise SceneLoadError(f'Failed to load {source_path.name}: {exc}') from exc

    if not isinstance(scene, trimesh.Scene):
        scene = scene.scene()

    vertices: list[PMXVertex] = []
    indices: list[int] = []
    materials: list[PMXMaterial] = []
    textures: list[str] = []
    embedded_textures: dict[str, bytes] = {}
    texture_index_by_key: dict[str, int] = {}

    node_names = list(scene.graph.nodes_geometry)
    if not node_names and scene.geometry:
        node_names = list(scene.geometry.keys())

    if log:
        log(f"Loaded {source_path.suffix.lower()} scene with {len(scene.geometry)} geometry object(s).")

    for node_name in node_names:
        try:
            transform, geometry_name = scene.graph[node_name]
        except Exception:
            geometry_name = node_name
            transform = np.eye(4, dtype=np.float64)

        geom = scene.geometry.get(geometry_name)
        if geom is None:
            continue
        if not isinstance(geom, trimesh.Trimesh):
            continue
        if len(geom.vertices) == 0 or len(geom.faces) == 0:
            continue

        context = _build_material_context(
            geom=geom,
            geometry_name=str(geometry_name),
            node_name=str(node_name),
            source_path=source_path,
            obj_material_overrides=obj_material_overrides,
        )
        texture_index = _register_texture(
            texture_ref=context.texture_ref,
            embedded_image_bytes=context.embedded_image_bytes,
            textures=textures,
            embedded_textures=embedded_textures,
            texture_index_by_key=texture_index_by_key,
        )

        transform_matrix = np.asarray(transform, dtype=np.float64) if transform is not None else np.eye(4, dtype=np.float64)
        local_vertices = np.asarray(geom.vertices, dtype=np.float64)
        world_vertices = _apply_transform(local_vertices, transform_matrix)
        local_normals = _extract_vertex_normals(geom)
        world_normals = _apply_normal_transform(local_normals, transform_matrix)
        uvs = _extract_vertex_uvs(geom, len(local_vertices))
        faces = np.asarray(geom.faces, dtype=np.int64)

        base_index = len(vertices)
        for idx in range(len(world_vertices)):
            position = tuple(float(v) for v in world_vertices[idx])
            normal = tuple(float(v) for v in world_normals[idx])
            uv_pair = tuple(float(v) for v in uvs[idx])
            vertices.append(PMXVertex(position=position, normal=normal, uv=uv_pair))

        surface_indices: list[int] = []
        for face in faces:
            if len(face) < 3:
                continue
            surface_indices.extend((base_index + int(face[0]), base_index + int(face[1]), base_index + int(face[2])))

        indices.extend(surface_indices)
        materials.append(
            PMXMaterial(
                name_local=context.name,
                name_en=context.name,
                diffuse=context.diffuse,
                draw_flags=0x01 if context.double_sided else 0,
                texture_index=texture_index,
                surface_count=len(surface_indices),
            )
        )

    if not vertices or not indices or not materials:
        raise SceneLoadError(f'No renderable mesh data was found in {source_path.name}.')

    model_name = source_path.stem
    return PMXModel(
        version=2.0,
        text_encoding=1,
        additional_uv_count=0,
        name_local=model_name,
        name_en=model_name,
        comment_local='',
        comment_en='',
        vertices=vertices,
        indices=indices,
        textures=textures,
        materials=materials,
        bone_count=0,
        morph_count=0,
        source_path=source_path,
        source_format=source_format,
        embedded_textures=embedded_textures,
    )



def _build_material_context(
    *,
    geom: trimesh.Trimesh,
    geometry_name: str,
    node_name: str,
    source_path: Path,
    obj_material_overrides: dict[str, _ObjMaterialOverride] | None,
) -> _MaterialContext:
    visual = getattr(geom, 'visual', None)
    material = getattr(visual, 'material', None)

    material_name = _first_nonempty(
        getattr(material, 'name', None),
        geometry_name,
        node_name,
        source_path.stem,
    )

    override = obj_material_overrides.get(material_name) if obj_material_overrides else None
    texture_ref = None
    embedded_image_bytes = None

    image = _extract_material_image(material)
    if image is not None:
        embedded_image_bytes = _encode_image_as_png_bytes(image)
    elif override is not None and override.resolved_texture is not None:
        try:
            texture_ref = override.resolved_texture.resolve().relative_to(source_path.parent.resolve()).as_posix()
        except Exception:
            texture_ref = str(override.resolved_texture)
    elif override is not None and override.texture_ref:
        texture_ref = override.texture_ref

    diffuse = _extract_material_diffuse(material)
    if override is not None and diffuse == (0.8, 0.8, 0.8, 1.0):
        diffuse = override.diffuse

    double_sided = bool(getattr(material, 'doubleSided', False)) if material is not None else False
    return _MaterialContext(
        name=material_name,
        geometry_name=geometry_name,
        node_name=node_name,
        texture_ref=texture_ref,
        embedded_image_bytes=embedded_image_bytes,
        diffuse=diffuse,
        double_sided=double_sided,
    )



def _extract_material_image(material) -> Image.Image | None:
    if material is None:
        return None
    for attribute in ('image', 'baseColorTexture'):
        if not hasattr(material, attribute):
            continue
        value = getattr(material, attribute)
        if value is None:
            continue
        if isinstance(value, Image.Image):
            return value
        if hasattr(value, 'size') and hasattr(value, 'mode') and hasattr(value, 'copy'):
            return value
    return None



def _extract_material_diffuse(material) -> tuple[float, float, float, float]:
    if material is None:
        return 0.8, 0.8, 0.8, 1.0

    if hasattr(material, 'main_color'):
        value = getattr(material, 'main_color')
        try:
            seq = list(value)
        except Exception:
            seq = []
        if len(seq) >= 4:
            return tuple(max(0.0, min(1.0, float(component) / 255.0)) for component in seq[:4])

    if hasattr(material, 'baseColorFactor'):
        value = getattr(material, 'baseColorFactor')
        if value is not None:
            try:
                seq = list(value)
            except Exception:
                seq = []
            if len(seq) >= 4:
                floats = [float(component) for component in seq[:4]]
                if max(floats) > 1.5:
                    floats = [component / 255.0 for component in floats]
                return tuple(max(0.0, min(1.0, component)) for component in floats)

    return 0.8, 0.8, 0.8, 1.0



def _encode_image_as_png_bytes(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.convert('RGBA').save(out, format='PNG')
    return out.getvalue()



def _register_texture(
    *,
    texture_ref: str | None,
    embedded_image_bytes: bytes | None,
    textures: list[str],
    embedded_textures: dict[str, bytes],
    texture_index_by_key: dict[str, int],
) -> int:
    if embedded_image_bytes is not None:
        content_hash = hashlib.sha1(embedded_image_bytes).hexdigest()[:12]
        key = f'__embedded__/{content_hash}.png'
        if key not in texture_index_by_key:
            texture_index_by_key[key] = len(textures)
            textures.append(key)
            embedded_textures[key] = embedded_image_bytes
        return texture_index_by_key[key]

    if texture_ref:
        normalized = texture_ref.replace('\\', '/').strip()
        if normalized not in texture_index_by_key:
            texture_index_by_key[normalized] = len(textures)
            textures.append(normalized)
        return texture_index_by_key[normalized]

    return -1



def _extract_vertex_normals(geom: trimesh.Trimesh) -> np.ndarray:
    normals = getattr(geom, 'vertex_normals', None)
    if normals is None or len(normals) != len(geom.vertices):
        normals = np.zeros((len(geom.vertices), 3), dtype=np.float64)
        normals[:, 2] = 1.0
        return normals
    return np.asarray(normals, dtype=np.float64)



def _extract_vertex_uvs(geom: trimesh.Trimesh, vertex_count: int) -> np.ndarray:
    visual = getattr(geom, 'visual', None)
    uv = getattr(visual, 'uv', None)
    if uv is None:
        return np.zeros((vertex_count, 2), dtype=np.float64)
    arr = np.asarray(uv, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] < 2:
        return np.zeros((vertex_count, 2), dtype=np.float64)
    if arr.shape[0] != vertex_count:
        return np.resize(arr[:, :2], (vertex_count, 2))
    return arr[:, :2]



def _apply_transform(vertices: np.ndarray, transform_matrix: np.ndarray) -> np.ndarray:
    if vertices.size == 0:
        return np.zeros((0, 3), dtype=np.float64)
    padded = np.concatenate([vertices, np.ones((len(vertices), 1), dtype=np.float64)], axis=1)
    transformed = padded @ transform_matrix.T
    return transformed[:, :3]



def _apply_normal_transform(normals: np.ndarray, transform_matrix: np.ndarray) -> np.ndarray:
    if normals.size == 0:
        return np.zeros((0, 3), dtype=np.float64)
    linear = np.asarray(transform_matrix[:3, :3], dtype=np.float64)
    try:
        normal_matrix = np.linalg.inv(linear).T
    except np.linalg.LinAlgError:
        normal_matrix = linear
    transformed = normals @ normal_matrix.T
    lengths = np.linalg.norm(transformed, axis=1)
    lengths[lengths < 1e-12] = 1.0
    return transformed / lengths[:, None]



def _parse_obj_material_overrides(obj_path: Path) -> dict[str, _ObjMaterialOverride]:
    mtllib_paths = _discover_mtl_files(obj_path)
    overrides: dict[str, _ObjMaterialOverride] = {}
    all_raw_refs: list[tuple[str, str]] = []
    for mtl_path in mtllib_paths:
        current: _ObjMaterialOverride | None = None
        for raw_line in mtl_path.read_text(encoding='utf-8', errors='ignore').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            key, _, value = line.partition(' ')
            value = value.strip()
            key_lower = key.lower()
            if key_lower == 'newmtl':
                current = _ObjMaterialOverride(name=value)
                overrides[current.name] = current
            elif current is None:
                continue
            elif key_lower == 'map_kd':
                current.texture_ref = value
                all_raw_refs.append((current.name, value))
            elif key_lower == 'kd':
                parts = value.split()
                if len(parts) >= 3:
                    try:
                        current.diffuse = (float(parts[0]), float(parts[1]), float(parts[2]), current.diffuse[3])
                    except ValueError:
                        pass
            elif key_lower == 'd':
                try:
                    current.diffuse = (current.diffuse[0], current.diffuse[1], current.diffuse[2], float(value.split()[0]))
                except Exception:
                    pass
            elif key_lower == 'tr':
                try:
                    alpha = 1.0 - float(value.split()[0])
                    current.diffuse = (current.diffuse[0], current.diffuse[1], current.diffuse[2], alpha)
                except Exception:
                    pass

    available_images = sorted(
        [path for path in obj_path.parent.rglob('*') if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES],
        key=lambda item: item.as_posix().lower(),
    )
    resolved_refs = _resolve_referenced_images(all_raw_refs, available_images)
    for material_name, resolved_path in resolved_refs.items():
        if material_name in overrides:
            overrides[material_name].resolved_texture = resolved_path
    return overrides



def _discover_mtl_files(obj_path: Path) -> list[Path]:
    mtllibs: list[Path] = []
    try:
        for raw_line in obj_path.read_text(encoding='utf-8', errors='ignore').splitlines():
            line = raw_line.strip()
            if not line.lower().startswith('mtllib '):
                continue
            name = line[7:].strip()
            if not name:
                continue
            candidate = (obj_path.parent / name).resolve()
            if candidate.exists():
                mtllibs.append(candidate)
    except Exception:
        pass

    default_candidate = obj_path.with_suffix('.mtl')
    if default_candidate.exists() and default_candidate not in mtllibs:
        mtllibs.append(default_candidate)
    return mtllibs



def _resolve_referenced_images(raw_refs: list[tuple[str, str]], available_images: list[Path]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    used: set[Path] = set()

    # pass 1: exact/relative/basename matching
    unresolved: list[tuple[str, str]] = []
    for material_name, raw_ref in raw_refs:
        resolved = _match_image_reference(raw_ref, available_images, used)
        if resolved is None:
            unresolved.append((material_name, raw_ref))
        else:
            result[material_name] = resolved
            used.add(resolved)

    # pass 2: fuzzy matching against remaining images
    remaining = [path for path in available_images if path not in used]
    still_unresolved: list[tuple[str, str]] = []
    for material_name, raw_ref in unresolved:
        resolved = _match_image_reference_fuzzy(raw_ref, remaining)
        if resolved is None:
            still_unresolved.append((material_name, raw_ref))
        else:
            result[material_name] = resolved
            used.add(resolved)
            remaining = [path for path in available_images if path not in used]

    # pass 3: if the counts line up, pair the leftovers in order.
    if still_unresolved and len(still_unresolved) == len(remaining):
        for (material_name, _raw_ref), resolved in zip(still_unresolved, remaining):
            result[material_name] = resolved
            used.add(resolved)

    return result



def _match_image_reference(raw_ref: str, candidates: list[Path], used: set[Path]) -> Path | None:
    raw_ref = raw_ref.strip().strip('"')
    if not raw_ref:
        return None

    direct_candidate = Path(raw_ref)
    if direct_candidate.exists() and direct_candidate.is_file():
        return direct_candidate.resolve()

    try:
        basename = PureWindowsPath(raw_ref).name or Path(raw_ref).name
    except Exception:
        basename = Path(raw_ref).name
    basename_lower = basename.lower()

    for candidate in candidates:
        if candidate in used:
            continue
        if candidate.name.lower() == basename_lower:
            return candidate

    normalized_target = _normalize_texture_name(basename)
    for candidate in candidates:
        if candidate in used:
            continue
        if _normalize_texture_name(candidate.name) == normalized_target:
            return candidate

    return None



def _match_image_reference_fuzzy(raw_ref: str, candidates: list[Path]) -> Path | None:
    if not candidates:
        return None
    try:
        basename = PureWindowsPath(raw_ref).name or Path(raw_ref).name
    except Exception:
        basename = Path(raw_ref).name
    target = _normalize_texture_name(basename)
    if not target:
        return None

    best_score = 0.0
    best_candidate: Path | None = None
    for candidate in candidates:
        candidate_key = _normalize_texture_name(candidate.name)
        if not candidate_key:
            continue
        score = difflib.SequenceMatcher(None, target, candidate_key).ratio()
        if target in candidate_key or candidate_key in target:
            score += 0.15
        if score > best_score:
            best_score = score
            best_candidate = candidate
    if best_score >= 0.52:
        return best_candidate
    return None



def _normalize_texture_name(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', text.lower())



def _first_nonempty(*values: str | None) -> str:
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return ''
