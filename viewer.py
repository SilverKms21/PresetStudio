#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NLE Compositing Viewer (DaVinci Resolve style) with:
- Oriented Bounding Box Gizmo (Body Move, 4 Corner Scale, 4 Edge Non-Uniform Scale, Top Rotation Handle)
- Dedicated Anchor Point Gizmo & Spatial Motion Path Keyframe Dragging
- Viewport Zoom & Pan (Wheel Zoom, Middle-Click Pan) + Magnetic Center/Thirds Snap Guides
- Live Transform HUD, Auto-Key toggle, and Layered Caching
"""

import copy
import math
import time
import tkinter as tk
from tkinter import colorchooser, ttk

from engine import (
    blend_rgba_on_bg,
    build_shape_vertices,
    evaluate_filmcraft_param,
    hex_to_rgba_float,
    inverse_rotate_offset,
    point_in_polygon,
    sample_motion_path,
    transform_point_2d,
)
from i18n import tr
from theme import MONO_FONT, UI_FONT


class ResolveViewerWidget(ttk.Frame):
    """NLE Viewer with multi-handle transform gizmos, motion path editing, and zoom/pan."""

    _TL_PAD = 12
    _TL_RULER_H = 24
    _TL_LABEL_W = 118
    _TL_ROW_H = 24

    _OBJ_KEYS = [
        "obj_auto", "obj_text", "obj_rect", "obj_square",
        "obj_circle", "obj_triangle", "obj_diamond", "obj_star", "obj_block_text",
    ]
    _BG_KEYS = ["bg_dark", "bg_checker", "bg_chroma"]
    _TOOL_KEYS = ["transform", "anchor", "path"]

    def __init__(self, parent, colors, lang="en", on_modified=None):
        super().__init__(parent, style="Panel.TFrame")
        self.c = colors
        self.lang = lang
        self.on_modified_callback = on_modified

        self.preset_data = None
        self.is_playing = True
        self.current_time_ns = 0
        self.duration_ns = 3_000_000_000
        self._last_tick = time.perf_counter()
        self._after_id = None
        self.fps = 30
        self.time_listener = None

        # Viewport Zoom & Pan
        self.zoom_factor = 1.0
        self.zoom_fit = True
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._panning = False
        self._pan_start = (0.0, 0.0)

        # Caching & Interaction State
        self._tl_dragging = False
        self._tl_drag_kf = None
        self._tl_bg_key = None
        self._bg_cache_key = None
        self._stage_bg_hex = "#0a0b0d"

        self._active_tool = "transform"  # "transform" | "anchor" | "path"
        self._drag_mode = None  # None | "move" | "scale_corner" | "scale_x" | "scale_y" | "rotate" | "anchor" | "path_kf"
        self._drag_kf_ref = None
        self._drag_start_canvas = (0.0, 0.0)
        self._drag_start_pos = (0.0, 0.0)
        self._drag_start_anchor = (0.0, 0.0)
        self._stage_transform = None
        self._gizmo_geometry = {}
        self._snap_lines = []
        self._keyframe_cache = None
        self._keyframe_cache_signature = None

        self.example_color_hex = "#e8943a"
        self.obj_mode_code = "obj_auto"
        self.bg_mode_code = "bg_dark"

        self._build_ui()

    def _t(self, key, **kwargs):
        return tr(self.lang, key, **kwargs)

    def _build_ui(self):
        # Row 1: Viewer Header + View & Overlay Toggles
        header = ttk.Frame(self, style="PanelHeader.TFrame", padding=(10, 6))
        header.pack(fill="x")

        title_wrap = ttk.Frame(header, style="PanelHeader.TFrame")
        title_wrap.pack(side="left")
        ttk.Label(title_wrap, text=self._t("viewer_header"), style="SectionTag.TLabel").pack(side="left")

        self.res_badge_var = tk.StringVar(value="1920 × 1080  •  3.00s")
        ttk.Label(title_wrap, textvariable=self.res_badge_var, style="Badge.TLabel").pack(side="left", padx=(8, 0))

        opts_frame = ttk.Frame(header, style="PanelHeader.TFrame")
        opts_frame.pack(side="right")

        self.guides_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text=self._t("chk_safe_guides"), style="Header.TCheckbutton", variable=self.guides_var, command=self._invalidate_bg_and_render).pack(side="left", padx=3)

        self.thirds_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts_frame, text=self._t("chk_thirds"), style="Header.TCheckbutton", variable=self.thirds_var, command=self._invalidate_bg_and_render).pack(side="left", padx=3)

        self.anchor_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text=self._t("chk_anchor"), style="Header.TCheckbutton", variable=self.anchor_var, command=self.render_frame).pack(side="left", padx=3)

        self.path_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text=self._t("chk_path"), style="Header.TCheckbutton", variable=self.path_var, command=self.render_frame).pack(side="left", padx=3)

        self.snap_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts_frame, text=self._t("chk_snap"), style="Header.TCheckbutton", variable=self.snap_var).pack(side="left", padx=3)

        ttk.Label(opts_frame, text=self._t("lbl_speed"), style="HeaderMuted.TLabel").pack(side="left", padx=(6, 2))
        self.speed_combo = ttk.Combobox(opts_frame, values=["1x", "2x", "5x", "10x", "50x", "100x"], state="readonly", width=4)
        self.speed_combo.current(0)
        self.speed_combo.pack(side="left", padx=(0, 6))

        bg_labels = [self._t(k) for k in self._BG_KEYS]
        self.bg_combo = ttk.Combobox(opts_frame, values=bg_labels, state="readonly", width=16)
        self.bg_combo.current(0)
        self.bg_combo.pack(side="left")
        self.bg_combo.bind("<<ComboboxSelected>>", self._on_bg_selected)

        tk.Frame(self, bg=self.c["border"], height=1).pack(fill="x")

        # Row 2: Compositing Tool Strip (Gizmo Modes, Zoom, Auto-Key, Quick Keyframe)
        toolstrip = ttk.Frame(self, style="Deck.TFrame", padding=(10, 5))
        toolstrip.pack(fill="x")

        tool_pills = tk.Frame(toolstrip, bg=self.c["well"], highlightbackground=self.c["border"], highlightthickness=1, padx=2, pady=2)
        tool_pills.pack(side="left")

        self.tool_btns = {}
        tool_map = [
            ("transform", self._t("tool_transform")),
            ("anchor", self._t("tool_anchor")),
            ("path", self._t("tool_path")),
        ]
        for code, label in tool_map:
            btn = tk.Label(tool_pills, text=label, bg=self.c["well"], fg=self.c["fg_muted"], font=(UI_FONT, 8, "bold"), padx=9, pady=2, cursor="hand2")
            btn.pack(side="left", padx=1)
            btn.bind("<Button-1>", lambda _e, c=code: self._set_active_tool(c))
            self.tool_btns[code] = btn
        self._update_tool_pill_styles()

        # Zoom controls
        zoom_wrap = ttk.Frame(toolstrip, style="Deck.TFrame")
        zoom_wrap.pack(side="left", padx=(12, 0))
        ttk.Label(zoom_wrap, text=self._t("lbl_zoom"), style="DeckMuted.TLabel").pack(side="left", padx=(0, 4))
        self.zoom_combo = ttk.Combobox(
            zoom_wrap,
            values=[self._t("zoom_fit"), "25%", "50%", "75%", "100%", "150%", "200%"],
            state="readonly",
            width=7,
        )
        self.zoom_combo.current(0)
        self.zoom_combo.pack(side="left")
        self.zoom_combo.bind("<<ComboboxSelected>>", self._on_zoom_selected)

        # Right side of toolstrip: Auto-Key, Stamp KF, Reset Transform
        kf_actions = ttk.Frame(toolstrip, style="Deck.TFrame")
        kf_actions.pack(side="right")

        self.auto_key_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(kf_actions, text=self._t("chk_autokey"), style="Deck.TCheckbutton", variable=self.auto_key_var).pack(side="left", padx=(0, 8))

        ttk.Button(kf_actions, text=self._t("btn_add_kf"), style="KeyframeOn.TButton", command=self._stamp_all_transform_keyframes).pack(side="left", padx=(0, 4))
        ttk.Button(kf_actions, text=self._t("btn_reset_tf"), style="Ghost.TButton", command=self._reset_active_transform).pack(side="left")

        tk.Frame(self, bg=self.c["border"], height=1).pack(fill="x")

        # Row 3: Monitor Stage (Canvas) + Floating Transform HUD
        monitor_stage = tk.Frame(self, bg=self.c["monitor_gutter"], padx=8, pady=8)
        monitor_stage.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            monitor_stage,
            bg=self.c["monitor_bg"],
            height=300,
            highlightthickness=1,
            highlightbackground=self.c["border"],
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self._invalidate_bg_and_render())
        self.canvas.bind("<Button-1>", self._on_viewer_press)
        self.canvas.bind("<B1-Motion>", self._on_viewer_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_viewer_release)
        self.canvas.bind("<Motion>", self._on_viewer_hover)

        # Pan & Zoom bindings
        self.canvas.bind("<Button-2>", self._on_pan_start)
        self.canvas.bind("<B2-Motion>", self._on_pan_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_pan_end)
        self.canvas.bind("<MouseWheel>", self._on_canvas_wheel)
        self.canvas.bind("<Button-4>", self._on_canvas_wheel)
        self.canvas.bind("<Button-5>", self._on_canvas_wheel)

        # Compact Live HUD Strip under Canvas
        hud_bar = tk.Frame(monitor_stage, bg=self.c["well"], highlightbackground=self.c["border"], highlightthickness=1, padx=8, pady=3)
        hud_bar.pack(fill="x", pady=(4, 0))

        self.hud_metrics_var = tk.StringVar(value="Pos: 960.0, 540.0  |  Scale: 100.0% × 100.0%  |  Rot: 0.0°  |  Anchor: 0.0, 0.0")
        tk.Label(hud_bar, textvariable=self.hud_metrics_var, bg=self.c["well"], fg=self.c["accent"], font=(MONO_FONT, 8, "bold")).pack(side="left")

        self.cursor_coords_var = tk.StringVar(value="XY: 0, 0")
        tk.Label(hud_bar, textvariable=self.cursor_coords_var, bg=self.c["well"], fg=self.c["fg_muted"], font=(MONO_FONT, 8)).pack(side="right")

        tk.Frame(self, bg=self.c["border"], height=1).pack(fill="x")

        # Row 4: Transport & Timeline Deck
        deck = ttk.Frame(self, style="Deck.TFrame", padding=(12, 7))
        deck.pack(fill="x")

        scrub_row = ttk.Frame(deck, style="Deck.TFrame")
        scrub_row.pack(fill="x", pady=(0, 6))

        self.timeline_canvas = tk.Canvas(
            scrub_row, height=126, bg=self.c["well"],
            highlightthickness=1, highlightbackground=self.c["border"],
            highlightcolor=self.c["accent"], cursor="sb_h_double_arrow",
        )
        self.timeline_canvas.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self.timeline_scroll = ttk.Scrollbar(scrub_row, orient="vertical", command=self.timeline_canvas.yview)
        self.timeline_scroll.pack(side="left", fill="y", padx=(0, 8))
        self.timeline_canvas.configure(yscrollcommand=self.timeline_scroll.set)
        self.timeline_canvas.bind("<Configure>", lambda _e: self._draw_timeline(force_bg=True))
        self.timeline_canvas.bind("<Button-1>", self._on_tl_press)
        self.timeline_canvas.bind("<B1-Motion>", self._on_tl_drag)
        self.timeline_canvas.bind("<ButtonRelease-1>", self._on_tl_release)
        self.timeline_canvas.bind("<Motion>", self._on_tl_hover)
        self.timeline_canvas.bind("<MouseWheel>", lambda e: self.timeline_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))

        self.time_label_var = tk.StringVar(value="00:00.00 / 00:03.00")
        tc_box = tk.Frame(scrub_row, bg=self.c["well"], highlightbackground=self.c["border"], highlightthickness=1, padx=8, pady=2)
        tc_box.pack(side="right")
        tk.Label(tc_box, textvariable=self.time_label_var, bg=self.c["well"], fg=self.c["accent"], font=(MONO_FONT, 9, "bold")).pack()

        transport_row = ttk.Frame(deck, style="Deck.TFrame")
        transport_row.pack(fill="x")

        t_btns = ttk.Frame(transport_row, style="Deck.TFrame")
        t_btns.pack(side="left")

        ttk.Button(t_btns, text="⏮", width=3, style="Transport.TButton", command=self.restart).pack(side="left", padx=(0, 4))
        self.play_btn = ttk.Button(
            t_btns,
            text=self._t("btn_pause") if self.is_playing else self._t("btn_play"),
            width=10,
            style="TransportAccent.TButton",
            command=self.toggle_play,
        )
        self.play_btn.pack(side="left", padx=(0, 8))

        self.loop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(t_btns, text=self._t("chk_loop"), style="Deck.TCheckbutton", variable=self.loop_var).pack(side="left", padx=(0, 8))

        # Dummy Object Controls
        dummy_wrap = ttk.Frame(transport_row, style="Deck.TFrame")
        dummy_wrap.pack(side="right")

        ttk.Label(dummy_wrap, text=self._t("lbl_object"), style="DeckMuted.TLabel").pack(side="left", padx=(0, 4))
        obj_labels = [self._t(k) for k in self._OBJ_KEYS]
        self.example_mode_combo = ttk.Combobox(dummy_wrap, values=obj_labels, state="readonly", width=18)
        self.example_mode_combo.current(0)
        self.example_mode_combo.pack(side="left", padx=(0, 5))
        self.example_mode_combo.bind("<<ComboboxSelected>>", self._on_obj_mode_selected)

        self.example_text_var = tk.StringVar(value=self._t("default_sample_text"))
        self.example_text_var.trace_add("write", lambda *_: self.render_frame())
        ttk.Entry(dummy_wrap, textvariable=self.example_text_var, width=15).pack(side="left", padx=(0, 5))

        self.shape_w_var = tk.StringVar(value="460")
        self.shape_h_var = tk.StringVar(value="240")
        self.shape_w_var.trace_add("write", lambda *_: self.render_frame())
        self.shape_h_var.trace_add("write", lambda *_: self.render_frame())
        ttk.Entry(dummy_wrap, textvariable=self.shape_w_var, width=4).pack(side="left")
        ttk.Label(dummy_wrap, text="×", style="DeckMuted.TLabel").pack(side="left", padx=2)
        ttk.Entry(dummy_wrap, textvariable=self.shape_h_var, width=4).pack(side="left", padx=(0, 5))

        self.example_swatch = tk.Label(
            dummy_wrap,
            bg=self.example_color_hex,
            width=2,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.c["border_light"],
            cursor="hand2",
        )
        self.example_swatch.pack(side="left", padx=(0, 4))
        self.example_swatch.bind("<Button-1>", lambda _e: self._pick_example_color())
        ttk.Button(dummy_wrap, text=self._t("btn_color"), width=5, style="Ghost.TButton", command=self._pick_example_color).pack(side="left")

    # --- Tool / Dropdown Handlers ---
    def _set_active_tool(self, code):
        self._active_tool = code
        self._update_tool_pill_styles()
        self.render_frame()

    def _update_tool_pill_styles(self):
        for code, btn in self.tool_btns.items():
            active = code == self._active_tool
            btn.config(
                bg=self.c["card_hover"] if active else self.c["well"],
                fg=self.c["accent"] if active else self.c["fg_muted"],
            )

    def _on_bg_selected(self, _event=None):
        idx = self.bg_combo.current()
        if 0 <= idx < len(self._BG_KEYS):
            self.bg_mode_code = self._BG_KEYS[idx]
        self._invalidate_bg_and_render()

    def _on_obj_mode_selected(self, _event=None):
        idx = self.example_mode_combo.current()
        if 0 <= idx < len(self._OBJ_KEYS):
            self.obj_mode_code = self._OBJ_KEYS[idx]
        self.render_frame()

    def _on_zoom_selected(self, _event=None):
        val = self.zoom_combo.get()
        if val == self._t("zoom_fit"):
            self.zoom_fit = True
            self.pan_x = 0.0
            self.pan_y = 0.0
        else:
            try:
                pct = float(val.rstrip("%"))
                self.zoom_fit = False
                self.zoom_factor = max(0.1, min(5.0, pct / 100.0))
            except ValueError:
                self.zoom_fit = True
        self._invalidate_bg_and_render()

    def _invalidate_bg_and_render(self):
        self._bg_cache_key = None
        self.render_frame()

    def _pick_example_color(self):
        chosen = colorchooser.askcolor(color=self.example_color_hex, title=self._t("dlg_pick_example_color"))
        if chosen and chosen[1]:
            self.example_color_hex = chosen[1]
            self.example_swatch.config(bg=chosen[1])
            self.render_frame()

    def _notify_modified(self):
        if callable(self.on_modified_callback):
            self.on_modified_callback()

    # --- Preset Setup & Duration ---
    def set_preset(self, preset_dict, reset_time=False):
        self.preset_data = preset_dict
        self._bg_cache_key = None
        self._tl_bg_key = None
        self._keyframe_cache = None
        self._recalculate_duration()
        if reset_time:
            self.current_time_ns = 0
        elif self.current_time_ns > self.duration_ns:
            self.current_time_ns = 0
        self.render_frame()
        if self.is_playing and self.preset_data is not None:
            self._schedule_tick()
        else:
            self._cancel_tick()

    def _recalculate_duration(self):
        if not isinstance(self.preset_data, dict):
            self.duration_ns = 3_000_000_000
            return

        max_kf_ns = 0
        for eff in self.preset_data.get("effects", []):
            for p_obj in eff.get("params", {}).values():
                if isinstance(p_obj, dict) and isinstance(p_obj.get("keyframes"), list):
                    for kf in p_obj["keyframes"]:
                        t = kf.get("time", 0)
                        if isinstance(t, (int, float)) and t > max_kf_ns:
                            max_kf_ns = int(t)

        src_dur = int(self.preset_data.get("source_duration", 3_000_000_000))
        self.duration_ns = max_kf_ns if max_kf_ns > 0 else max(1_000_000_000, min(src_dur, 10_000_000_000))

        dur_sec = self.duration_ns / 1_000_000_000.0
        if dur_sec > 120.0 and self.speed_combo.get() == "1x":
            self.speed_combo.set("50x")
        elif dur_sec <= 15.0 and self.speed_combo.get() in ("50x", "100x"):
            self.speed_combo.set("1x")

        src_size = self.preset_data.get("source_size", [1920, 1080])
        w = src_size[0] if isinstance(src_size, list) and len(src_size) >= 2 else 1920
        h = src_size[1] if isinstance(src_size, list) and len(src_size) >= 2 else 1080
        self.res_badge_var.set(f"{w} × {h}  •  {dur_sec:.2f}s")

    # --- Playback Timer (0% CPU when paused) ---
    def _schedule_tick(self):
        if self._after_id is None and self.is_playing and self.preset_data is not None:
            self._last_tick = time.perf_counter()
            self._after_id = self.after(33, self._tick)

    def _cancel_tick(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _tick(self):
        self._after_id = None
        if not self.is_playing or self.preset_data is None:
            return

        now = time.perf_counter()
        dt = now - self._last_tick
        self._last_tick = now

        if self.winfo_ismapped():
            try:
                speed_mult = float(self.speed_combo.get().rstrip("x"))
            except ValueError:
                speed_mult = 1.0

            self.current_time_ns += int(dt * speed_mult * 1_000_000_000)
            if self.current_time_ns >= self.duration_ns:
                if self.loop_var.get():
                    self.current_time_ns %= max(1, self.duration_ns)
                else:
                    self.current_time_ns = self.duration_ns
                    self.pause()
            self.render_frame()

        if self.is_playing:
            self._schedule_tick()

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.play_btn.config(text=self._t("btn_pause") if self.is_playing else self._t("btn_play"))
        if self.is_playing:
            self._schedule_tick()
        else:
            self._cancel_tick()

    def pause(self):
        if self.is_playing:
            self.is_playing = False
            self.play_btn.config(text=self._t("btn_play"))
            self._cancel_tick()

    def restart(self):
        self.current_time_ns = 0
        self._last_tick = time.perf_counter()
        self.render_frame()

    def destroy(self):
        self._cancel_tick()
        super().destroy()

    # --- Time Scrubbing ---
    def frame_ns(self):
        return 1_000_000_000.0 / max(1, self.fps)

    def seek(self, t_ns):
        self.current_time_ns = max(0, min(int(t_ns), int(self.duration_ns)))
        self._last_tick = time.perf_counter()
        self.render_frame()

    def step_frames(self, n):
        self.pause()
        idx = round(self.current_time_ns * self.fps / 1_000_000_000.0)
        self.seek(round((idx + n) * 1_000_000_000.0 / self.fps))

    def jump_keyframe(self, direction):
        times = self._collect_keyframe_times()
        cur = self.current_time_ns
        tol = self.frame_ns() / 2.0
        cands = [t for t in times if t > cur + tol] if direction > 0 else [t for t in times if t < cur - tol]
        if cands:
            self.pause()
            self.seek(cands[0] if direction > 0 else cands[-1])

    def go_to_start(self):
        self.pause()
        self.seek(0)

    def go_to_end(self):
        self.pause()
        self.seek(self.duration_ns)

    # --- Viewport Pan & Zoom ---
    def _on_pan_start(self, event):
        self._panning = True
        self._pan_start = (event.x - self.pan_x, event.y - self.pan_y)
        self.canvas.configure(cursor="fleur")

    def _on_pan_drag(self, event):
        if self._panning:
            self.pan_x = event.x - self._pan_start[0]
            self.pan_y = event.y - self._pan_start[1]
            self._invalidate_bg_and_render()

    def _on_pan_end(self, _event):
        self._panning = False
        self.canvas.configure(cursor="arrow")

    def _on_canvas_wheel(self, event):
        if not self._stage_transform:
            return
        _src_w, _src_h, _x0, _y0, cur_ratio = self._stage_transform
        delta = 1 if (getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0) else -1
        factor = 1.15 if delta > 0 else (1.0 / 1.15)
        new_ratio = max(0.05, min(4.0, cur_ratio * factor))
        self.zoom_fit = False
        self.zoom_factor = new_ratio
        self.zoom_combo.set(f"{int(round(new_ratio * 100))}%")
        self._invalidate_bg_and_render()

    # --- Timeline Rendering ---
    def _collect_animated_tracks(self):
        tracks = []
        if not isinstance(self.preset_data, dict):
            return tracks
        for eff_idx, effect in enumerate(self.preset_data.get("effects", [])):
            if not isinstance(effect, dict) or not effect.get("enabled", True):
                continue
            effect_name = str(effect.get("effect", f"Effect {eff_idx + 1}"))
            for key, param in effect.get("params", {}).items():
                kfs = param.get("keyframes") if isinstance(param, dict) else None
                if not isinstance(kfs, list) or not kfs:
                    continue
                valid = [kf for kf in kfs if isinstance(kf, dict) and isinstance(kf.get("time"), (int, float))]
                if valid:
                    tracks.append({"effect": effect, "effect_index": eff_idx, "effect_name": effect_name,
                                   "name": str(key), "param": param, "keyframes": valid})
        return tracks

    def _tl_span(self):
        w = max(60, self.timeline_canvas.winfo_width())
        return w, max(1, w - self._TL_LABEL_W - self._TL_PAD)

    def _tl_x_of(self, t_ns):
        _w, span = self._tl_span()
        return self._TL_LABEL_W + span * (t_ns / max(1, self.duration_ns))

    def _tl_time_of(self, x):
        _w, span = self._tl_span()
        frac = max(0.0, min(1.0, (x - self._TL_LABEL_W) / span))
        return int(frac * self.duration_ns)

    def _kf_at_xy(self, x, y, radius=9):
        tracks = self._collect_animated_tracks()
        row = int((y - self._TL_RULER_H) // self._TL_ROW_H)
        if row < 0 or row >= len(tracks):
            return None
        track = tracks[row]
        best = None
        best_dist = radius + 1
        for kf in track["keyframes"]:
            dx = abs(self._tl_x_of(int(kf.get("time", 0))) - x)
            if dx <= radius and dx < best_dist:
                best, best_dist = kf, dx
        return (track, best) if best is not None else None

    def _draw_timeline(self, force_bg=False):
        cv = getattr(self, "timeline_canvas", None)
        if cv is None:
            return
        w = max(180, cv.winfo_width())
        tracks = self._collect_animated_tracks()
        h = self._TL_RULER_H + max(1, len(tracks)) * self._TL_ROW_H + 5
        pad = self._TL_PAD
        span = max(1, w - self._TL_LABEL_W - pad)
        dur_s = max(0.01, self.duration_ns / 1_000_000_000.0)
        bg_key = (w, h, self.duration_ns, tuple((t["effect_index"], t["name"], len(t["keyframes"])) for t in tracks))
        if force_bg or self._tl_bg_key != bg_key:
            cv.delete("all")
            self._tl_bg_key = bg_key
            cv.create_rectangle(0, 0, w, h, fill=self.c["well"], outline="", tags=("tl_bg",))
            cv.create_rectangle(0, 0, self._TL_LABEL_W, h, fill=self.c["panel_header"], outline="", tags=("tl_bg",))
            cv.create_line(self._TL_LABEL_W, 0, self._TL_LABEL_W, h, fill=self.c["border_light"], tags=("tl_bg",))
            steps = (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600)
            step = next((v for v in steps if span * v / dur_s >= 72), steps[-1])
            cv.create_line(self._TL_LABEL_W, self._TL_RULER_H, w - pad, self._TL_RULER_H, fill=self.c["border_light"], tags=("tl_bg",))
            k = 0
            while k * step <= dur_s + 1e-9:
                sec = k * step
                x = self._TL_LABEL_W + span * sec / dur_s
                cv.create_line(x, self._TL_RULER_H - 7, x, h, fill=self.c["border"], tags=("tl_bg",))
                cv.create_text(x + 3, 3, text=self._fmt_tc(sec), anchor="nw", fill=self.c["fg_faint"], font=(MONO_FONT, 7), tags=("tl_bg",))
                k += 1
            if not tracks:
                cv.create_text(self._TL_LABEL_W + 12, self._TL_RULER_H + 12, text="No animated properties", anchor="w", fill=self.c["fg_faint"], font=(UI_FONT, 8), tags=("tl_bg",))
            for idx, track in enumerate(tracks):
                y0 = self._TL_RULER_H + idx * self._TL_ROW_H
                cy = y0 + self._TL_ROW_H / 2
                if idx % 2 == 0:
                    cv.create_rectangle(1, y0, w, y0 + self._TL_ROW_H, fill="#17191f", outline="", tags=("tl_bg",))
                cv.create_line(0, y0 + self._TL_ROW_H, w, y0 + self._TL_ROW_H, fill=self.c["border"], tags=("tl_bg",))
                label = f'{track["effect_name"][:11]}  ›  {track["name"]}'
                cv.create_text(8, cy, text=label[:22], anchor="w", fill=self.c["fg_muted"], font=(UI_FONT, 8), tags=("tl_bg",))
                times = sorted(int(kf.get("time", 0)) for kf in track["keyframes"])
                if len(times) > 1:
                    cv.create_line(self._tl_x_of(times[0]), cy, self._tl_x_of(times[-1]), cy, fill="#51402c", width=2, tags=("tl_bg",))
        else:
            cv.delete("tl_fg")

        for idx, track in enumerate(tracks):
            cy = self._TL_RULER_H + idx * self._TL_ROW_H + self._TL_ROW_H / 2
            for kf in track["keyframes"]:
                x = self._tl_x_of(int(kf.get("time", 0)))
                active = abs(int(kf.get("time", 0)) - self.current_time_ns) <= self.frame_ns() / 2
                r = 6 if active else 5
                cv.create_polygon(x, cy-r, x+r, cy, x, cy+r, x-r, cy,
                                  fill=self.c["accent"] if active else self.c["cyan"],
                                  outline=self.c["fg_text"] if active else self.c["border_light"],
                                  width=1, tags=("tl_fg",))
        px = self._tl_x_of(self.current_time_ns)
        cv.create_line(px, 0, px, h, fill=self.c["accent"], width=2, tags=("tl_fg",))
        cv.create_polygon(px-5, 0, px+5, 0, px, 8, fill=self.c["accent"], outline="", tags=("tl_fg",))
        cv.configure(scrollregion=(0, 0, w, h))

    def _on_tl_press(self, event):
        self.timeline_canvas.focus_set()
        self.pause()
        self._tl_dragging = True
        canvas_y = self.timeline_canvas.canvasy(event.y)
        hit = self._kf_at_xy(event.x, canvas_y, 10)
        self._tl_drag_kf = hit
        if hit:
            self.seek(int(hit[1].get("time", 0)))
        else:
            self.seek(self._tl_time_of(event.x))

    def _on_tl_drag(self, event):
        if not self._tl_dragging:
            return
        y = self.timeline_canvas.canvasy(event.y)
        if self._tl_drag_kf:
            track, kf = self._tl_drag_kf
            new_time = self._tl_time_of(event.x)
            if not (event.state & 0x1):
                frame = max(1, self.frame_ns())
                new_time = int(round(new_time / frame) * frame)
            kf["time"] = max(0, min(self.duration_ns, new_time))
            track["param"].setdefault("keyframes", []).sort(key=lambda item: item.get("time", 0))
            self._keyframe_cache = None
            self._tl_bg_key = None
            self._notify_modified()
            self.seek(int(kf["time"]))
        else:
            self.seek(self._tl_time_of(event.x))

    def _on_tl_release(self, _event):
        self._tl_dragging = False
        self._tl_drag_kf = None

    def _on_tl_hover(self, event):
        hit = self._kf_at_xy(event.x, self.timeline_canvas.canvasy(event.y), 10)
        self.timeline_canvas.config(cursor="hand2" if hit else "sb_h_double_arrow")

    # --- Active Transform Target & Parameters ---
    def _get_active_transform_effect(self):
        if not isinstance(self.preset_data, dict):
            return None
        effects = self.preset_data.get("effects", [])
        for preferred in ("motion", "graphic_text"):
            for eff in effects:
                if eff.get("enabled", True) and eff.get("effect") == preferred:
                    return eff
        return None

    def _get_motion_transform(self, src_w, src_h):
        default_tf = {
            "has_motion": False,
            "anchor_x": src_w / 2.0,
            "anchor_y": src_h / 2.0,
            "pos_x": src_w / 2.0,
            "pos_y": src_h / 2.0,
            "sx": 1.0,
            "sy": 1.0,
            "rot_deg": 0.0,
        }
        if not isinstance(self.preset_data, dict):
            return default_tf

        t = self.current_time_ns
        for eff in self.preset_data.get("effects", []):
            if eff.get("enabled", True) and eff.get("effect") == "motion":
                params = eff.get("params", {})
                anchor = evaluate_filmcraft_param(params.get("anchor"), t) or {"x": src_w / 2.0, "y": src_h / 2.0}
                pos = evaluate_filmcraft_param(params.get("position"), t) or {"x": src_w / 2.0, "y": src_h / 2.0}
                scale_pct = float(evaluate_filmcraft_param(params.get("scale"), t) or 100.0)
                scale_w_pct = float(evaluate_filmcraft_param(params.get("scale_width"), t) or 100.0)
                uniform = bool(evaluate_filmcraft_param(params.get("uniform_scale", {"value": {"Bool": True}}), t))
                rot_deg = float(evaluate_filmcraft_param(params.get("rotation"), t) or 0.0)

                sy = scale_pct / 100.0
                sx = sy if uniform else (scale_w_pct / 100.0)
                return {
                    "has_motion": True,
                    "anchor_x": float(anchor.get("x", src_w / 2.0)),
                    "anchor_y": float(anchor.get("y", src_h / 2.0)),
                    "pos_x": float(pos.get("x", src_w / 2.0)),
                    "pos_y": float(pos.get("y", src_h / 2.0)),
                    "sx": sx,
                    "sy": sy,
                    "rot_deg": rot_deg,
                }
        return default_tf

    def _get_global_opacity(self):
        t = self.current_time_ns
        for eff in self.preset_data.get("effects", []):
            if eff.get("enabled", True) and eff.get("effect") == "opacity":
                op = evaluate_filmcraft_param(eff.get("params", {}).get("opacity"), t)
                if op is not None:
                    return float(op)
        return 100.0

    @staticmethod
    def _fmt_tc(seconds):
        mins = int(seconds // 60)
        secs = seconds % 60.0
        return f"{mins:02d}:{secs:05.2f}"

    # --- Stage Background (Cached) ---
    def _draw_stage_background(self, x0, y0, x1, y1, stage_w, stage_h, mode, guides, thirds):
        self.canvas.delete("all")
        if mode == "bg_chroma":
            self._stage_bg_hex = "#00b140"
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=self._stage_bg_hex, outline=self.c["border_light"], width=1, tags=("bg",))
        elif mode == "bg_checker":
            self._stage_bg_hex = "#1b1d22"
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=self._stage_bg_hex, outline=self.c["border_light"], width=1, tags=("bg",))
            tile = 20
            cols = int(stage_w // tile) + 1
            rows = int(stage_h // tile) + 1
            for r in range(rows):
                for c in range(cols):
                    if (r + c) % 2 == 0:
                        tx0 = x0 + c * tile
                        ty0 = y0 + r * tile
                        self.canvas.create_rectangle(
                            tx0, ty0, min(x1, tx0 + tile), min(y1, ty0 + tile), fill="#252830", outline="", tags=("bg",)
                        )
        else:
            self._stage_bg_hex = "#0a0b0d"
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=self._stage_bg_hex, outline=self.c["border_light"], width=1, tags=("bg",))

        if guides:
            cx = x0 + stage_w / 2.0
            cy = y0 + stage_h / 2.0
            self.canvas.create_line(cx, y0, cx, y1, fill="#242730", dash=(3, 4), tags=("bg",))
            self.canvas.create_line(x0, cy, x1, cy, fill="#242730", dash=(3, 4), tags=("bg",))
            # Action Safe (95%) & Title Safe (90%)
            self.canvas.create_rectangle(
                x0 + stage_w * 0.05, y0 + stage_h * 0.05, x1 - stage_w * 0.05, y1 - stage_h * 0.05,
                outline="#23262f", dash=(4, 4), tags=("bg",),
            )
            self.canvas.create_rectangle(
                x0 + stage_w * 0.10, y0 + stage_h * 0.10, x1 - stage_w * 0.10, y1 - stage_h * 0.10,
                outline="#1e2129", dash=(2, 4), tags=("bg",),
            )

        if thirds:
            for frac in (1.0 / 3.0, 2.0 / 3.0):
                tx = x0 + stage_w * frac
                ty = y0 + stage_h * frac
                self.canvas.create_line(tx, y0, tx, y1, fill="#283244", dash=(2, 3), tags=("bg",))
                self.canvas.create_line(x0, ty, x1, ty, fill="#283244", dash=(2, 3), tags=("bg",))

    # --- Main Frame Render ---
    def render_frame(self):
        if not hasattr(self, "canvas"):
            return
        cw = max(10, self.canvas.winfo_width())
        ch = max(10, self.canvas.winfo_height())

        cur_sec = self.current_time_ns / 1_000_000_000.0
        dur_sec = self.duration_ns / 1_000_000_000.0
        self.time_label_var.set(f"{self._fmt_tc(cur_sec)} / {self._fmt_tc(dur_sec)}")
        self._draw_timeline()

        if self.time_listener is not None:
            try:
                self.time_listener(self.current_time_ns)
            except tk.TclError:
                pass

        if not isinstance(self.preset_data, dict):
            self.canvas.delete("all")
            self._bg_cache_key = None
            self.canvas.create_text(
                cw / 2, ch / 2, text=self._t("viewer_empty"), fill=self.c["fg_muted"], font=(UI_FONT, 10),
            )
            return

        src_size = self.preset_data.get("source_size", [1920, 1080])
        src_w = float(src_size[0]) if isinstance(src_size, list) and len(src_size) >= 2 and src_size[0] > 0 else 1920.0
        src_h = float(src_size[1]) if isinstance(src_size, list) and len(src_size) >= 2 and src_size[1] > 0 else 1080.0

        margin = 18.0
        if self.zoom_fit:
            ratio = min(max(20.0, cw - margin * 2) / src_w, max(20.0, ch - margin * 2) / src_h)
        else:
            ratio = self.zoom_factor

        stage_w = src_w * ratio
        stage_h = src_h * ratio
        x0 = (cw - stage_w) / 2.0 + self.pan_x
        y0 = (ch - stage_h) / 2.0 + self.pan_y
        x1 = x0 + stage_w
        y1 = y0 + stage_h
        self._stage_transform = (src_w, src_h, x0, y0, ratio)

        guides = self.guides_var.get()
        thirds = self.thirds_var.get()
        bg_key = (cw, ch, round(x0, 2), round(y0, 2), round(ratio, 5), self.bg_mode_code, guides, thirds)

        if self._bg_cache_key != bg_key:
            self._draw_stage_background(x0, y0, x1, y1, stage_w, stage_h, self.bg_mode_code, guides, thirds)
            self._bg_cache_key = bg_key
        else:
            self.canvas.delete("fg")

        stage_bg = self._stage_bg_hex
        motion_tf = self._get_motion_transform(src_w, src_h)
        global_op = self._get_global_opacity()

        has_graphic_text = any(
            eff.get("enabled", True) and eff.get("effect") == "graphic_text"
            for eff in self.preset_data.get("effects", [])
        )

        shape_map = {
            "obj_rect": "rect",
            "obj_square": "square",
            "obj_circle": "circle",
            "obj_triangle": "triangle",
            "obj_diamond": "diamond",
            "obj_star": "star",
            "obj_block_text": "block_text",
        }
        if self.obj_mode_code in shape_map:
            self._render_example_shape(shape_map[self.obj_mode_code], src_w, src_h, x0, y0, ratio, motion_tf, global_op, stage_bg)

        if self.obj_mode_code in ("obj_text", "obj_block_text") or (
            self.obj_mode_code == "obj_auto" and not has_graphic_text
        ):
            if has_graphic_text:
                for eff in self.preset_data.get("effects", []):
                    if eff.get("enabled", True) and eff.get("effect") == "graphic_text":
                        self._render_graphic_text(
                            eff.get("params", {}), x0, y0, ratio, stage_bg, motion_tf, global_op,
                            override_text=self.example_text_var.get(),
                        )
            else:
                self._render_dummy_text_for_motion(src_w, src_h, x0, y0, ratio, motion_tf, global_op, stage_bg)
        elif has_graphic_text and self.obj_mode_code == "obj_auto":
            for eff in self.preset_data.get("effects", []):
                if eff.get("enabled", True) and eff.get("effect") == "graphic_text":
                    self._render_graphic_text(eff.get("params", {}), x0, y0, ratio, stage_bg, motion_tf, global_op)

        # Draw Smart Alignment Snap Guides if currently snapping
        for orientation, coord in self._snap_lines:
            if orientation == "v":
                sx_c = x0 + coord * ratio
                self.canvas.create_line(sx_c, y0, sx_c, y1, fill=self.c["cyan"], width=1, dash=(4, 2), tags=("fg",))
            else:
                sy_c = y0 + coord * ratio
                self.canvas.create_line(x0, sy_c, x1, sy_c, fill=self.c["cyan"], width=1, dash=(4, 2), tags=("fg",))

        # Draw Spatial Motion Path & Compositing Gizmos
        self._render_motion_path_overlay(x0, y0, ratio)
        self._render_transform_gizmos(src_w, src_h, x0, y0, ratio, motion_tf)
        self._update_hud_metrics(src_w, src_h, motion_tf)

    # --- Spatial Motion Path & Interactive Bounding Box Gizmos ---
    def _compute_active_layer_box(self, src_w, src_h, motion_tf):
        """Computes oriented bounding box & transform parameters for the active effect."""
        eff = self._get_active_transform_effect()
        if eff is None:
            return None

        t = self.current_time_ns
        params = eff.get("params", {})
        eff_type = eff.get("effect")

        if eff_type == "motion":
            try:
                base_w = max(40.0, float(self.shape_w_var.get()))
                base_h = max(40.0, float(self.shape_h_var.get()))
            except ValueError:
                base_w, base_h = 460.0, 240.0

            anchor = evaluate_filmcraft_param(params.get("anchor"), t) or {"x": src_w / 2.0, "y": src_h / 2.0}
            pos = evaluate_filmcraft_param(params.get("position"), t) or {"x": src_w / 2.0, "y": src_h / 2.0}
            scale_pct = float(evaluate_filmcraft_param(params.get("scale"), t) or 100.0)
            scale_w_pct = float(evaluate_filmcraft_param(params.get("scale_width"), t) or 100.0)
            uniform = bool(evaluate_filmcraft_param(params.get("uniform_scale", {"value": {"Bool": True}}), t))
            rot_deg = float(evaluate_filmcraft_param(params.get("rotation"), t) or 0.0)

            sy = scale_pct / 100.0
            sx = sy if uniform else (scale_w_pct / 100.0)
            ax, ay = float(anchor.get("x", src_w / 2.0)), float(anchor.get("y", src_h / 2.0))
            px, py = float(pos.get("x", src_w / 2.0)), float(pos.get("y", src_h / 2.0))

            cx, cy = src_w / 2.0, src_h / 2.0
            hw, hh = base_w / 2.0, base_h / 2.0
            local_corners = [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)]
            world_corners = [transform_point_2d(lx, ly, ax, ay, px, py, sx, sy, rot_deg) for lx, ly in local_corners]

            return {
                "effect": eff,
                "eff_type": "motion",
                "base_w": base_w,
                "base_h": base_h,
                "anchor": (ax, ay),
                "pos": (px, py),
                "sx": sx,
                "sy": sy,
                "uniform": uniform,
                "rot_deg": rot_deg,
                "world_corners": world_corners,
                "pivot_world": (px, py),
            }

        # graphic_text
        raw_text = str(evaluate_filmcraft_param(params.get("text"), t) or "Text")
        base_size = float(evaluate_filmcraft_param(params.get("size"), t) or 100.0)
        scale_pct = float(evaluate_filmcraft_param(params.get("scale"), t) or 100.0)
        scale_w_pct = float(evaluate_filmcraft_param(params.get("scale_width"), t) or 100.0)
        uniform = bool(evaluate_filmcraft_param(params.get("uniform_scale", {"value": {"Bool": True}}), t))
        rot_deg = float(evaluate_filmcraft_param(params.get("rotation"), t) or 0.0)
        pos = evaluate_filmcraft_param(params.get("position"), t) or {"x": src_w / 2.0, "y": src_h / 2.0}
        anchor = evaluate_filmcraft_param(params.get("anchor"), t) or {"x": 0.0, "y": 0.0}

        sy = scale_pct / 100.0
        sx = sy if uniform else (scale_w_pct / 100.0)
        px, py = float(pos.get("x", src_w / 2.0)), float(pos.get("y", src_h / 2.0))
        ax, ay = float(anchor.get("x", 0.0)), float(anchor.get("y", 0.0))

        lines = raw_text.splitlines() or ["Text"]
        max_chars = max(1, max(len(line) for line in lines))
        base_w = max(80.0, max_chars * base_size * 0.58 + 36.0)
        base_h = max(50.0, len(lines) * base_size * 1.25 + 24.0)

        hw, hh = base_w / 2.0, base_h / 2.0
        local_corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        world_corners = []
        for lx, ly in local_corners:
            wx, wy = transform_point_2d(lx, ly, ax, ay, px, py, sx, sy, rot_deg)
            if motion_tf["has_motion"]:
                wx, wy = transform_point_2d(
                    wx, wy, motion_tf["anchor_x"], motion_tf["anchor_y"],
                    motion_tf["pos_x"], motion_tf["pos_y"], motion_tf["sx"], motion_tf["sy"], motion_tf["rot_deg"],
                )
            world_corners.append((wx, wy))

        pivot_x, pivot_y = px, py
        if motion_tf["has_motion"]:
            pivot_x, pivot_y = transform_point_2d(
                px, py, motion_tf["anchor_x"], motion_tf["anchor_y"],
                motion_tf["pos_x"], motion_tf["pos_y"], motion_tf["sx"], motion_tf["sy"], motion_tf["rot_deg"],
            )

        return {
            "effect": eff,
            "eff_type": "graphic_text",
            "base_w": base_w,
            "base_h": base_h,
            "anchor": (ax, ay),
            "pos": (px, py),
            "sx": sx,
            "sy": sy,
            "uniform": uniform,
            "rot_deg": rot_deg,
            "world_corners": world_corners,
            "pivot_world": (pivot_x, pivot_y),
        }

    def _render_motion_path_overlay(self, x0, y0, ratio):
        self._gizmo_geometry["path_nodes"] = []
        if not self.path_var.get() and self._active_tool != "path":
            return

        eff = self._get_active_transform_effect()
        if eff is None:
            return
        pos_param = eff.get("params", {}).get("position")
        curve_pts, kf_nodes = sample_motion_path(pos_param, samples_per_seg=16)
        if len(curve_pts) < 2:
            return

        canvas_pts = []
        for sx, sy in curve_pts:
            canvas_pts.extend([x0 + sx * ratio, y0 + sy * ratio])

        line_color = self.c["cyan"] if self._active_tool == "path" else "#3a7ca5"
        self.canvas.create_line(canvas_pts, fill=line_color, width=2 if self._active_tool == "path" else 1, dash=(4, 3), tags=("fg",))

        tol = self.frame_ns() / 2.0
        for node in kf_nodes:
            nx = x0 + node["x"] * ratio
            ny = y0 + node["y"] * ratio
            is_cur = abs(node["time"] - self.current_time_ns) <= tol
            r = 6 if self._active_tool == "path" else 4
            self.canvas.create_polygon(
                nx, ny - r, nx + r, ny, nx, ny + r, nx - r, ny,
                fill=self.c["accent"] if is_cur else self.c["cyan"],
                outline="#ffffff",
                width=1,
                tags=("fg",),
            )
            self._gizmo_geometry["path_nodes"].append((nx, ny, node["kf"]))

    def _render_transform_gizmos(self, src_w, src_h, x0, y0, ratio, motion_tf):
        self._gizmo_geometry["box_poly"] = []
        self._gizmo_geometry["handles"] = {}
        self._gizmo_geometry["box_info"] = None

        box = self._compute_active_layer_box(src_w, src_h, motion_tf)
        if box is None:
            return
        self._gizmo_geometry["box_info"] = box

        c_corners = [(x0 + wx * ratio, y0 + wy * ratio) for wx, wy in box["world_corners"]]
        self._gizmo_geometry["box_poly"] = c_corners

        flat_poly = [coord for pt in c_corners for coord in pt]
        box_outline = self.c["accent"] if self._active_tool == "transform" else "#5c6475"
        self.canvas.create_polygon(flat_poly, fill="", outline=box_outline, width=1, dash=() if self._active_tool == "transform" else (3, 3), tags=("fg",))

        # Anchor / Pivot Crosshair
        piv_x = x0 + box["pivot_world"][0] * ratio
        piv_y = y0 + box["pivot_world"][1] * ratio
        if self.anchor_var.get() or self._active_tool == "anchor":
            r_a = 7 if self._active_tool == "anchor" else 5
            col_a = self.c["cyan"] if self._active_tool == "anchor" else self.c["accent"]
            self.canvas.create_oval(piv_x - r_a, piv_y - r_a, piv_x + r_a, piv_y + r_a, outline=col_a, width=2, tags=("fg",))
            self.canvas.create_line(piv_x - (r_a + 4), piv_y, piv_x + (r_a + 4), piv_y, fill=col_a, width=1, tags=("fg",))
            self.canvas.create_line(piv_x, piv_y - (r_a + 4), piv_x, piv_y + (r_a + 4), fill=col_a, width=1, tags=("fg",))
            self._gizmo_geometry["handles"]["anchor"] = (piv_x, piv_y)

        if self._active_tool != "transform":
            return

        # 4 Corner Scale Handles
        for idx, (cx, cy) in enumerate(c_corners):
            self.canvas.create_rectangle(cx - 4, cy - 4, cx + 4, cy + 4, fill="#ffffff", outline=self.c["accent"], width=2, tags=("fg",))
            self._gizmo_geometry["handles"][f"corner_{idx}"] = (cx, cy)

        # 4 Edge Midpoint Non-Uniform Scale Handles (top, right, bottom, left)
        edge_names = ["edge_top", "edge_right", "edge_bottom", "edge_left"]
        top_mid = (0.0, 0.0)
        for i in range(4):
            p1 = c_corners[i]
            p2 = c_corners[(i + 1) % 4]
            mx, my = (p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0
            if i == 0:
                top_mid = (mx, my)
            self.canvas.create_oval(mx - 4, my - 4, mx + 4, my + 4, fill=self.c["accent"], outline="#ffffff", width=1, tags=("fg",))
            self._gizmo_geometry["handles"][edge_names[i]] = (mx, my)

        # Rotation Handle extending 26px outward from top edge normal
        rad = math.radians(box["rot_deg"])
        nx_up = math.sin(rad)
        ny_up = -math.cos(rad)
        rot_x = top_mid[0] + nx_up * 26.0
        rot_y = top_mid[1] + ny_up * 26.0
        self.canvas.create_line(top_mid[0], top_mid[1], rot_x, rot_y, fill=self.c["accent"], width=2, tags=("fg",))
        self.canvas.create_oval(rot_x - 6, rot_y - 6, rot_x + 6, rot_y + 6, fill=self.c["cyan"], outline="#ffffff", width=2, tags=("fg",))
        self._gizmo_geometry["handles"]["rotate"] = (rot_x, rot_y)

    def _update_hud_metrics(self, src_w, src_h, motion_tf):
        box = self._gizmo_geometry.get("box_info")
        if not box:
            self.hud_metrics_var.set(f"Canvas: {int(src_w)}×{int(src_h)}")
            return
        px, py = box["pos"]
        ax, ay = box["anchor"]
        sx_pct = box["sx"] * 100.0
        sy_pct = box["sy"] * 100.0
        rot = box["rot_deg"]
        self.hud_metrics_var.set(
            f"Pos: {px:.1f}, {py:.1f}  |  Scale: {sx_pct:.1f}% × {sy_pct:.1f}%  |  Rot: {rot:.1f}°  |  Anchor: {ax:.1f}, {ay:.1f}"
        )

    # --- Writing Transform Changes (Auto-Key aware) ---
    def _write_param_value(self, eff, key, type_tag, new_val, force_keyframe=False):
        param = eff.get("params", {}).get(key)
        if not isinstance(param, dict) or "value" not in param:
            return

        kfs = param.get("keyframes")
        has_kfs = isinstance(kfs, list) and len(kfs) > 0
        should_kf = force_keyframe or has_kfs or self.auto_key_var.get()

        if should_kf:
            if not isinstance(kfs, list):
                kfs = []
                param["keyframes"] = kfs
            t = int(self.current_time_ns)
            tol = self.frame_ns() / 2.0
            match = next((kf for kf in kfs if abs(int(kf.get("time", -1)) - t) <= tol), None)
            if match is None:
                kfs.append({
                    "time": t,
                    "value": {type_tag: copy.deepcopy(new_val)},
                    "interp": "AutoBezier",
                    "out_influence": 1.0 / 3.0,
                    "in_influence": 1.0 / 3.0,
                })
                kfs.sort(key=lambda item: item.get("time", 0))
            else:
                match.setdefault("value", {})[type_tag] = copy.deepcopy(new_val)
            param["value"][type_tag] = copy.deepcopy(new_val)
        else:
            param["value"][type_tag] = copy.deepcopy(new_val)

        self._keyframe_cache = None
        self._notify_modified()

    def _stamp_all_transform_keyframes(self):
        box = self._gizmo_geometry.get("box_info")
        if not box:
            return
        self.pause()
        eff = box["effect"]
        px, py = box["pos"]
        ax, ay = box["anchor"]
        self._write_param_value(eff, "position", "Vec2", {"x": round(px, 3), "y": round(py, 3)}, force_keyframe=True)
        self._write_param_value(eff, "scale", "Float", round(box["sy"] * 100.0, 3), force_keyframe=True)
        self._write_param_value(eff, "rotation", "Float", round(box["rot_deg"], 3), force_keyframe=True)
        self._write_param_value(eff, "anchor", "Vec2", {"x": round(ax, 3), "y": round(ay, 3)}, force_keyframe=True)
        self.render_frame()

    def _reset_active_transform(self):
        if not self._stage_transform:
            return
        src_w, src_h, _x0, _y0, _ratio = self._stage_transform
        box = self._gizmo_geometry.get("box_info")
        if not box:
            return
        self.pause()
        eff = box["effect"]
        is_motion = box["eff_type"] == "motion"
        def_pos = {"x": src_w / 2.0, "y": src_h / 2.0}
        def_anchor = {"x": src_w / 2.0, "y": src_h / 2.0} if is_motion else {"x": 0.0, "y": 0.0}

        self._write_param_value(eff, "position", "Vec2", def_pos)
        self._write_param_value(eff, "anchor", "Vec2", def_anchor)
        self._write_param_value(eff, "scale", "Float", 100.0)
        self._write_param_value(eff, "scale_width", "Float", 100.0)
        if "uniform_scale" in eff.get("params", {}):
            eff["params"]["uniform_scale"]["value"]["Bool"] = True
        self._write_param_value(eff, "rotation", "Float", 0.0)
        self.render_frame()

    # --- Mouse Hit-Testing & Direct Manipulation ---
    def _hit_test_gizmo(self, x, y):
        # 1. Check Motion Path Keyframe Nodes first if visible
        for nx, ny, kf_ref in self._gizmo_geometry.get("path_nodes", []):
            if math.hypot(x - nx, y - ny) <= 9.0:
                return "path_kf", kf_ref

        handles = self._gizmo_geometry.get("handles", {})
        if self._active_tool == "anchor" and "anchor" in handles:
            ax, ay = handles["anchor"]
            if math.hypot(x - ax, y - ay) <= 14.0:
                return "anchor", None

        if self._active_tool == "transform":
            if "rotate" in handles and math.hypot(x - handles["rotate"][0], y - handles["rotate"][1]) <= 11.0:
                return "rotate", None
            for idx in range(4):
                pt = handles.get(f"corner_{idx}")
                if pt and math.hypot(x - pt[0], y - pt[1]) <= 10.0:
                    return "scale_corner", None
            for edge in ("edge_left", "edge_right"):
                pt = handles.get(edge)
                if pt and math.hypot(x - pt[0], y - pt[1]) <= 10.0:
                    return "scale_x", None
            for edge in ("edge_top", "edge_bottom"):
                pt = handles.get(edge)
                if pt and math.hypot(x - pt[0], y - pt[1]) <= 10.0:
                    return "scale_y", None
            if "anchor" in handles and math.hypot(x - handles["anchor"][0], y - handles["anchor"][1]) <= 8.0:
                return "anchor", None

        poly = self._gizmo_geometry.get("box_poly", [])
        if poly and point_in_polygon(x, y, poly):
            return "anchor" if self._active_tool == "anchor" else "move", None

        return None, None

    def _on_viewer_press(self, event):
        self.canvas.focus_set()
        if not self._stage_transform:
            return
        mode, extra = self._hit_test_gizmo(event.x, event.y)
        box = self._gizmo_geometry.get("box_info")
        if mode and box:
            self.pause()
            self._drag_mode = mode
            self._drag_kf_ref = extra
            self._drag_start_canvas = (event.x, event.y)
            self._drag_start_pos = box["pos"]
            self._drag_start_anchor = box["anchor"]
            if mode == "path_kf" and isinstance(extra, dict):
                self.seek(int(extra.get("time", self.current_time_ns)))

    def _apply_snap(self, px, py, src_w, src_h, disable_snap=False):
        self._snap_lines = []
        if disable_snap or not self.snap_var.get():
            return px, py

        thresh = 10.0
        snap_x_targets = [src_w * 0.5]
        snap_y_targets = [src_h * 0.5]
        if self.thirds_var.get():
            snap_x_targets.extend([src_w / 3.0, src_w * 2.0 / 3.0])
            snap_y_targets.extend([src_h / 3.0, src_h * 2.0 / 3.0])

        for tx in snap_x_targets:
            if abs(px - tx) <= thresh:
                px = tx
                self._snap_lines.append(("v", tx))
                break
        for ty in snap_y_targets:
            if abs(py - ty) <= thresh:
                py = ty
                self._snap_lines.append(("h", ty))
                break
        return px, py

    def _on_viewer_drag(self, event):
        if not self._drag_mode or not self._stage_transform:
            return
        src_w, src_h, x0, y0, ratio = self._stage_transform
        box = self._gizmo_geometry.get("box_info")
        if not box:
            return

        eff = box["effect"]
        shift = bool(event.state & 0x1)
        ctrl = bool(event.state & 0x4)

        if self._drag_mode == "path_kf" and isinstance(self._drag_kf_ref, dict):
            sx = (event.x - x0) / ratio
            sy = (event.y - y0) / ratio
            sx, sy = self._apply_snap(sx, sy, src_w, src_h, disable_snap=ctrl)
            self._drag_kf_ref.setdefault("value", {})["Vec2"] = {"x": round(sx, 3), "y": round(sy, 3)}
            pos_param = eff.get("params", {}).get("position")
            if isinstance(pos_param, dict):
                pos_param["value"]["Vec2"] = {"x": round(sx, 3), "y": round(sy, 3)}
            self._keyframe_cache = None
            self._notify_modified()
            self.render_frame()
            return

        if self._drag_mode == "move":
            dx_src = (event.x - self._drag_start_canvas[0]) / ratio
            dy_src = (event.y - self._drag_start_canvas[1]) / ratio
            nx = self._drag_start_pos[0] + dx_src
            ny = self._drag_start_pos[1] + dy_src
            nx, ny = self._apply_snap(nx, ny, src_w, src_h, disable_snap=ctrl)
            self._write_param_value(eff, "position", "Vec2", {"x": round(nx, 3), "y": round(ny, 3)})

        elif self._drag_mode == "anchor":
            dx_src = (event.x - self._drag_start_canvas[0]) / ratio
            dy_src = (event.y - self._drag_start_canvas[1]) / ratio
            nax = self._drag_start_anchor[0] + dx_src
            nay = self._drag_start_anchor[1] + dy_src
            self._write_param_value(eff, "anchor", "Vec2", {"x": round(nax, 3), "y": round(nay, 3)})

        elif self._drag_mode == "rotate":
            piv_x = x0 + box["pivot_world"][0] * ratio
            piv_y = y0 + box["pivot_world"][1] * ratio
            ang = math.degrees(math.atan2(event.y - piv_y, event.x - piv_x)) + 90.0
            ang = ((ang + 180.0) % 360.0) - 180.0
            if shift:
                ang = round(ang / 15.0) * 15.0
            self._write_param_value(eff, "rotation", "Float", round(ang, 2))

        elif self._drag_mode in ("scale_corner", "scale_x", "scale_y"):
            wx = (event.x - x0) / ratio
            wy = (event.y - y0) / ratio
            px, py = box["pos"]
            ux, uy = inverse_rotate_offset(wx, wy, px, py, box["rot_deg"])
            hw = max(10.0, box["base_w"] / 2.0)
            hh = max(10.0, box["base_h"] / 2.0)

            new_sx = max(0.05, min(12.0, abs(ux) / hw))
            new_sy = max(0.05, min(12.0, abs(uy) / hh))

            if self._drag_mode == "scale_corner":
                if shift:
                    if "uniform_scale" in eff.get("params", {}):
                        eff["params"]["uniform_scale"]["value"]["Bool"] = False
                    self._write_param_value(eff, "scale_width", "Float", round(new_sx * 100.0, 2))
                    self._write_param_value(eff, "scale", "Float", round(new_sy * 100.0, 2))
                else:
                    uni = max(new_sx, new_sy)
                    self._write_param_value(eff, "scale", "Float", round(uni * 100.0, 2))
                    if eff.get("params", {}).get("uniform_scale", {}).get("value", {}).get("Bool", True):
                        self._write_param_value(eff, "scale_width", "Float", round(uni * 100.0, 2))
            elif self._drag_mode == "scale_x":
                if "uniform_scale" in eff.get("params", {}):
                    eff["params"]["uniform_scale"]["value"]["Bool"] = False
                self._write_param_value(eff, "scale_width", "Float", round(new_sx * 100.0, 2))
            elif self._drag_mode == "scale_y":
                self._write_param_value(eff, "scale", "Float", round(new_sy * 100.0, 2))

        self.render_frame()

    def _on_viewer_release(self, _event):
        if self._drag_mode:
            self._drag_mode = None
            self._drag_kf_ref = None
            self._snap_lines = []
            self.canvas.configure(cursor="arrow")
            self.render_frame()

    def _on_viewer_hover(self, event):
        if self._stage_transform:
            _sw, _sh, x0, y0, ratio = self._stage_transform
            cx = (event.x - x0) / ratio
            cy = (event.y - y0) / ratio
            self.cursor_coords_var.set(f"XY: {cx:.0f}, {cy:.0f}")

        if self._drag_mode:
            return
        mode, _extra = self._hit_test_gizmo(event.x, event.y)
        cursor_map = {
            "move": "fleur",
            "anchor": "crosshair",
            "path_kf": "hand2",
            "rotate": "exchange",
            "scale_corner": "sizing",
            "scale_x": "sb_h_double_arrow",
            "scale_y": "sb_v_double_arrow",
        }
        self.canvas.configure(cursor=cursor_map.get(mode, "arrow"))

    # --- Render Dummy Shapes & Graphic Text ---
    def _render_example_shape(self, shape_kind, src_w, src_h, x0, y0, ratio, motion_tf, global_op, stage_bg):
        try:
            sw = max(10.0, float(self.shape_w_var.get()))
        except ValueError:
            sw = 460.0
        try:
            sh = max(10.0, float(self.shape_h_var.get()))
        except ValueError:
            sh = 240.0

        verts = build_shape_vertices(shape_kind, src_w / 2.0, src_h / 2.0, sw, sh)
        poly_coords = []
        for vx, vy in verts:
            if motion_tf["has_motion"]:
                tx, ty = transform_point_2d(
                    vx, vy, motion_tf["anchor_x"], motion_tf["anchor_y"],
                    motion_tf["pos_x"], motion_tf["pos_y"], motion_tf["sx"], motion_tf["sy"], motion_tf["rot_deg"],
                )
            else:
                tx, ty = vx, vy
            poly_coords.extend([x0 + tx * ratio, y0 + ty * ratio])

        fill_hex = blend_rgba_on_bg(hex_to_rgba_float(self.example_color_hex, 0.85), global_op, stage_bg)
        self.canvas.create_polygon(poly_coords, fill=fill_hex, outline="#e4e6eb", width=2, tags=("fg",))

        if shape_kind in ("rect", "square", "block_text") and len(poly_coords) >= 8:
            self.canvas.create_line(poly_coords[0], poly_coords[1], poly_coords[4], poly_coords[5], fill="#16181d", dash=(3, 3), tags=("fg",))
            self.canvas.create_line(poly_coords[2], poly_coords[3], poly_coords[6], poly_coords[7], fill="#16181d", dash=(3, 3), tags=("fg",))

    def _render_dummy_text_for_motion(self, src_w, src_h, x0, y0, ratio, motion_tf, global_op, stage_bg):
        txt = self.example_text_var.get().strip() or self._t("default_sample_text")
        cx, cy = src_w / 2.0, src_h / 2.0
        if motion_tf["has_motion"]:
            tx, ty = transform_point_2d(
                cx, cy, motion_tf["anchor_x"], motion_tf["anchor_y"],
                motion_tf["pos_x"], motion_tf["pos_y"], motion_tf["sx"], motion_tf["sy"], motion_tf["rot_deg"],
            )
            avg_scale = (motion_tf["sx"] + motion_tf["sy"]) / 2.0
            rot_deg = motion_tf["rot_deg"]
        else:
            tx, ty, avg_scale, rot_deg = cx, cy, 1.0, 0.0

        px = x0 + tx * ratio
        py = y0 + ty * ratio
        font_pt = max(1, int(round(78.0 * avg_scale * ratio * 0.75)))
        tk_font = (UI_FONT, font_pt, "bold")

        for i in range(8):
            ang = (2.0 * math.pi * i) / 8.0
            self.canvas.create_text(
                px + math.cos(ang) * 2.0, py + math.sin(ang) * 2.0,
                text=txt, font=tk_font, fill="#0a0b0d", angle=-rot_deg, tags=("fg",),
            )

        txt_rgba = hex_to_rgba_float("#ffffff" if self.obj_mode_code == "obj_block_text" else self.example_color_hex, 1.0)
        self.canvas.create_text(px, py, text=txt, font=tk_font, fill=blend_rgba_on_bg(txt_rgba, global_op, stage_bg), angle=-rot_deg, tags=("fg",))

    def _render_graphic_text(self, params, x0, y0, ratio, stage_bg, motion_tf, global_op, override_text=None):
        t = self.current_time_ns
        raw_text = override_text if override_text is not None else str(evaluate_filmcraft_param(params.get("text"), t) or "")
        if not raw_text:
            return

        caps_choice = evaluate_filmcraft_param(params.get("caps"), t)
        if caps_choice == 1:
            raw_text = raw_text.upper()
        elif caps_choice == 2:
            raw_text = raw_text.title()

        font_family = str(evaluate_filmcraft_param(params.get("font"), t) or UI_FONT)
        font_style_str = str(evaluate_filmcraft_param(params.get("font_style"), t) or "Regular").lower()
        weight = "bold" if ("bold" in font_style_str or bool(evaluate_filmcraft_param(params.get("faux_bold"), t))) else "normal"
        slant = "italic" if ("italic" in font_style_str or bool(evaluate_filmcraft_param(params.get("faux_italic"), t))) else "roman"

        base_size = float(evaluate_filmcraft_param(params.get("size"), t) or 100.0)
        scale_pct = float(evaluate_filmcraft_param(params.get("scale"), t) or 100.0)
        opacity_pct = float(evaluate_filmcraft_param(params.get("opacity"), t) or 100.0) * (global_op / 100.0)
        rotation_deg = float(evaluate_filmcraft_param(params.get("rotation"), t) or 0.0)

        pos = evaluate_filmcraft_param(params.get("position"), t) or {"x": 960.0, "y": 540.0}
        src_px = float(pos.get("x", 960.0))
        src_py = float(pos.get("y", 540.0))

        if motion_tf["has_motion"]:
            src_px, src_py = transform_point_2d(
                src_px, src_py, motion_tf["anchor_x"], motion_tf["anchor_y"],
                motion_tf["pos_x"], motion_tf["pos_y"], motion_tf["sx"], motion_tf["sy"], motion_tf["rot_deg"],
            )
            scale_pct *= (motion_tf["sx"] + motion_tf["sy"]) / 2.0
            rotation_deg += motion_tf["rot_deg"]

        px = x0 + src_px * ratio
        py = y0 + src_py * ratio
        font_pt = max(1, int(round(base_size * (scale_pct / 100.0) * ratio * 0.75)))

        font_spec = [font_family, font_pt, weight, slant]
        if bool(evaluate_filmcraft_param(params.get("underline"), t)):
            font_spec.append("underline")
        if bool(evaluate_filmcraft_param(params.get("strikethrough"), t)):
            font_spec.append("overstrike")
        tk_font = tuple(font_spec)

        align_choice = evaluate_filmcraft_param(params.get("align"), t)
        justify = "left" if align_choice == 0 else ("right" if align_choice == 2 else "center")

        if bool(evaluate_filmcraft_param(params.get("background"), t)):
            temp_id = self.canvas.create_text(px, py, text=raw_text, font=tk_font, justify=justify)
            bbox = self.canvas.bbox(temp_id)
            self.canvas.delete(temp_id)
            if bbox:
                bg_pad = float(evaluate_filmcraft_param(params.get("background_size"), t) or 12.0) * ratio * (scale_pct / 100.0)
                bg_rgba = evaluate_filmcraft_param(params.get("background_color"), t) or [0.0, 0.0, 0.0, 1.0]
                bg_op = float(evaluate_filmcraft_param(params.get("background_opacity"), t) or 75.0)
                bg_hex = blend_rgba_on_bg(bg_rgba, bg_op * (opacity_pct / 100.0), stage_bg)
                self.canvas.create_rectangle(
                    bbox[0] - bg_pad, bbox[1] - bg_pad * 0.6, bbox[2] + bg_pad, bbox[3] + bg_pad * 0.6,
                    fill=bg_hex, outline="", tags=("fg",),
                )

        if bool(evaluate_filmcraft_param(params.get("shadow"), t)):
            sh_angle = math.radians(float(evaluate_filmcraft_param(params.get("shadow_angle"), t) or 135.0))
            sh_dist = float(evaluate_filmcraft_param(params.get("shadow_distance"), t) or 10.0) * ratio * (scale_pct / 100.0)
            sh_rgba = evaluate_filmcraft_param(params.get("shadow_color"), t) or [0.0, 0.0, 0.0, 1.0]
            sh_op = float(evaluate_filmcraft_param(params.get("shadow_opacity"), t) or 75.0)
            sh_hex = blend_rgba_on_bg(sh_rgba, sh_op * (opacity_pct / 100.0), stage_bg)
            self.canvas.create_text(
                px + math.cos(sh_angle) * sh_dist, py + math.sin(sh_angle) * sh_dist,
                text=raw_text, font=tk_font, fill=sh_hex, justify=justify, angle=-rotation_deg, tags=("fg",),
            )

        if bool(evaluate_filmcraft_param(params.get("stroke"), t)):
            st_width = float(evaluate_filmcraft_param(params.get("stroke_width"), t) or 7.0) * ratio * (scale_pct / 100.0)
            st_rgba = evaluate_filmcraft_param(params.get("stroke_color"), t) or [0.0, 0.0, 0.0, 1.0]
            st_hex = blend_rgba_on_bg(st_rgba, opacity_pct, stage_bg)
            r_px = max(1.0, st_width)
            steps = 12 if r_px >= 2.5 else 8
            for i in range(steps):
                ang = (2.0 * math.pi * i) / steps
                self.canvas.create_text(
                    px + math.cos(ang) * r_px, py + math.sin(ang) * r_px,
                    text=raw_text, font=tk_font, fill=st_hex, justify=justify, angle=-rotation_deg, tags=("fg",),
                )

        if bool(evaluate_filmcraft_param(params.get("fill", {"value": {"Bool": True}}), t)):
            fill_rgba = evaluate_filmcraft_param(params.get("fill_color"), t) or [1.0, 1.0, 1.0, 1.0]
            fill_hex = blend_rgba_on_bg(fill_rgba, opacity_pct, stage_bg)
            self.canvas.create_text(px, py, text=raw_text, font=tk_font, fill=fill_hex, justify=justify, angle=-rotation_deg, tags=("fg",))