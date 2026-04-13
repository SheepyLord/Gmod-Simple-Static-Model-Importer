from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from typing import Callable
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

from importer_core import transform_vector
from pmx_parser import PMXModel


@dataclass(slots=True)
class PreviewTriangle:
    a: int
    b: int
    c: int
    color: tuple[int, int, int]


@dataclass(slots=True)
class PreviewGeometry:
    vertices: list[tuple[float, float, float]]
    triangles: list[PreviewTriangle]
    total_triangle_count: int
    shown_triangle_count: int
    radius: float


@dataclass(slots=True)
class PreviewStats:
    shown_triangle_count: int
    total_triangle_count: int
    vertex_count: int
    sampled: bool


class PMXPreviewWidget(ttk.Frame):
    def __init__(self, master, *, stats_callback: Callable[[PreviewStats | None], None] | None = None):
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#1b1b1b")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self._stats_callback = stats_callback
        self._photo_image: ImageTk.PhotoImage | None = None
        self._geometry: PreviewGeometry | None = None
        self._empty_message = ""
        self._render_after_id: str | None = None
        self._drag_last: tuple[int, int] | None = None
        self._yaw = math.radians(35.0)
        self._pitch = math.radians(-20.0)
        self._zoom = 1.0

        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda _event: self._adjust_zoom(1.1))
        self.canvas.bind("<Button-5>", lambda _event: self._adjust_zoom(1 / 1.1))

    def set_empty_message(self, text: str) -> None:
        self._empty_message = text
        if self._geometry is None:
            self.request_render()

    def clear(self, message: str | None = None) -> None:
        if message is not None:
            self._empty_message = message
        self._geometry = None
        self._photo_image = None
        self._notify_stats(None)
        self.request_render()

    def set_model(self, model: PMXModel | None, *, axis_preset: str, scale: float) -> None:
        if model is None or not model.vertices or not model.indices:
            self.clear()
            return
        self._geometry = build_preview_geometry(model, axis_preset=axis_preset, scale=scale)
        self._yaw = math.radians(35.0)
        self._pitch = math.radians(-20.0)
        self._zoom = 1.0
        self._notify_stats(
            PreviewStats(
                shown_triangle_count=self._geometry.shown_triangle_count,
                total_triangle_count=self._geometry.total_triangle_count,
                vertex_count=len(self._geometry.vertices),
                sampled=self._geometry.shown_triangle_count < self._geometry.total_triangle_count,
            )
        )
        self.request_render()

    def request_render(self) -> None:
        if self._render_after_id is not None:
            return
        self._render_after_id = self.after(10, self._render_now)

    def _notify_stats(self, stats: PreviewStats | None) -> None:
        if self._stats_callback is not None:
            self._stats_callback(stats)

    def _on_configure(self, _event=None) -> None:
        self.request_render()

    def _on_drag_start(self, event) -> None:
        self._drag_last = (event.x, event.y)

    def _on_drag_motion(self, event) -> None:
        if self._drag_last is None:
            self._drag_last = (event.x, event.y)
            return
        last_x, last_y = self._drag_last
        dx = event.x - last_x
        dy = event.y - last_y
        self._drag_last = (event.x, event.y)
        self._yaw += dx * 0.0125
        self._pitch += dy * 0.0125
        self._pitch = max(-1.45, min(1.45, self._pitch))
        self.request_render()

    def _on_mouse_wheel(self, event) -> None:
        if event.delta > 0:
            self._adjust_zoom(1.1)
        elif event.delta < 0:
            self._adjust_zoom(1 / 1.1)

    def _adjust_zoom(self, multiplier: float) -> None:
        self._zoom = max(0.25, min(4.0, self._zoom * multiplier))
        self.request_render()

    def _render_now(self) -> None:
        self._render_after_id = None

        width = max(2, int(self.canvas.winfo_width()))
        height = max(2, int(self.canvas.winfo_height()))
        image = Image.new("RGBA", (width, height), (27, 27, 27, 255))

        if self._geometry is None:
            if self._empty_message:
                draw = ImageDraw.Draw(image)
                draw.multiline_text(
                    (width // 2, height // 2),
                    self._empty_message,
                    fill=(210, 210, 210, 255),
                    anchor="mm",
                    align="center",
                )
            self._photo_image = ImageTk.PhotoImage(image)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, image=self._photo_image, anchor="nw")
            return

        geometry = self._geometry
        rotated_vertices = [rotate_point(vertex, yaw=self._yaw, pitch=self._pitch) for vertex in geometry.vertices]
        draw_list: list[tuple[float, list[tuple[float, float]], tuple[int, int, int, int]]] = []

        light = normalize3((0.35, 0.45, 1.0))
        radius = max(geometry.radius, 1e-6)
        cam_distance = radius * 3.0
        perspective_scale = min(width, height) * 1.55 * self._zoom

        for triangle in geometry.triangles:
            try:
                p0 = rotated_vertices[triangle.a]
                p1 = rotated_vertices[triangle.b]
                p2 = rotated_vertices[triangle.c]
            except IndexError:
                continue

            edge1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
            edge2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
            normal = cross(edge1, edge2)
            normal_length = math.sqrt((normal[0] ** 2) + (normal[1] ** 2) + (normal[2] ** 2))
            if normal_length <= 1e-8:
                continue
            normal = (normal[0] / normal_length, normal[1] / normal_length, normal[2] / normal_length)

            z0 = cam_distance - p0[2]
            z1 = cam_distance - p1[2]
            z2 = cam_distance - p2[2]
            if z0 <= 0.01 or z1 <= 0.01 or z2 <= 0.01:
                continue

            pts = [
                (
                    (width * 0.5) + (p0[0] / z0) * perspective_scale,
                    (height * 0.5) - (p0[1] / z0) * perspective_scale,
                ),
                (
                    (width * 0.5) + (p1[0] / z1) * perspective_scale,
                    (height * 0.5) - (p1[1] / z1) * perspective_scale,
                ),
                (
                    (width * 0.5) + (p2[0] / z2) * perspective_scale,
                    (height * 0.5) - (p2[1] / z2) * perspective_scale,
                ),
            ]

            intensity = 0.18 + (0.82 * abs(dot(normal, light)))
            fill = (
                max(16, min(255, int(triangle.color[0] * intensity))),
                max(16, min(255, int(triangle.color[1] * intensity))),
                max(16, min(255, int(triangle.color[2] * intensity))),
                232,
            )
            avg_depth = (p0[2] + p1[2] + p2[2]) / 3.0
            draw_list.append((avg_depth, pts, fill))

        draw_list.sort(key=lambda item: item[0])
        draw = ImageDraw.Draw(image, "RGBA")
        for _depth, pts, fill in draw_list:
            draw.polygon(pts, fill=fill, outline=(0, 0, 0, 80))

        self._photo_image = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._photo_image, anchor="nw")


