from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO


class PMXParseError(RuntimeError):
    """Raised when a PMX file cannot be parsed."""


@dataclass(slots=True)
class PMXVertex:
    position: tuple[float, float, float]
    normal: tuple[float, float, float]
    uv: tuple[float, float]


@dataclass(slots=True)
class PMXMaterial:
    name_local: str
    name_en: str
    diffuse: tuple[float, float, float, float]
    draw_flags: int
    texture_index: int
    surface_count: int


@dataclass(slots=True)
class PMXModel:
    version: float
    text_encoding: int
    additional_uv_count: int
    name_local: str
    name_en: str
    comment_local: str
    comment_en: str
    vertices: list[PMXVertex]
    indices: list[int]
    textures: list[str]
    materials: list[PMXMaterial]
    bone_count: int = 0
    morph_count: int = 0
    source_path: Path | None = None
    source_format: str = "pmx"
    embedded_textures: dict[str, bytes] = field(default_factory=dict)

    @property
    def triangle_count(self) -> int:
        return len(self.indices) // 3

    @property
    def has_morphs(self) -> bool:
        return self.morph_count > 0


class _Reader:
    def __init__(self, fh: BinaryIO):
        self._fh = fh

    def tell(self) -> int:
        return self._fh.tell()

    def read(self, count: int) -> bytes:
        data = self._fh.read(count)
        if len(data) != count:
            raise PMXParseError(f"Unexpected end of file at offset {self.tell():#x}.")
        return data

    def skip(self, count: int) -> None:
        if count <= 0:
            return
        self.read(count)

    def unpack(self, fmt: str):
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.read(size))

    def read_u8(self) -> int:
        return self.unpack("<B")[0]

    def read_i8(self) -> int:
        return self.unpack("<b")[0]

    def read_u16(self) -> int:
        return self.unpack("<H")[0]

    def read_i16(self) -> int:
        return self.unpack("<h")[0]

    def read_u32(self) -> int:
        return self.unpack("<I")[0]

    def read_i32(self) -> int:
        return self.unpack("<i")[0]

    def read_f32(self) -> float:
        return self.unpack("<f")[0]


