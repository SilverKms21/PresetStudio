#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preset Studio — Universal JSON Preset Manager & Visual Compositing Editor
Default language: English (en) with instant switch to Portuguese (pt).
"""

import copy
import json
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

from engine import evaluate_filmcraft_param, hex_to_rgba_float, rgba_float_to_hex
from i18n import tr
from templates import FILMCRAFT_MOTION_TEMPLATE, FILMCRAFT_TEXT_TEMPLATE, GENERIC_DEFAULT_TEMPLATE
from theme import MONO_FONT, UI_FONT, ScrollableFrame, create_hairline_card, setup_theme
from viewer import ResolveViewerWidget

CONFIG_DIR = Path.home() / ".config" / "universal-preset-manager"
PROFILES_FILE = CONFIG_DIR / "profiles.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


class PresetManagerApp:
    _ARROW_PASSTHROUGH = {
        "Entry", "TEntry", "Text", "TCombobox", "Spinbox", "TSpinbox",
        "Listbox", "Treeview", "Scale", "TScale",
    }

    def __init__(self, root):
        self.root = root
        self.lang = self._load_language_setting()
        self.root.title("Preset Studio")
        self.root.geometry("1460x900")
        self.root.minsize(1140, 720)

        self.c = setup_theme(self.root)
        self.profiles = self._load_profiles()
        self.current_profile_name = next(iter(self.profiles.keys()))
        self.current_file_path = None
        self.current_data = None
        self.selected_preset_idx = 0
        self.selected_effect_idx = 0
        self.modified = False
        self.current_page = "studio"
        self._inspector_syncing = False
        self._live_params = []
        self._param_labels = {}

        self._build_ui()
        self._bind_shortcuts()
        self._refresh_file_list()

    def _t(self, key, **kwargs):
        return tr(self.lang, key, **kwargs)

    # ------------------------------------------------------------------
    # Settings & Profiles Storage
    # ------------------------------------------------------------------
    def _load_language_setting(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data.get("language") in ("en", "pt"):
                    return data["language"]
            except Exception:
                pass
        return "en"

    def _save_language_setting(self, lang_code):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"language": lang_code}, f, indent=2)

    def _set_language(self, lang_code):
        if lang_code == self.lang:
            return
        # Preserve viewer state across UI language rebuild
        prev_time = self.preview_widget.current_time_ns if hasattr(self, "preview_widget") else 0
        prev_playing = self.preview_widget.is_playing if hasattr(self, "preview_widget") else True
        prev_color = self.preview_widget.example_color_hex if hasattr(self, "preview_widget") else "#e8943a"
        prev_obj_mode = self.preview_widget.obj_mode_code if hasattr(self, "preview_widget") else "obj_auto"
        prev_bg_mode = self.preview_widget.bg_mode_code if hasattr(self, "preview_widget") else "bg_dark"
        prev_guides = self.preview_widget.guides_var.get() if hasattr(self, "preview_widget") else True
        prev_thirds = self.preview_widget.thirds_var.get() if hasattr(self, "preview_widget") else False
        prev_anchor = self.preview_widget.anchor_var.get() if hasattr(self, "preview_widget") else True
        prev_path = self.preview_widget.path_var.get() if hasattr(self, "preview_widget") else True
        prev_snap = self.preview_widget.snap_var.get() if hasattr(self, "preview_widget") else True
        prev_autokey = self.preview_widget.auto_key_var.get() if hasattr(self, "preview_widget") else True
        prev_search = self.search_var.get() if hasattr(self, "search_var") else ""

        if hasattr(self, "preview_widget"):
            self.preview_widget.destroy()

        for child in self.root.winfo_children():
            child.destroy()

        self.lang = lang_code
        self._save_language_setting(lang_code)

        self._build_ui()
        self.search_var.set(prev_search)
        self._refresh_file_list()
        self._update_doc_pill()

        pv = self.preview_widget
        pv.is_playing = prev_playing
        pv.play_btn.config(text=self._t("btn_pause") if prev_playing else self._t("btn_play"))
        pv.example_color_hex = prev_color
        pv.example_swatch.config(bg=prev_color)
        pv.obj_mode_code = prev_obj_mode
        if prev_obj_mode in pv._OBJ_KEYS:
            pv.example_mode_combo.current(pv._OBJ_KEYS.index(prev_obj_mode))
        pv.bg_mode_code = prev_bg_mode
        if prev_bg_mode in pv._BG_KEYS:
            pv.bg_combo.current(pv._BG_KEYS.index(prev_bg_mode))
        pv.guides_var.set(prev_guides)
        pv.thirds_var.set(prev_thirds)
        pv.anchor_var.set(prev_anchor)
        pv.path_var.set(prev_path)
        pv.snap_var.set(prev_snap)
        pv.auto_key_var.set(prev_autokey)

        self._render_all_views(reset_preview=False)
        pv.current_time_ns = prev_time
        pv.render_frame()

        if self.current_page != "studio":
            target = self.current_page
            self.current_page = "studio"
            self._switch_page(target)

    def _load_profiles(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if PROFILES_FILE.exists():
            try:
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
            except Exception:
                pass

        presents_dir = Path.home() / "Documentos" / "Presents"
        if not presents_dir.exists():
            presents_dir = Path.home() / "Documents" / "Presets"

        default_profiles = {
            "Filmcraft (Effect Presets)": {
                "folder": str(presents_dir),
                "schema_type": "filmcraft",
                "template": FILMCRAFT_TEXT_TEMPLATE,
            },
            "Generic (Any JSON App)": {
                "folder": str(Path.home() / "Documents" / "Presets_JSON"),
                "schema_type": "generic",
                "template": GENERIC_DEFAULT_TEMPLATE,
            },
        }
        self._save_profiles(default_profiles)
        return default_profiles

    def _save_profiles(self, profiles=None):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles or self.profiles, f, indent=2, ensure_ascii=False)

    @property
    def active_profile(self):
        return self.profiles[self.current_profile_name]

    # ------------------------------------------------------------------
    # Main UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        titlebar = ttk.Frame(self.root, style="Titlebar.TFrame", padding=(14, 8))
        titlebar.pack(fill="x")

        left_tb = ttk.Frame(titlebar, style="Titlebar.TFrame")
        left_tb.pack(side="left")

        dots = tk.Canvas(left_tb, width=44, height=16, bg=self.c["titlebar"], highlightthickness=0)
        dots.pack(side="left", padx=(0, 8))
        dots.create_oval(2, 3, 12, 13, fill="#ff5f56", outline="")
        dots.create_oval(17, 3, 27, 13, fill="#ffbd2e", outline="")
        dots.create_oval(32, 3, 42, 13, fill="#27c93f", outline="")

        ttk.Label(left_tb, text=self._t("app_title"), style="Title.TLabel").pack(side="left", padx=(0, 12))
        tk.Frame(left_tb, bg=self.c["border_light"], width=1, height=20).pack(side="left", padx=(0, 12))

        self.profile_var = tk.StringVar(value=self.current_profile_name)
        self.profile_combo = ttk.Combobox(
            left_tb, textvariable=self.profile_var, values=list(self.profiles.keys()), state="readonly", width=23
        )
        self.profile_combo.pack(side="left", padx=(0, 6))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_changed)

        ttk.Button(left_tb, text=self._t("btn_add_app"), style="Ghost.TButton", command=self._add_new_profile).pack(side="left", padx=2)
        ttk.Button(left_tb, text=self._t("btn_folder"), style="Ghost.TButton", command=self._change_profile_folder).pack(side="left", padx=2)
        ttk.Button(left_tb, text=self._t("btn_template"), style="Ghost.TButton", command=self._save_current_as_template).pack(side="left", padx=2)

        # Center Document Pill
        self.doc_pill_var = tk.StringVar(value=self._t("no_file_selected"))
        doc_pill = tk.Frame(titlebar, bg=self.c["well"], highlightbackground=self.c["border"], highlightthickness=1, padx=14, pady=4)
        doc_pill.pack(side="left", expand=True, padx=12)
        tk.Label(doc_pill, textvariable=self.doc_pill_var, bg=self.c["well"], fg=self.c["fg_text"], font=(UI_FONT, 9, "bold")).pack()

        # Right Action Buttons + Language Toggle (EN / PT)
        right_tb = ttk.Frame(titlebar, style="Titlebar.TFrame")
        right_tb.pack(side="right")

        lang_box = tk.Frame(right_tb, bg=self.c["well"], highlightbackground=self.c["border"], highlightthickness=1, padx=2, pady=2)
        lang_box.pack(side="left", padx=(0, 10))
        for code, lbl in [("en", "EN"), ("pt", "PT")]:
            active = self.lang == code
            lbtn = tk.Label(
                lang_box,
                text=lbl,
                bg=self.c["card_hover"] if active else self.c["well"],
                fg=self.c["accent"] if active else self.c["fg_muted"],
                font=(UI_FONT, 8, "bold"),
                padx=7,
                pady=2,
                cursor="hand2",
            )
            lbtn.pack(side="left", padx=1)
            lbtn.bind("<Button-1>", lambda _e, c=code: self._set_language(c))

        ttk.Button(right_tb, text=self._t("btn_new"), style="TButton", command=self._create_new_preset).pack(side="left", padx=2)
        ttk.Button(right_tb, text=self._t("btn_duplicate"), style="TButton", command=self._duplicate_preset).pack(side="left", padx=2)
        ttk.Button(right_tb, text=self._t("btn_import"), style="TButton", command=self._import_preset).pack(side="left", padx=2)
        ttk.Button(right_tb, text=self._t("btn_validate"), style="TButton", command=self._validate_current_json).pack(side="left", padx=2)
        ttk.Button(right_tb, text=self._t("btn_save"), style="Accent.TButton", command=self._save_current_file).pack(side="left", padx=(6, 0))

        tk.Frame(self.root, bg=self.c["border"], height=1).pack(fill="x")

        main_paned = ttk.PanedWindow(self.root, orient="horizontal")
        main_paned.pack(fill="both", expand=True)

        # Left Panel: Preset Library
        left_wrap = tk.Frame(main_paned, bg=self.c["border"], width=260)
        main_paned.add(left_wrap, weight=1)

        left_panel = ttk.Frame(left_wrap, style="Panel.TFrame")
        left_panel.pack(fill="both", expand=True, padx=(0, 1))

        lib_header = ttk.Frame(left_panel, style="PanelHeader.TFrame", padding=(12, 7))
        lib_header.pack(fill="x")
        ttk.Label(lib_header, text=self._t("library_header"), style="SectionTag.TLabel").pack(side="left")

        tk.Frame(left_panel, bg=self.c["border"], height=1).pack(fill="x")

        lib_body = ttk.Frame(left_panel, style="Panel.TFrame", padding=10)
        lib_body.pack(fill="both", expand=True)

        search_row = ttk.Frame(lib_body, style="Panel.TFrame")
        search_row.pack(fill="x", pady=(0, 8))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_file_list())
        ttk.Entry(search_row, textvariable=self.search_var).pack(side="left", fill="x", expand=True)
        ttk.Button(search_row, text="↻", width=3, style="Ghost.TButton", command=self._refresh_file_list).pack(side="right", padx=(5, 0))

        list_border = tk.Frame(lib_body, bg=self.c["border"], padx=1, pady=1)
        list_border.pack(fill="both", expand=True)

        list_container = tk.Frame(list_border, bg=self.c["input"], padx=4, pady=4)
        list_container.pack(fill="both", expand=True)

        self.file_listbox = tk.Listbox(
            list_container,
            bg=self.c["input"],
            fg=self.c["fg_text"],
            selectbackground=self.c["select_bg"],
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=0,
            font=(UI_FONT, 10),
            activestyle="none",
        )
        file_scroll = ttk.Scrollbar(list_container, orient="vertical", command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=file_scroll.set)
        self.file_listbox.pack(side="left", fill="both", expand=True)
        file_scroll.pack(side="right", fill="y")
        self.file_listbox.bind("<<ListboxSelect>>", self._on_file_select)

        file_actions = ttk.Frame(lib_body, style="Panel.TFrame")
        file_actions.pack(fill="x", pady=(8, 4))
        ttk.Button(file_actions, text=self._t("btn_rename"), command=self._rename_file).pack(side="left", fill="x", expand=True, padx=(0, 3))
        ttk.Button(file_actions, text=self._t("btn_delete"), style="Danger.TButton", command=self._delete_file).pack(side="right", fill="x", expand=True, padx=(3, 0))

        self.folder_info_label = ttk.Label(lib_body, text="", style="Muted.TLabel", wraplength=240, font=(UI_FONT, 8))
        self.folder_info_label.pack(anchor="w", pady=(4, 0))

        # Right Workspace
        self.workspace_host = ttk.Frame(main_paned, style="Root.TFrame")
        main_paned.add(self.workspace_host, weight=5)

        self.page_studio = ttk.PanedWindow(self.workspace_host, orient="horizontal")

        center_wrap = tk.Frame(self.page_studio, bg=self.c["border"], width=660)
        self.page_studio.add(center_wrap, weight=3)

        center_panel = ttk.Frame(center_wrap, style="Panel.TFrame")
        center_panel.pack(fill="both", expand=True, padx=(0, 1))

        self.preview_widget = ResolveViewerWidget(center_panel, self.c, lang=self.lang, on_modified=self._mark_modified)
        self.preview_widget.pack(fill="both", expand=True)
        self.preview_widget.time_listener = self._refresh_live_params

        right_inspector = ttk.Frame(self.page_studio, style="Panel.TFrame", width=420)
        self.page_studio.add(right_inspector, weight=2)

        insp_header = ttk.Frame(right_inspector, style="PanelHeader.TFrame", padding=(12, 7))
        insp_header.pack(fill="x")
        ttk.Label(insp_header, text=self._t("inspector_header"), style="SectionTag.TLabel").pack(side="left")
        ttk.Label(insp_header, text=self._t("inspector_sub"), style="HeaderMuted.TLabel").pack(side="right")

        tk.Frame(right_inspector, bg=self.c["border"], height=1).pack(fill="x")

        self.visual_scroll = ScrollableFrame(right_inspector, bg_color=self.c["panel"])
        self.visual_scroll.pack(fill="both", expand=True)

        self.page_tree = ttk.Frame(self.workspace_host, style="Panel.TFrame")
        self._build_tree_tab()

        self.page_raw = ttk.Frame(self.workspace_host, style="Panel.TFrame")
        self._build_raw_tab()

        self.page_studio.pack(fill="both", expand=True)

        # Bottom Dock
        tk.Frame(self.root, bg=self.c["border"], height=1).pack(fill="x")
        bottom_dock = ttk.Frame(self.root, style="Dock.TFrame", padding=(14, 6))
        bottom_dock.pack(fill="x", side="bottom")

        status_left = ttk.Frame(bottom_dock, style="Dock.TFrame")
        status_left.pack(side="left", fill="x", expand=True)

        self.status_dot = tk.Label(status_left, text="●", bg=self.c["titlebar"], fg=self.c["success"], font=(UI_FONT, 9))
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_var = tk.StringVar(value=self._t("status_ready"))
        tk.Label(status_left, textvariable=self.status_var, bg=self.c["titlebar"], fg=self.c["fg_muted"], font=(UI_FONT, 9), anchor="w").pack(side="left")

        switcher = tk.Frame(bottom_dock, bg=self.c["well"], highlightbackground=self.c["border"], highlightthickness=1, padx=3, pady=3)
        switcher.pack(side="left", padx=12)

        self.page_buttons = {}
        for key, label in [("studio", self._t("page_studio")), ("tree", self._t("page_tree")), ("raw", self._t("page_raw"))]:
            btn = tk.Label(switcher, text=label, bg=self.c["well"], fg=self.c["fg_muted"], font=(UI_FONT, 9, "bold"), padx=12, pady=3, cursor="hand2")
            btn.pack(side="left", padx=2)
            btn.bind("<Button-1>", lambda _e, k=key: self._switch_page(k))
            self.page_buttons[key] = btn

        tk.Label(
            bottom_dock,
            text=self._t("shortcuts_hint"),
            bg=self.c["titlebar"], fg=self.c["fg_faint"], font=(UI_FONT, 8),
        ).pack(side="right")

        self._update_page_dock_styles()

    def _switch_page(self, page_key):
        if self.current_page == page_key:
            return
        self.current_page = page_key
        self.page_studio.pack_forget()
        self.page_tree.pack_forget()
        self.page_raw.pack_forget()

        if page_key == "studio":
            self.page_studio.pack(fill="both", expand=True)
            self._sync_preview(reset_time=False)
            self._render_visual_editor()
        elif page_key == "tree":
            self.page_tree.pack(fill="both", expand=True)
            self._render_tree_view()
        elif page_key == "raw":
            self.page_raw.pack(fill="both", expand=True)
            self._render_raw_view()

        self._update_page_dock_styles()

    def _update_page_dock_styles(self):
        for key, btn in self.page_buttons.items():
            btn.config(
                bg=self.c["card_hover"] if key == self.current_page else self.c["well"],
                fg=self.c["accent"] if key == self.current_page else self.c["fg_muted"],
            )

    def _build_tree_tab(self):
        header = ttk.Frame(self.page_tree, style="PanelHeader.TFrame", padding=(14, 8))
        header.pack(fill="x")
        ttk.Label(header, text=self._t("tree_header"), style="SectionTag.TLabel").pack(side="left")
        ttk.Label(header, text=self._t("tree_sub"), style="HeaderMuted.TLabel").pack(side="left", padx=(12, 0))

        actions = ttk.Frame(header, style="PanelHeader.TFrame")
        actions.pack(side="right")
        ttk.Button(actions, text=self._t("btn_edit_val"), command=self._tree_edit_selected).pack(side="left", padx=3)
        ttk.Button(actions, text=self._t("btn_add_node"), command=self._tree_add_node).pack(side="left", padx=3)
        ttk.Button(actions, text=self._t("btn_remove"), style="Danger.TButton", command=self._tree_delete_node).pack(side="left", padx=3)

        tk.Frame(self.page_tree, bg=self.c["border"], height=1).pack(fill="x")
        tree_container = ttk.Frame(self.page_tree, style="Panel.TFrame", padding=12)
        tree_container.pack(fill="both", expand=True)

        border_box = tk.Frame(tree_container, bg=self.c["border"], padx=1, pady=1)
        border_box.pack(fill="both", expand=True)

        inner_box = ttk.Frame(border_box, style="Panel.TFrame")
        inner_box.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(inner_box, columns=("type", "value"), show="tree headings")
        self.tree.heading("#0", text=self._t("col_key"), anchor="w")
        self.tree.heading("type", text=self._t("col_type"), anchor="center")
        self.tree.heading("value", text=self._t("col_value"), anchor="w")
        self.tree.column("#0", width=320)
        self.tree.column("type", width=110, anchor="center")
        self.tree.column("value", width=520)

        tree_scroll = ttk.Scrollbar(inner_box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _e: self._tree_edit_selected())

    def _build_raw_tab(self):
        header = ttk.Frame(self.page_raw, style="PanelHeader.TFrame", padding=(14, 8))
        header.pack(fill="x")
        ttk.Label(header, text=self._t("raw_header"), style="SectionTag.TLabel").pack(side="left")
        ttk.Label(header, text=self._t("raw_sub"), style="HeaderMuted.TLabel").pack(side="left", padx=(12, 0))

        actions = ttk.Frame(header, style="PanelHeader.TFrame")
        actions.pack(side="right")
        ttk.Button(actions, text=self._t("btn_format_json"), command=self._format_raw_json).pack(side="left", padx=3)
        ttk.Button(actions, text=self._t("btn_apply_json"), style="Accent.TButton", command=self._apply_raw_json_to_model).pack(side="left", padx=3)

        tk.Frame(self.page_raw, bg=self.c["border"], height=1).pack(fill="x")
        body = ttk.Frame(self.page_raw, style="Panel.TFrame", padding=12)
        body.pack(fill="both", expand=True)

        border_box = tk.Frame(body, bg=self.c["border"], padx=1, pady=1)
        border_box.pack(fill="both", expand=True)

        text_container = ttk.Frame(border_box, style="Panel.TFrame")
        text_container.pack(fill="both", expand=True)

        self.raw_text = tk.Text(
            text_container,
            bg=self.c["well"],
            fg=self.c["fg_text"],
            insertbackground=self.c["accent"],
            selectbackground=self.c["select_bg"],
            selectforeground="#ffffff",
            font=(MONO_FONT, 10),
            undo=True,
            wrap="none",
            borderwidth=0,
            highlightthickness=0,
            padx=14,
            pady=12,
        )
        y_scroll = ttk.Scrollbar(text_container, orient="vertical", command=self.raw_text.yview)
        x_scroll = ttk.Scrollbar(text_container, orient="horizontal", command=self.raw_text.xview)
        self.raw_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.raw_text.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        text_container.rowconfigure(0, weight=1)
        text_container.columnconfigure(0, weight=1)

    def _bind_shortcuts(self):
        self.root.bind("<Control-s>", lambda _e: self._save_current_file())
        self.root.bind("<Control-n>", lambda _e: self._create_new_preset())
        self.root.bind("<space>", self._on_space_shortcut)
        for key in ("<Left>", "<Right>", "<Home>", "<End>"):
            self.root.bind(key, self._on_timeline_key)

    def _on_timeline_key(self, event):
        if self.current_page != "studio":
            return None
        try:
            if event.widget.winfo_class() in self._ARROW_PASSTHROUGH:
                return None
        except (tk.TclError, AttributeError):
            return None

        pv = self.preview_widget
        shift = bool(event.state & 0x1)
        ctrl = bool(event.state & 0x4)
        direction = {"Left": -1, "Right": 1}.get(event.keysym, 0)

        if event.keysym == "Home":
            pv.go_to_start()
        elif event.keysym == "End":
            pv.go_to_end()
        elif ctrl:
            pv.jump_keyframe(direction)
        else:
            pv.step_frames(direction * (10 if shift else 1))
        return "break"

    def _on_space_shortcut(self, event):
        if not isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)):
            self.preview_widget.toggle_play()

    # ------------------------------------------------------------------
    # File & Profile Operations
    # ------------------------------------------------------------------
    def _on_profile_changed(self, _event=None):
        self.current_profile_name = self.profile_var.get()
        self.current_file_path = None
        self.current_data = None
        self.modified = False
        self._update_doc_pill()
        self._refresh_file_list()
        self._render_all_views(reset_preview=True)

    def _add_new_profile(self):
        app_name = simpledialog.askstring(self._t("dlg_new_app_title"), self._t("dlg_new_app_prompt"), parent=self.root)
        if not app_name or not app_name.strip():
            return
        app_name = app_name.strip()
        folder = filedialog.askdirectory(title=self._t("dlg_select_folder", app=app_name))
        if not folder:
            return

        is_fc = messagebox.askyesno(self._t("dlg_schema_title"), self._t("dlg_schema_msg"))
        self.profiles[app_name] = {
            "folder": folder,
            "schema_type": "filmcraft" if is_fc else "generic",
            "template": copy.deepcopy(FILMCRAFT_TEXT_TEMPLATE if is_fc else GENERIC_DEFAULT_TEMPLATE),
        }
        self._save_profiles()
        self.current_profile_name = app_name
        self.profile_combo["values"] = list(self.profiles.keys())
        self.profile_var.set(app_name)
        self._refresh_file_list()
        self._set_status(self._t("status_profile_created", app=app_name))

    def _change_profile_folder(self):
        new_folder = filedialog.askdirectory(title=self._t("dlg_choose_folder"), initialdir=self.active_profile.get("folder", str(Path.home())))
        if new_folder:
            self.active_profile["folder"] = new_folder
            self._save_profiles()
            self._refresh_file_list()
            self._set_status(self._t("status_folder_updated", folder=new_folder))

    def _save_current_as_template(self):
        if self.current_data is None:
            messagebox.showinfo(self._t("dlg_notice"), self._t("dlg_open_before_tpl"))
            return
        self.active_profile["template"] = copy.deepcopy(self.current_data)
        self._save_profiles()
        self._set_status(self._t("status_tpl_updated", profile=self.current_profile_name))

    def _refresh_file_list(self):
        folder = Path(self.active_profile["folder"])
        folder.mkdir(parents=True, exist_ok=True)
        self.folder_info_label.config(text=f"📁 {folder}")

        query = self.search_var.get().strip().lower()
        self.file_listbox.delete(0, tk.END)

        for f in sorted(folder.glob("*.json"), key=lambda p: p.name.lower()):
            if not query or query in f.name.lower():
                self.file_listbox.insert(tk.END, f"  {f.name}")
                if self.current_file_path and f == self.current_file_path:
                    self.file_listbox.selection_set(tk.END)

    def _on_file_select(self, _event=None):
        sel = self.file_listbox.curselection()
        if sel:
            filename = self.file_listbox.get(sel[0]).strip()
            self._load_file(Path(self.active_profile["folder"]) / filename)

    def _load_file(self, filepath: Path):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.current_file_path = filepath
            self.current_data = data
            self.selected_preset_idx = 0
            self.selected_effect_idx = 0
            self.modified = False
            self._update_doc_pill()
            self._render_all_views(reset_preview=True)
            self._set_status(self._t("status_loaded", name=filepath.name))
        except Exception as e:
            messagebox.showerror(self._t("dlg_err_open_title"), self._t("dlg_err_open_msg", name=filepath.name, err=e))

    def _create_new_preset(self):
        is_filmcraft = self.active_profile.get("schema_type") == "filmcraft"
        win = tk.Toplevel(self.root)
        win.title(self._t("dlg_new_preset_title"))
        win.geometry("440x230" if is_filmcraft else "440x160")
        win.configure(bg=self.c["panel"])
        win.transient(self.root)
        win.grab_set()

        ttk.Label(win, text=self._t("dlg_new_preset_lbl"), padding=(16, 14, 16, 4)).pack(anchor="w")
        name_var = tk.StringVar(value="New_Preset")
        ent = ttk.Entry(win, textvariable=name_var, width=42)
        ent.pack(padx=16, fill="x")
        ent.select_range(0, tk.END)
        ent.focus_set()

        kind_cb = None
        if is_filmcraft:
            ttk.Label(win, text=self._t("dlg_fc_type_lbl"), padding=(16, 10, 16, 4)).pack(anchor="w")
            kind_cb = ttk.Combobox(
                win,
                values=[self._t("fc_type_motion"), self._t("fc_type_text"), self._t("fc_type_profile")],
                state="readonly",
            )
            kind_cb.current(0)
            kind_cb.pack(padx=16, fill="x")

        def confirm():
            clean_name = name_var.get().strip()
            if not clean_name:
                return
            filename = clean_name if clean_name.endswith(".json") else f"{clean_name}.json"
            folder = Path(self.active_profile["folder"])
            folder.mkdir(parents=True, exist_ok=True)
            target_path = folder / filename

            if target_path.exists():
                messagebox.showwarning(self._t("dlg_file_exists_title"), self._t("dlg_file_exists_msg", name=filename), parent=win)
                return

            if is_filmcraft and kind_cb is not None:
                idx = kind_cb.current()
                if idx == 0:
                    new_data = copy.deepcopy(FILMCRAFT_MOTION_TEMPLATE)
                elif idx == 1:
                    new_data = copy.deepcopy(FILMCRAFT_TEXT_TEMPLATE)
                else:
                    new_data = copy.deepcopy(self.active_profile.get("template", FILMCRAFT_TEXT_TEMPLATE))
            else:
                new_data = copy.deepcopy(self.active_profile.get("template", GENERIC_DEFAULT_TEMPLATE))

            if isinstance(new_data, dict):
                if "presets" in new_data and isinstance(new_data["presets"], list) and new_data["presets"]:
                    new_data["presets"][0]["name"] = clean_name.replace(".json", "")
                elif "name" in new_data:
                    new_data["name"] = clean_name.replace(".json", "")

            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)

            win.destroy()
            self._refresh_file_list()
            self._load_file(target_path)
            self._set_status(self._t("status_created", name=filename))

        btn_row = ttk.Frame(win, padding=16)
        btn_row.pack(fill="x", side="bottom")
        ttk.Button(btn_row, text=self._t("btn_cancel"), command=win.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btn_row, text=self._t("btn_create_preset"), style="Accent.TButton", command=confirm).pack(side="right")
        win.bind("<Return>", lambda _e: confirm())

    def _duplicate_preset(self):
        if not self.current_file_path or self.current_data is None:
            messagebox.showinfo(self._t("dlg_notice"), self._t("dlg_select_to_dup"))
            return
        new_name = simpledialog.askstring(
            self._t("dlg_dup_title"), self._t("dlg_dup_prompt"),
            initialvalue=f"{self.current_file_path.stem}_copy", parent=self.root,
        )
        if not new_name or not new_name.strip():
            return
        filename = new_name.strip() if new_name.strip().endswith(".json") else f"{new_name.strip()}.json"
        target_path = self.current_file_path.parent / filename
        if target_path.exists():
            messagebox.showwarning(self._t("dlg_file_exists_title"), self._t("dlg_file_exists_msg", name=filename))
            return

        dup_data = copy.deepcopy(self.current_data)
        if isinstance(dup_data, dict) and "presets" in dup_data and dup_data["presets"]:
            dup_data["presets"][0]["name"] = Path(filename).stem

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(dup_data, f, indent=2, ensure_ascii=False)

        self._refresh_file_list()
        self._load_file(target_path)
        self._set_status(self._t("status_duplicated", name=filename))

    def _import_preset(self):
        src = filedialog.askopenfilename(title=self._t("dlg_import_title"), filetypes=[("JSON Files", "*.json"), ("All", "*.*")])
        if not src:
            return
        src_path = Path(src)
        try:
            with open(src_path, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception as e:
            messagebox.showerror(self._t("dlg_invalid_json_title"), self._t("dlg_invalid_json_msg", err=e))
            return

        dest_path = Path(self.active_profile["folder"]) / src_path.name
        if dest_path.exists() and not messagebox.askyesno(self._t("dlg_overwrite_title"), self._t("dlg_overwrite_msg", name=src_path.name)):
            return

        shutil.copy2(src_path, dest_path)
        self._refresh_file_list()
        self._load_file(dest_path)
        self._set_status(self._t("status_imported", name=src_path.name))

    def _rename_file(self):
        if not self.current_file_path:
            return
        new_name = simpledialog.askstring(self._t("dlg_rename_title"), self._t("dlg_rename_prompt"), initialvalue=self.current_file_path.stem, parent=self.root)
        if not new_name or not new_name.strip():
            return
        filename = new_name.strip() if new_name.strip().endswith(".json") else f"{new_name.strip()}.json"
        new_path = self.current_file_path.parent / filename
        if new_path.exists():
            messagebox.showwarning(self._t("dlg_error"), self._t("dlg_name_exists"))
            return
        self.current_file_path.rename(new_path)
        self.current_file_path = new_path
        self._update_doc_pill()
        self._refresh_file_list()
        self._set_status(self._t("status_renamed", name=filename))

    def _delete_file(self):
        if not self.current_file_path:
            return
        if not messagebox.askyesno(self._t("dlg_delete_title"), self._t("dlg_delete_msg", name=self.current_file_path.name)):
            return
        deleted_name = self.current_file_path.name
        self.current_file_path.unlink(missing_ok=True)
        self.current_file_path = None
        self.current_data = None
        self.modified = False
        self._update_doc_pill()
        self._refresh_file_list()
        self._render_all_views(reset_preview=True)
        self._set_status(self._t("status_deleted", name=deleted_name))

    def _save_current_file(self):
        if not self.current_file_path or self.current_data is None:
            messagebox.showinfo(self._t("dlg_notice"), self._t("dlg_no_file_save"))
            return
        if self.current_page == "raw" and not self._apply_raw_json_to_model(silent=True):
            return
        try:
            if self.current_file_path.exists():
                shutil.copy2(self.current_file_path, self.current_file_path.with_suffix(".json.bak"))
            with open(self.current_file_path, "w", encoding="utf-8") as f:
                json.dump(self.current_data, f, indent=2, ensure_ascii=False)
            self.modified = False
            self._update_doc_pill()
            self._set_status(self._t("status_saved", name=self.current_file_path.name))
        except Exception as e:
            messagebox.showerror(self._t("dlg_save_err_title"), self._t("dlg_save_err_msg", err=e))

    def _validate_current_json(self):
        if self.current_data is None:
            messagebox.showinfo(self._t("dlg_val_title"), self._t("dlg_val_no_file"))
            return
        if self.current_page == "raw" and not self._apply_raw_json_to_model(silent=True):
            return

        issues = []
        if isinstance(self.current_data, dict) and (
            self.active_profile.get("schema_type") == "filmcraft" or self.current_data.get("format") == "filmcraft.effect-presets"
        ):
            if self.current_data.get("format") != "filmcraft.effect-presets":
                issues.append("- Missing or invalid 'format' field (expected 'filmcraft.effect-presets').")
            if "version" not in self.current_data:
                issues.append("- Missing 'version' field (recommended: 1).")
            presets = self.current_data.get("presets")
            if not isinstance(presets, list) or len(presets) == 0:
                issues.append("- 'presets' array is missing or empty.")
            else:
                for i, p in enumerate(presets):
                    if "name" not in p:
                        issues.append(f"- Preset [{i}] missing 'name' field.")
                    if "effects" not in p or not isinstance(p["effects"], list):
                        issues.append(f"- Preset [{i}] missing 'effects' array.")

        if issues:
            messagebox.showwarning(self._t("dlg_val_warn_title"), self._t("dlg_val_warn_msg", issues="\n".join(issues)))
        else:
            messagebox.showinfo(self._t("dlg_val_ok_title"), self._t("dlg_val_ok_msg"))

    # ------------------------------------------------------------------
    # Inspector & Views
    # ------------------------------------------------------------------
    def _sync_preview(self, reset_time=False):
        if self._is_filmcraft_data() and self.current_data["presets"]:
            idx = min(self.selected_preset_idx, len(self.current_data["presets"]) - 1)
            self.preview_widget.set_preset(self.current_data["presets"][idx], reset_time=reset_time)
        else:
            self.preview_widget.set_preset(None, reset_time=reset_time)

    def _render_all_views(self, reset_preview=False):
        self._sync_preview(reset_time=reset_preview)
        self._render_visual_editor()
        self._render_tree_view()
        self._render_raw_view()

    def _is_filmcraft_data(self):
        return (
            isinstance(self.current_data, dict)
            and self.current_data.get("format") == "filmcraft.effect-presets"
            and isinstance(self.current_data.get("presets"), list)
        )

    def _render_visual_editor(self):
        self._live_params = []
        self._param_labels = {}
        container = self.visual_scroll.inner
        for child in container.winfo_children():
            child.destroy()

        if self.current_data is None:
            ttk.Label(container, text=self._t("inspector_empty"), style="Muted.TLabel", padding=20).pack(anchor="w")
            return

        if self._is_filmcraft_data():
            self._render_filmcraft_editor(container)
        else:
            self._render_generic_visual_editor(container)

    def _render_filmcraft_editor(self, parent):
        presets = self.current_data["presets"]
        if not presets:
            ttk.Label(parent, text=self._t("empty_presets_list"), padding=15).pack(anchor="w")
            return

        if self.selected_preset_idx >= len(presets):
            self.selected_preset_idx = 0
        preset = presets[self.selected_preset_idx]

        # Card 1: Preset Variations
        outer1, top_card = create_hairline_card(parent, padding=10)
        outer1.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(top_card, text=self._t("card_variation"), style="CardSection.TLabel").pack(anchor="w", pady=(0, 6))

        var_row = ttk.Frame(top_card, style="Card.TFrame")
        var_row.pack(fill="x")

        p_combo = ttk.Combobox(var_row, values=[f"[{i}] {p.get('name', 'Untitled')}" for i, p in enumerate(presets)], state="readonly")
        p_combo.current(self.selected_preset_idx)
        p_combo.pack(side="left", fill="x", expand=True, padx=(0, 6))

        def on_preset_switch(_e):
            self.selected_preset_idx = p_combo.current()
            self.selected_effect_idx = 0
            self._sync_preview(reset_time=True)
            self._render_visual_editor()

        p_combo.bind("<<ComboboxSelected>>", on_preset_switch)

        def add_subpreset():
            clone = copy.deepcopy(preset)
            clone["name"] = f"{preset.get('name', 'Preset')} (Copy)"
            presets.append(clone)
            self.selected_preset_idx = len(presets) - 1
            self._mark_modified()
            self._render_all_views(reset_preview=True)

        def del_subpreset():
            if len(presets) <= 1:
                messagebox.showinfo(self._t("dlg_notice"), self._t("dlg_keep_one_preset"))
                return
            presets.pop(self.selected_preset_idx)
            self.selected_preset_idx = max(0, self.selected_preset_idx - 1)
            self._mark_modified()
            self._render_all_views(reset_preview=True)

        ttk.Button(var_row, text="+", width=3, command=add_subpreset).pack(side="left", padx=2)
        ttk.Button(var_row, text="✕", width=3, style="Danger.TButton", command=del_subpreset).pack(side="left", padx=(2, 0))

        # Card 2: Properties & Resolution
        outer2, meta_card = create_hairline_card(parent, padding=10)
        outer2.pack(fill="x", padx=10, pady=6)
        ttk.Label(meta_card, text=self._t("card_properties"), style="CardSection.TLabel").pack(anchor="w", pady=(0, 8))

        meta_grid = ttk.Frame(meta_card, style="Card.TFrame")
        meta_grid.pack(fill="x")
        meta_grid.columnconfigure(1, weight=1)

        ttk.Label(meta_grid, text=self._t("lbl_name"), style="CardMuted.TLabel", width=15).grid(row=0, column=0, sticky="w", pady=4)
        name_var = tk.StringVar(value=str(preset.get("name", "")))
        ttk.Entry(meta_grid, textvariable=name_var).grid(row=0, column=1, sticky="ew", pady=4)
        name_var.trace_add("write", lambda *_: self._set_dict_val(preset, "name", name_var.get()))

        ttk.Label(meta_grid, text=self._t("lbl_kf_tag"), style="CardMuted.TLabel", width=15).grid(row=1, column=0, sticky="w", pady=4)
        kf_var = tk.StringVar(value=str(preset.get("keyframes", "")))
        ttk.Entry(meta_grid, textvariable=kf_var).grid(row=1, column=1, sticky="ew", pady=4)
        kf_var.trace_add("write", lambda *_: self._set_dict_val(preset, "keyframes", kf_var.get()))

        src_size = preset.get("source_size", [1920, 1080])
        w_val = src_size[0] if isinstance(src_size, list) and len(src_size) >= 2 else 1920
        h_val = src_size[1] if isinstance(src_size, list) and len(src_size) >= 2 else 1080

        ttk.Label(meta_grid, text=self._t("lbl_base_res"), style="CardMuted.TLabel", width=15).grid(row=2, column=0, sticky="w", pady=4)
        res_frame = ttk.Frame(meta_grid, style="Card.TFrame")
        res_frame.grid(row=2, column=1, sticky="w", pady=4)

        w_var = tk.StringVar(value=str(w_val))
        h_var = tk.StringVar(value=str(h_val))
        ttk.Entry(res_frame, textvariable=w_var, width=6).pack(side="left")
        ttk.Label(res_frame, text=" × ", style="CardMuted.TLabel").pack(side="left")
        ttk.Entry(res_frame, textvariable=h_var, width=6).pack(side="left")

        def apply_resolution_scale():
            try:
                new_w, new_h = int(w_var.get()), int(h_var.get())
                if new_w <= 0 or new_h <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror(self._t("dlg_error"), self._t("dlg_invalid_res"))
                return

            old_size = preset.get("source_size", [1920, 1080])
            scale_x = new_w / (old_size[0] or 1920)
            scale_y = new_h / (old_size[1] or 1080)

            preset["source_size"] = [new_w, new_h]
            for eff in preset.get("effects", []):
                params = eff.get("params", {})
                for vec_key in ("position", "anchor"):
                    v_obj = params.get(vec_key)
                    if isinstance(v_obj, dict):
                        vec = v_obj.get("value", {}).get("Vec2")
                        if isinstance(vec, dict):
                            vec["x"] = round(vec.get("x", 0.0) * scale_x, 4)
                            vec["y"] = round(vec.get("y", 0.0) * scale_y, 4)
                        for kf in v_obj.get("keyframes", []):
                            kvec = kf.get("value", {}).get("Vec2")
                            if isinstance(kvec, dict):
                                kvec["x"] = round(kvec.get("x", 0.0) * scale_x, 4)
                                kvec["y"] = round(kvec.get("y", 0.0) * scale_y, 4)

            self._mark_modified()
            self._render_all_views(reset_preview=False)
            self._set_status(self._t("status_res_scaled", w=new_w, h=new_h))

        ttk.Button(res_frame, text=self._t("btn_scale_res"), command=apply_resolution_scale).pack(side="left", padx=(6, 0))

        # Card 3: Active Effect Controls
        effects = preset.get("effects", [])
        if not effects:
            return
        if self.selected_effect_idx >= len(effects):
            self.selected_effect_idx = 0
        effect = effects[self.selected_effect_idx]

        outer3, eff_card = create_hairline_card(parent, padding=10)
        outer3.pack(fill="x", padx=10, pady=(6, 14))

        eff_top = ttk.Frame(eff_card, style="Card.TFrame")
        eff_top.pack(fill="x", pady=(0, 8))
        ttk.Label(eff_top, text=self._t("card_active_effect"), style="CardSection.TLabel").pack(side="left")

        enabled_var = tk.BooleanVar(value=bool(effect.get("enabled", True)))
        ttk.Checkbutton(
            eff_top, text=self._t("chk_enabled"), style="Card.TCheckbutton", variable=enabled_var,
            command=lambda: self._set_dict_val(effect, "enabled", enabled_var.get(), refresh_preview=True),
        ).pack(side="right")

        eff_combo = ttk.Combobox(eff_card, values=[f"[{i}] {e.get('effect', 'unknown')}" for i, e in enumerate(effects)], state="readonly")
        eff_combo.current(self.selected_effect_idx)
        eff_combo.pack(fill="x", pady=(0, 10))
        eff_combo.bind("<<ComboboxSelected>>", lambda _e: (setattr(self, "selected_effect_idx", eff_combo.current()), self._render_visual_editor()))

        tk.Frame(eff_card, bg=self.c["border"], height=1).pack(fill="x", pady=(0, 8))

        params = effect.get("params", {})
        priority_keys = [
            "text", "font", "font_style", "caps", "size", "position", "scale", "scale_width",
            "uniform_scale", "rotation", "anchor", "anti_flicker", "fill", "fill_color", "stroke",
            "stroke_color", "stroke_width", "background", "background_color", "background_opacity",
            "background_size", "shadow", "shadow_color", "shadow_distance", "opacity",
        ]
        ordered_keys = [k for k in priority_keys if k in params] + [k for k in sorted(params.keys()) if k not in priority_keys]
        groups = {
            "Transform": [], "Text & Typography": [], "Fill & Outline": [],
            "Background & Shadow": [], "Other": [],
        }
        for key in ordered_keys:
            low = key.lower()
            if low in {"position", "scale", "scale_width", "uniform_scale", "rotation", "anchor", "anti_flicker"}:
                group = "Transform"
            elif any(token in low for token in ("font", "text", "caps", "tracking", "kerning", "leading", "baseline", "vertical", "align", "size")):
                group = "Text & Typography"
            elif any(token in low for token in ("fill", "stroke", "color", "gradient", "opacity")) and not low.startswith("background") and not low.startswith("shadow"):
                group = "Fill & Outline"
            elif low.startswith(("background", "shadow")):
                group = "Background & Shadow"
            else:
                group = "Other"
            groups[group].append(key)

        group_titles = {
            "Transform": "TRANSFORMAÇÃO" if self.lang == "pt" else "TRANSFORM",
            "Text & Typography": "TEXTO E TIPOGRAFIA" if self.lang == "pt" else "TEXT & TYPOGRAPHY",
            "Fill & Outline": "PREENCHIMENTO E CONTORNO" if self.lang == "pt" else "FILL & OUTLINE",
            "Background & Shadow": "FUNDO E SOMBRA" if self.lang == "pt" else "BACKGROUND & SHADOW",
            "Other": "OUTROS" if self.lang == "pt" else "OTHER",
        }
        for group_name, group_keys in groups.items():
            valid_keys = [k for k in group_keys if isinstance(params.get(k), dict) and isinstance(params[k].get("value"), dict) and params[k]["value"]]
            if not valid_keys:
                continue
            group_outer, group_card = create_hairline_card(eff_card, padding=8)
            group_outer.pack(fill="x", pady=(4, 6))
            ttk.Label(group_card, text=group_titles[group_name], style="CardSection.TLabel").pack(anchor="w", pady=(0, 5))
            grid_frame = ttk.Frame(group_card, style="Card.TFrame")
            grid_frame.pack(fill="x")
            grid_frame.columnconfigure(1, weight=1)
            for row_idx, key in enumerate(valid_keys):
                param_obj = params[key]
                val_wrapper = param_obj["value"]
                type_tag = next(iter(val_wrapper.keys()))
                raw_val = val_wrapper[type_tag]
                has_kf = isinstance(param_obj.get("keyframes"), list) and len(param_obj["keyframes"]) > 0
                label_text = f"{key}" + (f" ({len(param_obj['keyframes'])})" if has_kf else "")
                name_lbl = ttk.Label(grid_frame, text=label_text, style="CardMuted.TLabel", width=18)
                name_lbl.grid(row=row_idx, column=0, sticky="w", pady=4, padx=(0, 6))
                self._param_labels[id(param_obj)] = (name_lbl, key)
                self._build_filmcraft_param_widget(grid_frame, row_idx, key, val_wrapper, type_tag, raw_val, param_obj)

        self._refresh_live_params()

    def _build_filmcraft_param_widget(self, parent, row, key, val_wrapper, type_tag, raw_val, param_obj):
        row_box = ttk.Frame(parent, style="Card.TFrame")
        row_box.grid(row=row, column=1, sticky="ew", pady=3)

        if type_tag == "Bool":
            var = tk.BooleanVar(value=bool(raw_val))
            cb = ttk.Checkbutton(
                row_box, text=self._t("chk_active") if raw_val else self._t("chk_inactive"), style="Card.TCheckbutton", variable=var,
                command=lambda: (
                    self._set_dict_val(val_wrapper, "Bool", var.get(), refresh_preview=True),
                    cb.config(text=self._t("chk_active") if var.get() else self._t("chk_inactive")),
                ),
            )
            cb.pack(side="left")

        elif type_tag == "Text":
            var = tk.StringVar(value=str(raw_val))
            ttk.Entry(row_box, textvariable=var).pack(side="left", fill="x", expand=True)
            var.trace_add("write", lambda *_: self._set_dict_val(val_wrapper, "Text", var.get(), refresh_preview=True))

        elif type_tag in ("Float", "Choice"):
            var = tk.StringVar(value=str(raw_val))
            num_entry = ttk.Entry(row_box, textvariable=var, width=10)
            num_entry.pack(side="left")

            def on_num_change(*_):
                if self._inspector_syncing:
                    return
                try:
                    parsed = int(var.get().strip()) if type_tag == "Choice" else float(var.get().strip())
                except ValueError:
                    return
                if type_tag == "Float" and param_obj.get("keyframes"):
                    self._write_keyframed_value(param_obj, "Float", parsed)
                else:
                    self._set_dict_val(val_wrapper, type_tag, parsed, refresh_preview=True)

            var.trace_add("write", on_num_change)

            if type_tag == "Float":
                def refresh_float(t_ns, playing, var=var, entry=num_entry):
                    if not playing and self._has_focus(entry):
                        return
                    val = evaluate_filmcraft_param(param_obj, t_ns)
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        self._set_var_quiet(var, self._fmt_num(val), float(val))

                self._live_params.append(refresh_float)

        elif type_tag == "Color":
            hex_code = rgba_float_to_hex(raw_val)
            swatch = tk.Label(row_box, bg=hex_code, width=3, relief="flat", highlightthickness=1, highlightbackground=self.c["border_light"], cursor="hand2")
            swatch.pack(side="left", padx=(0, 6))
            info_lbl = ttk.Label(row_box, text=hex_code.upper(), style="Card.TLabel", font=(MONO_FONT, 9))

            def pick_color():
                chosen = colorchooser.askcolor(color=rgba_float_to_hex(val_wrapper["Color"]), title=self._t("dlg_pick_color"))
                if chosen and chosen[1]:
                    alpha = val_wrapper["Color"][3] if len(val_wrapper["Color"]) >= 4 else 1.0
                    val_wrapper["Color"] = hex_to_rgba_float(chosen[1], alpha)
                    swatch.config(bg=chosen[1])
                    info_lbl.config(text=chosen[1].upper())
                    self._mark_modified()
                    self.preview_widget.render_frame()

            swatch.bind("<Button-1>", lambda _e: pick_color())
            ttk.Button(row_box, text=self._t("btn_color"), width=5, command=pick_color).pack(side="left", padx=(0, 6))
            info_lbl.pack(side="left")

        elif type_tag == "Vec2" and isinstance(raw_val, dict):
            x_var = tk.StringVar(value=str(raw_val.get("x", 0.0)))
            y_var = tk.StringVar(value=str(raw_val.get("y", 0.0)))
            ttk.Label(row_box, text="X", style="CardMuted.TLabel").pack(side="left")
            x_entry = ttk.Entry(row_box, textvariable=x_var, width=7)
            x_entry.pack(side="left", padx=(3, 6))
            ttk.Label(row_box, text="Y", style="CardMuted.TLabel").pack(side="left")
            y_entry = ttk.Entry(row_box, textvariable=y_var, width=7)
            y_entry.pack(side="left", padx=(3, 0))

            def on_vec_change(*_):
                if self._inspector_syncing:
                    return
                try:
                    nx, ny = float(x_var.get()), float(y_var.get())
                except ValueError:
                    return
                if param_obj.get("keyframes"):
                    self._write_keyframed_value(param_obj, "Vec2", {"x": nx, "y": ny})
                else:
                    raw_val["x"], raw_val["y"] = nx, ny
                    self._mark_modified()
                    self.preview_widget.render_frame()

            x_var.trace_add("write", on_vec_change)
            y_var.trace_add("write", on_vec_change)

            def refresh_vec(t_ns, playing):
                if not playing and (self._has_focus(x_entry) or self._has_focus(y_entry)):
                    return
                val = evaluate_filmcraft_param(param_obj, t_ns)
                if isinstance(val, dict):
                    nx, ny = float(val.get("x", 0.0)), float(val.get("y", 0.0))
                    self._set_var_quiet(x_var, self._fmt_num(nx), nx)
                    self._set_var_quiet(y_var, self._fmt_num(ny), ny)

            self._live_params.append(refresh_vec)
        else:
            ttk.Label(row_box, text=json.dumps(raw_val), style="CardMuted.TLabel").pack(side="left")

        if type_tag in ("Float", "Vec2"):
            has_kf = isinstance(param_obj.get("keyframes"), list) and len(param_obj["keyframes"]) > 0
            ttk.Button(
                row_box,
                text="◆" if has_kf else "◇",
                width=2,
                style="KeyframeOn.TButton" if has_kf else "KeyframeOff.TButton",
                command=lambda k=key, p=param_obj, t=type_tag: self._open_keyframes_editor(k, p, t),
            ).pack(side="right", padx=(6, 0))

    def _open_keyframes_editor(self, param_name, param_obj, type_tag):
        win = tk.Toplevel(self.root)
        win.title(self._t("kf_win_title", param=param_name, tag=type_tag))
        win.geometry("640x400")
        win.configure(bg=self.c["panel"])
        win.transient(self.root)

        if not isinstance(param_obj.get("keyframes"), list) or len(param_obj["keyframes"]) == 0:
            base_val = copy.deepcopy(param_obj["value"][type_tag])
            param_obj["keyframes"] = [
                {"time": 0, "value": {type_tag: copy.deepcopy(base_val)}, "interp": "AutoBezier", "out_influence": 1 / 3, "in_influence": 1 / 3},
                {"time": 1500000000, "value": {type_tag: copy.deepcopy(base_val)}, "interp": "ContinuousBezier", "out_influence": 1 / 3, "in_influence": 1 / 3},
            ]
            self._mark_modified()
            self._sync_preview(reset_time=False)

        top_info = ttk.Frame(win, style="PanelHeader.TFrame", padding=(14, 10))
        top_info.pack(fill="x")
        ttk.Label(top_info, text=self._t("kf_header", param=param_name.upper()), style="SectionTag.TLabel").pack(side="left")

        list_frame = ScrollableFrame(win, bg_color=self.c["panel"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=8)

        def rebuild_rows():
            for w in list_frame.inner.winfo_children():
                w.destroy()

            kfs = param_obj.get("keyframes", [])
            for idx, kf in enumerate(kfs):
                outer, row = create_hairline_card(list_frame.inner, padding=8)
                outer.pack(fill="x", pady=4)

                t_var = tk.StringVar(value=f"{kf.get('time', 0) / 1_000_000_000.0:.3f}")
                kf_lbl = ttk.Label(row, text=self._t("kf_time_lbl", idx=idx + 1), style="Card.TLabel", cursor="hand2")
                kf_lbl.pack(side="left", padx=(0, 4))
                kf_lbl.bind("<Button-1>", lambda _e, k_item=kf: (self.preview_widget.pause(), self.preview_widget.seek(int(k_item.get("time", 0)))))
                ttk.Entry(row, textvariable=t_var, width=8).pack(side="left", padx=(0, 8))

                interp_var = tk.StringVar(value=kf.get("interp", "AutoBezier"))
                ttk.Combobox(row, textvariable=interp_var, values=["AutoBezier", "ContinuousBezier", "Linear", "Hold"], state="readonly", width=16).pack(side="left", padx=(0, 8))

                val_dict = kf.setdefault("value", {})
                if type_tag == "Float":
                    v_var = tk.StringVar(value=str(val_dict.get("Float", 0.0)))
                    ttk.Label(row, text=self._t("kf_val_lbl"), style="CardMuted.TLabel").pack(side="left")
                    ttk.Entry(row, textvariable=v_var, width=10).pack(side="left", padx=(4, 8))

                    def bind_float(k_item=kf, tv=t_var, vv=v_var, iv=interp_var):
                        def _upd(*_):
                            try:
                                k_item["time"] = int(round(float(tv.get()) * 1_000_000_000))
                                k_item["value"]["Float"] = float(vv.get())
                                k_item["interp"] = iv.get()
                                self._mark_modified()
                                self._sync_preview(reset_time=False)
                            except ValueError:
                                pass
                        tv.trace_add("write", _upd)
                        vv.trace_add("write", _upd)
                        iv.trace_add("write", _upd)
                    bind_float()
                else:
                    vec = val_dict.setdefault("Vec2", {"x": 0.0, "y": 0.0})
                    vx_var = tk.StringVar(value=str(vec.get("x", 0.0)))
                    vy_var = tk.StringVar(value=str(vec.get("y", 0.0)))
                    ttk.Label(row, text="X:", style="CardMuted.TLabel").pack(side="left")
                    ttk.Entry(row, textvariable=vx_var, width=8).pack(side="left", padx=(2, 6))
                    ttk.Label(row, text="Y:", style="CardMuted.TLabel").pack(side="left")
                    ttk.Entry(row, textvariable=vy_var, width=8).pack(side="left", padx=(2, 8))

                    def bind_vec(k_item=kf, tv=t_var, xv=vx_var, yv=vy_var, iv=interp_var):
                        def _upd(*_):
                            try:
                                k_item["time"] = int(round(float(tv.get()) * 1_000_000_000))
                                k_item["value"]["Vec2"]["x"] = float(xv.get())
                                k_item["value"]["Vec2"]["y"] = float(yv.get())
                                k_item["interp"] = iv.get()
                                self._mark_modified()
                                self._sync_preview(reset_time=False)
                            except ValueError:
                                pass
                        tv.trace_add("write", _upd)
                        xv.trace_add("write", _upd)
                        yv.trace_add("write", _upd)
                        iv.trace_add("write", _upd)
                    bind_vec()

                def remove_kf(i=idx):
                    if len(kfs) <= 1:
                        del param_obj["keyframes"]
                        self._mark_modified()
                        self._render_all_views(reset_preview=False)
                        win.destroy()
                        return
                    kfs.pop(i)
                    self._mark_modified()
                    self._sync_preview(reset_time=False)
                    rebuild_rows()

                ttk.Button(row, text="✕", width=3, style="Danger.TButton", command=remove_kf).pack(side="right")

        def add_kf():
            kfs = param_obj.setdefault("keyframes", [])
            last = copy.deepcopy(kfs[-1]) if kfs else {"time": 0, "value": copy.deepcopy(param_obj["value"])}
            last["time"] = int(last.get("time", 0) + 500_000_000)
            kfs.append(last)
            self._mark_modified()
            self._sync_preview(reset_time=False)
            rebuild_rows()

        bottom = ttk.Frame(win, style="PanelHeader.TFrame", padding=12)
        bottom.pack(fill="x")
        ttk.Button(bottom, text=self._t("btn_add_kf_row"), style="Accent.TButton", command=add_kf).pack(side="left")
        ttk.Button(bottom, text=self._t("btn_done"), command=lambda: (self._render_visual_editor(), win.destroy())).pack(side="right")
        rebuild_rows()

    def _render_generic_visual_editor(self, parent):
        outer, card = create_hairline_card(parent, padding=12)
        outer.pack(fill="x", padx=10, pady=10)
        ttk.Label(card, text=self._t("card_generic_props"), style="CardSection.TLabel").pack(anchor="w", pady=(0, 10))

        if not isinstance(self.current_data, dict):
            ttk.Label(card, text=self._t("generic_non_dict"), style="Card.TLabel").pack(anchor="w")
            return

        grid = ttk.Frame(card, style="Card.TFrame")
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        row = 0
        for key, val in self.current_data.items():
            if isinstance(val, (str, int, float, bool)):
                ttk.Label(grid, text=f"{key}", style="CardMuted.TLabel", width=20).grid(row=row, column=0, sticky="w", pady=4)
                if isinstance(val, bool):
                    bvar = tk.BooleanVar(value=val)
                    ttk.Checkbutton(grid, text=self._t("chk_enabled"), style="Card.TCheckbutton", variable=bvar, command=lambda k=key, v=bvar: self._set_dict_val(self.current_data, k, v.get())).grid(row=row, column=1, sticky="w", pady=4)
                else:
                    svar = tk.StringVar(value=str(val))
                    ttk.Entry(grid, textvariable=svar).grid(row=row, column=1, sticky="ew", pady=4)
                    svar.trace_add("write", lambda *_, d=self.current_data, k=key, v=svar, t=type(val): self._apply_typed_var(d, k, v, t))
                row += 1
            elif isinstance(val, dict):
                ttk.Label(grid, text=key.upper(), style="CardSection.TLabel").grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 4))
                row += 1
                for sub_k, sub_v in val.items():
                    if isinstance(sub_v, (str, int, float, bool)):
                        ttk.Label(grid, text=f"  {sub_k}", style="CardMuted.TLabel", width=20).grid(row=row, column=0, sticky="w", pady=3)
                        if isinstance(sub_v, bool):
                            sbvar = tk.BooleanVar(value=sub_v)
                            ttk.Checkbutton(grid, text=self._t("chk_enabled"), style="Card.TCheckbutton", variable=sbvar, command=lambda d=val, k=sub_k, v=sbvar: self._set_dict_val(d, k, v.get())).grid(row=row, column=1, sticky="w", pady=3)
                        else:
                            ssvar = tk.StringVar(value=str(sub_v))
                            ttk.Entry(grid, textvariable=ssvar).grid(row=row, column=1, sticky="ew", pady=3)
                            ssvar.trace_add("write", lambda *_, d=val, k=sub_k, v=ssvar, t=type(sub_v): self._apply_typed_var(d, k, v, t))
                        row += 1

    def _apply_typed_var(self, target_dict, key, var, orig_type):
        txt = var.get()
        try:
            parsed = int(txt) if orig_type is int else (float(txt) if orig_type is float else txt)
            self._set_dict_val(target_dict, key, parsed)
        except ValueError:
            pass

    # --- Universal JSON Tree ---
    def _render_tree_view(self):
        self.tree.delete(*self.tree.get_children())
        self._tree_paths = {}
        if self.current_data is not None:
            self._populate_tree("", "root", self.current_data, [])

    def _populate_tree(self, parent_id, label, node, path):
        if isinstance(node, dict):
            item_id = self.tree.insert(parent_id, "end", text=str(label), values=("Object", f"{{{len(node)}}}"), open=(len(path) < 3))
            self._tree_paths[item_id] = path
            for k, v in node.items():
                self._populate_tree(item_id, k, v, path + [k])
        elif isinstance(node, list):
            item_id = self.tree.insert(parent_id, "end", text=str(label), values=("Array", f"[{len(node)}]"), open=(len(path) < 3))
            self._tree_paths[item_id] = path
            for idx, v in enumerate(node):
                self._populate_tree(item_id, f"[{idx}]", v, path + [idx])
        else:
            item_id = self.tree.insert(parent_id, "end", text=str(label), values=(type(node).__name__, str(node)))
            self._tree_paths[item_id] = path

    def _get_by_path(self, path):
        curr = self.current_data
        for step in path:
            curr = curr[step]
        return curr

    def _tree_edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        path = self._tree_paths.get(sel[0])
        if not path:
            return
        current_val = self._get_by_path(path)
        if isinstance(current_val, (dict, list)):
            messagebox.showinfo(self._t("dlg_notice"), self._t("dlg_select_leaf"))
            return
        new_str = simpledialog.askstring(
            self._t("dlg_edit_val_title"), self._t("dlg_edit_val_prompt", key=path[-1]),
            initialvalue=json.dumps(current_val) if isinstance(current_val, bool) else str(current_val),
            parent=self.root,
        )
        if new_str is not None:
            self._get_by_path(path[:-1])[path[-1]] = self._smart_parse_value(new_str, type(current_val))
            self._mark_modified()
            self._render_all_views(reset_preview=False)

    def _tree_add_node(self):
        if self.current_data is None:
            return
        sel = self.tree.selection()
        path = self._tree_paths.get(sel[0], []) if sel else []
        target = self._get_by_path(path)
        if not isinstance(target, (dict, list)):
            path = path[:-1]
            target = self._get_by_path(path)

        if isinstance(target, dict):
            key = simpledialog.askstring(self._t("dlg_new_key_title"), self._t("dlg_new_key_prompt"), parent=self.root)
            if not key:
                return
            val_str = simpledialog.askstring(self._t("dlg_init_val_title"), self._t("dlg_init_val_prompt", key=key), parent=self.root)
            if val_str is None:
                return
            target[key] = self._smart_parse_value(val_str)
        elif isinstance(target, list):
            val_str = simpledialog.askstring(self._t("dlg_new_item_title"), self._t("dlg_new_item_prompt"), parent=self.root)
            if val_str is None:
                return
            target.append(self._smart_parse_value(val_str))

        self._mark_modified()
        self._render_all_views(reset_preview=False)

    def _tree_delete_node(self):
        sel = self.tree.selection()
        if not sel:
            return
        path = self._tree_paths.get(sel[0])
        if not path:
            messagebox.showwarning(self._t("dlg_notice"), self._t("dlg_cannot_del_root"))
            return
        del self._get_by_path(path[:-1])[path[-1]]
        self._mark_modified()
        self._render_all_views(reset_preview=False)

    @staticmethod
    def _smart_parse_value(text, hint_type=None):
        s = text.strip()
        if s.lower() == "true":
            return True
        if s.lower() == "false":
            return False
        if s.lower() == "null":
            return None
        try:
            return json.loads(s)
        except Exception:
            if hint_type is int:
                try:
                    return int(s)
                except ValueError:
                    pass
            if hint_type is float:
                try:
                    return float(s)
                except ValueError:
                    pass
            return text

    # --- Raw JSON Code ---
    def _render_raw_view(self):
        self.raw_text.delete("1.0", tk.END)
        if self.current_data is not None:
            self.raw_text.insert("1.0", json.dumps(self.current_data, indent=2, ensure_ascii=False))

    def _format_raw_json(self):
        content = self.raw_text.get("1.0", tk.END).strip()
        if not content:
            return
        try:
            parsed = json.loads(content)
            self.raw_text.delete("1.0", tk.END)
            self.raw_text.insert("1.0", json.dumps(parsed, indent=2, ensure_ascii=False))
        except json.JSONDecodeError as e:
            messagebox.showerror(self._t("dlg_json_syntax_title"), self._t("dlg_json_syntax_msg", line=e.lineno, col=e.colno, msg=e.msg))

    def _apply_raw_json_to_model(self, silent=False):
        content = self.raw_text.get("1.0", tk.END).strip()
        if not content:
            return False
        try:
            self.current_data = json.loads(content)
            self._mark_modified()
            self._sync_preview(reset_time=False)
            self._render_visual_editor()
            self._render_tree_view()
            if not silent:
                self._set_status(self._t("status_raw_applied"))
            return True
        except json.JSONDecodeError as e:
            messagebox.showerror(self._t("dlg_json_syntax_title"), self._t("dlg_json_fix_msg", line=e.lineno, col=e.colno, msg=e.msg))
            return False

    # --- Helpers ---
    def _update_doc_pill(self):
        if not self.current_file_path:
            self.doc_pill_var.set(self._t("no_file_selected"))
            self.status_dot.config(fg=self.c["success"])
        elif self.modified:
            self.doc_pill_var.set(f"{self.current_file_path.name}  •")
            self.status_dot.config(fg=self.c["accent"])
        else:
            self.doc_pill_var.set(self.current_file_path.name)
            self.status_dot.config(fg=self.c["success"])

    def _set_dict_val(self, target_dict, key, value, refresh_preview=False):
        target_dict[key] = value
        self._mark_modified()
        if refresh_preview:
            self.preview_widget.render_frame()

    def _refresh_live_params(self, t_ns=None):
        if not self._live_params:
            return
        if t_ns is None:
            t_ns = self.preview_widget.current_time_ns
        playing = self.preview_widget.is_playing
        for refresh in list(self._live_params):
            try:
                refresh(t_ns, playing)
            except tk.TclError:
                pass

    def _has_focus(self, widget):
        try:
            return self.root.focus_get() is widget
        except (KeyError, tk.TclError):
            return False

    @staticmethod
    def _fmt_num(value):
        s = f"{float(value):.4f}".rstrip("0")
        return s + "0" if s.endswith(".") else s

    def _set_var_quiet(self, var, text, number):
        try:
            if abs(float(var.get()) - number) < 1e-6:
                return
        except ValueError:
            pass
        self._inspector_syncing = True
        try:
            var.set(text)
        finally:
            self._inspector_syncing = False

    def _write_keyframed_value(self, param_obj, type_tag, new_val):
        pv = self.preview_widget
        pv.pause()
        t = int(pv.current_time_ns)
        tol = int(pv.frame_ns() // 2)
        kfs = param_obj.setdefault("keyframes", [])

        target = next((kf for kf in kfs if abs(int(kf.get("time", 0)) - t) <= tol), None)
        if target is None:
            earlier = [kf for kf in kfs if int(kf.get("time", 0)) < t]
            prev = max(earlier, key=lambda k: k.get("time", 0)) if earlier else {}
            kfs.append({
                "time": t,
                "value": {type_tag: copy.deepcopy(new_val)},
                "interp": prev.get("interp", "AutoBezier"),
                "out_influence": 1 / 3,
                "in_influence": 1 / 3,
            })
            kfs.sort(key=lambda k: k.get("time", 0))
            lbl_info = self._param_labels.get(id(param_obj))
            if lbl_info:
                lbl_info[0].config(text=f"{lbl_info[1]} ({len(kfs)})")
        else:
            target.setdefault("value", {})[type_tag] = copy.deepcopy(new_val)

        self._mark_modified()
        self._sync_preview(reset_time=False)

    def _mark_modified(self):
        self.modified = True
        self._update_doc_pill()
        if self.current_file_path:
            self._set_status(self._t("status_editing", name=self.current_file_path.name))

    def _set_status(self, msg):
        self.status_var.set(msg)


def main():
    root = tk.Tk()
    PresetManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()