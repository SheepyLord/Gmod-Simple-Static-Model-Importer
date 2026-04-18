"""Dialog for resolving unmatched material textures during import."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import filedialog, ttk

from PIL import Image, ImageDraw, ImageTk

from pmx_parser import PMXModel, PMXMaterial

# Suffixes considered image files
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".tif", ".tiff", ".webp"}

TranslateFn = Callable[[str], str]


def _collect_images_from_roots(*roots: Path) -> list[Path]:
    """Collect image files from one or more directory trees."""
    seen: set[Path] = set()
    results: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES:
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    results.append(path)
    results.sort(key=lambda p: p.name.lower())
    return results


def _extract_material_uvs(
    model: PMXModel, material_index: int, sub_indices: list[int] | None = None,
) -> list[tuple[float, float]]:
    """Return the list of UV coordinates for triangles belonging to *material_index*."""
    if sub_indices is None:
        # Fallback: derive from material surface_counts
        index_cursor = 0
        for i, mat in enumerate(model.materials):
            count = max(0, mat.surface_count)
            if i == material_index:
                sub_indices = model.indices[index_cursor: index_cursor + count]
                break
            index_cursor += count
        else:
            return []
    uvs: list[tuple[float, float]] = []
    for idx in sub_indices:
        if 0 <= idx < len(model.vertices):
            uvs.append(model.vertices[idx].uv)
    return uvs


def _render_uv_overlay(
    texture_image: Image.Image | None,
    uvs: list[tuple[float, float]],
    size: int = 400,
    flip_v: bool = False,
) -> Image.Image:
    """Render the texture (or grey bg) with triangle wireframes from *uvs* overlaid."""
    if texture_image is not None:
        base = texture_image.convert("RGBA").resize((size, size), Image.LANCZOS)
    else:
        base = Image.new("RGBA", (size, size), (80, 80, 80, 255))

    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Draw triangle wireframes — wrap UVs into 0-1 so tiled coordinates stay visible
    for i in range(0, len(uvs) - 2, 3):
        points = []
        for j in range(3):
            u, v = uvs[i + j]
            u = u % 1.0
            v = v % 1.0
            if flip_v:
                v = 1.0 - v
            px = u * size
            py = v * size
            points.append((px, py))
        # Close the triangle
        points.append(points[0])
        draw.line(points, fill=(0, 255, 0, 180), width=1)

    return Image.alpha_composite(base, overlay)


class MaterialPickerDialog:
    """Modal dialog asking the user to assign a texture to an unresolved material."""

    def __init__(
        self,
        parent: tk.Tk | tk.Toplevel,
        material: PMXMaterial,
        material_index: int,
        model: PMXModel,
        available_images: list[Path],
        t: TranslateFn,
        used_texture_paths: set[Path] | None = None,
        sub_indices: list[int] | None = None,
        flip_v: bool = False,
    ) -> None:
        self._result: Path | None = None
        self._skipped = False
        self._t = t
        self._model = model
        self._material = material
        self._material_index = material_index
        self._available_images = available_images
        self._used_texture_paths = used_texture_paths or set()
        self._tk_preview: ImageTk.PhotoImage | None = None

        self._flip_v = flip_v
        self._uvs = _extract_material_uvs(model, material_index, sub_indices=sub_indices)

        mat_name = material.name_en or material.name_local or f"Material {material_index}"
        raw_ref = ""
        if 0 <= material.texture_index < len(model.textures):
            raw_ref = model.textures[material.texture_index]

        self._win = tk.Toplevel(parent)
        self._win.title(t("picker_title"))
        self._win.geometry("820x560")
        self._win.resizable(True, True)
        self._win.transient(parent)
        self._win.grab_set()

        # ── Header ──
        header = ttk.Frame(self._win)
        header.pack(fill="x", padx=10, pady=(10, 4))
        ttk.Label(header, text=t("picker_header"), font=("", 11, "bold")).pack(anchor="w")
        ttk.Label(header, text=f"{t('picker_material')}: {mat_name}").pack(anchor="w")
        if raw_ref:
            ttk.Label(header, text=f"{t('picker_expected')}: {raw_ref}").pack(anchor="w")

        # ── Body: left list + right preview ──
        body = ttk.PanedWindow(self._win, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=6)

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=2)
        body.add(right, weight=3)

        # Texture list
        ttk.Label(left, text=t("picker_available")).pack(anchor="w")
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self._listbox = tk.Listbox(
            list_frame, selectmode="browse", yscrollcommand=scrollbar.set
        )
        scrollbar.configure(command=self._listbox.yview)
        self._listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for list_idx, img_path in enumerate(available_images):
            label = img_path.name
            self._listbox.insert("end", label)
            if img_path.resolve() in self._used_texture_paths:
                self._listbox.itemconfig(list_idx, fg="#888888")

        self._listbox.bind("<<ListboxSelect>>", self._on_list_select)

        # Browse button
        browse_btn = ttk.Button(left, text=t("picker_browse"), command=self._on_browse)
        browse_btn.pack(fill="x", pady=(6, 0))

        # Preview
        ttk.Label(right, text=t("picker_preview")).pack(anchor="w")
        self._preview_label = ttk.Label(right)
        self._preview_label.pack(fill="both", expand=True)

        # ── Footer buttons ──
        footer = ttk.Frame(self._win)
        footer.pack(fill="x", padx=10, pady=(4, 10))

        skip_btn = ttk.Button(footer, text=t("picker_skip"), command=self._on_skip)
        skip_btn.pack(side="left")

        confirm_btn = ttk.Button(footer, text=t("picker_confirm"), command=self._on_confirm)
        confirm_btn.pack(side="right")

        self._win.protocol("WM_DELETE_WINDOW", self._on_skip)

    # ── Event handlers ──

    def _on_list_select(self, _event: object = None) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        img_path = self._available_images[idx]
        self._show_preview(img_path)

    def _on_browse(self) -> None:
        path = filedialog.askopenfilename(
            title=self._t("picker_browse_title"),
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tga *.tif *.tiff *.webp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            p = Path(path)
            if p not in self._available_images:
                self._available_images.append(p)
                self._listbox.insert("end", p.name)
            idx = self._available_images.index(p)
            self._listbox.selection_clear(0, "end")
            self._listbox.selection_set(idx)
            self._listbox.see(idx)
            self._show_preview(p)

    def _on_skip(self) -> None:
        self._skipped = True
        self._result = None
        self._win.destroy()

    def _on_confirm(self) -> None:
        sel = self._listbox.curselection()
        if not sel:
            return
        self._result = self._available_images[sel[0]]
        self._skipped = False
        self._win.destroy()

    def _show_preview(self, img_path: Path) -> None:
        try:
            tex_img = Image.open(img_path)
        except Exception:
            tex_img = None

        preview_size = 400
        composite = _render_uv_overlay(tex_img, self._uvs, size=preview_size, flip_v=self._flip_v)
        self._tk_preview = ImageTk.PhotoImage(composite)
        self._preview_label.configure(image=self._tk_preview)

    # ── Public API ──

    def show(self) -> Path | None:
        """Block until the dialog is closed. Returns chosen Path or None if skipped."""
        self._win.wait_window()
        return self._result

    @property
    def skipped(self) -> bool:
        return self._skipped


def ask_texture_for_material(
    parent: tk.Tk | tk.Toplevel,
    material: PMXMaterial,
    material_index: int,
    model: PMXModel,
    model_dir: Path,
    t: TranslateFn,
    used_texture_paths: set[Path] | None = None,
    sub_indices: list[int] | None = None,
    boundary: Path | None = None,
    flip_v: bool = False,
) -> Path | None:
    """Convenience wrapper: collect images, show dialog, return chosen path or None."""
    search_roots: list[Path] = []
    current = model_dir.resolve()
    boundary_resolved = boundary.resolve() if boundary else None
    for _ in range(4):
        if boundary_resolved is not None:
            try:
                current.relative_to(boundary_resolved)
            except ValueError:
                # current is outside boundary – stop walking up
                break
        elif len(search_roots) >= 2:
            # No boundary set; still limit to at most model_dir + one parent
            break
        if current.exists() and current not in search_roots:
            search_roots.append(current)
        parent_dir = current.parent
        if parent_dir == current:
            break
        current = parent_dir
    if boundary_resolved is not None and not search_roots:
        # model_dir was outside boundary – fall back to boundary itself
        if boundary_resolved.exists():
            search_roots = [boundary_resolved]
    available = _collect_images_from_roots(*search_roots)
    dialog = MaterialPickerDialog(
        parent=parent,
        material=material,
        material_index=material_index,
        model=model,
        available_images=available,
        t=t,
        used_texture_paths=used_texture_paths,
        sub_indices=sub_indices,
        flip_v=flip_v,
    )
    return dialog.show()
