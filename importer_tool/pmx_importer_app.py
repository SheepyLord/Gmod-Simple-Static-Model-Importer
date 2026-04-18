from __future__ import annotations

import os
import re
import threading
import traceback
import webbrowser
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen, Request
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from _compile_date import COMPILE_DATE

from archive_utils import StagedSource, stage_input
from cl_material_picker import ask_texture_for_material
from gmod_locator import find_gmod_installations, normalize_game_root
from i18n import CODE_BY_LANGUAGE_NAME, LANGUAGE_NAME_BY_CODE, LANGUAGE_OPTIONS, detect_default_language, tr
from importer_core import (
    ImportOptions,
    ImportedModelRecord,
    StaticImportWarning,
    build_model_id,
    collect_static_import_warnings,
    default_scale_for_path,
    ensure_unique_model_id,
    export_models_as_gma,
    import_pmx_model,
    is_valid_display_name,
    list_imported_models,
    normalize_display_name,
    remove_imported_model,
    sanitize_ascii_name,
    suggest_display_name,
)
from pmx_parser import PMXModel, PMXParseError
from preview_renderer import PMXPreviewWidget, PreviewStats
from scene_loader import SceneLoadError, load_supported_model, scan_supported_model_files


_AXIS_LABELS = {
    "x,-z,y": "MMD-ish -> Source (X, -Z, Y) [default]",
    "x,z,y": "Swap Y/Z only (X, Z, Y)",
    "-x,-z,y": "Flip X and Z (-X, -Z, Y)",
    "x,y,z": "No axis remap (X, Y, Z)",
}

_RELEASES_URL = "https://github.com/SheepyLord/Gmod-Simple-Static-Model-Importer/releases/tag/Release"
_RELEASES_API_URL = "https://api.github.com/repos/SheepyLord/Gmod-Simple-Static-Model-Importer/releases/tags/Release"
_UPDATE_THRESHOLD_DAYS = 3


