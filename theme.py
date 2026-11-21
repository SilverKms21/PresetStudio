#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DaVinci Resolve Studio + macOS Dark Mode theme and base scrollable container."""

import tkinter as tk
from tkinter import ttk

UI_FONT = "Sans"
MONO_FONT = "Monospace"

PALETTE = {
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
    "accent": "#e8943a",
    "accent_hover": "#f4a44c",
    "accent_pressed": "#c97926",
    "cyan": "#4cc9f0",
    "select_bg": "#2b3952",
    "select_border": "#4a89dc",
    "success": "#4cc38a",
    "danger": "#e55353",
    "danger_bg": "#351d21",
}


def setup_theme(root):
    c = PALETTE
    root.configure(bg=c["bg_root"])
    root.option_add("*Font", (UI_FONT, 10))

    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        ".",
        background=c["panel"],
        foreground=c["fg_text"],
        bordercolor=c["border"],
        focuscolor=c["accent"],
        font=(UI_FONT, 10),
    )

    style.configure("Root.TFrame", background=c["bg_root"])
    style.configure("Titlebar.TFrame", background=c["titlebar"])
    style.configure("Panel.TFrame", background=c["panel"])
    style.configure("PanelHeader.TFrame", background=c["panel_header"])
    style.configure("Deck.TFrame", background=c["deck"])
    style.configure("Card.TFrame", background=c["card"])
    style.configure("Dock.TFrame", background=c["titlebar"])

    style.configure("TLabel", background=c["panel"], foreground=c["fg_text"], font=(UI_FONT, 10))
    style.configure("Title.TLabel", background=c["titlebar"], foreground=c["fg_text"], font=(UI_FONT, 11, "bold"))
    style.configure("TitleMuted.TLabel", background=c["titlebar"], foreground=c["fg_muted"], font=(UI_FONT, 9))
    style.configure("SectionTag.TLabel", background=c["panel_header"], foreground=c["fg_muted"], font=(UI_FONT, 8, "bold"))
    style.configure("Badge.TLabel", background=c["panel_header"], foreground=c["accent"], font=(MONO_FONT, 9, "bold"))
    style.configure("HeaderMuted.TLabel", background=c["panel_header"], foreground=c["fg_muted"], font=(UI_FONT, 9))
    style.configure("DeckMuted.TLabel", background=c["deck"], foreground=c["fg_muted"], font=(UI_FONT, 9))
    style.configure("Muted.TLabel", background=c["panel"], foreground=c["fg_muted"], font=(UI_FONT, 9))
    style.configure("Card.TLabel", background=c["card"], foreground=c["fg_text"], font=(UI_FONT, 9))
    style.configure("CardMuted.TLabel", background=c["card"], foreground=c["fg_muted"], font=(UI_FONT, 9))
    style.configure("CardSection.TLabel", background=c["card"], foreground=c["accent"], font=(UI_FONT, 8, "bold"))

    style.configure(
        "TButton",
        background=c["card_hover"],
        foreground=c["fg_text"],
        bordercolor=c["border_light"],
        borderwidth=1,
        focusthickness=0,
        padding=(9, 4),
        font=(UI_FONT, 9, "bold"),
    )
    style.map("TButton", background=[("active", "#323642"), ("pressed", "#22242c")], bordercolor=[("active", "#4b5060")])

    style.configure(
        "Accent.TButton",
        background=c["accent"],
        foreground="#121317",
        bordercolor=c["accent"],
        borderwidth=1,
        padding=(11, 4),
        font=(UI_FONT, 9, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[("active", c["accent_hover"]), ("pressed", c["accent_pressed"])],
        bordercolor=[("active", c["accent_hover"])],
    )

    style.configure(
        "Ghost.TButton",
        background=c["titlebar"],
        foreground=c["fg_muted"],
        bordercolor=c["border"],
        borderwidth=1,
        padding=(7, 4),
        font=(UI_FONT, 9),
    )
    style.map("Ghost.TButton", background=[("active", c["card_hover"])], foreground=[("active", c["fg_text"])])

    style.configure(
        "Danger.TButton",
        background=c["danger_bg"],
        foreground=c["danger"],
        bordercolor="#54282e",
        borderwidth=1,
        padding=(8, 4),
        font=(UI_FONT, 9, "bold"),
    )
    style.map("Danger.TButton", background=[("active", "#472429")])

    style.configure(
        "Transport.TButton",
        background=c["card_hover"],
        foreground=c["fg_text"],
        bordercolor=c["border_light"],
        borderwidth=1,
        padding=(8, 4),
        font=(UI_FONT, 9, "bold"),
    )
    style.map("Transport.TButton", background=[("active", "#343846")])

    style.configure(
        "TransportAccent.TButton",
        background=c["accent"],
        foreground="#121317",
        bordercolor=c["accent"],
        borderwidth=1,
        padding=(10, 4),
        font=(UI_FONT, 9, "bold"),
    )
    style.map("TransportAccent.TButton", background=[("active", c["accent_hover"])])

    style.configure(
        "KeyframeOff.TButton",
        background=c["input"],
        foreground=c["fg_muted"],
        bordercolor=c["border_light"],
        borderwidth=1,
        padding=(7, 3),
        font=(UI_FONT, 8, "bold"),
    )
    style.map("KeyframeOff.TButton", background=[("active", c["card_hover"])], foreground=[("active", c["fg_text"])])

    style.configure(
        "KeyframeOn.TButton",
        background="#382918",
        foreground=c["accent"],
        bordercolor=c["accent"],
        borderwidth=1,
        padding=(7, 3),
        font=(UI_FONT, 8, "bold"),
    )
    style.map("KeyframeOn.TButton", background=[("active", "#4a351e")])

    style.configure(
        "TEntry",
        fieldbackground=c["input"],
        background=c["input"],
        foreground=c["fg_text"],
        insertcolor=c["accent"],
        bordercolor=c["border_light"],
        lightcolor=c["border_light"],
        darkcolor=c["border_light"],
        borderwidth=1,
        padding=4,
    )
    style.map("TEntry", bordercolor=[("focus", c["accent"])], lightcolor=[("focus", c["accent"])], darkcolor=[("focus", c["accent"])])

    style.configure(
        "TCombobox",
        fieldbackground=c["input"],
        background=c["card_hover"],
        foreground=c["fg_text"],
        arrowcolor=c["fg_muted"],
        bordercolor=c["border_light"],
        lightcolor=c["border_light"],
        darkcolor=c["border_light"],
        padding=3,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", c["input"])],
        background=[("readonly", c["card_hover"])],
        bordercolor=[("focus", c["accent"])],
    )

    style.configure("TCheckbutton", background=c["panel"], foreground=c["fg_text"])
    style.map("TCheckbutton", background=[("active", c["panel"])])
    style.configure("Header.TCheckbutton", background=c["panel_header"], foreground=c["fg_text"], font=(UI_FONT, 8))
    style.map("Header.TCheckbutton", background=[("active", c["panel_header"])])
    style.configure("Deck.TCheckbutton", background=c["deck"], foreground=c["fg_text"], font=(UI_FONT, 9))
    style.map("Deck.TCheckbutton", background=[("active", c["deck"])])
    style.configure("Card.TCheckbutton", background=c["card"], foreground=c["fg_text"], font=(UI_FONT, 9))
    style.map("Card.TCheckbutton", background=[("active", c["card"])])

    style.configure("Treeview", background=c["panel"], foreground=c["fg_text"], fieldbackground=c["panel"], rowheight=28, borderwidth=0)
    style.configure("Treeview.Heading", background=c["panel_header"], foreground=c["fg_muted"], relief="flat", font=(UI_FONT, 9, "bold"), padding=(8, 6))
    style.map("Treeview", background=[("selected", c["select_bg"])], foreground=[("selected", "#ffffff")])

    style.configure("TScrollbar", background=c["card_hover"], troughcolor=c["panel"], bordercolor=c["panel"], arrowcolor=c["fg_muted"], relief="flat")
    style.map("TScrollbar", background=[("active", c["border_light"])])
    style.configure("TPanedwindow", background=c["bg_root"], borderwidth=0)
    return c


def create_hairline_card(parent, padding=12):
    """Creates a 1px hairline-bordered card styled after macOS / DaVinci Resolve."""
    outer = tk.Frame(parent, bg=PALETTE["border"], padx=1, pady=1)
    inner = ttk.Frame(outer, style="Card.TFrame", padding=padding)
    inner.pack(fill="both", expand=True)
    return outer, inner


class ScrollableFrame(ttk.Frame):
    """Lightweight scrollable frame for the Inspector."""

    def __init__(self, container, bg_color="#1b1d22", *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="Panel.TFrame")

        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.window_id, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _bind_mousewheel(self, _event):
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_win)

    def _unbind_mousewheel(self, _event):
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel_linux(self, event):
        self.canvas.yview_scroll(-2 if event.num == 4 else 2, "units")

    def _on_mousewheel_win(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")