MAX_PREVIEW_TRIANGLES = 3500


def build_preview_geometry(model: PMXModel, *, axis_preset: str, scale: float) -> PreviewGeometry:
    transformed_vertices = [transform_vector(vertex.position, axis_preset, scale) for vertex in model.vertices]
    if not transformed_vertices:
        return PreviewGeometry(vertices=[], triangles=[], total_triangle_count=0, shown_triangle_count=0, radius=1.0)

    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]
    for x, y, z in transformed_vertices:
        mins[0] = min(mins[0], x)
        mins[1] = min(mins[1], y)
        mins[2] = min(mins[2], z)
        maxs[0] = max(maxs[0], x)
        maxs[1] = max(maxs[1], y)
        maxs[2] = max(maxs[2], z)

    center = (
        (mins[0] + maxs[0]) * 0.5,
        (mins[1] + maxs[1]) * 0.5,
        (mins[2] + maxs[2]) * 0.5,
    )
    centered_vertices = [(x - center[0], y - center[1], z - center[2]) for x, y, z in transformed_vertices]
    radius = max(
        1e-3,
        max(math.sqrt((x * x) + (y * y) + (z * z)) for x, y, z in centered_vertices),
    )

    triangles = build_triangle_list(model)
    total_triangle_count = len(triangles)
    if total_triangle_count > MAX_PREVIEW_TRIANGLES:
        step = total_triangle_count / MAX_PREVIEW_TRIANGLES
        sampled: list[PreviewTriangle] = []
        position = 0.0
        while int(position) < total_triangle_count and len(sampled) < MAX_PREVIEW_TRIANGLES:
            sampled.append(triangles[int(position)])
            position += step
        triangles = sampled

    return PreviewGeometry(
        vertices=centered_vertices,
        triangles=triangles,
        total_triangle_count=total_triangle_count,
        shown_triangle_count=len(triangles),
        radius=radius,
    )



def build_triangle_list(model: PMXModel) -> list[PreviewTriangle]:
    triangles: list[PreviewTriangle] = []
    index_cursor = 0
    for material_index, material in enumerate(model.materials):
        count = max(0, int(material.surface_count))
        color = (
            max(45, min(245, int(round(material.diffuse[0] * 255.0)))),
            max(45, min(245, int(round(material.diffuse[1] * 255.0)))),
            max(45, min(245, int(round(material.diffuse[2] * 255.0)))),
        )
        for i in range(index_cursor, min(index_cursor + count, len(model.indices) - 2), 3):
            a = model.indices[i]
            b = model.indices[i + 1]
            c = model.indices[i + 2]
            if a < 0 or b < 0 or c < 0:
                continue
            triangles.append(PreviewTriangle(a=a, b=b, c=c, color=color))
        index_cursor += count

    if triangles:
        return triangles

    fallback_color = (185, 195, 215)
    for i in range(0, len(model.indices) - 2, 3):
        a = model.indices[i]
        b = model.indices[i + 1]
        c = model.indices[i + 2]
        if a < 0 or b < 0 or c < 0:
            continue
        triangles.append(PreviewTriangle(a=a, b=b, c=c, color=fallback_color))
    return triangles



def rotate_point(point: tuple[float, float, float], *, yaw: float, pitch: float) -> tuple[float, float, float]:
    x, y, z = point
    cos_yaw = math.cos(yaw)
    sin_yaw = math.sin(yaw)
    x1 = (x * cos_yaw) + (z * sin_yaw)
    z1 = (-x * sin_yaw) + (z * cos_yaw)

    cos_pitch = math.cos(pitch)
    sin_pitch = math.sin(pitch)
    y2 = (y * cos_pitch) - (z1 * sin_pitch)
    z2 = (y * sin_pitch) + (z1 * cos_pitch)
    return x1, y2, z2



def cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        (a[1] * b[2]) - (a[2] * b[1]),
        (a[2] * b[0]) - (a[0] * b[2]),
        (a[0] * b[1]) - (a[1] * b[0]),
    )



def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])



def normalize3(value: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt((value[0] * value[0]) + (value[1] * value[1]) + (value[2] * value[2]))
    if length <= 1e-9:
        return 0.0, 0.0, 1.0
    return value[0] / length, value[1] / length, value[2] / length