def _check_for_update() -> str:
    """Return 'update', 'up_to_date', or 'error'.

    Uses the GitHub API to get the release's ``updated_at`` timestamp, which
    reflects the most recent asset upload.  If that date is more than
    _UPDATE_THRESHOLD_DAYS after the compile date, returns 'update'.
    """
    try:
        import json as _json

        compile_dt = datetime.strptime(COMPILE_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        req = Request(
            _RELEASES_API_URL,
            headers={
                "User-Agent": "PMXStaticImporter-UpdateCheck",
                "Accept": "application/vnd.github+json",
            },
        )
        with urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read().decode("utf-8", errors="replace"))

        # Prefer the most recent asset upload date, fall back to release updated_at
        candidate_dates: list[str] = []
        for asset in data.get("assets") or []:
            ts = asset.get("updated_at") or asset.get("created_at")
            if ts:
                candidate_dates.append(ts)
        if not candidate_dates:
            ts = data.get("updated_at") or data.get("published_at")
            if ts:
                candidate_dates.append(ts)
        if not candidate_dates:
            return "error"

        latest_str = max(candidate_dates)[:10]  # "YYYY-MM-DD"
        latest_dt = datetime.strptime(latest_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if latest_dt >= compile_dt + timedelta(days=_UPDATE_THRESHOLD_DAYS):
            return "update"
        return "up_to_date"
    except Exception:
        return "error"


@dataclass(slots=True)
class ModelSummary:
    path: Path
    display_name_suggestion: str
    generated_model_id: str
    vertex_count: int
    triangle_count: int
    material_count: int
    texture_count: int
    bone_count: int
    morph_count: int
    warnings: list[StaticImportWarning]
    model: PMXModel


class PMXImporterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.staged_source: StagedSource | None = None
        self.model_summaries: dict[str, ModelSummary] = {}
        self.installed_records: list[ImportedModelRecord] = []
        self.installed_records_by_iid: dict[str, ImportedModelRecord] = {}

        self._language_code = detect_default_language()
        self._preview_after_id: str | None = None
        self._setting_display_name = False

        self.gmod_path_var = tk.StringVar()
        self.display_name_var = tk.StringVar()
        self.generated_id_var = tk.StringVar()
        self.language_name_var = tk.StringVar(value=LANGUAGE_NAME_BY_CODE.get(self._language_code, "English"))
        self.axis_var = tk.StringVar(value="x,-z,y")
        self.scale_var = tk.StringVar(value="3.6")
        self.flip_v_var = tk.BooleanVar(value=False)
        self.ignore_missing_tex_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value=self.t("status_ready"))
        self.display_name_status_var = tk.StringVar(value="")
        self.preview_info_var = tk.StringVar(value="")
        self.preview_warning_var = tk.StringVar(value="")
        self.installed_empty_var = tk.StringVar(value="")

        self._build_ui()
        self._apply_language()
        self._setup_variable_traces()
        self._setup_window_drop_target()
        self._autodetect_gmod()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start_update_check()

    def t(self, key: str, **kwargs) -> str:
        return tr(self._language_code, key, **kwargs)

    def _set_status(self, text: str, *, fg: str = "") -> None:
        self._status_fg_override = fg
        self.status_var.set(text)

    def _on_status_var_changed(self, *_args) -> None:
        fg = getattr(self, "_status_fg_override", "")
        self.status_label.configure(fg=fg)
        self._status_fg_override = ""

    def _build_ui(self) -> None:
        self.root.geometry("1200x820")
        self.root.minsize(1080, 720)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        header = ttk.Frame(self.root, padding=10)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        left_header = ttk.Frame(header)
        left_header.grid(row=0, column=0, sticky="w")
        self.header_title_label = ttk.Label(left_header, font=("Segoe UI", 15, "bold"))
        self.header_title_label.grid(row=0, column=0, sticky="w")
        self.header_subtitle_label = ttk.Label(left_header)
        self.header_subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        language_frame = ttk.Frame(header)
        language_frame.grid(row=0, column=1, sticky="e")
        self.language_label = ttk.Label(language_frame)
        self.language_label.grid(row=0, column=0, sticky="e", padx=(0, 8))
        self.language_combo = ttk.Combobox(
            language_frame,
            state="readonly",
            values=[name for _code, name in LANGUAGE_OPTIONS],
            textvariable=self.language_name_var,
            width=16,
        )
        self.language_combo.grid(row=0, column=1, sticky="e")
        self.language_combo.bind("<<ComboboxSelected>>", self._on_language_changed)

        top = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        top.grid(row=1, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)

        self.source_frame = ttk.LabelFrame(top, padding=10)
        self.source_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.source_frame.columnconfigure(0, weight=1)

        self.drop_label = tk.Label(
            self.source_frame,
            relief="groove",
            bd=2,
            padx=20,
            pady=24,
            justify="center",
            bg="#1f1f1f",
            fg="white",
        )
        self.drop_label.grid(row=0, column=0, sticky="ew")

        source_buttons = ttk.Frame(self.source_frame)
        source_buttons.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.browse_archive_button = ttk.Button(source_buttons, command=self._browse_archive)
        self.browse_archive_button.grid(row=0, column=0, padx=(0, 6))
        self.browse_folder_button = ttk.Button(source_buttons, command=self._browse_folder)
        self.browse_folder_button.grid(row=0, column=1)

        self.settings_frame = ttk.LabelFrame(top, padding=10)
        self.settings_frame.grid(row=0, column=1, sticky="nsew")
        self.settings_frame.columnconfigure(1, weight=1)

        self.gmod_label = ttk.Label(self.settings_frame)
        self.gmod_label.grid(row=0, column=0, sticky="w")
        self.gmod_entry = ttk.Entry(self.settings_frame, textvariable=self.gmod_path_var)
        self.gmod_entry.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        self.gmod_entry.bind("<Return>", self._on_gmod_path_committed)
        self.gmod_entry.bind("<FocusOut>", self._on_gmod_path_committed)
        gmod_buttons = ttk.Frame(self.settings_frame)
        gmod_buttons.grid(row=0, column=2, sticky="e")
        self.gmod_auto_button = ttk.Button(gmod_buttons, command=self._autodetect_gmod)
        self.gmod_auto_button.grid(row=0, column=0, padx=(0, 6))
        self.gmod_browse_button = ttk.Button(gmod_buttons, command=self._browse_gmod)
        self.gmod_browse_button.grid(row=0, column=1)

        self.display_name_label = ttk.Label(self.settings_frame)
        self.display_name_label.grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.display_name_entry = ttk.Entry(self.settings_frame, textvariable=self.display_name_var)
        self.display_name_entry.grid(row=1, column=1, sticky="ew", padx=(8, 8), pady=(10, 0))
        self.display_name_help_label = ttk.Label(self.settings_frame)
        self.display_name_help_label.grid(row=1, column=2, sticky="w", pady=(10, 0))

        self.generated_id_label = ttk.Label(self.settings_frame)
        self.generated_id_label.grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.generated_id_value_label = ttk.Label(self.settings_frame, textvariable=self.generated_id_var, font=("Segoe UI", 9, "bold"))
        self.generated_id_value_label.grid(row=2, column=1, sticky="w", padx=(8, 8), pady=(10, 0))
        self.generated_id_help_label = ttk.Label(self.settings_frame)
        self.generated_id_help_label.grid(row=2, column=2, sticky="w", pady=(10, 0))

        self.display_name_status_label = tk.Label(self.settings_frame, textvariable=self.display_name_status_var, anchor="w")
        self.display_name_status_label.grid(row=3, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=(4, 0))

        self.axis_label = ttk.Label(self.settings_frame)
        self.axis_label.grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.axis_combo = ttk.Combobox(self.settings_frame, state="readonly", values=list(_AXIS_LABELS.values()))
        self.axis_combo.grid(row=4, column=1, sticky="ew", padx=(8, 8), pady=(10, 0))
        self.axis_combo.set(_AXIS_LABELS[self.axis_var.get()])
        self.axis_combo.bind("<<ComboboxSelected>>", self._on_axis_changed)

        self.scale_label = ttk.Label(self.settings_frame)
        self.scale_label.grid(row=5, column=0, sticky="w", pady=(10, 0))
        self.scale_entry = ttk.Entry(self.settings_frame, textvariable=self.scale_var, width=10)
        self.scale_entry.grid(row=5, column=1, sticky="w", padx=(8, 8), pady=(10, 0))
        self.scale_help_label = ttk.Label(self.settings_frame)
        self.scale_help_label.grid(row=5, column=2, sticky="w", pady=(10, 0))

        self.flip_v_check = ttk.Checkbutton(self.settings_frame, variable=self.flip_v_var)
        self.flip_v_check.grid(row=6, column=0, sticky="w", pady=(10, 0))
        self.flip_v_hint_label = tk.Label(self.settings_frame, fg="red", font=("", 9))
        self.flip_v_hint_label.grid(row=6, column=1, columnspan=2, sticky="w", padx=(4, 0), pady=(10, 0))
        self.flip_v_var.trace_add("write", self._on_flip_v_changed)

        self.ignore_missing_tex_check = ttk.Checkbutton(self.settings_frame, variable=self.ignore_missing_tex_var)
        self.ignore_missing_tex_check.grid(row=7, column=0, columnspan=3, sticky="w", pady=(10, 0))

        action_row = ttk.Frame(self.settings_frame)
        action_row.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        self.open_workshop_button = ttk.Button(action_row, command=self._open_workshop_page)
        self.open_workshop_button.grid(row=0, column=0, padx=(0, 6))
        self.import_button = ttk.Button(action_row, command=self._import_selected_model)
        self.import_button.grid(row=0, column=1)

        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        left_panel = ttk.Frame(body)
        right_panel = ttk.Frame(body)
        body.add(left_panel, weight=3)
        body.add(right_panel, weight=2)

        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(1, weight=1)
        self.pmx_list_title_label = ttk.Label(left_panel, font=("Segoe UI", 11, "bold"))
        self.pmx_list_title_label.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.tree = ttk.Treeview(
            left_panel,
            columns=("file", "display", "tris", "mats", "textures"),
            show="headings",
            selectmode="browse",
        )
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.column("file", width=260, anchor="w")
        self.tree.column("display", width=240, anchor="w")
        self.tree.column("tris", width=90, anchor="e")
        self.tree.column("mats", width=80, anchor="e")
        self.tree.column("textures", width=80, anchor="e")
        pmx_scroll = ttk.Scrollbar(left_panel, orient="vertical", command=self.tree.yview)
        pmx_scroll.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=pmx_scroll.set)

        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self.preview_tab = ttk.Frame(self.notebook, padding=8)
        self.details_tab = ttk.Frame(self.notebook, padding=8)
        self.installed_tab = ttk.Frame(self.notebook, padding=8)
        self.log_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.preview_tab, text="")
        self.notebook.add(self.details_tab, text="")
        self.notebook.add(self.installed_tab, text="")
        self.notebook.add(self.log_tab, text="")

        self.preview_tab.columnconfigure(0, weight=1)
        self.preview_tab.rowconfigure(0, weight=1)
        self.preview_widget = PMXPreviewWidget(self.preview_tab, stats_callback=self._on_preview_stats)
        self.preview_widget.grid(row=0, column=0, sticky="nsew")
        self.preview_hint_label = ttk.Label(self.preview_tab, wraplength=420, justify="left")
        self.preview_hint_label.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.preview_info_label = ttk.Label(self.preview_tab, textvariable=self.preview_info_var, justify="left")
        self.preview_info_label.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self.preview_warning_label = tk.Label(
            self.preview_tab,
            textvariable=self.preview_warning_var,
            justify="left",
            anchor="w",
            bg=self.root.cget("bg"),
            fg="#b06d00",
        )
        self.preview_warning_label.grid(row=3, column=0, sticky="ew", pady=(6, 0))

        self.details_tab.columnconfigure(0, weight=1)
        self.details_tab.rowconfigure(0, weight=1)
        self.info_text = tk.Text(self.details_tab, wrap="word", state="disabled")
        self.info_text.grid(row=0, column=0, sticky="nsew")
        info_scroll = ttk.Scrollbar(self.details_tab, orient="vertical", command=self.info_text.yview)
        info_scroll.grid(row=0, column=1, sticky="ns")
        self.info_text.configure(yscrollcommand=info_scroll.set)

        self.installed_tab.columnconfigure(0, weight=1)
        self.installed_tab.rowconfigure(0, weight=1)
        self.installed_tree = ttk.Treeview(
            self.installed_tab,
            columns=("id", "display", "tris", "mats", "updated"),
            show="headings",
            selectmode="extended",
            height=12,
        )
        self.installed_tree.grid(row=0, column=0, sticky="nsew")
        self.installed_tree.column("id", width=170, anchor="w")
        self.installed_tree.column("display", width=180, anchor="w")
        self.installed_tree.column("tris", width=90, anchor="e")
        self.installed_tree.column("mats", width=80, anchor="e")
        self.installed_tree.column("updated", width=130, anchor="w")
        installed_scroll = ttk.Scrollbar(self.installed_tab, orient="vertical", command=self.installed_tree.yview)
        installed_scroll.grid(row=0, column=1, sticky="ns")
        self.installed_tree.configure(yscrollcommand=installed_scroll.set)

        installed_actions = ttk.Frame(self.installed_tab)
        installed_actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.installed_refresh_button = ttk.Button(installed_actions, command=self._refresh_imported_models)
        self.installed_refresh_button.grid(row=0, column=0, padx=(0, 6))
        self.installed_remove_button = ttk.Button(installed_actions, command=self._remove_selected_installed)
        self.installed_remove_button.grid(row=0, column=1, padx=(0, 6))
        self.installed_export_button = ttk.Button(installed_actions, command=self._export_selected_as_gma)
        self.installed_export_button.grid(row=0, column=2)
        self.installed_empty_label = ttk.Label(self.installed_tab, textvariable=self.installed_empty_var, wraplength=420, justify="left")
        self.installed_empty_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self.log_tab.columnconfigure(0, weight=1)
        self.log_tab.rowconfigure(0, weight=1)
        self.log_text = tk.Text(self.log_tab, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(self.log_tab, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        # Update notification (hidden by default)
        self.update_label = tk.Label(
            self.root,
            text="",
            fg="#1a6dd4",
            cursor="hand2",
            font=("Segoe UI", 9, "underline"),
            anchor="w",
            padx=10,
        )
        self.update_label.grid(row=3, column=0, sticky="ew")
        self.update_label.grid_remove()
        self.update_label.bind("<Button-1>", lambda _e: webbrowser.open(_RELEASES_URL))

        self.status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            padx=10,
            pady=5,
        )
        self.status_label.grid(row=4, column=0, sticky="ew")

    def _setup_variable_traces(self) -> None:
        self.display_name_var.trace_add("write", self._on_display_name_var_changed)
        self.scale_var.trace_add("write", self._on_preview_setting_var_changed)
        self.axis_var.trace_add("write", self._on_preview_setting_var_changed)
        self.status_var.trace_add("write", self._on_status_var_changed)

    def _apply_language(self) -> None:
        self.root.title(self.t("app_window_title"))
        self.header_title_label.configure(text=self.t("header_title"))
        self.header_subtitle_label.configure(text=self.t("header_subtitle"))
        self.language_label.configure(text=self.t("language"))
        self.source_frame.configure(text=self.t("source_group"))
        self.drop_label.configure(text=self.t("drop_hint"))
        self.browse_archive_button.configure(text=self.t("browse_archive"))
        self.browse_folder_button.configure(text=self.t("browse_folder"))
        self.settings_frame.configure(text=self.t("import_settings_group"))
        self.gmod_label.configure(text=self.t("gmod_folder"))
        self.gmod_auto_button.configure(text=self.t("auto_detect"))
        self.gmod_browse_button.configure(text=self.t("browse"))
        self.display_name_label.configure(text=self.t("display_name"))
        self.display_name_help_label.configure(text=self.t("display_name_help"))
        self.generated_id_label.configure(text=self.t("generated_model_id"))
        self.generated_id_help_label.configure(text=self.t("generated_model_id_help"))
        self.axis_label.configure(text=self.t("axis_preset"))
        self.scale_label.configure(text=self.t("scale"))
        self.scale_help_label.configure(text=self.t("scale_help"))
        self.flip_v_check.configure(text=self.t("flip_v"))
        self._on_flip_v_changed()
        self.ignore_missing_tex_check.configure(text=self.t("ignore_missing_tex"))
        self.open_workshop_button.configure(text=self.t("open_workshop"))
        self.import_button.configure(text=self.t("import_selected"))
        self.pmx_list_title_label.configure(text=self.t("pmx_list_title"))

        self.tree.heading("file", text=self.t("pmx_col_file"))
        self.tree.heading("display", text=self.t("pmx_col_display"))
        self.tree.heading("tris", text=self.t("pmx_col_tris"))
        self.tree.heading("mats", text=self.t("pmx_col_mats"))
        self.tree.heading("textures", text=self.t("pmx_col_textures"))

        self.notebook.tab(self.preview_tab, text=self.t("tab_preview"))
        self.notebook.tab(self.details_tab, text=self.t("tab_details"))
        self.notebook.tab(self.installed_tab, text=self.t("tab_installed"))
        self.notebook.tab(self.log_tab, text=self.t("tab_log"))
        self.preview_hint_label.configure(text=self.t("preview_hint"))
        self.preview_widget.set_empty_message(self.t("preview_empty"))

        self.installed_tree.heading("id", text=self.t("installed_col_id"))
        self.installed_tree.heading("display", text=self.t("installed_col_display"))
        self.installed_tree.heading("tris", text=self.t("installed_col_tris"))
        self.installed_tree.heading("mats", text=self.t("installed_col_mats"))
        self.installed_tree.heading("updated", text=self.t("installed_col_updated"))
        self.installed_refresh_button.configure(text=self.t("installed_refresh"))
        self.installed_remove_button.configure(text=self.t("installed_remove"))
        self.installed_export_button.configure(text=self.t("installed_export_gma"))

        # Update the update-available label text if it's visible
        if self.update_label.winfo_ismapped():
            state = getattr(self, "_update_check_state", None)
            if state == "update":
                self.update_label.configure(text=self.t("update_available"))
            elif state == "up_to_date":
                self.update_label.configure(text=self.t("update_up_to_date"))
            elif state == "error":
                self.update_label.configure(text=self.t("update_check_failed"))

        if not self.status_var.get().strip():
            self.status_var.set(self.t("status_ready"))

        self._refresh_imported_models(quiet=True, keep_status=True)
        self._update_generated_model_id()
        self._update_details(self._get_selected_summary())
        self._update_preview(self._get_selected_summary())

    def _on_language_changed(self, _event=None) -> None:
        selected_name = self.language_name_var.get()
        self._language_code = CODE_BY_LANGUAGE_NAME.get(selected_name, "en")
        self._apply_language()

    def _on_axis_changed(self, _event=None) -> None:
        selected_label = self.axis_combo.get()
        for key, label in _AXIS_LABELS.items():
            if label == selected_label:
                self.axis_var.set(key)
                break

    def _setup_window_drop_target(self) -> None:
        if os.name != "nt":
            self.log("Drag-and-drop is enabled automatically on Windows builds. On this platform, use the Browse buttons.")
            return

        try:
            enable_windows_drop_target(self.root, self._handle_dropped_paths)
            self.log(self.t("drag_drop_enabled"))
        except Exception as exc:
            detail = str(exc).strip()
            lowered = detail.lower()
            if "_ctypes" in lowered or "ctypes" in lowered:
                self.log(self.t("drag_drop_ctypes_unavailable"))
            else:
                self.log(self.t("drag_drop_failed", error=exc))

    def _handle_dropped_paths(self, paths: list[str]) -> None:
        if not paths:
            return
        self.open_source(paths[0])

    def _browse_archive(self) -> None:
        path = filedialog.askopenfilename(
            title=self.t("browse_archive"),
            filetypes=[("Archives", "*.zip *.rar"), ("ZIP files", "*.zip"), ("RAR files", "*.rar"), ("All files", "*.*")],
        )
        if path:
            self.open_source(path)

    def _browse_folder(self) -> None:
        path = filedialog.askdirectory(title=self.t("browse_folder"))
        if path:
            self.open_source(path)

    def _browse_gmod(self) -> None:
        path = filedialog.askdirectory(title=self.t("gmod_folder"))
        if not path:
            return
        try:
            install = normalize_game_root(path)
        except FileNotFoundError as exc:
            messagebox.showerror(self.t("invalid_gmod_title"), str(exc))
            return
        self.gmod_path_var.set(str(install.game_root))
        self.status_var.set(self.t("status_gmod_selected", path=install.game_root))
        self.log(self.t("status_gmod_selected", path=install.game_root))
        self._refresh_imported_models()

    def _autodetect_gmod(self) -> None:
        installs = find_gmod_installations()
        if installs:
            self.gmod_path_var.set(str(installs[0].game_root))
            self.status_var.set(self.t("status_gmod_detected", path=installs[0].game_root))
            self.log(self.t("status_gmod_detected", path=installs[0].game_root))
            self._refresh_imported_models()
            return
        self.status_var.set(self.t("status_gmod_not_found"))
        self.log(self.t("status_gmod_not_found"))
        self._refresh_imported_models(quiet=True, keep_status=True)

    def _on_gmod_path_committed(self, _event=None) -> None:
        self._refresh_imported_models(quiet=True, keep_status=True)

    def open_source(self, path: str | Path) -> None:
        self._cleanup_staged_source()
        self.model_summaries.clear()
        self.tree.delete(*self.tree.get_children())
        self._set_display_name_programmatically("")
        self._set_info_text("")
        self.preview_widget.clear(self.t("preview_empty"))
        self.preview_warning_var.set("")

        # Check source size and prompt if > 10 MB
        src = Path(path).expanduser().resolve()
        size_mb = self._get_source_size_mb(src)
        if size_mb > 10:
            if not messagebox.askyesno(
                self.t("large_source_title"),
                self.t("large_source_confirm", size_mb=size_mb),
            ):
                return

        self._set_status(self.t("status_working_open_source"), fg="#1a6dd4")
        self.root.update_idletasks()

        try:
            staged = stage_input(path, log=self.log)
            self.staged_source = staged
            model_files = scan_supported_model_files(staged.workspace_path)
            if not model_files:
                raise FileNotFoundError(self.t("source_no_pmx"))

            for model_file in model_files:
                summary = self._build_summary(model_file)
                key = model_file.as_posix()
                self.model_summaries[key] = summary
                file_label = model_file.relative_to(staged.workspace_path).as_posix()
                self.tree.insert(
                    "",
                    "end",
                    iid=key,
                    values=(
                        file_label,
                        summary.display_name_suggestion,
                        f"{summary.triangle_count:,}",
                        f"{summary.material_count:,}",
                        f"{summary.texture_count:,}",
                    ),
                )

            first = model_files[0].as_posix()
            self.tree.selection_set(first)
            self.tree.focus(first)
            self._on_tree_select()
            self.status_var.set(self.t("status_loaded_source", count=len(model_files), path=staged.workspace_path))
            self.log(self.t("loaded_source_log", count=len(model_files)))
        except Exception as exc:
            self._cleanup_staged_source()
            self.status_var.set(self.t("status_open_failed"))
            self.log(self.t("open_source_failed_log", error=exc))
            self.log(traceback.format_exc())
            messagebox.showerror(self.t("open_source_failed_title"), str(exc))

    def _build_summary(self, pmx_file: Path) -> ModelSummary:
        boundary = self.staged_source.workspace_path if self.staged_source else None
        try:
            model = load_supported_model(pmx_file, log=self.log, boundary=boundary)
        except PMXParseError as exc:
            raise PMXParseError(f"{pmx_file.name}: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"{pmx_file.name}: {exc}") from exc

        display_name_suggestion = suggest_display_name(model)
        generated_model_id = self._unique_model_id_for_name(display_name_suggestion, model)
        warnings = collect_static_import_warnings(model)
        return ModelSummary(
            path=pmx_file,
            display_name_suggestion=display_name_suggestion,
            generated_model_id=generated_model_id,
            vertex_count=len(model.vertices),
            triangle_count=model.triangle_count,
            material_count=len(model.materials),
            texture_count=len(model.textures),
            bone_count=model.bone_count,
            morph_count=model.morph_count,
            warnings=warnings,
            model=model,
        )

    def _get_selected_summary(self) -> ModelSummary | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self.model_summaries.get(selection[0])

    def _on_tree_select(self, _event=None) -> None:
        summary = self._get_selected_summary()
        if summary is None:
            self._set_info_text("")
            self.preview_widget.clear(self.t("preview_empty"))
            self.preview_warning_var.set("")
            return

        self._set_display_name_programmatically(summary.display_name_suggestion)
        self._update_generated_model_id()
        self.scale_var.set(str(default_scale_for_path(summary.path)))
        suffix = summary.path.suffix.lower()
        is_pmx = suffix == ".pmx"
        self.flip_v_var.set(not is_pmx)
        self.ignore_missing_tex_var.set(suffix in (".glb", ".gltf"))
        self._update_details(summary)
        self._update_preview(summary)
        self.log(self.t("auto_selected_pmx", name=summary.path.name))

    def _on_flip_v_changed(self, *_args) -> None:
        if self.flip_v_var.get():
            self.flip_v_hint_label.configure(text=self.t("flip_v_hint"))
        else:
            self.flip_v_hint_label.configure(text="")

    def _update_details(self, summary: ModelSummary | None) -> None:
        if summary is None:
            self._set_info_text("")
            return

        material_lines = []
        for index, material in enumerate(summary.model.materials):
            display_name = material.name_en or material.name_local or f"Material {index}"
            tex_ref = self.t("details_texture_none")
            if 0 <= material.texture_index < len(summary.model.textures):
                tex_ref = summary.model.textures[material.texture_index]
            material_lines.append(
                f"  {index:02d}. {display_name} | texture={tex_ref} | {self.t('details_faces')}={material.surface_count // 3}"
            )

        warning_lines = self._format_warning_lines(summary.warnings)
        if not warning_lines:
            warning_lines = [f"  {self.t('details_no_warnings')}"]

        info = [
            f"{self.t('details_source_file')}: {summary.path}",
            f"{self.t('details_display_name')}: {normalize_display_name(self.display_name_var.get()) or summary.display_name_suggestion}",
            f"{self.t('details_generated_id')}: {self.generated_id_var.get() or summary.generated_model_id}",
            f"{self.t('details_vertices')}: {summary.vertex_count:,}",
            f"{self.t('details_triangles')}: {summary.triangle_count:,}",
            f"{self.t('details_materials')}: {summary.material_count:,}",
            f"{self.t('details_textures')}: {summary.texture_count:,}",
            f"{self.t('details_bones')}: {summary.bone_count:,}",
            f"{self.t('details_morphs')}: {summary.morph_count:,}",
            "",
            f"{self.t('details_warnings')}:",
            *warning_lines,
            "",
            f"{self.t('details_material_list')}:",
            *material_lines,
        ]
        self._set_info_text("\n".join(info))

    def _format_warning_lines(self, warnings: list[StaticImportWarning]) -> list[str]:
        lines: list[str] = []
        for warning in warnings:
            if warning.code == "bones":
                lines.append(self.t("warning_bones", value=warning.value))
            elif warning.code == "vertices":
                lines.append(self.t("warning_vertices", value=warning.value, time=warning.value / 25000))
            elif warning.code == "morphs":
                lines.append(self.t("warning_morphs", value=warning.value))
            elif warning.code == "submesh_vertices":
                lines.append(self.t("warning_submesh_vertices", value=warning.value, detail=warning.detail))
        return lines

    def _update_preview(self, summary: ModelSummary | None) -> None:
        self.preview_widget.set_empty_message(self.t("preview_empty"))
        if summary is None:
            self.preview_widget.clear(self.t("preview_empty"))
            self.preview_warning_var.set("")
            return

        try:
            scale = float(self.scale_var.get())
            if scale <= 0:
                raise ValueError
        except ValueError:
            self.preview_widget.clear(self.t("preview_empty"))
            self.preview_warning_var.set(self.t("invalid_scale_number"))
            return

        self.preview_widget.set_model(summary.model, axis_preset=self.axis_var.get(), scale=scale)
        warning_lines = self._format_warning_lines(summary.warnings)
        if warning_lines:
            self.preview_warning_var.set(self.t("warning_static_intro") + "\n" + "\n".join(warning_lines))
        else:
            self.preview_warning_var.set("")

    def _on_preview_stats(self, stats: PreviewStats | None) -> None:
        if stats is None:
            self.preview_info_var.set("")
            return
        message = self.t(
            "preview_stats",
            shown=stats.shown_triangle_count,
            total=stats.total_triangle_count,
            vertices=stats.vertex_count,
        )
        if stats.sampled:
            message += "\n" + self.t(
                "preview_sampled",
                shown=stats.shown_triangle_count,
                total=stats.total_triangle_count,
            )
        self.preview_info_var.set(message)

    def _set_info_text(self, text: str) -> None:
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", text)
        self.info_text.configure(state="disabled")

    def log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_display_name_programmatically(self, text: str) -> None:
        self._setting_display_name = True
        try:
            self.display_name_var.set(text)
        finally:
            self._setting_display_name = False
        self._update_generated_model_id()

    def _on_display_name_var_changed(self, *_args) -> None:
        if self._setting_display_name:
            return
        self._update_generated_model_id()
        self._update_details(self._get_selected_summary())

    def _on_preview_setting_var_changed(self, *_args) -> None:
        if self._preview_after_id is not None:
            self.root.after_cancel(self._preview_after_id)
        self._preview_after_id = self.root.after(100, self._refresh_preview_from_current_selection)

    def _refresh_preview_from_current_selection(self) -> None:
        self._preview_after_id = None
        self._update_preview(self._get_selected_summary())

    def _existing_model_ids(self) -> list[str]:
        return [record.model_id for record in self.installed_records]

    def _unique_model_id_for_name(self, display_name: str, model: PMXModel | None = None) -> str:
        base_id = sanitize_ascii_name(display_name, fallback="model")
        if model is not None:
            base_id = build_model_id(model, display_name=display_name)
        return ensure_unique_model_id(base_id, self._existing_model_ids())

    def _update_generated_model_id(self) -> None:
        display_name = normalize_display_name(self.display_name_var.get())
        if not display_name:
            self.generated_id_var.set("")
            self.display_name_status_var.set("")
            self.display_name_status_label.configure(fg="#666666")
            return

        if not is_valid_display_name(display_name):
            self.generated_id_var.set("")
            self.display_name_status_var.set(self.t("display_name_invalid_inline"))
            self.display_name_status_label.configure(fg="#a03030")
            return

        summary = self._get_selected_summary()
        generated_id = self._unique_model_id_for_name(display_name, model=summary.model if summary else None)
        self.generated_id_var.set(generated_id)
        self.display_name_status_var.set(self.t("display_name_valid_inline", model_id=generated_id))
        self.display_name_status_label.configure(fg="#2f6f2f")
        if summary is not None:
            self._update_details(summary)

    def _build_import_options(self) -> ImportOptions:
        try:
            scale = float(self.scale_var.get())
        except ValueError as exc:
            raise ValueError(self.t("invalid_scale_number")) from exc
        if scale <= 0:
            raise ValueError(self.t("invalid_scale_positive"))

        display_name = normalize_display_name(self.display_name_var.get())
        if not is_valid_display_name(display_name):
            raise ValueError(self.t("invalid_display_name_message"))

        output_id = self.generated_id_var.get().strip() or sanitize_ascii_name(display_name, fallback="model")

        return ImportOptions(
            axis_preset=self.axis_var.get(),
            global_scale=scale,
            flip_v=bool(self.flip_v_var.get()),
            output_model_id=output_id,
            display_name_override=display_name,
            resolve_missing_texture=None if self.ignore_missing_tex_var.get() else self._resolve_missing_texture,
            workspace_root=self.staged_source.workspace_path if self.staged_source else None,
        )

    def _resolve_missing_texture(
        self, material: 'PMXMaterial', material_index: int, model: 'PMXModel', model_dir: Path,
        used_texture_paths: set[Path] | None = None,
        sub_indices: list[int] | None = None,
        flip_v: bool = False,
    ) -> Path | None:
        from pmx_parser import PMXMaterial as _PMXMat, PMXModel as _PMXMod
        boundary = self.staged_source.workspace_path if self.staged_source else None
        return ask_texture_for_material(
            parent=self.root,
            material=material,
            material_index=material_index,
            model=model,
            model_dir=model_dir,
            t=self.t,
            used_texture_paths=used_texture_paths,
            sub_indices=sub_indices,
            boundary=boundary,
            flip_v=flip_v,
        )

    def _open_workshop_page(self) -> None:
        webbrowser.open("https://steamcommunity.com/workshop/filedetails/?id=3706539692")

    def _show_fbx_blender_dialog(self) -> None:
        """Show a custom dialog for missing Blender with download buttons."""
        dlg = tk.Toplevel(self.root)
        dlg.title(self.t("fbx_needs_blender_title"))
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        frame = ttk.Frame(dlg, padding=16)
        frame.pack(fill="both", expand=True)

        msg_label = ttk.Label(frame, text=self.t("fbx_needs_blender_message"), wraplength=420, justify="left")
        msg_label.pack(pady=(0, 12))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x")

        def _open_blender_download() -> None:
            webbrowser.open("https://www.blender.org/download/")

        def _open_blender_steam() -> None:
            webbrowser.open("https://store.steampowered.com/app/365670/Blender/")

        ttk.Button(btn_frame, text=self.t("fbx_needs_blender_download"), command=_open_blender_download).pack(side="left", padx=(0, 6))
        ttk.Button(btn_frame, text=self.t("fbx_needs_blender_steam"), command=_open_blender_steam).pack(side="left", padx=(0, 6))
        ttk.Button(btn_frame, text="OK", command=dlg.destroy).pack(side="right")

        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dlg.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")
        dlg.wait_window()

    def _import_selected_model(self) -> None:
        summary = self._get_selected_summary()
        if summary is None:
            messagebox.showwarning(self.t("no_pmx_selected_title"), self.t("no_pmx_selected_message"))
            return

        gmod_root = self.gmod_path_var.get().strip()
        if not gmod_root:
            messagebox.showwarning(self.t("missing_gmod_title"), self.t("missing_gmod_message"))
            return

        try:
            options = self._build_import_options()
        except ValueError as exc:
            message = str(exc)
            if message in {self.t("invalid_scale_number"), self.t("invalid_scale_positive")}:
                title = self.t("invalid_scale_title")
            else:
                title = self.t("invalid_display_name_title")
            messagebox.showerror(title, message)
            return

        if summary.warnings:
            warning_message = self.t("warning_static_intro") + "\n\n" + "\n".join(self._format_warning_lines(summary.warnings))
            warning_message += "\n\n" + self.t("warning_continue")
            if not messagebox.askyesno(self.t("warning_static_title"), warning_message):
                return

        if summary.vertex_count > 50_000:
            if not messagebox.askyesno(
                self.t("vertex_game_warning_title"),
                self.t("vertex_game_warning_message", count=summary.vertex_count),
            ):
                return

        self._set_status(self.t("status_working_import"), fg="#1a6dd4")
        self.root.update_idletasks()

        try:
            result = import_pmx_model(summary.path, gmod_root, options=options, log=self.log)
            self.status_var.set(self.t("status_imported", display_name=result.display_name, model_id=result.model_id))
            self._refresh_imported_models(quiet=True, keep_status=True)
            self._update_generated_model_id()
            messagebox.showinfo(
                self.t("import_finished_title"),
                self.t(
                    "import_finished_message",
                    display_name=result.display_name,
                    model_id=result.model_id,
                    triangles=result.triangle_count,
                    materials=result.material_count,
                    manifest=result.manifest_path,
                    mesh=result.mesh_path,
                    textures=result.material_dir,
                ),
            )
        except Exception as exc:
            self.status_var.set(self.t("status_import_failed"))
            self.log(self.t("import_failed_log", error=exc))
            self.log(traceback.format_exc())
            if isinstance(exc, SceneLoadError) and "blender" in str(exc).lower():
                self._show_fbx_blender_dialog()
            else:
                messagebox.showerror(self.t("import_failed_title"), str(exc))

    def _refresh_imported_models(self, quiet: bool = False, keep_status: bool = False) -> None:
        self.installed_tree.delete(*self.installed_tree.get_children())
        self.installed_records = []
        self.installed_records_by_iid.clear()

        raw_path = self.gmod_path_var.get().strip()
        if not raw_path:
            self.installed_empty_var.set(self.t("installed_empty"))
            self._update_generated_model_id()
            return

        try:
            install = normalize_game_root(raw_path)
        except FileNotFoundError as exc:
            self.installed_empty_var.set(self.t("installed_empty"))
            if not quiet:
                self.log(self.t("installed_models_scan_failed", error=exc))
            if not keep_status:
                self.status_var.set(self.t("status_invalid_gmod"))
            self._update_generated_model_id()
            return

        try:
            records = list_imported_models(install)
        except Exception as exc:
            self.installed_empty_var.set(self.t("installed_empty"))
            if not quiet:
                self.log(self.t("installed_models_scan_failed", error=exc))
            self._update_generated_model_id()
            return

        self.installed_records = records
        for record in records:
            iid = record.model_id
            updated = datetime.fromtimestamp(record.updated_timestamp).strftime("%Y-%m-%d %H:%M")
            self.installed_records_by_iid[iid] = record
            self.installed_tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    record.model_id,
                    record.display_name,
                    f"{record.triangle_count:,}",
                    f"{record.material_count:,}",
                    updated,
                ),
            )

        if records:
            self.installed_empty_var.set("")
        else:
            self.installed_empty_var.set(self.t("installed_empty"))

        if not keep_status:
            self.status_var.set(self.t("status_installed_scanned", count=len(records), path=install.game_root))
        self._update_generated_model_id()

    def _get_selected_installed_record(self) -> ImportedModelRecord | None:
        selection = self.installed_tree.selection()
        if not selection:
            return None
        return self.installed_records_by_iid.get(selection[0])

    def _remove_selected_installed(self) -> None:
        record = self._get_selected_installed_record()
        if record is None:
            messagebox.showwarning(self.t("no_installed_selected_title"), self.t("no_installed_selected_message"))
            return

        confirmed = messagebox.askyesno(
            self.t("delete_installed_title"),
            self.t("delete_installed_confirm", display_name=record.display_name, model_id=record.model_id),
        )
        if not confirmed:
            return

        try:
            remove_imported_model(self.gmod_path_var.get().strip(), record.model_id)
            self.status_var.set(self.t("status_installed_removed", model_id=record.model_id))
            self._refresh_imported_models(quiet=True, keep_status=True)
        except Exception as exc:
            self.log(self.t("installed_models_scan_failed", error=exc))
            messagebox.showerror(self.t("delete_failed_title"), str(exc))

    def _export_selected_as_gma(self) -> None:
        selection = self.installed_tree.selection()
        if not selection:
            messagebox.showwarning(self.t("no_installed_selected_title"), self.t("export_gma_no_selection_message"))
            return

        model_ids = [iid for iid in selection if iid in self.installed_records_by_iid]
        if not model_ids:
            messagebox.showwarning(self.t("no_installed_selected_title"), self.t("export_gma_no_selection_message"))
            return

        gmod_root = self.gmod_path_var.get().strip()
        if not gmod_root:
            messagebox.showwarning(self.t("missing_gmod_title"), self.t("missing_gmod_message"))
            return

        output_path = filedialog.asksaveasfilename(
            title=self.t("export_gma_save_title"),
            defaultextension=".gma",
            filetypes=[("GMA Addon", "*.gma"), ("All files", "*.*")],
            initialfile="exported_models.gma",
        )
        if not output_path:
            return

        try:
            names = [self.installed_records_by_iid[mid].display_name for mid in model_ids]
            self.log(self.t("export_gma_started", count=len(model_ids), names=", ".join(names)))
            result_path = export_models_as_gma(
                install=gmod_root,
                model_ids=model_ids,
                output_path=output_path,
                log=self.log,
            )
            self.status_var.set(self.t("status_export_gma_done", path=result_path))
            messagebox.showinfo(
                self.t("export_gma_finished_title"),
                self.t("export_gma_finished_message", count=len(model_ids), path=result_path),
            )
        except Exception as exc:
            self.log(self.t("export_gma_failed_log", error=exc))
            self.log(traceback.format_exc())
            messagebox.showerror(self.t("export_gma_failed_title"), str(exc))

    def _cleanup_staged_source(self) -> None:
        if self.staged_source is not None:
            self.staged_source.cleanup()
            self.staged_source = None

    @staticmethod
    def _get_source_size_mb(src: Path) -> float:
        if src.is_file():
            return src.stat().st_size / (1024 * 1024)
        if src.is_dir():
            total = sum(f.stat().st_size for f in src.rglob("*") if f.is_file())
            return total / (1024 * 1024)
        return 0

    def _start_update_check(self) -> None:
        def _worker():
            result = _check_for_update()
            if result == "update":
                self.root.after(0, self._on_update_available)
            elif result == "up_to_date":
                self.root.after(0, self._on_update_up_to_date)
            else:
                self.root.after(0, self._on_update_check_failed)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _on_update_available(self) -> None:
        self._update_check_state = "update"
        self.update_label.configure(
            text=self.t("update_available"),
            fg="#1a6dd4",
            cursor="hand2",
            font=("Segoe UI", 9, "underline"),
        )
        self.update_label.grid()

    def _on_update_up_to_date(self) -> None:
        self._update_check_state = "up_to_date"
        self.update_label.configure(
            text=self.t("update_up_to_date"),
            fg="#2e7d32",
            cursor="",
            font=("Segoe UI", 9),
        )
        self.update_label.grid()

    def _on_update_check_failed(self) -> None:
        self._update_check_state = "error"
        self.update_label.configure(
            text=self.t("update_check_failed"),
            fg="#888888",
            cursor="",
            font=("Segoe UI", 9),
        )
        self.update_label.grid()

    def _on_close(self) -> None:
        self._cleanup_staged_source()
        self.root.destroy()