class PMXParser:
    """PMX parser focused on static-mesh import.

    The importer needs vertices, indices, material assignments, and texture references.
    It also reads bone/morph counts as metadata so the UI can warn when a model is
    likely intended for animation rather than static rendering.
    """

    SIGNATURE = b"PMX "

    def parse(self, path: str | Path) -> PMXModel:
        pmx_path = Path(path)
        with pmx_path.open("rb") as fh:
            model = self.parse_file(fh)
        model.source_path = pmx_path
        return model

    def parse_bytes(self, data: bytes) -> PMXModel:
        return self.parse_file(io.BytesIO(data))

    def parse_file(self, fh: BinaryIO) -> PMXModel:
        r = _Reader(fh)

        signature = r.read(4)
        if signature != self.SIGNATURE:
            raise PMXParseError("File does not start with PMX signature.")

        version = r.read_f32()
        if version < 2.0 or version > 2.1:
            raise PMXParseError(f"Unsupported PMX version: {version!r}")

        header_size = r.read_u8()
        global_settings = list(r.read(header_size))
        if len(global_settings) < 8:
            raise PMXParseError("PMX global settings header is too short.")

        text_encoding = global_settings[0]
        additional_uv_count = global_settings[1]
        vertex_index_size = global_settings[2]
        texture_index_size = global_settings[3]
        material_index_size = global_settings[4]
        bone_index_size = global_settings[5]
        morph_index_size = global_settings[6]
        rigidbody_index_size = global_settings[7]

        if text_encoding not in (0, 1):
            raise PMXParseError(f"Unsupported PMX text encoding value: {text_encoding}")
        if additional_uv_count < 0 or additional_uv_count > 4:
            raise PMXParseError(f"Unsupported additional UV count: {additional_uv_count}")

        name_local = self._read_text(r, text_encoding)
        name_en = self._read_text(r, text_encoding)
        comment_local = self._read_text(r, text_encoding)
        comment_en = self._read_text(r, text_encoding)

        vertex_count = r.read_i32()
        if vertex_count < 0:
            raise PMXParseError("Negative vertex count.")
        vertices: list[PMXVertex] = []
        vertices_extend = vertices.append
        for _ in range(vertex_count):
            px, py, pz = r.unpack("<3f")
            nx, ny, nz = r.unpack("<3f")
            u, v = r.unpack("<2f")
            if additional_uv_count:
                r.skip(16 * additional_uv_count)
            self._skip_vertex_deform(r, bone_index_size)
            r.read_f32()  # edge scale
            vertices_extend(PMXVertex((px, py, pz), (nx, ny, nz), (u, v)))

        face_index_count = r.read_i32()
        if face_index_count < 0:
            raise PMXParseError("Negative face index count.")
        indices = [self._read_vertex_index(r, vertex_index_size) for _ in range(face_index_count)]

        texture_count = r.read_i32()
        if texture_count < 0:
            raise PMXParseError("Negative texture count.")
        textures = [self._read_text(r, text_encoding) for _ in range(texture_count)]

        material_count = r.read_i32()
        if material_count < 0:
            raise PMXParseError("Negative material count.")
        materials: list[PMXMaterial] = []
        materials_extend = materials.append
        for _ in range(material_count):
            mat_name_local = self._read_text(r, text_encoding)
            mat_name_en = self._read_text(r, text_encoding)
            dr, dg, db, da = r.unpack("<4f")
            r.skip(16)  # specular rgb + power
            r.skip(12)  # ambient rgb
            draw_flags = r.read_u8()
            r.skip(20)  # edge color + edge size
            texture_index = self._read_signed_index(r, texture_index_size)
            self._read_signed_index(r, texture_index_size)  # sphere texture index
            r.read_u8()  # sphere mode
            toon_mode = r.read_u8()
            if toon_mode == 0:
                self._read_signed_index(r, texture_index_size)
            else:
                r.read_i8()
            self._read_text(r, text_encoding)  # memo
            surface_count = r.read_i32()
            materials_extend(
                PMXMaterial(
                    name_local=mat_name_local,
                    name_en=mat_name_en,
                    diffuse=(dr, dg, db, da),
                    draw_flags=draw_flags,
                    texture_index=texture_index,
                    surface_count=surface_count,
                )
            )

        bone_count, morph_count = self._read_animation_metadata_best_effort(
            r=r,
            text_encoding=text_encoding,
            bone_index_size=bone_index_size,
        )

        _ = material_index_size, morph_index_size, rigidbody_index_size

        return PMXModel(
            version=version,
            text_encoding=text_encoding,
            additional_uv_count=additional_uv_count,
            name_local=name_local,
            name_en=name_en,
            comment_local=comment_local,
            comment_en=comment_en,
            vertices=vertices,
            indices=indices,
            textures=textures,
            materials=materials,
            bone_count=bone_count,
            morph_count=morph_count,
        )

    def _read_animation_metadata_best_effort(self, *, r: _Reader, text_encoding: int, bone_index_size: int) -> tuple[int, int]:
        """Read bone/morph counts without turning metadata issues into hard import failures."""
        try:
            bone_count = r.read_i32()
            if bone_count < 0:
                bone_count = 0
            else:
                self._skip_bones(r=r, text_encoding=text_encoding, bone_index_size=bone_index_size, bone_count=bone_count)

            morph_count = r.read_i32()
            if morph_count < 0:
                morph_count = 0
            return bone_count, morph_count
        except Exception:
            return 0, 0

    @staticmethod
    def _read_text(r: _Reader, text_encoding: int) -> str:
        byte_length = r.read_i32()
        if byte_length < 0:
            raise PMXParseError("Negative PMX text byte length.")
        raw = r.read(byte_length)
        if not raw:
            return ""
        encoding = "utf-16-le" if text_encoding == 0 else "utf-8"
        return raw.decode(encoding, errors="replace").rstrip("\x00")

    @staticmethod
    def _read_vertex_index(r: _Reader, size: int) -> int:
        if size == 1:
            return r.read_u8()
        if size == 2:
            return r.read_u16()
        if size == 4:
            return r.read_u32()
        raise PMXParseError(f"Unsupported vertex index size: {size}")

    @staticmethod
    def _read_signed_index(r: _Reader, size: int) -> int:
        if size == 1:
            return r.read_i8()
        if size == 2:
            return r.read_i16()
        if size == 4:
            return r.read_i32()
        raise PMXParseError(f"Unsupported signed index size: {size}")

    def _skip_vertex_deform(self, r: _Reader, bone_index_size: int) -> None:
        deform_type = r.read_u8()
        if deform_type == 0:  # BDEF1
            self._read_signed_index(r, bone_index_size)
            return
        if deform_type == 1:  # BDEF2
            self._read_signed_index(r, bone_index_size)
            self._read_signed_index(r, bone_index_size)
            r.skip(4)
            return
        if deform_type == 2:  # BDEF4
            for _ in range(4):
                self._read_signed_index(r, bone_index_size)
            r.skip(16)
            return
        if deform_type == 3:  # SDEF
            self._read_signed_index(r, bone_index_size)
            self._read_signed_index(r, bone_index_size)
            r.skip(4 + 12 + 12 + 12)
            return
        if deform_type == 4:  # QDEF (PMX 2.1)
            for _ in range(4):
                self._read_signed_index(r, bone_index_size)
            r.skip(16)
            return
        raise PMXParseError(f"Unsupported vertex deform type: {deform_type}")

    def _skip_bones(self, *, r: _Reader, text_encoding: int, bone_index_size: int, bone_count: int) -> None:
        for _ in range(bone_count):
            self._read_text(r, text_encoding)
            self._read_text(r, text_encoding)
            r.skip(12)  # position
            self._read_signed_index(r, bone_index_size)  # parent bone
            r.skip(4)  # deform layer
            flags = r.read_u16()

            if flags & 0x0001:
                self._read_signed_index(r, bone_index_size)  # tail bone index
            else:
                r.skip(12)  # tail position offset

            if flags & 0x0100 or flags & 0x0200:
                self._read_signed_index(r, bone_index_size)  # inherit parent
                r.skip(4)  # inherit ratio

            if flags & 0x0400:
                r.skip(12)  # fixed axis

            if flags & 0x0800:
                r.skip(24)  # local axes

            if flags & 0x2000:
                r.skip(4)  # external parent key

            if flags & 0x0020:  # IK
                self._read_signed_index(r, bone_index_size)  # target bone
                r.skip(4)  # loop count
                r.skip(4)  # angle limit
                link_count = r.read_i32()
                if link_count < 0:
                    raise PMXParseError("Negative IK link count.")
                for _ in range(link_count):
                    self._read_signed_index(r, bone_index_size)
                    has_limits = r.read_u8()
                    if has_limits:
                        r.skip(24)  # min/max angles
