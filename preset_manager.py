#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preset Studio — Gerenciador Universal de Presets JSON
- Interface inspirada no DaVinci Resolve Studio & macOS Dark Mode
- Suporte nativo ao Filmcraft (graphic_text e motion)
- Pré-visualização em tempo real com Texto de Exemplo, Blocos e Formas Geométricas
- Compatível com qualquer aplicativo que utilize arquivos .json para presets
"""

import copy
import json
import math
import shutil
import time
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk


CONFIG_DIR = Path.home() / ".config" / "universal-preset-manager"
PROFILES_FILE = CONFIG_DIR / "profiles.json"

UI_FONT = "Sans"
MONO_FONT = "Monospace"

FILMCRAFT_TEXT_TEMPLATE = {
    "format": "filmcraft.effect-presets",
    "version": 1,
    "presets": [
        {
            "name": "Legenda Rápida - Micro Pop",
            "keyframes": "Scale",
            "source_duration": 46569600000,
            "source_size": [1920, 1080],
            "effects": [
                {
                    "effect": "graphic_text",
                    "enabled": True,
                    "params": {
                        "align": {"value": {"Choice": 1}},
                        "anchor": {"value": {"Vec2": {"x": 0.0, "y": 0.0}}},
                        "background": {"value": {"Bool": False}},
                        "background_color": {"value": {"Color": [0.0, 0.0, 0.0, 1.0]}},
                        "background_opacity": {"value": {"Float": 75.0}},
                        "background_radius": {"value": {"Float": 0.0}},
                        "background_size": {"value": {"Float": 12.0}},
                        "baseline_shift": {"value": {"Float": 0.0}},
                        "box_height": {"value": {"Float": 0.0}},
                        "box_width": {"value": {"Float": 0.0}},
                        "caps": {"value": {"Choice": 1}},
                        "faux_bold": {"value": {"Bool": False}},
                        "faux_italic": {"value": {"Bool": False}},
                        "fill": {"value": {"Bool": True}},
                        "fill_color": {"value": {"Color": [1.0, 0.9647059, 0.41568628, 1.0]}},
                        "fill_kind": {"value": {"Choice": 0}},
                        "font": {"value": {"Text": "Inter"}},
                        "font_style": {"value": {"Text": "Regular"}},
                        "gradient_angle": {"value": {"Float": 0.0}},
                        "gradient_end": {"value": {"Color": [0.15, 0.15, 0.15, 1.0]}},
                        "gradient_start": {"value": {"Color": [1.0, 1.0, 1.0, 1.0]}},
                        "kerning": {"value": {"Bool": True}},
                        "leading": {"value": {"Float": 0.0}},
                        "ligatures": {"value": {"Bool": True}},
                        "name": {"value": {"Text": ""}},
                        "opacity": {"value": {"Float": 100.0}},
                        "position": {
                            "value": {"Vec2": {"x": 960.0, "y": 576.376953125}},
                            "keyframes": [
                                {
                                    "time": 0,
                                    "value": {"Vec2": {"x": 960.0, "y": 596.0}},
                                    "interp": "AutoBezier",
                                    "out_influence": 0.3333333333333333,
                                    "in_influence": 0.3333333333333333,
                                },
                                {
                                    "time": 1500000000,
                                    "value": {"Vec2": {"x": 960.0, "y": 566.0}},
                                    "interp": "AutoBezier",
                                    "out_influence": 0.3333333333333333,
                                    "in_influence": 0.3333333333333333,
                                },
                                {
                                    "time": 3000000000,
                                    "value": {"Vec2": {"x": 960.0, "y": 576.376953125}},
                                    "interp": "ContinuousBezier",
                                    "out_influence": 0.3333333333333333,
                                    "in_influence": 0.3333333333333333,
                                },
                            ],
                        },
                        "rotation": {
                            "value": {"Float": 0.0},
                            "keyframes": [
                                {
                                    "time": 0,
                                    "value": {"Float": 0.0},
                                    "interp": "AutoBezier",
                                    "out_influence": 0.3333333333333333,
                                    "in_influence": 0.3333333333333333,
                                },
                                {
                                    "time": 1500000000,
                                    "value": {"Float": 0.0},
                                    "interp": "AutoBezier",
                                    "out_influence": 0.3333333333333333,
                                    "in_influence": 0.3333333333333333,
                                },
                                {
                                    "time": 3000000000,
                                    "value": {"Float": 0.0},
                                    "interp": "ContinuousBezier",
                                    "out_influence": 0.3333333333333333,
                                    "in_influence": 0.3333333333333333,
                                },
                            ],
                        },
                        "scale": {
                            "value": {"Float": 100.0},
                            "keyframes": [
                                {
                                    "time": 0,
                                    "value": {"Float": 82.0},
                                    "interp": "AutoBezier",
                                    "out_influence": 0.3333333333333333,
                                    "in_influence": 0.3333333333333333,
                                },
                                {
                                    "time": 1500000000,
                                    "value": {"Float": 112.0},
                                    "interp": "AutoBezier",
                                    "out_influence": 0.3333333333333333,
                                    "in_influence": 0.3333333333333333,
                                },
                                {
                                    "time": 3000000000,
                                    "value": {"Float": 100.0},
                                    "interp": "ContinuousBezier",
                                    "out_influence": 0.3333333333333333,
                                    "in_influence": 0.3333333333333333,
                                },
                            ],
                        },
                        "scale_width": {"value": {"Float": 100.0}},
                        "shadow": {"value": {"Bool": False}},
                        "shadow_angle": {"value": {"Float": 135.0}},
                        "shadow_blur": {"value": {"Float": 40.0}},
                        "shadow_color": {"value": {"Color": [0.0, 0.0, 0.0, 1.0]}},
                        "shadow_distance": {"value": {"Float": 10.0}},
                        "shadow_opacity": {"value": {"Float": 75.0}},
                        "shadow_size": {"value": {"Float": 0.0}},
                        "size": {"value": {"Float": 100.0}},
                        "strikethrough": {"value": {"Bool": False}},
                        "stroke": {"value": {"Bool": True}},
                        "stroke2": {"value": {"Bool": False}},
                        "stroke2_color": {"value": {"Color": [1.0, 0.85, 0.2, 1.0]}},
                        "stroke2_type": {"value": {"Choice": 0}},
                        "stroke2_width": {"value": {"Float": 10.0}},
                        "stroke_color": {"value": {"Color": [0.0, 0.0, 0.0, 1.0]}},
                        "stroke_type": {"value": {"Choice": 0}},
                        "stroke_width": {"value": {"Float": 7.0}},
                        "text": {"value": {"Text": "oi"}},
                        "tracking": {"value": {"Float": 0.0}},
                        "underline": {"value": {"Bool": False}},
                        "uniform_scale": {"value": {"Bool": True}},
                        "vertical": {"value": {"Bool": False}},
                    },
                    "layer": {"uid": 1},
                }
            ],
        }
    ],
}

FILMCRAFT_MOTION_TEMPLATE = {
    "format": "filmcraft.effect-presets",
    "version": 1,
    "presets": [
        {
            "name": "Motion Zoom Suave",
            "keyframes": "Scale",
            "source_duration": 3000000000,
            "source_size": [1920, 1080],
            "effects": [
                {
                    "effect": "motion",
                    "enabled": True,
                    "params": {
                        "anchor": {"value": {"Vec2": {"x": 960.0, "y": 540.0}}},
                        "anti_flicker": {"value": {"Float": 0.0}},
                        "position": {"value": {"Vec2": {"x": 960.0, "y": 540.0}}},
                        "rotation": {"value": {"Float": 0.0}},
                        "scale": {
                            "value": {"Float": 100.0},
                            "keyframes": [
                                {
                                    "time": 0,
                                    "value": {"Float": 100.0},
                                    "interp": "AutoBezier",
                                    "out_influence": 0.3333333333333333,
                                    "in_influence": 0.3333333333333333,
                                },
                                {
                                    "time": 3000000000,
                                    "value": {"Float": 135.0},
                                    "interp": "AutoBezier",
                                    "out_influence": 0.3333333333333333,
                                    "in_influence": 0.3333333333333333,
                                },
                            ],
                        },
                        "scale_width": {"value": {"Float": 100.0}},
                        "uniform_scale": {"value": {"Bool": True}},
                    },
                }
            ],
        }
    ],
}

GENERIC_DEFAULT_TEMPLATE = {
    "name": "Novo Preset",
    "version": 1,
    "enabled": True,
    "parameters": {
        "intensity": 1.0,
        "mode": "standard",
        "label": "Exemplo",
    },
}


# ----------------------------------------------------------------------
# Utilitários de Cor, Geometria e Interpolação de Keyframes
# ----------------------------------------------------------------------
def rgba_float_to_hex(rgba):
    if not isinstance(rgba, list) or len(rgba) < 3:
        return "#ffffff"
    r = max(0, min(255, int(round(float(rgba[0]) * 255))))
    g = max(0, min(255, int(round(float(rgba[1]) * 255))))
    b = max(0, min(255, int(round(float(rgba[2]) * 255))))
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgba_float(hex_color, alpha=1.0):
    hex_color = hex_color.lstrip("#")
    r = round(int(hex_color[0:2], 16) / 255.0, 6)
    g = round(int(hex_color[2:4], 16) / 255.0, 6)
    b = round(int(hex_color[4:6], 16) / 255.0, 6)
    return [r, g, b, float(alpha)]


def blend_rgba_on_bg(rgba, opacity_pct=100.0, bg_hex="#0d0e11"):
    if not isinstance(rgba, list) or len(rgba) < 3:
        rgba = [1.0, 1.0, 1.0, 1.0]
    a_col = float(rgba[3]) if len(rgba) >= 4 else 1.0
    alpha = max(0.0, min(1.0, a_col * (float(opacity_pct) / 100.0)))

    bg = bg_hex.lstrip("#")
    bg_r = int(bg[0:2], 16)
    bg_g = int(bg[2:4], 16)
    bg_b = int(bg[4:6], 16)

    fg_r = float(rgba[0]) * 255.0
    fg_g = float(rgba[1]) * 255.0
    fg_b = float(rgba[2]) * 255.0

    out_r = max(0, min(255, int(round(fg_r * alpha + bg_r * (1.0 - alpha)))))
    out_g = max(0, min(255, int(round(fg_g * alpha + bg_g * (1.0 - alpha)))))
    out_b = max(0, min(255, int(round(fg_b * alpha + bg_b * (1.0 - alpha)))))
    return f"#{out_r:02x}{out_g:02x}{out_b:02x}"


def cubic_bezier_ease(u, out_influence=0.33333333, in_influence=0.33333333):
    if u <= 0.0:
        return 0.0
    if u >= 1.0:
        return 1.0

    x1 = max(0.0, min(1.0, float(out_influence)))
    x2 = max(0.0, min(1.0, 1.0 - float(in_influence)))

    s = u
    for _ in range(6):
        inv = 1.0 - s
        x_s = 3.0 * inv * inv * s * x1 + 3.0 * inv * s * s * x2 + s * s * s
        dx_s = (
            3.0 * inv * inv * x1
            + 6.0 * inv * s * (x2 - x1)
            + 3.0 * s * s * (1.0 - x2)
        )
        if abs(dx_s) < 1e-6:
            break
        s = max(0.0, min(1.0, s - (x_s - u) / dx_s))

    inv = 1.0 - s
    return 3.0 * inv * s * s + s * s * s


def evaluate_filmcraft_param(param_obj, time_ns):
    if not isinstance(param_obj, dict) or "value" not in param_obj:
        return None
    val_wrapper = param_obj["value"]
    if not isinstance(val_wrapper, dict) or not val_wrapper:
        return None

    type_tag = next(iter(val_wrapper.keys()))
    base_val = val_wrapper[type_tag]

    keyframes = param_obj.get("keyframes")
    if not isinstance(keyframes, list) or len(keyframes) == 0:
        return base_val

    kfs = sorted(keyframes, key=lambda k: k.get("time", 0))
    if time_ns <= kfs[0].get("time", 0):
        return kfs[0].get("value", {}).get(type_tag, base_val)
    if time_ns >= kfs[-1].get("time", 0):
        return kfs[-1].get("value", {}).get(type_tag, base_val)

    for i in range(len(kfs) - 1):
        kf0 = kfs[i]
        kf1 = kfs[i + 1]
        t0 = kf0.get("time", 0)
        t1 = kf1.get("time", 0)
        if t0 <= time_ns <= t1:
            if t1 == t0:
                return kf1.get("value", {}).get(type_tag, base_val)

            u = (time_ns - t0) / float(t1 - t0)
            interp = kf0.get("interp", "Linear")
            if interp in ("Hold", "Step"):
                eased = 0.0
            elif interp == "Linear":
                eased = u
            else:
                eased = cubic_bezier_ease(
                    u,
                    kf0.get("out_influence", 0.33333333),
                    kf1.get("in_influence", 0.33333333),
                )

            v0 = kf0.get("value", {}).get(type_tag, base_val)
            v1 = kf1.get("value", {}).get(type_tag, base_val)

            if type_tag == "Float" and isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
                return float(v0) + (float(v1) - float(v0)) * eased
            if type_tag == "Vec2" and isinstance(v0, dict) and isinstance(v1, dict):
                return {
                    "x": float(v0.get("x", 0.0)) + (float(v1.get("x", 0.0)) - float(v0.get("x", 0.0))) * eased,
                    "y": float(v0.get("y", 0.0)) + (float(v1.get("y", 0.0)) - float(v0.get("y", 0.0))) * eased,
                }
            return v0

    return base_val


def transform_point_2d(px, py, anchor_x, anchor_y, pos_x, pos_y, sx, sy, rot_deg):
    """Aplica transformação 2D (Âncora -> Escala X/Y -> Rotação -> Posição)."""
    dx = (px - anchor_x) * sx
    dy = (py - anchor_y) * sy
    rad = math.radians(rot_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    rx = dx * cos_a - dy * sin_a
    ry = dx * sin_a + dy * cos_a
    return pos_x + rx, pos_y + ry


def build_shape_vertices(shape_kind, cx, cy, width, height):
    """Gera vértices em coordenadas de origem para formas geométricas."""
    hw = width / 2.0
    hh = height / 2.0

    if shape_kind in ("Bloco (Retângulo)", "Bloco + Texto"):
        return [
            (cx - hw, cy - hh),
            (cx + hw, cy - hh),
            (cx + hw, cy + hh),
            (cx - hw, cy + hh),
        ]
    if shape_kind == "Quadrado":
        side = min(hw, hh)
        return [
            (cx - side, cy - side),
            (cx + side, cy - side),
            (cx + side, cy + side),
            (cx - side, cy + side),
        ]
    if shape_kind == "Triângulo":
        return [
            (cx, cy - hh),
            (cx + hw, cy + hh),
            (cx - hw, cy + hh),
        ]
    if shape_kind == "Losango":
        return [
            (cx, cy - hh),
            (cx + hw, cy),
            (cx, cy + hh),
            (cx - hw, cy),
        ]
    if shape_kind == "Estrela":
        pts = []
        outer_rx, outer_ry = hw, hh
        inner_rx, inner_ry = hw * 0.42, hh * 0.42
        for i in range(10):
            ang = -math.pi / 2.0 + (i * math.pi / 5.0)
            rx = outer_rx if i % 2 == 0 else inner_rx
            ry = outer_ry if i % 2 == 0 else inner_ry
            pts.append((cx + math.cos(ang) * rx, cy + math.sin(ang) * ry))
        return pts

    pts = []
    steps = 48
    for i in range(steps):
        ang = (2.0 * math.pi * i) / steps
        pts.append((cx + math.cos(ang) * hw, cy + math.sin(ang) * hh))
    return pts


# ----------------------------------------------------------------------
# Monitor / Viewer Estilo DaVinci Resolve
# ----------------------------------------------------------------------
class ResolveViewerWidget(ttk.Frame):
    """Monitor de pré-visualização NLE com Deck de Transporte, Timecode e Objetos de Teste."""

    def __init__(self, parent, colors):
        super().__init__(parent, style="Panel.TFrame")
        self.c = colors

        self.preset_data = None
        self.is_playing = True
        self.current_time_ns = 0
        self.duration_ns = 3_000_000_000
        self._last_tick = time.perf_counter()
        self._after_id = None
        self.fps = 30                    # passo das setas do teclado (quadros/s)
        self.time_listener = None        # callback(time_ns) chamado a cada quadro desenhado
        self._tl_dragging = False
        self._last_timeline_draw = 0.0
        self._timeline_dirty = True
        self._drag_target = None
        self._drag_param = None
        self._drag_effect = None
        self._stage_transform = None
        self._keyframe_cache = None
        self._keyframe_cache_signature = None
        self.example_color_hex = "#e8943a"

        self._build_ui()
        self._schedule_tick()

    def _build_ui(self):
        # --- Cabeçalho do Viewer ---
        header = ttk.Frame(self, style="PanelHeader.TFrame", padding=(12, 7))
        header.pack(fill="x")

        title_wrap = ttk.Frame(header, style="PanelHeader.TFrame")
        title_wrap.pack(side="left")

        ttk.Label(title_wrap, text="VIEWER", style="SectionTag.TLabel").pack(side="left")

        self.res_badge_var = tk.StringVar(value="1920 × 1080  •  3.00s")
        ttk.Label(title_wrap, textvariable=self.res_badge_var, style="Badge.TLabel").pack(side="left", padx=(10, 0))

        opts_frame = ttk.Frame(header, style="PanelHeader.TFrame")
        opts_frame.pack(side="right")

        self.guides_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opts_frame, text="Guias", style="Header.TCheckbutton", variable=self.guides_var, command=self.render_frame
        ).pack(side="left", padx=4)

        self.anchor_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opts_frame, text="Âncora", style="Header.TCheckbutton", variable=self.anchor_var, command=self.render_frame
        ).pack(side="left", padx=4)

        ttk.Label(opts_frame, text="Vel.:", style="HeaderMuted.TLabel").pack(side="left", padx=(8, 3))
        self.speed_combo = ttk.Combobox(
            opts_frame,
            values=["1x", "2x", "5x", "10x", "50x", "100x"],
            state="readonly",
            width=5,
        )
        self.speed_combo.current(0)
        self.speed_combo.pack(side="left", padx=(0, 8))

        self.bg_combo = ttk.Combobox(
            opts_frame,
            values=["Monitor Escuro", "Grade Transparente", "Verde Chroma"],
            state="readonly",
            width=17,
        )
        self.bg_combo.current(0)
        self.bg_combo.pack(side="left")
        self.bg_combo.bind("<<ComboboxSelected>>", lambda _e: self.render_frame())

        self.control_mode_var = tk.StringVar(value="Posição")
        self.control_mode_combo = ttk.Combobox(
            opts_frame, textvariable=self.control_mode_var,
            values=["Posição", "Escala", "Rotação"], state="readonly", width=10,
        )
        self.control_mode_combo.pack(side="left", padx=(8, 0))
        self.control_mode_combo.bind("<<ComboboxSelected>>", lambda _e: self.render_frame())

        tk.Frame(self, bg=self.c["border"], height=1).pack(fill="x")

        # --- Área do Monitor (Canvas) ---
        monitor_stage = tk.Frame(self, bg=self.c["monitor_gutter"], padx=10, pady=10)
        monitor_stage.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            monitor_stage,
            bg=self.c["monitor_bg"],
            height=300,
            highlightthickness=1,
            highlightbackground=self.c["border"],
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _e: self.render_frame())
        self.canvas.bind("<Button-1>", self._on_viewer_press)
        self.canvas.bind("<B1-Motion>", self._on_viewer_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_viewer_release)
        self.canvas.bind("<Motion>", self._on_viewer_hover)

        tk.Frame(self, bg=self.c["border"], height=1).pack(fill="x")

        # --- Deck de Transporte & Scrubber (estilo DaVinci Resolve) ---
        deck = ttk.Frame(self, style="Deck.TFrame", padding=(14, 8))
        deck.pack(fill="x")

        # Linha superior do deck: Timeline Scrubber + Timecode Digital
        scrub_row = ttk.Frame(deck, style="Deck.TFrame")
        scrub_row.pack(fill="x", pady=(0, 6))

        # Timeline com régua, losangos de keyframe e playhead
        self.timeline_canvas = tk.Canvas(
            scrub_row,
            height=46,
            bg=self.c["well"],
            highlightthickness=1,
            highlightbackground=self.c["border"],
            highlightcolor=self.c["accent"],
            cursor="sb_h_double_arrow",
        )
        self.timeline_canvas.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.timeline_canvas.bind("<Configure>", lambda _e: self._draw_timeline())
        self.timeline_canvas.bind("<Button-1>", self._on_tl_press)
        self.timeline_canvas.bind("<B1-Motion>", self._on_tl_drag)
        self.timeline_canvas.bind("<ButtonRelease-1>", self._on_tl_release)
        self.timeline_canvas.bind("<Motion>", self._on_tl_hover)

        self.time_label_var = tk.StringVar(value="00:00.00 / 00:03.00")
        tc_box = tk.Frame(scrub_row, bg=self.c["well"], highlightbackground=self.c["border"], highlightthickness=1, padx=8, pady=2)
        tc_box.pack(side="right")
        tk.Label(
            tc_box,
            textvariable=self.time_label_var,
            bg=self.c["well"],
            fg=self.c["accent"],
            font=(MONO_FONT, 9, "bold"),
        ).pack()

        # Linha inferior do deck: Controles de Transporte + Objeto de Teste
        transport_row = ttk.Frame(deck, style="Deck.TFrame")
        transport_row.pack(fill="x")

        t_btns = ttk.Frame(transport_row, style="Deck.TFrame")
        t_btns.pack(side="left")

        ttk.Button(t_btns, text="⏮", width=3, style="Transport.TButton", command=self.restart).pack(side="left", padx=(0, 4))

        self.play_btn = ttk.Button(t_btns, text="⏸  Pausar", width=10, style="TransportAccent.TButton", command=self.toggle_play)
        self.play_btn.pack(side="left", padx=(0, 8))

        self.loop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(t_btns, text="Loop", style="Deck.TCheckbutton", variable=self.loop_var).pack(side="left", padx=(0, 10))

        # Controles de Objeto de Teste acoplados à direita do deck
        dummy_wrap = ttk.Frame(transport_row, style="Deck.TFrame")
        dummy_wrap.pack(side="right")

        ttk.Label(dummy_wrap, text="Objeto:", style="DeckMuted.TLabel").pack(side="left", padx=(0, 4))

        self.example_mode_var = tk.StringVar(value="Auto (Preset / Texto)")
        self.example_mode_combo = ttk.Combobox(
            dummy_wrap,
            textvariable=self.example_mode_var,
            values=[
                "Auto (Preset / Texto)",
                "Texto de Exemplo",
                "Bloco (Retângulo)",
                "Quadrado",
                "Círculo",
                "Triângulo",
                "Losango",
                "Estrela",
                "Bloco + Texto",
            ],
            state="readonly",
            width=18,
        )
        self.example_mode_combo.pack(side="left", padx=(0, 6))
        self.example_mode_combo.bind("<<ComboboxSelected>>", lambda _e: self.render_frame())

        self.example_text_var = tk.StringVar(value="Texto de Exemplo")
        self.example_text_var.trace_add("write", lambda *_: self.render_frame())
        ttk.Entry(dummy_wrap, textvariable=self.example_text_var, width=16).pack(side="left", padx=(0, 6))

        self.shape_w_var = tk.StringVar(value="460")
        self.shape_h_var = tk.StringVar(value="240")
        self.shape_w_var.trace_add("write", lambda *_: self.render_frame())
        self.shape_h_var.trace_add("write", lambda *_: self.render_frame())
        ttk.Entry(dummy_wrap, textvariable=self.shape_w_var, width=4).pack(side="left")
        ttk.Label(dummy_wrap, text="×", style="DeckMuted.TLabel").pack(side="left", padx=2)
        ttk.Entry(dummy_wrap, textvariable=self.shape_h_var, width=4).pack(side="left", padx=(0, 6))

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
        ttk.Button(dummy_wrap, text="Cor", width=4, style="Ghost.TButton", command=self._pick_example_color).pack(side="left")

    def _pick_example_color(self):
        chosen = colorchooser.askcolor(color=self.example_color_hex, title="Cor do Objeto de Exemplo")
        if chosen and chosen[1]:
            self.example_color_hex = chosen[1]
            self.example_swatch.config(bg=chosen[1])
            self.render_frame()

    def set_preset(self, preset_dict, reset_time=False):
        self.preset_data = preset_dict
        self._recalculate_duration()
        if reset_time:
            self.current_time_ns = 0
        elif self.current_time_ns > self.duration_ns:
            self.current_time_ns = 0
        self._timeline_dirty = True
        self.render_frame()

    def _recalculate_duration(self):
        if not isinstance(self.preset_data, dict):
            self.duration_ns = 3_000_000_000
            return

        max_kf_ns = 0
        for eff in self.preset_data.get("effects", []):
            params = eff.get("params", {})
            for p_obj in params.values():
                if isinstance(p_obj, dict) and isinstance(p_obj.get("keyframes"), list):
                    for kf in p_obj["keyframes"]:
                        t = kf.get("time", 0)
                        if isinstance(t, (int, float)) and t > max_kf_ns:
                            max_kf_ns = int(t)

        src_dur = int(self.preset_data.get("source_duration", 3_000_000_000))
        if max_kf_ns > 0:
            self.duration_ns = max_kf_ns
        else:
            self.duration_ns = max(1_000_000_000, min(src_dur, 10_000_000_000))

        dur_sec = self.duration_ns / 1_000_000_000.0
        if dur_sec > 120.0 and self.speed_combo.get() == "1x":
            self.speed_combo.set("50x")
        elif dur_sec <= 15.0 and self.speed_combo.get() in ("50x", "100x"):
            self.speed_combo.set("1x")

        src_size = self.preset_data.get("source_size", [1920, 1080])
        w = src_size[0] if isinstance(src_size, list) and len(src_size) >= 2 else 1920
        h = src_size[1] if isinstance(src_size, list) and len(src_size) >= 2 else 1080
        self.res_badge_var.set(f"{w} × {h}  •  {dur_sec:.2f}s")

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.play_btn.config(text="⏸  Pausar" if self.is_playing else "▶  Play")
        self._last_tick = time.perf_counter()

    def restart(self):
        self.current_time_ns = 0
        self._last_tick = time.perf_counter()
        self.render_frame()

    # --- Navegação no tempo ------------------------------------------------
    def pause(self):
        if self.is_playing:
            self.is_playing = False
            self.play_btn.config(text="▶  Play")

    def frame_ns(self):
        return 1_000_000_000.0 / max(1, self.fps)

    def seek(self, t_ns):
        """Move o cursor para t_ns e atualiza Viewer, timeline e Inspetor."""
        self.current_time_ns = max(0, min(int(t_ns), int(self.duration_ns)))
        self._timeline_dirty = True
        self._last_tick = time.perf_counter()
        self.render_frame()

    def step_frames(self, n):
        """Pausa e move o cursor n quadros (negativo = para trás)."""
        self.pause()
        idx = round(self.current_time_ns * self.fps / 1_000_000_000.0)
        self.seek(round((idx + n) * 1_000_000_000.0 / self.fps))

    def jump_keyframe(self, direction):
        """Pausa e vai para o keyframe anterior (-1) ou próximo (+1)."""
        times = self._collect_keyframe_times()
        cur = self.current_time_ns
        tol = self.frame_ns() / 2.0
        if direction > 0:
            cands = [t for t in times if t > cur + tol]
            target = cands[0] if cands else None
        else:
            cands = [t for t in times if t < cur - tol]
            target = cands[-1] if cands else None
        if target is not None:
            self.pause()
            self.seek(target)

    def go_to_start(self):
        self.pause()
        self.seek(0)

    def go_to_end(self):
        self.pause()
        self.seek(self.duration_ns)

    # --- Timeline com keyframes (losangos) ---------------------------------
    _TL_PAD = 12
    _TL_RULER_H = 16

    def _collect_keyframe_times(self):
        """Tempos (ns) únicos de todos os keyframes dos efeitos habilitados."""
        # Cacheia os tempos: a estrutura só muda quando um keyframe é editado.
        signature = id(self.preset_data)
        if isinstance(self.preset_data, dict):
            signature = (id(self.preset_data), tuple(
                (id(param), tuple(kf.get("time", 0) for kf in param.get("keyframes", [])))
                for effect in self.preset_data.get("effects", [])
                for param in effect.get("params", {}).values()
                if isinstance(param, dict) and isinstance(param.get("keyframes"), list)
            ))
        if self._keyframe_cache is not None and signature == self._keyframe_cache_signature:
            return self._keyframe_cache
        times = set()
        if isinstance(self.preset_data, dict):
            for eff in self.preset_data.get("effects", []):
                if not eff.get("enabled", True):
                    continue
                params = eff.get("params", {})
                if not isinstance(params, dict):
                    continue
                for p_obj in params.values():
                    if isinstance(p_obj, dict) and isinstance(p_obj.get("keyframes"), list):
                        for kf in p_obj["keyframes"]:
                            t = kf.get("time") if isinstance(kf, dict) else None
                            if isinstance(t, (int, float)) and not isinstance(t, bool):
                                times.add(int(t))
        self._keyframe_cache = sorted(times)
        self._keyframe_cache_signature = signature
        return self._keyframe_cache

    def _tl_span(self):
        w = max(60, self.timeline_canvas.winfo_width())
        return w, max(1, w - 2 * self._TL_PAD)

    def _tl_x_of(self, t_ns):
        _w, span = self._tl_span()
        return self._TL_PAD + span * (t_ns / max(1, self.duration_ns))

    def _tl_time_of(self, x):
        _w, span = self._tl_span()
        frac = max(0.0, min(1.0, (x - self._TL_PAD) / span))
        return int(frac * self.duration_ns)

    def _kf_at_x(self, x, radius):
        """Tempo do keyframe mais próximo de x (em pixels) dentro do raio, ou None."""
        best, best_dx = None, radius + 1
        for t in self._collect_keyframe_times():
            dx = abs(self._tl_x_of(t) - x)
            if dx <= radius and dx < best_dx:
                best, best_dx = t, dx
        return best

    def _draw_timeline(self):
        cv = getattr(self, "timeline_canvas", None)
        if cv is None:
            return
        cv.delete("all")
        w = max(60, cv.winfo_width())
        h = max(30, cv.winfo_height())
        pad = self._TL_PAD
        ruler_h = self._TL_RULER_H
        span = max(1, w - 2 * pad)
        dur_s = max(0.01, self.duration_ns / 1_000_000_000.0)

        # Régua: escolhe um passo "redondo" com pelo menos ~72px entre marcas
        steps = (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600)
        step = steps[-1]
        for s in steps:
            if span * s / dur_s >= 72:
                step = s
                break

        cv.create_line(pad, ruler_h, w - pad, ruler_h, fill=self.c["border_light"])
        k = 0
        last_label_end = -1000.0
        while k * step <= dur_s + 1e-9:
            sec = k * step
            x = pad + span * sec / dur_s
            cv.create_line(x, ruler_h - 6, x, ruler_h, fill=self.c["fg_faint"])
            on_left = x + 52 < w
            label_left = x + 3 if on_left else x - 3 - 46
            if label_left >= last_label_end + 4:      # evita rótulos sobrepostos na ponta direita
                cv.create_text(
                    x + (3 if on_left else -3),
                    ruler_h - 9,
                    text=self._fmt_tc(sec),
                    anchor="w" if on_left else "e",
                    fill=self.c["fg_faint"],
                    font=(MONO_FONT, 7),
                )
                last_label_end = label_left + 46
            k += 1

        # Faixa dos keyframes
        cy = ruler_h + (h - ruler_h) / 2.0
        cv.create_line(pad, cy, w - pad, cy, fill=self.c["border"])

        times = self._collect_keyframe_times()
        if len(times) >= 2:
            cv.create_line(self._tl_x_of(times[0]), cy, self._tl_x_of(times[-1]), cy, fill="#5c4326", width=2)

        cur = self.current_time_ns
        tol = self.frame_ns() / 2.0
        for t in times:
            x = self._tl_x_of(t)
            active = abs(t - cur) <= tol
            r = 7 if active else 6
            cv.create_polygon(
                x, cy - r, x + r, cy, x, cy + r, x - r, cy,
                fill=self.c["accent"] if active else self.c["fg_muted"],
                outline=self.c["fg_text"] if active else self.c["border_light"],
                width=1,
            )

        # Playhead
        px = self._tl_x_of(cur)
        cv.create_line(px, 0, px, h, fill=self.c["accent"], width=1)
        cv.create_polygon(px - 5, 0, px + 5, 0, px, 8, fill=self.c["accent"], outline="")

    def _on_tl_press(self, event):
        self.timeline_canvas.focus_set()
        self.pause()
        self._tl_dragging = True
        t = None
        if event.y >= self._TL_RULER_H:          # clique na faixa dos losangos: encaixa no keyframe
            t = self._kf_at_x(event.x, 9)
        self.seek(t if t is not None else self._tl_time_of(event.x))

    def _on_tl_drag(self, event):
        if not self._tl_dragging:
            return
        snap = None if (event.state & 0x1) else self._kf_at_x(event.x, 5)   # Shift desliga o encaixe
        self.seek(snap if snap is not None else self._tl_time_of(event.x))

    def _on_tl_release(self, _event):
        self._tl_dragging = False

    def _on_tl_hover(self, event):
        over_kf = event.y >= self._TL_RULER_H and self._kf_at_x(event.x, 9) is not None
        self.timeline_canvas.config(cursor="hand2" if over_kf else "sb_h_double_arrow")

    def _schedule_tick(self):
        self._after_id = self.after(33, self._tick)  # ~30 FPS: reduz carga do Tkinter

    def _tick(self):
        now = time.perf_counter()
        dt = now - self._last_tick
        self._last_tick = now

        if self.is_playing and self.preset_data is not None and self.winfo_ismapped():
            speed_str = self.speed_combo.get().rstrip("x")
            try:
                speed_mult = float(speed_str)
            except ValueError:
                speed_mult = 1.0

            self.current_time_ns += int(dt * speed_mult * 1_000_000_000)
            if self.current_time_ns >= self.duration_ns:
                if self.loop_var.get():
                    self.current_time_ns %= max(1, self.duration_ns)
                else:
                    self.current_time_ns = self.duration_ns
                    self.is_playing = False
                    self.play_btn.config(text="▶  Play")
            self.render_frame()

        self._schedule_tick()

    def destroy(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        super().destroy()

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
            if not eff.get("enabled", True):
                continue
            if eff.get("effect") == "motion":
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

    def render_frame(self):
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        cw = max(10, self.canvas.winfo_width())
        ch = max(10, self.canvas.winfo_height())

        cur_sec = self.current_time_ns / 1_000_000_000.0
        dur_sec = self.duration_ns / 1_000_000_000.0
        self.time_label_var.set(f"{self._fmt_tc(cur_sec)} / {self._fmt_tc(dur_sec)}")

        now = time.perf_counter()
        if self._timeline_dirty or now - self._last_timeline_draw >= 0.10:
            self._draw_timeline()
            self._last_timeline_draw = now
            self._timeline_dirty = False
        if self.time_listener is not None:
            try:
                self.time_listener(self.current_time_ns)
            except tk.TclError:
                pass

        if not isinstance(self.preset_data, dict):
            self.canvas.create_text(
                cw / 2,
                ch / 2,
                text="Selecione um preset Filmcraft na Biblioteca para visualizar no Monitor",
                fill=self.c["fg_muted"],
                font=(UI_FONT, 10),
            )
            return

        src_size = self.preset_data.get("source_size", [1920, 1080])
        src_w = float(src_size[0]) if isinstance(src_size, list) and len(src_size) >= 2 and src_size[0] > 0 else 1920.0
        src_h = float(src_size[1]) if isinstance(src_size, list) and len(src_size) >= 2 and src_size[1] > 0 else 1080.0

        margin = 16.0
        avail_w = max(20.0, cw - margin * 2)
        avail_h = max(20.0, ch - margin * 2)
        ratio = min(avail_w / src_w, avail_h / src_h)

        stage_w = src_w * ratio
        stage_h = src_h * ratio
        x0 = (cw - stage_w) / 2.0
        y0 = (ch - stage_h) / 2.0
        x1 = x0 + stage_w
        y1 = y0 + stage_h
        self._stage_transform = (src_w, src_h, x0, y0, ratio)

        mode = self.bg_combo.get()
        if mode == "Verde Chroma":
            stage_bg = "#00b140"
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=stage_bg, outline=self.c["border_light"], width=1)
        elif mode == "Grade Transparente":
            stage_bg = "#1b1d22"
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=stage_bg, outline=self.c["border_light"], width=1)
            tile = 16
            cols = int(stage_w // tile) + 1
            rows = int(stage_h // tile) + 1
            for r in range(rows):
                for c in range(cols):
                    if (r + c) % 2 == 0:
                        tx0 = x0 + c * tile
                        ty0 = y0 + r * tile
                        tx1 = min(x1, tx0 + tile)
                        ty1 = min(y1, ty0 + tile)
                        self.canvas.create_rectangle(tx0, ty0, tx1, ty1, fill="#252830", outline="")
        else:
            stage_bg = "#0a0b0d"
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=stage_bg, outline=self.c["border_light"], width=1)

        # Guias de centro e Title/Action Safe (padrão NLE)
        if self.guides_var.get():
            cx = x0 + stage_w / 2.0
            cy = y0 + stage_h / 2.0
            self.canvas.create_line(cx, y0, cx, y1, fill="#242730", dash=(3, 4))
            self.canvas.create_line(x0, cy, x1, cy, fill="#242730", dash=(3, 4))
            # Action Safe (95%) e Title Safe (90%)
            self.canvas.create_rectangle(
                x0 + stage_w * 0.05,
                y0 + stage_h * 0.05,
                x1 - stage_w * 0.05,
                y1 - stage_h * 0.05,
                outline="#23262f",
                dash=(4, 4),
            )
            self.canvas.create_rectangle(
                x0 + stage_w * 0.10,
                y0 + stage_h * 0.10,
                x1 - stage_w * 0.10,
                y1 - stage_h * 0.10,
                outline="#1e2129",
                dash=(2, 4),
            )

        motion_tf = self._get_motion_transform(src_w, src_h)
        global_op = self._get_global_opacity()
        example_mode = self.example_mode_var.get()

        has_graphic_text = any(
            eff.get("enabled", True) and eff.get("effect") == "graphic_text"
            for eff in self.preset_data.get("effects", [])
        )

        shape_modes = ("Bloco (Retângulo)", "Quadrado", "Círculo", "Triângulo", "Losango", "Estrela", "Bloco + Texto")
        if example_mode in shape_modes:
            self._render_example_shape(example_mode, src_w, src_h, x0, y0, ratio, motion_tf, global_op, stage_bg)

        if example_mode in ("Texto de Exemplo", "Bloco + Texto") or (
            example_mode == "Auto (Preset / Texto)" and not has_graphic_text
        ):
            if has_graphic_text:
                for eff in self.preset_data.get("effects", []):
                    if eff.get("enabled", True) and eff.get("effect") == "graphic_text":
                        self._render_graphic_text(
                            eff.get("params", {}),
                            x0,
                            y0,
                            ratio,
                            stage_bg,
                            motion_tf,
                            global_op,
                            override_text=self.example_text_var.get(),
                        )
            else:
                self._render_dummy_text_for_motion(src_w, src_h, x0, y0, ratio, motion_tf, global_op, stage_bg)
        elif has_graphic_text and example_mode == "Auto (Preset / Texto)":
            for eff in self.preset_data.get("effects", []):
                if eff.get("enabled", True) and eff.get("effect") == "graphic_text":
                    self._render_graphic_text(eff.get("params", {}), x0, y0, ratio, stage_bg, motion_tf, global_op)

        if self.anchor_var.get() and motion_tf["has_motion"]:
            ax = x0 + motion_tf["pos_x"] * ratio
            ay = y0 + motion_tf["pos_y"] * ratio
            self.canvas.create_oval(ax - 5, ay - 5, ax + 5, ay + 5, outline=self.c["accent"], width=2)
            self.canvas.create_line(ax - 9, ay, ax + 9, ay, fill=self.c["accent"], width=1)
            self.canvas.create_line(ax, ay - 9, ax, ay + 9, fill=self.c["accent"], width=1)

        # Alça contextual estilo editor de vídeo: posição, escala ou rotação.
        control_points = self._viewer_control_points()
        control_mode = self.control_mode_var.get()
        active_key = {"Posição": "position", "Escala": "scale", "Rotação": "rotation"}.get(control_mode)
        handle = control_points.get(active_key)
        if handle:
            hx, hy = handle
            if control_mode == "Rotação" and control_points.get("center"):
                cxh, cyh = control_points["center"]
                self.canvas.create_line(cxh, cyh, hx, hy, fill=self.c["accent"], dash=(3, 2), width=2)
            self.canvas.create_oval(hx-9, hy-9, hx+9, hy+9, fill=self.c["accent"], outline="#ffffff", width=2, tags=("viewer_control",))
            self.canvas.create_line(hx-14, hy, hx+14, hy, fill="#ffffff", width=1)
            self.canvas.create_line(hx, hy-14, hx, hy+14, fill="#ffffff", width=1)
            hint = {"Posição": "Arraste para animar posição", "Escala": "Arraste para alterar escala", "Rotação": "Arraste para girar"}.get(control_mode, "")
            self.canvas.create_text(x0+8, y1-8, text=f"{hint} • cria/atualiza keyframe no tempo atual", anchor="sw", fill=self.c["fg_muted"], font=(UI_FONT, 8))

    def _find_editable_position(self):
        """Prioriza position do efeito motion; caso contrário usa graphic_text."""
        if not isinstance(self.preset_data, dict):
            return None, None
        effects = self.preset_data.get("effects", [])
        for preferred in ("motion", "graphic_text"):
            for effect in effects:
                if effect.get("enabled", True) and effect.get("effect") == preferred:
                    param = effect.get("params", {}).get("position")
                    if isinstance(param, dict) and isinstance(param.get("value", {}).get("Vec2"), dict):
                        return effect, param
        return None, None

    def _write_viewer_position(self, x, y):
        effect, param = self._find_editable_position()
        if param is None:
            return
        kfs = param.setdefault("keyframes", [])
        t = int(self.current_time_ns)
        match = next((kf for kf in kfs if abs(int(kf.get("time", -1)) - t) <= self.frame_ns() / 2), None)
        value = {"Vec2": {"x": round(float(x), 3), "y": round(float(y), 3)}}
        if match is None:
            match = {"time": t, "value": value, "interp": "AutoBezier", "out_influence": 1/3, "in_influence": 1/3}
            kfs.append(match)
            kfs.sort(key=lambda item: item.get("time", 0))
        else:
            match.setdefault("value", {})["Vec2"] = value["Vec2"]
        param["value"]["Vec2"] = value["Vec2"]
        self._keyframe_cache = None
        self._timeline_dirty = True
        if self.time_listener is not None:
            try:
                self.time_listener(self.current_time_ns)
            except tk.TclError:
                pass

    def _viewer_position_screen(self):
        if not self._stage_transform:
            return None
        effect, param = self._find_editable_position()
        if param is None:
            return None
        src_w, src_h, x0, y0, ratio = self._stage_transform
        pos = evaluate_filmcraft_param(param, self.current_time_ns) or {"x": src_w/2, "y": src_h/2}
        return x0 + float(pos.get("x", src_w/2))*ratio, y0 + float(pos.get("y", src_h/2))*ratio

    def _motion_effect(self):
        if not isinstance(self.preset_data, dict):
            return None
        return next((e for e in self.preset_data.get("effects", [])
                     if e.get("enabled", True) and e.get("effect") == "motion"), None)

    def _write_viewer_scalar(self, key, value):
        effect = self._motion_effect()
        if effect is None:
            return
        param = effect.get("params", {}).get(key)
        if not isinstance(param, dict) or "value" not in param:
            return
        kfs = param.setdefault("keyframes", [])
        t = int(self.current_time_ns)
        match = next((kf for kf in kfs if abs(int(kf.get("time", -1))-t) <= self.frame_ns()/2), None)
        value = float(value)
        if match is None:
            match = {"time": t, "value": {"Float": value}, "interp": "AutoBezier",
                     "out_influence": 1/3, "in_influence": 1/3}
            kfs.append(match)
            kfs.sort(key=lambda item: item.get("time", 0))
        else:
            match.setdefault("value", {})["Float"] = value
        param["value"]["Float"] = value
        self._keyframe_cache = None
        self._timeline_dirty = True

    def _viewer_control_points(self):
        if not self._stage_transform:
            return {}
        src_w, src_h, x0, y0, ratio = self._stage_transform
        mode = self.control_mode_var.get()
        if mode == "Posição":
            effect, param = self._find_editable_position()
            if param is None:
                return {}
            pos = evaluate_filmcraft_param(param, self.current_time_ns) or {"x": src_w/2, "y": src_h/2}
            return {"position": (x0+float(pos.get("x", src_w/2))*ratio,
                                  y0+float(pos.get("y", src_h/2))*ratio)}
        effect = self._motion_effect()
        if effect is None:
            return {}
        params = effect.get("params", {})
        center = (x0+src_w*ratio/2, y0+src_h*ratio/2)
        if mode == "Escala":
            scale = float(evaluate_filmcraft_param(params.get("scale"), self.current_time_ns) or 100.0)
            offset = max(28.0, min(100.0, 65.0*scale/100.0))
            return {"scale": (center[0]+offset, center[1]-offset), "center": center}
        angle = float(evaluate_filmcraft_param(params.get("rotation"), self.current_time_ns) or 0.0)
        rad = math.radians(angle-90.0)
        return {"rotation": (center[0]+math.cos(rad)*75, center[1]+math.sin(rad)*75), "center": center}

    def _on_viewer_press(self, event):
        self.canvas.focus_set()
        points = self._viewer_control_points()
        mode = self.control_mode_var.get()
        key = {"Posição": "position", "Escala": "scale", "Rotação": "rotation"}.get(mode)
        point = points.get(key)
        if point and math.hypot(event.x-point[0], event.y-point[1]) <= 18:
            self.pause()
            self._drag_target = key
            self.canvas.configure(cursor="fleur")

    def _on_viewer_drag(self, event):
        if not self._drag_target or not self._stage_transform:
            return
        src_w, src_h, x0, y0, ratio = self._stage_transform
        if self._drag_target == "position":
            x = max(0.0, min(src_w, (event.x-x0)/ratio))
            y = max(0.0, min(src_h, (event.y-y0)/ratio))
            self._write_viewer_position(x, y)
        else:
            points = self._viewer_control_points()
            center = points.get("center")
            if not center:
                return
            if self._drag_target == "scale":
                value = max(1.0, min(1000.0, math.hypot(event.x-center[0], event.y-center[1]) / (math.sqrt(2)*0.65) ))
                self._write_viewer_scalar("scale", value)
            elif self._drag_target == "rotation":
                value = math.degrees(math.atan2(event.y-center[1], event.x-center[0])) + 90.0
                self._write_viewer_scalar("rotation", ((value+180.0) % 360.0)-180.0)
        self.render_frame()

    def _on_viewer_release(self, _event):
        if self._drag_target:
            self._drag_target = None
            self.canvas.configure(cursor="arrow")
            self.render_frame()

    def _on_viewer_hover(self, event):
        points = self._viewer_control_points()
        mode = self.control_mode_var.get()
        key = {"Posição": "position", "Escala": "scale", "Rotação": "rotation"}.get(mode)
        point = points.get(key)
        self.canvas.configure(cursor="fleur" if point and math.hypot(event.x-point[0], event.y-point[1]) <= 18 else "arrow")

    def _render_example_shape(self, shape_kind, src_w, src_h, x0, y0, ratio, motion_tf, global_op, stage_bg):
        try:
            sw = max(10.0, float(self.shape_w_var.get()))
        except ValueError:
            sw = 460.0
        try:
            sh = max(10.0, float(self.shape_h_var.get()))
        except ValueError:
            sh = 240.0

        cx = src_w / 2.0
        cy = src_h / 2.0
        verts = build_shape_vertices(shape_kind, cx, cy, sw, sh)

        poly_coords = []
        for vx, vy in verts:
            if motion_tf["has_motion"]:
                tx, ty = transform_point_2d(
                    vx,
                    vy,
                    motion_tf["anchor_x"],
                    motion_tf["anchor_y"],
                    motion_tf["pos_x"],
                    motion_tf["pos_y"],
                    motion_tf["sx"],
                    motion_tf["sy"],
                    motion_tf["rot_deg"],
                )
            else:
                tx, ty = vx, vy
            poly_coords.extend([x0 + tx * ratio, y0 + ty * ratio])

        fill_rgba = hex_to_rgba_float(self.example_color_hex, 0.85)
        fill_hex = blend_rgba_on_bg(fill_rgba, global_op, stage_bg)
        self.canvas.create_polygon(poly_coords, fill=fill_hex, outline="#e4e6eb", width=2)

        if shape_kind in ("Bloco (Retângulo)", "Quadrado", "Bloco + Texto") and len(poly_coords) >= 8:
            self.canvas.create_line(
                poly_coords[0], poly_coords[1], poly_coords[4], poly_coords[5], fill="#16181d", dash=(3, 3)
            )
            self.canvas.create_line(
                poly_coords[2], poly_coords[3], poly_coords[6], poly_coords[7], fill="#16181d", dash=(3, 3)
            )

    def _render_dummy_text_for_motion(self, src_w, src_h, x0, y0, ratio, motion_tf, global_op, stage_bg):
        txt = self.example_text_var.get().strip() or "Texto de Exemplo"
        cx = src_w / 2.0
        cy = src_h / 2.0

        if motion_tf["has_motion"]:
            tx, ty = transform_point_2d(
                cx,
                cy,
                motion_tf["anchor_x"],
                motion_tf["anchor_y"],
                motion_tf["pos_x"],
                motion_tf["pos_y"],
                motion_tf["sx"],
                motion_tf["sy"],
                motion_tf["rot_deg"],
            )
            avg_scale = (motion_tf["sx"] + motion_tf["sy"]) / 2.0
            rot_deg = motion_tf["rot_deg"]
        else:
            tx, ty = cx, cy
            avg_scale = 1.0
            rot_deg = 0.0

        px = x0 + tx * ratio
        py = y0 + ty * ratio
        font_pt = max(1, int(round(78.0 * avg_scale * ratio * 0.75)))
        tk_font = (UI_FONT, font_pt, "bold")

        for i in range(8):
            ang = (2.0 * math.pi * i) / 8.0
            self.canvas.create_text(
                px + math.cos(ang) * 2.0,
                py + math.sin(ang) * 2.0,
                text=txt,
                font=tk_font,
                fill="#0a0b0d",
                angle=-rot_deg,
            )

        txt_rgba = hex_to_rgba_float("#ffffff" if self.example_mode_var.get() == "Bloco + Texto" else self.example_color_hex, 1.0)
        txt_hex = blend_rgba_on_bg(txt_rgba, global_op, stage_bg)
        self.canvas.create_text(px, py, text=txt, font=tk_font, fill=txt_hex, angle=-rot_deg)

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
        faux_bold = bool(evaluate_filmcraft_param(params.get("faux_bold"), t))
        faux_italic = bool(evaluate_filmcraft_param(params.get("faux_italic"), t))
        underline = bool(evaluate_filmcraft_param(params.get("underline"), t))
        strikethrough = bool(evaluate_filmcraft_param(params.get("strikethrough"), t))

        weight = "bold" if ("bold" in font_style_str or faux_bold) else "normal"
        slant = "italic" if ("italic" in font_style_str or faux_italic) else "roman"

        base_size = float(evaluate_filmcraft_param(params.get("size"), t) or 100.0)
        scale_pct = float(evaluate_filmcraft_param(params.get("scale"), t) or 100.0)
        opacity_pct = float(evaluate_filmcraft_param(params.get("opacity"), t) or 100.0) * (global_op / 100.0)
        rotation_deg = float(evaluate_filmcraft_param(params.get("rotation"), t) or 0.0)

        pos = evaluate_filmcraft_param(params.get("position"), t) or {"x": 960.0, "y": 540.0}
        src_px = float(pos.get("x", 960.0))
        src_py = float(pos.get("y", 540.0))

        if motion_tf["has_motion"]:
            src_px, src_py = transform_point_2d(
                src_px,
                src_py,
                motion_tf["anchor_x"],
                motion_tf["anchor_y"],
                motion_tf["pos_x"],
                motion_tf["pos_y"],
                motion_tf["sx"],
                motion_tf["sy"],
                motion_tf["rot_deg"],
            )
            scale_pct *= (motion_tf["sx"] + motion_tf["sy"]) / 2.0
            rotation_deg += motion_tf["rot_deg"]

        px = x0 + src_px * ratio
        py = y0 + src_py * ratio

        effective_px_size = base_size * (scale_pct / 100.0) * ratio
        font_pt = max(1, int(round(effective_px_size * 0.75)))

        font_spec = [font_family, font_pt, weight, slant]
        if underline:
            font_spec.append("underline")
        if strikethrough:
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
                    bbox[0] - bg_pad,
                    bbox[1] - bg_pad * 0.6,
                    bbox[2] + bg_pad,
                    bbox[3] + bg_pad * 0.6,
                    fill=bg_hex,
                    outline="",
                )

        if bool(evaluate_filmcraft_param(params.get("shadow"), t)):
            sh_angle = math.radians(float(evaluate_filmcraft_param(params.get("shadow_angle"), t) or 135.0))
            sh_dist = float(evaluate_filmcraft_param(params.get("shadow_distance"), t) or 10.0) * ratio * (scale_pct / 100.0)
            sh_rgba = evaluate_filmcraft_param(params.get("shadow_color"), t) or [0.0, 0.0, 0.0, 1.0]
            sh_op = float(evaluate_filmcraft_param(params.get("shadow_opacity"), t) or 75.0)
            sh_hex = blend_rgba_on_bg(sh_rgba, sh_op * (opacity_pct / 100.0), stage_bg)
            self.canvas.create_text(
                px + math.cos(sh_angle) * sh_dist,
                py + math.sin(sh_angle) * sh_dist,
                text=raw_text,
                font=tk_font,
                fill=sh_hex,
                justify=justify,
                angle=-rotation_deg,
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
                    px + math.cos(ang) * r_px,
                    py + math.sin(ang) * r_px,
                    text=raw_text,
                    font=tk_font,
                    fill=st_hex,
                    justify=justify,
                    angle=-rotation_deg,
                )

        if bool(evaluate_filmcraft_param(params.get("fill", {"value": {"Bool": True}}), t)):
            fill_rgba = evaluate_filmcraft_param(params.get("fill_color"), t) or [1.0, 1.0, 1.0, 1.0]
            fill_hex = blend_rgba_on_bg(fill_rgba, opacity_pct, stage_bg)
            self.canvas.create_text(
                px,
                py,
                text=raw_text,
                font=tk_font,
                fill=fill_hex,
                justify=justify,
                angle=-rotation_deg,
            )


class ScrollableFrame(ttk.Frame):
    """Frame rolável para o Inspetor estilo DaVinci Resolve."""

    def __init__(self, container, bg_color="#1b1d22", *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="Panel.TFrame")

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _bind_mousewheel(self, _event):
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_win)

    def _unbind_mousewheel(self, _event):
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-2, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(2, "units")

    def _on_mousewheel_win(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class PresetManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Preset Studio")
        self.root.geometry("1420x880")
        self.root.minsize(1120, 700)

        self.profiles = self._load_profiles()
        self.current_profile_name = next(iter(self.profiles.keys()))
        self.current_file_path = None
        self.current_data = None
        self.selected_preset_idx = 0
        self.selected_effect_idx = 0
        self.modified = False
        self.current_page = "studio"
        self._inspector_syncing = False   # True enquanto o app (e não o usuário) escreve nos campos
        self._live_params = []            # callbacks que atualizam o Inspetor conforme o tempo
        self._param_labels = {}           # id(param_obj) -> (Label, nome) para o contador de keyframes

        self._setup_theme()
        self._build_ui()
        self._bind_shortcuts()
        self._refresh_file_list()

    # ------------------------------------------------------------------
    # Configuração de Perfis & Armazenamento
    # ------------------------------------------------------------------
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
            presents_dir = Path.home() / "Documentos" / "Presets"

        default_profiles = {
            "Filmcraft (Effect Presets)": {
                "folder": str(presents_dir),
                "schema_type": "filmcraft",
                "template": FILMCRAFT_TEXT_TEMPLATE,
            },
            "Genérico (Qualquer App JSON)": {
                "folder": str(Path.home() / "Documentos" / "Presets_JSON"),
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
    # Tema DaVinci Resolve Studio + macOS Dark Vibrancy
    # ------------------------------------------------------------------
    def _setup_theme(self):
        self.c = {
            "bg_root": "#121317",
            "titlebar": "#1c1e24",
            "panel": "#191b20",
            "panel_header": "#21232a",
            "card": "#202229",
            "card_hover": "#282b34",
            "deck": "#17191e",
            "well": "#111216",
            "input": "#15171c",
            "border": "#2b2e38",
            "border_light": "#3a3e4b",
            "monitor_gutter": "#111216",
            "monitor_bg": "#0a0b0d",
            "fg_text": "#e4e6eb",
            "fg_muted": "#9499a6",
            "fg_faint": "#636875",
            "accent": "#e8943a",        # DaVinci Resolve Amber/Gold
            "accent_hover": "#f4a44c",
            "accent_pressed": "#c97926",
            "select_bg": "#2b3952",     # macOS Cobalt Selection
            "select_border": "#4a89dc",
            "success": "#4cc38a",
            "danger": "#e55353",
            "danger_bg": "#351d21",
        }

        self.root.configure(bg=self.c["bg_root"])
        self.root.option_add("*Font", (UI_FONT, 10))

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            ".",
            background=self.c["panel"],
            foreground=self.c["fg_text"],
            bordercolor=self.c["border"],
            focuscolor=self.c["accent"],
            font=(UI_FONT, 10),
        )

        # Frames
        style.configure("Root.TFrame", background=self.c["bg_root"])
        style.configure("Titlebar.TFrame", background=self.c["titlebar"])
        style.configure("Panel.TFrame", background=self.c["panel"])
        style.configure("PanelHeader.TFrame", background=self.c["panel_header"])
        style.configure("Deck.TFrame", background=self.c["deck"])
        style.configure("Card.TFrame", background=self.c["card"])
        style.configure("Dock.TFrame", background=self.c["titlebar"])

        # Labels
        style.configure("TLabel", background=self.c["panel"], foreground=self.c["fg_text"], font=(UI_FONT, 10))
        style.configure("Title.TLabel", background=self.c["titlebar"], foreground=self.c["fg_text"], font=(UI_FONT, 11, "bold"))
        style.configure("TitleMuted.TLabel", background=self.c["titlebar"], foreground=self.c["fg_muted"], font=(UI_FONT, 9))
        style.configure("SectionTag.TLabel", background=self.c["panel_header"], foreground=self.c["fg_muted"], font=(UI_FONT, 8, "bold"))
        style.configure("Badge.TLabel", background=self.c["panel_header"], foreground=self.c["accent"], font=(MONO_FONT, 9, "bold"))
        style.configure("HeaderMuted.TLabel", background=self.c["panel_header"], foreground=self.c["fg_muted"], font=(UI_FONT, 9))
        style.configure("DeckMuted.TLabel", background=self.c["deck"], foreground=self.c["fg_muted"], font=(UI_FONT, 9))
        style.configure("Muted.TLabel", background=self.c["panel"], foreground=self.c["fg_muted"], font=(UI_FONT, 9))
        style.configure("Card.TLabel", background=self.c["card"], foreground=self.c["fg_text"], font=(UI_FONT, 9))
        style.configure("CardMuted.TLabel", background=self.c["card"], foreground=self.c["fg_muted"], font=(UI_FONT, 9))
        style.configure("CardSection.TLabel", background=self.c["card"], foreground=self.c["accent"], font=(UI_FONT, 8, "bold"))

        # Botões estilo macOS / DaVinci Resolve
        style.configure(
            "TButton",
            background=self.c["card_hover"],
            foreground=self.c["fg_text"],
            bordercolor=self.c["border_light"],
            borderwidth=1,
            focusthickness=0,
            padding=(10, 5),
            font=(UI_FONT, 9, "bold"),
        )
        style.map(
            "TButton",
            background=[("active", "#323642"), ("pressed", "#22242c")],
            bordercolor=[("active", "#4b5060")],
        )

        style.configure(
            "Accent.TButton",
            background=self.c["accent"],
            foreground="#121317",
            bordercolor=self.c["accent"],
            borderwidth=1,
            padding=(12, 5),
            font=(UI_FONT, 9, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", self.c["accent_hover"]), ("pressed", self.c["accent_pressed"])],
            bordercolor=[("active", self.c["accent_hover"])],
        )

        style.configure(
            "Ghost.TButton",
            background=self.c["titlebar"],
            foreground=self.c["fg_muted"],
            bordercolor=self.c["border"],
            borderwidth=1,
            padding=(8, 4),
            font=(UI_FONT, 9),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", self.c["card_hover"])],
            foreground=[("active", self.c["fg_text"])],
        )

        style.configure(
            "Danger.TButton",
            background=self.c["danger_bg"],
            foreground=self.c["danger"],
            bordercolor="#54282e",
            borderwidth=1,
            padding=(9, 5),
            font=(UI_FONT, 9, "bold"),
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#472429")],
        )

        style.configure(
            "Transport.TButton",
            background=self.c["card_hover"],
            foreground=self.c["fg_text"],
            bordercolor=self.c["border_light"],
            borderwidth=1,
            padding=(8, 4),
            font=(UI_FONT, 9, "bold"),
        )
        style.map("Transport.TButton", background=[("active", "#343846")])

        style.configure(
            "TransportAccent.TButton",
            background=self.c["accent"],
            foreground="#121317",
            bordercolor=self.c["accent"],
            borderwidth=1,
            padding=(10, 4),
            font=(UI_FONT, 9, "bold"),
        )
        style.map("TransportAccent.TButton", background=[("active", self.c["accent_hover"])])

        style.configure(
            "KeyframeOff.TButton",
            background=self.c["input"],
            foreground=self.c["fg_muted"],
            bordercolor=self.c["border_light"],
            borderwidth=1,
            padding=(7, 3),
            font=(UI_FONT, 8, "bold"),
        )
        style.map(
            "KeyframeOff.TButton",
            background=[("active", self.c["card_hover"])],
            foreground=[("active", self.c["fg_text"])],
        )

        style.configure(
            "KeyframeOn.TButton",
            background="#382918",
            foreground=self.c["accent"],
            bordercolor=self.c["accent"],
            borderwidth=1,
            padding=(7, 3),
            font=(UI_FONT, 8, "bold"),
        )
        style.map("KeyframeOn.TButton", background=[("active", "#4a351e")])

        # Entradas e Comboboxes rebaixados
        style.configure(
            "TEntry",
            fieldbackground=self.c["input"],
            background=self.c["input"],
            foreground=self.c["fg_text"],
            insertcolor=self.c["accent"],
            bordercolor=self.c["border_light"],
            lightcolor=self.c["border_light"],
            darkcolor=self.c["border_light"],
            borderwidth=1,
            padding=5,
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", self.c["accent"])],
            lightcolor=[("focus", self.c["accent"])],
            darkcolor=[("focus", self.c["accent"])],
        )

        style.configure(
            "TCombobox",
            fieldbackground=self.c["input"],
            background=self.c["card_hover"],
            foreground=self.c["fg_text"],
            arrowcolor=self.c["fg_muted"],
            bordercolor=self.c["border_light"],
            lightcolor=self.c["border_light"],
            darkcolor=self.c["border_light"],
            padding=4,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.c["input"])],
            background=[("readonly", self.c["card_hover"])],
            bordercolor=[("focus", self.c["accent"])],
        )

        # Checkbuttons
        style.configure("TCheckbutton", background=self.c["panel"], foreground=self.c["fg_text"])
        style.map("TCheckbutton", background=[("active", self.c["panel"])])
        style.configure("Header.TCheckbutton", background=self.c["panel_header"], foreground=self.c["fg_text"], font=(UI_FONT, 9))
        style.map("Header.TCheckbutton", background=[("active", self.c["panel_header"])])
        style.configure("Deck.TCheckbutton", background=self.c["deck"], foreground=self.c["fg_text"], font=(UI_FONT, 9))
        style.map("Deck.TCheckbutton", background=[("active", self.c["deck"])])
        style.configure("Card.TCheckbutton", background=self.c["card"], foreground=self.c["fg_text"], font=(UI_FONT, 9))
        style.map("Card.TCheckbutton", background=[("active", self.c["card"])])

        # Scale (Timeline Scrubber)
        style.configure(
            "Horizontal.TScale",
            background=self.c["deck"],
            troughcolor=self.c["well"],
            bordercolor=self.c["border"],
            sliderthickness=14,
        )

        # Treeview
        style.configure(
            "Treeview",
            background=self.c["panel"],
            foreground=self.c["fg_text"],
            fieldbackground=self.c["panel"],
            rowheight=28,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=self.c["panel_header"],
            foreground=self.c["fg_muted"],
            relief="flat",
            font=(UI_FONT, 9, "bold"),
            padding=(8, 6),
        )
        style.map("Treeview", background=[("selected", self.c["select_bg"])], foreground=[("selected", "#ffffff")])

        # Scrollbar & PanedWindow
        style.configure(
            "TScrollbar",
            background=self.c["card_hover"],
            troughcolor=self.c["panel"],
            bordercolor=self.c["panel"],
            arrowcolor=self.c["fg_muted"],
            relief="flat",
        )
        style.map("TScrollbar", background=[("active", self.c["border_light"])])
        style.configure("TPanedwindow", background=self.c["bg_root"], borderwidth=0)

    def _create_hairline_card(self, parent, padding=12):
        """Cria um cartão com borda fina de 1px estilo macOS / DaVinci Resolve."""
        outer = tk.Frame(parent, bg=self.c["border"], padx=1, pady=1)
        inner = ttk.Frame(outer, style="Card.TFrame", padding=padding)
        inner.pack(fill="both", expand=True)
        return outer, inner

    # ------------------------------------------------------------------
    # Interface Principal (macOS Topbar + 3 Painéis Resolve + Page Dock)
    # ------------------------------------------------------------------
    def _build_ui(self):
        # 1. Barra Superior Unificada (macOS Toolbar)
        titlebar = ttk.Frame(self.root, style="Titlebar.TFrame", padding=(14, 8))
        titlebar.pack(fill="x")

        # Esquerda: Semáforo macOS + Identidade + Seletor de Perfil
        left_tb = ttk.Frame(titlebar, style="Titlebar.TFrame")
        left_tb.pack(side="left")

        dots = tk.Canvas(left_tb, width=44, height=16, bg=self.c["titlebar"], highlightthickness=0)
        dots.pack(side="left", padx=(0, 8))
        dots.create_oval(2, 3, 12, 13, fill="#ff5f56", outline="")
        dots.create_oval(17, 3, 27, 13, fill="#ffbd2e", outline="")
        dots.create_oval(32, 3, 42, 13, fill="#27c93f", outline="")

        ttk.Label(left_tb, text="Preset Studio", style="Title.TLabel").pack(side="left", padx=(0, 12))

        tk.Frame(left_tb, bg=self.c["border_light"], width=1, height=20).pack(side="left", padx=(0, 12))

        self.profile_var = tk.StringVar(value=self.current_profile_name)
        self.profile_combo = ttk.Combobox(
            left_tb,
            textvariable=self.profile_var,
            values=list(self.profiles.keys()),
            state="readonly",
            width=24,
        )
        self.profile_combo.pack(side="left", padx=(0, 6))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_changed)

        ttk.Button(left_tb, text="+ App", style="Ghost.TButton", command=self._add_new_profile).pack(side="left", padx=2)
        ttk.Button(left_tb, text="Pasta", style="Ghost.TButton", command=self._change_profile_folder).pack(side="left", padx=2)
        ttk.Button(left_tb, text="Modelo", style="Ghost.TButton", command=self._save_current_as_template).pack(side="left", padx=2)

        # Centro: Pílula de Arquivo Ativo (macOS Document Pill)
        self.doc_pill_var = tk.StringVar(value="Nenhum arquivo selecionado")
        doc_pill = tk.Frame(
            titlebar,
            bg=self.c["well"],
            highlightbackground=self.c["border"],
            highlightthickness=1,
            padx=14,
            pady=4,
        )
        doc_pill.pack(side="left", expand=True, padx=16)
        tk.Label(
            doc_pill,
            textvariable=self.doc_pill_var,
            bg=self.c["well"],
            fg=self.c["fg_text"],
            font=(UI_FONT, 9, "bold"),
        ).pack()

        # Direita: Ações Principais
        right_tb = ttk.Frame(titlebar, style="Titlebar.TFrame")
        right_tb.pack(side="right")

        ttk.Button(right_tb, text="+ Novo", style="TButton", command=self._create_new_preset).pack(side="left", padx=3)
        ttk.Button(right_tb, text="Duplicar", style="TButton", command=self._duplicate_preset).pack(side="left", padx=3)
        ttk.Button(right_tb, text="Importar", style="TButton", command=self._import_preset).pack(side="left", padx=3)
        ttk.Button(right_tb, text="Validar", style="TButton", command=self._validate_current_json).pack(side="left", padx=3)
        ttk.Button(right_tb, text="Salvar", style="Accent.TButton", command=self._save_current_file).pack(side="left", padx=(6, 0))

        tk.Frame(self.root, bg=self.c["border"], height=1).pack(fill="x")

        # 2. Área Principal de Trabalho (Media Pool à esquerda + Páginas Resolve à direita)
        main_paned = ttk.PanedWindow(self.root, orient="horizontal")
        main_paned.pack(fill="both", expand=True)

        # --- Painel Esquerdo: BIBLIOTECA / MEDIA POOL ---
        left_wrap = tk.Frame(main_paned, bg=self.c["border"], width=265)
        main_paned.add(left_wrap, weight=1)

        left_panel = ttk.Frame(left_wrap, style="Panel.TFrame")
        left_panel.pack(fill="both", expand=True, padx=(0, 1))

        lib_header = ttk.Frame(left_panel, style="PanelHeader.TFrame", padding=(12, 7))
        lib_header.pack(fill="x")
        ttk.Label(lib_header, text="BIBLIOTECA DE PRESETS", style="SectionTag.TLabel").pack(side="left")

        tk.Frame(left_panel, bg=self.c["border"], height=1).pack(fill="x")

        lib_body = ttk.Frame(left_panel, style="Panel.TFrame", padding=10)
        lib_body.pack(fill="both", expand=True)

        # Busca estilo macOS
        search_row = ttk.Frame(lib_body, style="Panel.TFrame")
        search_row.pack(fill="x", pady=(0, 8))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_file_list())
        search_ent = ttk.Entry(search_row, textvariable=self.search_var)
        search_ent.pack(side="left", fill="x", expand=True)

        ttk.Button(search_row, text="↻", width=3, style="Ghost.TButton", command=self._refresh_file_list).pack(
            side="right", padx=(5, 0)
        )

        # Lista de arquivos com borda fina (sem padx/pady no Listbox!)
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
        ttk.Button(file_actions, text="Renomear", command=self._rename_file).pack(
            side="left", fill="x", expand=True, padx=(0, 3)
        )
        ttk.Button(file_actions, text="Excluir", style="Danger.TButton", command=self._delete_file).pack(
            side="right", fill="x", expand=True, padx=(3, 0)
        )

        self.folder_info_label = ttk.Label(lib_body, text="", style="Muted.TLabel", wraplength=240, font=(UI_FONT, 8))
        self.folder_info_label.pack(anchor="w", pady=(4, 0))

        # --- Container das Páginas à Direita ---
        self.workspace_host = ttk.Frame(main_paned, style="Root.TFrame")
        main_paned.add(self.workspace_host, weight=5)

        # Página 1: STUDIO (Viewer Central + Inspetor à Direita)
        self.page_studio = ttk.PanedWindow(self.workspace_host, orient="horizontal")

        center_wrap = tk.Frame(self.page_studio, bg=self.c["border"], width=620)
        self.page_studio.add(center_wrap, weight=3)

        center_panel = ttk.Frame(center_wrap, style="Panel.TFrame")
        center_panel.pack(fill="both", expand=True, padx=(0, 1))

        self.preview_widget = ResolveViewerWidget(center_panel, self.c)
        self.preview_widget.pack(fill="both", expand=True)
        self.preview_widget.time_listener = self._on_viewer_time_changed

        right_inspector = ttk.Frame(self.page_studio, style="Panel.TFrame", width=440)
        self.page_studio.add(right_inspector, weight=2)

        insp_header = ttk.Frame(right_inspector, style="PanelHeader.TFrame", padding=(12, 7))
        insp_header.pack(fill="x")
        ttk.Label(insp_header, text="INSPETOR", style="SectionTag.TLabel").pack(side="left")
        ttk.Label(insp_header, text="Parâmetros & Keyframes", style="HeaderMuted.TLabel").pack(side="right")

        tk.Frame(right_inspector, bg=self.c["border"], height=1).pack(fill="x")

        self.visual_scroll = ScrollableFrame(right_inspector, bg_color=self.c["panel"])
        self.visual_scroll.pack(fill="both", expand=True)

        # Página 2: ÁRVORE JSON UNIVERSAL
        self.page_tree = ttk.Frame(self.workspace_host, style="Panel.TFrame")
        self._build_tree_tab()

        # Página 3: CÓDIGO JSON BRUTO
        self.page_raw = ttk.Frame(self.workspace_host, style="Panel.TFrame")
        self._build_raw_tab()

        # Exibe página inicial
        self.page_studio.pack(fill="both", expand=True)

        # 3. Dock Inferior estilo DaVinci Resolve Page Switcher + Status
        tk.Frame(self.root, bg=self.c["border"], height=1).pack(fill="x")

        bottom_dock = ttk.Frame(self.root, style="Dock.TFrame", padding=(14, 6))
        bottom_dock.pack(fill="x", side="bottom")

        # Status à esquerda
        status_left = ttk.Frame(bottom_dock, style="Dock.TFrame")
        status_left.pack(side="left", fill="x", expand=True)

        self.status_dot = tk.Label(
            status_left, text="●", bg=self.c["titlebar"], fg=self.c["success"], font=(UI_FONT, 9)
        )
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_var = tk.StringVar(value="Pronto. Selecione ou crie um preset .json.")
        tk.Label(
            status_left,
            textvariable=self.status_var,
            bg=self.c["titlebar"],
            fg=self.c["fg_muted"],
            font=(UI_FONT, 9),
            anchor="w",
        ).pack(side="left")

        # Page Switcher Central (DaVinci Resolve style)
        switcher = tk.Frame(
            bottom_dock,
            bg=self.c["well"],
            highlightbackground=self.c["border"],
            highlightthickness=1,
            padx=3,
            pady=3,
        )
        switcher.pack(side="left", padx=12)

        self.page_buttons = {}
        pages_meta = [
            ("studio", "🎛  Inspetor & Viewer"),
            ("tree", "🌲  Árvore JSON"),
            ("raw", "</>  Código JSON"),
        ]
        for key, label in pages_meta:
            btn = tk.Label(
                switcher,
                text=label,
                bg=self.c["well"],
                fg=self.c["fg_muted"],
                font=(UI_FONT, 9, "bold"),
                padx=12,
                pady=3,
                cursor="hand2",
            )
            btn.pack(side="left", padx=2)
            btn.bind("<Button-1>", lambda _e, k=key: self._switch_page(k))
            self.page_buttons[key] = btn

        # Atalhos à direita
        tk.Label(
            bottom_dock,
            text="Ctrl+S Salvar  •  Ctrl+N Novo  •  Espaço Play/Pause  •  ← → Quadro",
            bg=self.c["titlebar"],
            fg=self.c["fg_faint"],
            font=(UI_FONT, 8),
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
            if key == self.current_page:
                btn.config(bg=self.c["card_hover"], fg=self.c["accent"])
            else:
                btn.config(bg=self.c["well"], fg=self.c["fg_muted"])

    def _build_tree_tab(self):
        header = ttk.Frame(self.page_tree, style="PanelHeader.TFrame", padding=(14, 8))
        header.pack(fill="x")

        ttk.Label(header, text="ESTRUTURA UNIVERSAL JSON", style="SectionTag.TLabel").pack(side="left")
        ttk.Label(header, text="Duplo clique em qualquer folha para editar", style="HeaderMuted.TLabel").pack(
            side="left", padx=(12, 0)
        )

        actions = ttk.Frame(header, style="PanelHeader.TFrame")
        actions.pack(side="right")
        ttk.Button(actions, text="Editar Valor", command=self._tree_edit_selected).pack(side="left", padx=3)
        ttk.Button(actions, text="+ Chave / Item", command=self._tree_add_node).pack(side="left", padx=3)
        ttk.Button(actions, text="Remover", style="Danger.TButton", command=self._tree_delete_node).pack(side="left", padx=3)

        tk.Frame(self.page_tree, bg=self.c["border"], height=1).pack(fill="x")

        tree_container = ttk.Frame(self.page_tree, style="Panel.TFrame", padding=12)
        tree_container.pack(fill="both", expand=True)

        border_box = tk.Frame(tree_container, bg=self.c["border"], padx=1, pady=1)
        border_box.pack(fill="both", expand=True)

        inner_box = ttk.Frame(border_box, style="Panel.TFrame")
        inner_box.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(inner_box, columns=("type", "value"), show="tree headings")
        self.tree.heading("#0", text="Chave / Índice", anchor="w")
        self.tree.heading("type", text="Tipo", anchor="center")
        self.tree.heading("value", text="Valor", anchor="w")
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

        ttk.Label(header, text="CÓDIGO FONTE JSON", style="SectionTag.TLabel").pack(side="left")
        ttk.Label(header, text="Edite o JSON diretamente e clique em Aplicar", style="HeaderMuted.TLabel").pack(
            side="left", padx=(12, 0)
        )

        actions = ttk.Frame(header, style="PanelHeader.TFrame")
        actions.pack(side="right")
        ttk.Button(actions, text="Formatar JSON", command=self._format_raw_json).pack(side="left", padx=3)
        ttk.Button(
            actions,
            text="Aplicar ao Viewer & Inspetor",
            style="Accent.TButton",
            command=self._apply_raw_json_to_model,
        ).pack(side="left", padx=3)

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

    # Widgets que usam as setas por conta própria (digitação, listas, árvore...)
    _ARROW_PASSTHROUGH = {
        "Entry", "TEntry", "Text", "TCombobox", "Spinbox", "TSpinbox",
        "Listbox", "Treeview", "Scale", "TScale",
    }

    def _on_timeline_key(self, event):
        """←/→ = 1 quadro • Shift = 10 quadros • Ctrl = keyframe anterior/próximo • Home/End = início/fim."""
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
        if isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)):
            return
        self.preview_widget.toggle_play()

    # ------------------------------------------------------------------
    # Perfis e Arquivos
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
        app_name = simpledialog.askstring("Novo Aplicativo", "Nome do aplicativo (ex: OBS, EasyEffects, Godot):", parent=self.root)
        if not app_name or not app_name.strip():
            return
        app_name = app_name.strip()

        folder = filedialog.askdirectory(title=f"Selecione a pasta de presets para {app_name}")
        if not folder:
            return

        is_fc = messagebox.askyesno(
            "Tipo de Esquema",
            "Este aplicativo usa a estrutura do Filmcraft (filmcraft.effect-presets)?\n\n"
            "Clique em 'Sim' para usar o modelo do Filmcraft ou 'Não' para JSON genérico.",
        )

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
        self._set_status(f"Perfil '{app_name}' criado com sucesso.")

    def _change_profile_folder(self):
        new_folder = filedialog.askdirectory(
            title="Escolher pasta de presets",
            initialdir=self.active_profile.get("folder", str(Path.home())),
        )
        if new_folder:
            self.active_profile["folder"] = new_folder
            self._save_profiles()
            self._refresh_file_list()
            self._set_status(f"Pasta atualizada para: {new_folder}")

    def _save_current_as_template(self):
        if self.current_data is None:
            messagebox.showinfo("Aviso", "Abra um arquivo de preset antes de defini-lo como modelo.")
            return
        self.active_profile["template"] = copy.deepcopy(self.current_data)
        self._save_profiles()
        self._set_status(f"Modelo padrão do perfil '{self.current_profile_name}' atualizado!")

    def _refresh_file_list(self):
        folder = Path(self.active_profile["folder"])
        folder.mkdir(parents=True, exist_ok=True)
        self.folder_info_label.config(text=f"📁 {folder}")

        query = self.search_var.get().strip().lower()
        self.file_listbox.delete(0, tk.END)

        files = sorted(folder.glob("*.json"), key=lambda p: p.name.lower())
        for idx, f in enumerate(files):
            if not query or query in f.name.lower():
                self.file_listbox.insert(tk.END, f"  {f.name}")
                if self.current_file_path and f == self.current_file_path:
                    self.file_listbox.selection_set(tk.END)

    def _on_file_select(self, _event=None):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        filename = self.file_listbox.get(sel[0]).strip()
        filepath = Path(self.active_profile["folder"]) / filename
        self._load_file(filepath)

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
            self._set_status(f"Carregado: {filepath.name}")
        except Exception as e:
            messagebox.showerror("Erro ao abrir JSON", f"Não foi possível ler '{filepath.name}':\n{e}")

    def _create_new_preset(self):
        is_filmcraft = self.active_profile.get("schema_type") == "filmcraft"

        win = tk.Toplevel(self.root)
        win.title("Novo Preset")
        win.geometry("440x230" if is_filmcraft else "440x160")
        win.configure(bg=self.c["panel"])
        win.transient(self.root)
        win.grab_set()

        ttk.Label(win, text="Nome do arquivo / preset (sem .json):", padding=(16, 14, 16, 4)).pack(anchor="w")
        name_var = tk.StringVar(value="Novo_Preset")
        ent = ttk.Entry(win, textvariable=name_var, width=42)
        ent.pack(padx=16, fill="x")
        ent.select_range(0, tk.END)
        ent.focus_set()

        kind_var = tk.StringVar(value="motion")
        if is_filmcraft:
            ttk.Label(win, text="Tipo de Preset do Filmcraft:", padding=(16, 10, 16, 4)).pack(anchor="w")
            kind_cb = ttk.Combobox(
                win,
                textvariable=kind_var,
                values=[
                    "Movimento / Animação (motion)",
                    "Texto / Legenda (graphic_text)",
                    "Modelo Salvo do Perfil",
                ],
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
                messagebox.showwarning("Arquivo existente", f"O arquivo '{filename}' já existe nesta pasta.", parent=win)
                return

            if is_filmcraft:
                choice = kind_var.get()
                if choice.startswith("Movimento"):
                    new_data = copy.deepcopy(FILMCRAFT_MOTION_TEMPLATE)
                elif choice.startswith("Texto"):
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
            self._set_status(f"Novo preset criado: {filename}")

        btn_row = ttk.Frame(win, padding=16)
        btn_row.pack(fill="x", side="bottom")
        ttk.Button(btn_row, text="Cancelar", command=win.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(btn_row, text="Criar Preset", style="Accent.TButton", command=confirm).pack(side="right")
        win.bind("<Return>", lambda _e: confirm())

    def _duplicate_preset(self):
        if not self.current_file_path or self.current_data is None:
            messagebox.showinfo("Aviso", "Selecione um preset para duplicar.")
            return

        base_stem = self.current_file_path.stem
        new_name = simpledialog.askstring(
            "Duplicar Preset",
            "Nome da cópia:",
            initialvalue=f"{base_stem}_copia",
            parent=self.root,
        )
        if not new_name or not new_name.strip():
            return

        filename = new_name.strip()
        if not filename.endswith(".json"):
            filename += ".json"

        target_path = self.current_file_path.parent / filename
        if target_path.exists():
            messagebox.showwarning("Arquivo existente", f"Já existe um arquivo chamado '{filename}'.")
            return

        dup_data = copy.deepcopy(self.current_data)
        if isinstance(dup_data, dict) and "presets" in dup_data and dup_data["presets"]:
            dup_data["presets"][0]["name"] = Path(filename).stem

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(dup_data, f, indent=2, ensure_ascii=False)

        self._refresh_file_list()
        self._load_file(target_path)
        self._set_status(f"Preset duplicado para: {filename}")

    def _import_preset(self):
        src = filedialog.askopenfilename(
            title="Importar arquivo .json de preset",
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os arquivos", "*.*")],
        )
        if not src:
            return
        src_path = Path(src)
        try:
            with open(src_path, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception as e:
            messagebox.showerror("JSON Inválido", f"O arquivo selecionado não é um JSON válido:\n{e}")
            return

        dest_path = Path(self.active_profile["folder"]) / src_path.name
        if dest_path.exists():
            if not messagebox.askyesno("Sobrescrever?", f"'{src_path.name}' já existe na pasta. Deseja substituir?"):
                return

        shutil.copy2(src_path, dest_path)
        self._refresh_file_list()
        self._load_file(dest_path)
        self._set_status(f"Importado com sucesso: {src_path.name}")

    def _rename_file(self):
        if not self.current_file_path:
            return
        new_name = simpledialog.askstring(
            "Renomear Arquivo",
            "Novo nome do arquivo:",
            initialvalue=self.current_file_path.stem,
            parent=self.root,
        )
        if not new_name or not new_name.strip():
            return
        filename = new_name.strip()
        if not filename.endswith(".json"):
            filename += ".json"
        new_path = self.current_file_path.parent / filename
        if new_path.exists():
            messagebox.showwarning("Erro", "Já existe um arquivo com esse nome.")
            return
        self.current_file_path.rename(new_path)
        self.current_file_path = new_path
        self._update_doc_pill()
        self._refresh_file_list()
        self._set_status(f"Renomeado para: {filename}")

    def _delete_file(self):
        if not self.current_file_path:
            return
        if not messagebox.askyesno("Excluir Preset", f"Tem certeza que deseja excluir '{self.current_file_path.name}'?"):
            return
        deleted_name = self.current_file_path.name
        self.current_file_path.unlink(missing_ok=True)
        self.current_file_path = None
        self.current_data = None
        self.modified = False
        self._update_doc_pill()
        self._refresh_file_list()
        self._render_all_views(reset_preview=True)
        self._set_status(f"Arquivo excluído: {deleted_name}")

    def _save_current_file(self):
        if not self.current_file_path or self.current_data is None:
            messagebox.showinfo("Aviso", "Nenhum arquivo aberto para salvar.")
            return

        if self.current_page == "raw":
            if not self._apply_raw_json_to_model(silent=True):
                return

        try:
            if self.current_file_path.exists():
                bak_path = self.current_file_path.with_suffix(".json.bak")
                shutil.copy2(self.current_file_path, bak_path)

            with open(self.current_file_path, "w", encoding="utf-8") as f:
                json.dump(self.current_data, f, indent=2, ensure_ascii=False)

            self.modified = False
            self._update_doc_pill()
            self._set_status(f"Salvo: {self.current_file_path.name} (backup .bak atualizado)")
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Falha ao gravar arquivo:\n{e}")

    def _validate_current_json(self):
        if self.current_data is None:
            messagebox.showinfo("Validação", "Nenhum arquivo carregado.")
            return

        if self.current_page == "raw":
            if not self._apply_raw_json_to_model(silent=True):
                return

        issues = []
        if isinstance(self.current_data, dict) and (
            self.active_profile.get("schema_type") == "filmcraft"
            or self.current_data.get("format") == "filmcraft.effect-presets"
        ):
            if self.current_data.get("format") != "filmcraft.effect-presets":
                issues.append("- Campo obrigatório 'format' ausente ou diferente de 'filmcraft.effect-presets'.")
            if "version" not in self.current_data:
                issues.append("- Campo 'version' ausente (recomendado: 1).")
            presets = self.current_data.get("presets")
            if not isinstance(presets, list) or len(presets) == 0:
                issues.append("- Lista 'presets' ausente ou vazia.")
            else:
                for i, p in enumerate(presets):
                    if "name" not in p:
                        issues.append(f"- Preset [{i}] sem campo 'name'.")
                    if "effects" not in p or not isinstance(p["effects"], list):
                        issues.append(f"- Preset [{i}] sem lista 'effects'.")

        if issues:
            messagebox.showwarning("Problemas Encontrados", "Foram detectados avisos no esquema:\n\n" + "\n".join(issues))
        else:
            messagebox.showinfo("JSON Válido", "A estrutura JSON e todos os campos obrigatórios estão válidos!")

    # ------------------------------------------------------------------
    # Sincronização e Renderização do Inspetor + Viewer
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
            ttk.Label(
                container,
                text="Nenhum preset ativo.\nSelecione um arquivo na Biblioteca à esquerda ou clique em '+ Novo'.",
                style="Muted.TLabel",
                padding=20,
            ).pack(anchor="w")
            return

        if self._is_filmcraft_data():
            self._render_filmcraft_editor(container)
        else:
            self._render_generic_visual_editor(container)

    def _render_filmcraft_editor(self, parent):
        presets = self.current_data["presets"]
        if not presets:
            ttk.Label(parent, text="Este arquivo Filmcraft não possui presets na lista.", padding=15).pack(anchor="w")
            return

        if self.selected_preset_idx >= len(presets):
            self.selected_preset_idx = 0

        preset = presets[self.selected_preset_idx]

        # Cartão 1: Variações no Arquivo
        outer1, top_card = self._create_hairline_card(parent, padding=10)
        outer1.pack(fill="x", padx=10, pady=(10, 6))

        ttk.Label(top_card, text="VARIAÇÃO DO PRESET", style="CardSection.TLabel").pack(anchor="w", pady=(0, 6))

        var_row = ttk.Frame(top_card, style="Card.TFrame")
        var_row.pack(fill="x")

        preset_names = [f"[{i}] {p.get('name', 'Sem nome')}" for i, p in enumerate(presets)]
        p_combo = ttk.Combobox(var_row, values=preset_names, state="readonly")
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
            clone["name"] = f"{preset.get('name', 'Preset')} (Novo)"
            presets.append(clone)
            self.selected_preset_idx = len(presets) - 1
            self._mark_modified()
            self._render_all_views(reset_preview=True)

        def del_subpreset():
            if len(presets) <= 1:
                messagebox.showinfo("Aviso", "O arquivo precisa manter pelo menos 1 preset.")
                return
            presets.pop(self.selected_preset_idx)
            self.selected_preset_idx = max(0, self.selected_preset_idx - 1)
            self._mark_modified()
            self._render_all_views(reset_preview=True)

        ttk.Button(var_row, text="+", width=3, command=add_subpreset).pack(side="left", padx=2)
        ttk.Button(var_row, text="✕", width=3, style="Danger.TButton", command=del_subpreset).pack(side="left", padx=(2, 0))

        # Cartão 2: Metadados & Resolução
        outer2, meta_card = self._create_hairline_card(parent, padding=10)
        outer2.pack(fill="x", padx=10, pady=6)

        ttk.Label(meta_card, text="PROPRIEDADES & RESOLUÇÃO", style="CardSection.TLabel").pack(anchor="w", pady=(0, 8))

        meta_grid = ttk.Frame(meta_card, style="Card.TFrame")
        meta_grid.pack(fill="x")
        meta_grid.columnconfigure(1, weight=1)

        ttk.Label(meta_grid, text="Nome", style="CardMuted.TLabel", width=15).grid(row=0, column=0, sticky="w", pady=4)
        name_var = tk.StringVar(value=str(preset.get("name", "")))
        ttk.Entry(meta_grid, textvariable=name_var).grid(row=0, column=1, sticky="ew", pady=4)
        name_var.trace_add("write", lambda *_: self._set_dict_val(preset, "name", name_var.get()))

        ttk.Label(meta_grid, text="Keyframes Tag", style="CardMuted.TLabel", width=15).grid(row=1, column=0, sticky="w", pady=4)
        kf_var = tk.StringVar(value=str(preset.get("keyframes", "")))
        ttk.Entry(meta_grid, textvariable=kf_var).grid(row=1, column=1, sticky="ew", pady=4)
        kf_var.trace_add("write", lambda *_: self._set_dict_val(preset, "keyframes", kf_var.get()))

        src_size = preset.get("source_size", [1920, 1080])
        w_val = src_size[0] if isinstance(src_size, list) and len(src_size) >= 2 else 1920
        h_val = src_size[1] if isinstance(src_size, list) and len(src_size) >= 2 else 1080

        ttk.Label(meta_grid, text="Resolução Base", style="CardMuted.TLabel", width=15).grid(row=2, column=0, sticky="w", pady=4)
        res_frame = ttk.Frame(meta_grid, style="Card.TFrame")
        res_frame.grid(row=2, column=1, sticky="w", pady=4)

        w_var = tk.StringVar(value=str(w_val))
        h_var = tk.StringVar(value=str(h_val))
        ttk.Entry(res_frame, textvariable=w_var, width=6).pack(side="left")
        ttk.Label(res_frame, text=" × ", style="CardMuted.TLabel").pack(side="left")
        ttk.Entry(res_frame, textvariable=h_var, width=6).pack(side="left")

        def apply_resolution_scale():
            try:
                new_w = int(w_var.get())
                new_h = int(h_var.get())
                if new_w <= 0 or new_h <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Erro", "Informe largura e altura válidas (números inteiros positivos).")
                return

            old_size = preset.get("source_size", [1920, 1080])
            old_w = old_size[0] if old_size[0] else 1920
            old_h = old_size[1] if old_size[1] else 1080
            scale_x = new_w / old_w
            scale_y = new_h / old_h

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
            self._set_status(f"Resolução ajustada para {new_w}×{new_h} com coordenadas recalculadas.")

        ttk.Button(res_frame, text="Escalar", command=apply_resolution_scale).pack(side="left", padx=(6, 0))

        # Cartão 3: Controles do Efeito (Inspetor)
        effects = preset.get("effects", [])
        if not effects:
            return

        if self.selected_effect_idx >= len(effects):
            self.selected_effect_idx = 0
        effect = effects[self.selected_effect_idx]

        outer3, eff_card = self._create_hairline_card(parent, padding=10)
        outer3.pack(fill="x", padx=10, pady=(6, 14))

        eff_top = ttk.Frame(eff_card, style="Card.TFrame")
        eff_top.pack(fill="x", pady=(0, 8))

        ttk.Label(eff_top, text="EFEITO ATIVO", style="CardSection.TLabel").pack(side="left")

        enabled_var = tk.BooleanVar(value=bool(effect.get("enabled", True)))
        ttk.Checkbutton(
            eff_top,
            text="Habilitado",
            style="Card.TCheckbutton",
            variable=enabled_var,
            command=lambda: self._set_dict_val(effect, "enabled", enabled_var.get(), refresh_preview=True),
        ).pack(side="right")

        eff_names = [f"[{i}] {e.get('effect', 'desconhecido')}" for i, e in enumerate(effects)]
        eff_combo = ttk.Combobox(eff_card, values=eff_names, state="readonly")
        eff_combo.current(self.selected_effect_idx)
        eff_combo.pack(fill="x", pady=(0, 10))

        def on_eff_switch(_e):
            self.selected_effect_idx = eff_combo.current()
            self._render_visual_editor()

        eff_combo.bind("<<ComboboxSelected>>", on_eff_switch)

        tk.Frame(eff_card, bg=self.c["border"], height=1).pack(fill="x", pady=(0, 8))

        params = effect.get("params", {})
        grid_frame = ttk.Frame(eff_card, style="Card.TFrame")
        grid_frame.pack(fill="x")
        grid_frame.columnconfigure(1, weight=1)

        priority_keys = [
            "text",
            "font",
            "font_style",
            "caps",
            "size",
            "position",
            "scale",
            "scale_width",
            "uniform_scale",
            "rotation",
            "anchor",
            "anti_flicker",
            "fill",
            "fill_color",
            "stroke",
            "stroke_color",
            "stroke_width",
            "background",
            "background_color",
            "background_opacity",
            "background_size",
            "shadow",
            "shadow_color",
            "shadow_distance",
            "opacity",
        ]
        ordered_keys = [k for k in priority_keys if k in params] + [k for k in sorted(params.keys()) if k not in priority_keys]

        for row_idx, key in enumerate(ordered_keys):
            param_obj = params[key]
            if not isinstance(param_obj, dict) or "value" not in param_obj:
                continue

            val_wrapper = param_obj["value"]
            if not isinstance(val_wrapper, dict) or not val_wrapper:
                continue

            type_tag = next(iter(val_wrapper.keys()))
            raw_val = val_wrapper[type_tag]

            has_kf = "keyframes" in param_obj and isinstance(param_obj["keyframes"], list) and len(param_obj["keyframes"]) > 0
            label_text = f"{key}" + (f" ({len(param_obj['keyframes'])})" if has_kf else "")
            name_lbl = ttk.Label(grid_frame, text=label_text, style="CardMuted.TLabel", width=18)
            name_lbl.grid(row=row_idx, column=0, sticky="w", pady=4, padx=(0, 6))
            self._param_labels[id(param_obj)] = (name_lbl, key)

            self._build_filmcraft_param_widget(grid_frame, row_idx, key, val_wrapper, type_tag, raw_val, param_obj)

        # Mostra já os valores animados do instante atual
        self._refresh_live_params()

    def _build_filmcraft_param_widget(self, parent, row, key, val_wrapper, type_tag, raw_val, param_obj):
        row_box = ttk.Frame(parent, style="Card.TFrame")
        row_box.grid(row=row, column=1, sticky="ew", pady=3)

        if type_tag == "Bool":
            var = tk.BooleanVar(value=bool(raw_val))
            cb = ttk.Checkbutton(
                row_box,
                text="Ativo" if raw_val else "Inativo",
                style="Card.TCheckbutton",
                variable=var,
                command=lambda: (
                    self._set_dict_val(val_wrapper, "Bool", var.get(), refresh_preview=True),
                    cb.config(text="Ativo" if var.get() else "Inativo"),
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
                txt = var.get().strip()
                try:
                    parsed = int(txt) if type_tag == "Choice" else float(txt)
                except ValueError:
                    return
                if type_tag == "Float" and param_obj.get("keyframes"):
                    # Parâmetro animado: grava no keyframe sob o cursor (cria se não houver)
                    self._write_keyframed_value(param_obj, "Float", parsed)
                else:
                    self._set_dict_val(val_wrapper, type_tag, parsed, refresh_preview=True)

            var.trace_add("write", on_num_change)

            if type_tag == "Float":

                def refresh_float(t_ns, playing, var=var, entry=num_entry):
                    if not param_obj.get("keyframes"):
                        return
                    if not playing and self._has_focus(entry):
                        return
                    val = evaluate_filmcraft_param(param_obj, t_ns)
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        self._set_var_quiet(var, self._fmt_num(val), float(val))

                self._live_params.append(refresh_float)

        elif type_tag == "Color":
            hex_code = rgba_float_to_hex(raw_val)
            swatch = tk.Label(
                row_box,
                bg=hex_code,
                width=3,
                relief="flat",
                highlightthickness=1,
                highlightbackground=self.c["border_light"],
                cursor="hand2",
            )
            swatch.pack(side="left", padx=(0, 6))

            info_lbl = ttk.Label(row_box, text=hex_code.upper(), style="Card.TLabel", font=(MONO_FONT, 9))

            def pick_color():
                chosen = colorchooser.askcolor(color=rgba_float_to_hex(val_wrapper["Color"]), title="Selecionar Cor")
                if chosen and chosen[1]:
                    alpha = val_wrapper["Color"][3] if len(val_wrapper["Color"]) >= 4 else 1.0
                    new_rgba = hex_to_rgba_float(chosen[1], alpha)
                    val_wrapper["Color"] = new_rgba
                    swatch.config(bg=chosen[1])
                    info_lbl.config(text=chosen[1].upper())
                    self._mark_modified()
                    self.preview_widget.render_frame()

            swatch.bind("<Button-1>", lambda _e: pick_color())
            ttk.Button(row_box, text="Cor", width=4, command=pick_color).pack(side="left", padx=(0, 6))
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
                    nx = float(x_var.get())
                    ny = float(y_var.get())
                except ValueError:
                    return
                if param_obj.get("keyframes"):
                    self._write_keyframed_value(param_obj, "Vec2", {"x": nx, "y": ny})
                else:
                    raw_val["x"] = nx
                    raw_val["y"] = ny
                    self._mark_modified()
                    self.preview_widget.render_frame()

            x_var.trace_add("write", on_vec_change)
            y_var.trace_add("write", on_vec_change)

            def refresh_vec(t_ns, playing):
                if not param_obj.get("keyframes"):
                    return
                if not playing and (self._has_focus(x_entry) or self._has_focus(y_entry)):
                    return
                val = evaluate_filmcraft_param(param_obj, t_ns)
                if isinstance(val, dict):
                    nx = float(val.get("x", 0.0))
                    ny = float(val.get("y", 0.0))
                    self._set_var_quiet(x_var, self._fmt_num(nx), nx)
                    self._set_var_quiet(y_var, self._fmt_num(ny), ny)

            self._live_params.append(refresh_vec)

        else:
            ttk.Label(row_box, text=json.dumps(raw_val), style="CardMuted.TLabel").pack(side="left")

        # Diamante de Keyframe estilo DaVinci Resolve (◆ ativo / ◇ estático)
        if type_tag in ("Float", "Vec2"):
            has_kf = isinstance(param_obj.get("keyframes"), list) and len(param_obj["keyframes"]) > 0
            btn_txt = "◆" if has_kf else "◇"
            btn_style = "KeyframeOn.TButton" if has_kf else "KeyframeOff.TButton"
            ttk.Button(
                row_box,
                text=btn_txt,
                width=2,
                style=btn_style,
                command=lambda k=key, p=param_obj, t=type_tag: self._open_keyframes_editor(k, p, t),
            ).pack(side="right", padx=(6, 0))

    def _open_keyframes_editor(self, param_name, param_obj, type_tag):
        win = tk.Toplevel(self.root)
        win.title(f"Keyframes — {param_name} ({type_tag})")
        win.geometry("640x400")
        win.configure(bg=self.c["panel"])
        win.transient(self.root)

        if not isinstance(param_obj.get("keyframes"), list) or len(param_obj["keyframes"]) == 0:
            base_val = copy.deepcopy(param_obj["value"][type_tag])
            param_obj["keyframes"] = [
                {
                    "time": 0,
                    "value": {type_tag: copy.deepcopy(base_val)},
                    "interp": "AutoBezier",
                    "out_influence": 0.3333333333333333,
                    "in_influence": 0.3333333333333333,
                },
                {
                    "time": 1500000000,
                    "value": {type_tag: copy.deepcopy(base_val)},
                    "interp": "ContinuousBezier",
                    "out_influence": 0.3333333333333333,
                    "in_influence": 0.3333333333333333,
                },
            ]
            self._mark_modified()
            self._sync_preview(reset_time=False)

        top_info = ttk.Frame(win, style="PanelHeader.TFrame", padding=(14, 10))
        top_info.pack(fill="x")
        ttk.Label(top_info, text=f"◆ EDITOR DE KEYFRAMES — {param_name.upper()}", style="SectionTag.TLabel").pack(side="left")

        list_frame = ScrollableFrame(win, bg_color=self.c["panel"])
        list_frame.pack(fill="both", expand=True, padx=10, pady=8)

        def rebuild_rows():
            for w in list_frame.inner.winfo_children():
                w.destroy()

            kfs = param_obj.get("keyframes", [])
            for idx, kf in enumerate(kfs):
                outer, row = self._create_hairline_card(list_frame.inner, padding=8)
                outer.pack(fill="x", pady=4)

                t_sec = kf.get("time", 0) / 1_000_000_000.0
                t_var = tk.StringVar(value=f"{t_sec:.3f}")
                kf_lbl = ttk.Label(row, text=f"◆ #{idx + 1}  Tempo (s):", style="Card.TLabel", cursor="hand2")
                kf_lbl.pack(side="left", padx=(0, 4))
                kf_lbl.bind("<Button-1>", lambda _e, k_item=kf: self._seek_to_keyframe(k_item))
                ttk.Entry(row, textvariable=t_var, width=8).pack(side="left", padx=(0, 8))

                interp_var = tk.StringVar(value=kf.get("interp", "AutoBezier"))
                interp_cb = ttk.Combobox(
                    row,
                    textvariable=interp_var,
                    values=["AutoBezier", "ContinuousBezier", "Linear", "Hold"],
                    state="readonly",
                    width=16,
                )
                interp_cb.pack(side="left", padx=(0, 8))

                val_dict = kf.setdefault("value", {})
                if type_tag == "Float":
                    v_var = tk.StringVar(value=str(val_dict.get("Float", 0.0)))
                    ttk.Label(row, text="Valor:", style="CardMuted.TLabel").pack(side="left")
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
        ttk.Button(bottom, text="+ Adicionar Keyframe", style="Accent.TButton", command=add_kf).pack(side="left")
        ttk.Button(
            bottom,
            text="Concluir",
            command=lambda: (self._render_visual_editor(), win.destroy()),
        ).pack(side="right")

        rebuild_rows()

    def _render_generic_visual_editor(self, parent):
        outer, card = self._create_hairline_card(parent, padding=12)
        outer.pack(fill="x", padx=10, pady=10)

        ttk.Label(card, text="PROPRIEDADES DO PRESET", style="CardSection.TLabel").pack(anchor="w", pady=(0, 10))

        if not isinstance(self.current_data, dict):
            ttk.Label(
                card,
                text="A raiz deste JSON é uma lista/valor simples. Use a página 'Árvore JSON' ou 'Código JSON'.",
                style="Card.TLabel",
            ).pack(anchor="w")
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
                    ttk.Checkbutton(
                        grid,
                        text="Ativado",
                        style="Card.TCheckbutton",
                        variable=bvar,
                        command=lambda k=key, v=bvar: self._set_dict_val(self.current_data, k, v.get()),
                    ).grid(row=row, column=1, sticky="w", pady=4)
                else:
                    svar = tk.StringVar(value=str(val))
                    ttk.Entry(grid, textvariable=svar).grid(row=row, column=1, sticky="ew", pady=4)

                    def make_updater(k, v, orig_type):
                        def _upd(*_):
                            txt = v.get()
                            try:
                                if orig_type is int:
                                    self._set_dict_val(self.current_data, k, int(txt))
                                elif orig_type is float:
                                    self._set_dict_val(self.current_data, k, float(txt))
                                else:
                                    self._set_dict_val(self.current_data, k, txt)
                            except ValueError:
                                pass

                        return _upd

                    svar.trace_add("write", make_updater(key, svar, type(val)))
                row += 1
            elif isinstance(val, dict):
                ttk.Label(grid, text=f"{key.upper()}", style="CardSection.TLabel").grid(
                    row=row, column=0, columnspan=2, sticky="w", pady=(10, 4)
                )
                row += 1
                for sub_k, sub_v in val.items():
                    if isinstance(sub_v, (str, int, float, bool)):
                        ttk.Label(grid, text=f"  {sub_k}", style="CardMuted.TLabel", width=20).grid(
                            row=row, column=0, sticky="w", pady=3
                        )
                        if isinstance(sub_v, bool):
                            sbvar = tk.BooleanVar(value=sub_v)
                            ttk.Checkbutton(
                                grid,
                                text="Ativado",
                                style="Card.TCheckbutton",
                                variable=sbvar,
                                command=lambda d=val, k=sub_k, v=sbvar: self._set_dict_val(d, k, v.get()),
                            ).grid(row=row, column=1, sticky="w", pady=3)
                        else:
                            ssvar = tk.StringVar(value=str(sub_v))
                            ttk.Entry(grid, textvariable=ssvar).grid(row=row, column=1, sticky="ew", pady=3)

                            def make_sub_updater(d, k, v, orig_type):
                                def _upd(*_):
                                    txt = v.get()
                                    try:
                                        if orig_type is int:
                                            self._set_dict_val(d, k, int(txt))
                                        elif orig_type is float:
                                            self._set_dict_val(d, k, float(txt))
                                        else:
                                            self._set_dict_val(d, k, txt)
                                    except ValueError:
                                        pass

                                return _upd

                            ssvar.trace_add("write", make_sub_updater(val, sub_k, ssvar, type(sub_v)))
                        row += 1

    # --- Página 2: Árvore Universal JSON ---
    def _render_tree_view(self):
        self.tree.delete(*self.tree.get_children())
        self._tree_paths = {}
        if self.current_data is None:
            return
        self._populate_tree("", "root", self.current_data, [])

    def _populate_tree(self, parent_id, label, node, path):
        if isinstance(node, dict):
            item_id = self.tree.insert(
                parent_id, "end", text=str(label), values=("Object", f"{{{len(node)} chaves}}"), open=(len(path) < 3)
            )
            self._tree_paths[item_id] = path
            for k, v in node.items():
                self._populate_tree(item_id, k, v, path + [k])
        elif isinstance(node, list):
            item_id = self.tree.insert(
                parent_id, "end", text=str(label), values=("Array", f"[{len(node)} itens]"), open=(len(path) < 3)
            )
            self._tree_paths[item_id] = path
            for idx, v in enumerate(node):
                self._populate_tree(item_id, f"[{idx}]", v, path + [idx])
        else:
            t_name = type(node).__name__
            item_id = self.tree.insert(parent_id, "end", text=str(label), values=(t_name, str(node)))
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
        if path is None or len(path) == 0:
            return

        current_val = self._get_by_path(path)
        if isinstance(current_val, (dict, list)):
            messagebox.showinfo("Aviso", "Selecione um campo folha (texto, número ou booleano) para editar o valor.")
            return

        new_str = simpledialog.askstring(
            "Editar Valor",
            f"Novo valor para '{path[-1]}':",
            initialvalue=json.dumps(current_val) if isinstance(current_val, bool) else str(current_val),
            parent=self.root,
        )
        if new_str is None:
            return

        parsed_val = self._smart_parse_value(new_str, type(current_val))
        parent_obj = self._get_by_path(path[:-1])
        parent_obj[path[-1]] = parsed_val
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
            key = simpledialog.askstring("Nova Chave", "Nome da nova chave:", parent=self.root)
            if not key:
                return
            val_str = simpledialog.askstring(
                "Valor Inicial", f"Valor para '{key}' (ou {{}} para objeto, [] para lista):", parent=self.root
            )
            if val_str is None:
                return
            target[key] = self._smart_parse_value(val_str)
        elif isinstance(target, list):
            val_str = simpledialog.askstring("Novo Item na Lista", "Valor JSON do item (ex: 10, \"texto\", {}, []):", parent=self.root)
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
            messagebox.showwarning("Aviso", "Não é possível remover a raiz do documento.")
            return
        parent_obj = self._get_by_path(path[:-1])
        del parent_obj[path[-1]]
        self._mark_modified()
        self._render_all_views(reset_preview=False)

    def _smart_parse_value(self, text, hint_type=None):
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

    # --- Página 3: Código JSON Bruto ---
    def _render_raw_view(self):
        self.raw_text.delete("1.0", tk.END)
        if self.current_data is not None:
            formatted = json.dumps(self.current_data, indent=2, ensure_ascii=False)
            self.raw_text.insert("1.0", formatted)

    def _format_raw_json(self):
        content = self.raw_text.get("1.0", tk.END).strip()
        if not content:
            return
        try:
            parsed = json.loads(content)
            self.raw_text.delete("1.0", tk.END)
            self.raw_text.insert("1.0", json.dumps(parsed, indent=2, ensure_ascii=False))
        except json.JSONDecodeError as e:
            messagebox.showerror("Erro de Sintaxe JSON", f"Linha {e.lineno}, Coluna {e.colno}:\n{e.msg}")

    def _apply_raw_json_to_model(self, silent=False):
        content = self.raw_text.get("1.0", tk.END).strip()
        if not content:
            return False
        try:
            parsed = json.loads(content)
            self.current_data = parsed
            self._mark_modified()
            self._sync_preview(reset_time=False)
            self._render_visual_editor()
            self._render_tree_view()
            if not silent:
                self._set_status("Código JSON aplicado ao Viewer e Inspetor.")
            return True
        except json.JSONDecodeError as e:
            messagebox.showerror("Erro de Sintaxe JSON", f"Corrija o JSON antes de aplicar:\nLinha {e.lineno}, Coluna {e.colno}: {e.msg}")
            return False

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------
    def _update_doc_pill(self):
        if not self.current_file_path:
            self.doc_pill_var.set("Nenhum arquivo selecionado")
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

    # --- Inspetor em tempo real -------------------------------------------
    def _on_viewer_time_changed(self, t_ns):
        self._refresh_live_params(t_ns)

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
        """Atualiza um campo sem disparar a gravação no JSON."""
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

    def _seek_to_keyframe(self, kf):
        self.preview_widget.pause()
        self.preview_widget.seek(int(kf.get("time", 0)))

    def _write_keyframed_value(self, param_obj, type_tag, new_val):
        """Edição de um parâmetro animado: grava no keyframe sob o cursor, ou cria um novo ali."""
        pv = self.preview_widget
        pv.pause()
        t = int(pv.current_time_ns)
        tol = int(pv.frame_ns() // 2)
        kfs = param_obj.setdefault("keyframes", [])

        target = next((kf for kf in kfs if abs(int(kf.get("time", 0)) - t) <= tol), None)
        if target is None:
            earlier = [kf for kf in kfs if int(kf.get("time", 0)) < t]
            prev = max(earlier, key=lambda k: k.get("time", 0)) if earlier else {}
            kfs.append(
                {
                    "time": t,
                    "value": {type_tag: copy.deepcopy(new_val)},
                    "interp": prev.get("interp", "AutoBezier"),
                    "out_influence": 0.3333333333333333,
                    "in_influence": 0.3333333333333333,
                }
            )
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
            self._set_status(f"Editando: {self.current_file_path.name} (alterações não salvas)")

    def _set_status(self, msg):
        self.status_var.set(msg)


def main():
    root = tk.Tk()
    app = PresetManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()