def enable_windows_drop_target(root: tk.Tk, callback):
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32

    GWL_WNDPROC = -4
    WM_DROPFILES = 0x0233
    LONG_PTR = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
    WNDPROC = ctypes.WINFUNCTYPE(LONG_PTR, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    if ctypes.sizeof(ctypes.c_void_p) == 8:
        get_window_long_ptr = user32.GetWindowLongPtrW
        set_window_long_ptr = user32.SetWindowLongPtrW
    else:
        get_window_long_ptr = user32.GetWindowLongW
        set_window_long_ptr = user32.SetWindowLongW

    get_window_long_ptr.argtypes = [wintypes.HWND, ctypes.c_int]
    get_window_long_ptr.restype = ctypes.c_void_p
    set_window_long_ptr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    set_window_long_ptr.restype = ctypes.c_void_p
    user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.CallWindowProcW.restype = LONG_PTR

    shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
    shell32.DragAcceptFiles.restype = None
    shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
    shell32.DragQueryFileW.restype = wintypes.UINT
    shell32.DragFinish.argtypes = [wintypes.HANDLE]
    shell32.DragFinish.restype = None

    root.update_idletasks()
    hwnd = wintypes.HWND(root.winfo_id())
    shell32.DragAcceptFiles(hwnd, True)

    old_proc = get_window_long_ptr(hwnd, GWL_WNDPROC)

    def _window_proc(hWnd, msg, wParam, lParam):
        if msg == WM_DROPFILES:
            drop_handle = wintypes.HANDLE(wParam)
            count = shell32.DragQueryFileW(drop_handle, 0xFFFFFFFF, None, 0)
            paths: list[str] = []
            for index in range(count):
                length = shell32.DragQueryFileW(drop_handle, index, None, 0)
                buffer = ctypes.create_unicode_buffer(length + 1)
                shell32.DragQueryFileW(drop_handle, index, buffer, length + 1)
                paths.append(buffer.value)
            shell32.DragFinish(drop_handle)
            root.after(0, lambda dropped=paths: callback(dropped))
            return 0
        return user32.CallWindowProcW(old_proc, hWnd, msg, wParam, lParam)

    new_proc = WNDPROC(_window_proc)
    new_proc_ptr = ctypes.cast(new_proc, ctypes.c_void_p)
    set_window_long_ptr(hwnd, GWL_WNDPROC, new_proc_ptr)

    def restore_original_proc(_event=None):
        try:
            set_window_long_ptr(hwnd, GWL_WNDPROC, old_proc)
        except Exception:
            pass

    root.bind("<Destroy>", restore_original_proc, add="+")
    root._pmx_drop_proc = new_proc
    root._pmx_drop_old_proc = old_proc



def launch() -> None:
    root = tk.Tk()
    app = PMXImporterApp(root)
    _ = app
    root.mainloop()
