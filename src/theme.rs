//! DaVinci Resolve Studio + macOS dark-mode theme and small UI helpers.

use eframe::egui::{self, Color32, RichText, Rounding, Stroke, Ui};

pub const fn rgb(hex: u32) -> Color32 {
    Color32::from_rgb((hex >> 16) as u8, (hex >> 8) as u8, hex as u8)
}

/// Parses `#rrggbb` into a `Color32`.
pub fn hex_color(s: &str) -> Color32 {
    let (r, g, b) = crate::engine::parse_hex(s);
    Color32::from_rgb(r, g, b)
}

pub mod pal {
    use super::rgb;
    use eframe::egui::Color32;

    pub const BG_ROOT: Color32 = rgb(0x121317);
    pub const TITLEBAR: Color32 = rgb(0x1c1e24);
    pub const PANEL: Color32 = rgb(0x191b20);
    pub const PANEL_HEADER: Color32 = rgb(0x21232a);
    pub const CARD: Color32 = rgb(0x202229);
    pub const CARD_HOVER: Color32 = rgb(0x282b34);
    pub const DECK: Color32 = rgb(0x17191e);
    pub const WELL: Color32 = rgb(0x111216);
    pub const INPUT: Color32 = rgb(0x15171c);
    pub const BORDER: Color32 = rgb(0x2b2e38);
    pub const BORDER_LIGHT: Color32 = rgb(0x3a3e4b);
    pub const MONITOR_GUTTER: Color32 = rgb(0x111216);
    pub const MONITOR_BG: Color32 = rgb(0x0a0b0d);
    pub const FG_TEXT: Color32 = rgb(0xe4e6eb);
    pub const FG_MUTED: Color32 = rgb(0x9499a6);
    pub const FG_FAINT: Color32 = rgb(0x636875);
    pub const ACCENT: Color32 = rgb(0xe8943a);
    pub const ACCENT_HOVER: Color32 = rgb(0xf4a44c);
    pub const ACCENT_PRESSED: Color32 = rgb(0xc97926);
    pub const CYAN: Color32 = rgb(0x4cc9f0);
    pub const SELECT_BG: Color32 = rgb(0x2b3952);
    pub const SELECT_BORDER: Color32 = rgb(0x4a89dc);
    pub const SUCCESS: Color32 = rgb(0x4cc38a);
    pub const DANGER: Color32 = rgb(0xe55353);
    pub const DANGER_BG: Color32 = rgb(0x351d21);
}

pub fn setup_theme(ctx: &egui::Context) {
    let mut v = egui::Visuals::dark();
    v.panel_fill = pal::PANEL;
    v.window_fill = pal::PANEL;
    v.extreme_bg_color = pal::INPUT;
    v.faint_bg_color = pal::CARD;
    v.window_stroke = Stroke::new(1.0, pal::BORDER_LIGHT);
    v.window_rounding = Rounding::same(6.0);
    v.selection.bg_fill = pal::SELECT_BG;
    v.selection.stroke = Stroke::new(1.0, pal::SELECT_BORDER);

    let w = &mut v.widgets;
    w.noninteractive.bg_fill = pal::PANEL;
    w.noninteractive.weak_bg_fill = pal::PANEL;
    w.noninteractive.bg_stroke = Stroke::new(1.0, pal::BORDER);
    w.noninteractive.fg_stroke = Stroke::new(1.0, pal::FG_TEXT);

    w.inactive.bg_fill = pal::CARD_HOVER;
    w.inactive.weak_bg_fill = pal::CARD_HOVER;
    w.inactive.bg_stroke = Stroke::new(1.0, pal::BORDER_LIGHT);
    w.inactive.fg_stroke = Stroke::new(1.0, pal::FG_TEXT);

    w.hovered.bg_fill = rgb(0x323642);
    w.hovered.weak_bg_fill = rgb(0x323642);
    w.hovered.bg_stroke = Stroke::new(1.0, rgb(0x4b5060));
    w.hovered.fg_stroke = Stroke::new(1.0, pal::FG_TEXT);

    w.active.bg_fill = rgb(0x22242c);
    w.active.weak_bg_fill = rgb(0x22242c);
    w.active.bg_stroke = Stroke::new(1.0, pal::ACCENT);
    w.active.fg_stroke = Stroke::new(1.0, pal::FG_TEXT);

    w.open.bg_fill = pal::CARD_HOVER;
    w.open.weak_bg_fill = pal::CARD_HOVER;
    for s in [&mut w.noninteractive, &mut w.inactive, &mut w.hovered, &mut w.active, &mut w.open] {
        s.rounding = Rounding::same(3.0);
    }
    ctx.set_visuals(v);

    ctx.style_mut(|s| {
        s.spacing.item_spacing = egui::vec2(6.0, 5.0);
        s.spacing.button_padding = egui::vec2(9.0, 4.0);
        s.spacing.interact_size.y = 22.0;
    });
}

// ---------------------------------------------------------------- helpers

pub fn section_tag(text: &str) -> RichText {
    RichText::new(text).size(11.0).strong().color(pal::FG_MUTED)
}

pub fn card_section(text: &str) -> RichText {
    RichText::new(text).size(11.0).strong().color(pal::ACCENT)
}

pub fn muted(text: &str) -> RichText {
    RichText::new(text).size(12.0).color(pal::FG_MUTED)
}

pub fn mono(text: &str, size: f32, color: Color32) -> RichText {
    RichText::new(text).monospace().size(size).strong().color(color)
}

/// 1px hairline-bordered card (macOS / DaVinci Resolve style).
pub fn hairline_card<R>(ui: &mut Ui, add: impl FnOnce(&mut Ui) -> R) -> R {
    egui::Frame::none()
        .fill(pal::CARD)
        .stroke(Stroke::new(1.0, pal::BORDER))
        .inner_margin(egui::Margin::same(10.0))
        .show(ui, |ui| {
            ui.set_width(ui.available_width());
            add(ui)
        })
        .inner
}

pub fn header_frame() -> egui::Frame {
    egui::Frame::none()
        .fill(pal::PANEL_HEADER)
        .inner_margin(egui::Margin::symmetric(12.0, 7.0))
}

pub fn separator_line(ui: &mut Ui) {
    let (rect, _) = ui.allocate_exact_size(egui::vec2(ui.available_width(), 1.0), egui::Sense::hover());
    ui.painter().rect_filled(rect, 0.0, pal::BORDER);
}

/// Pill toggle used for tool strip / page switcher / language switch. Returns `true` when clicked.
pub fn pill(ui: &mut Ui, text: &str, active: bool, size: f32) -> bool {
    let resp = ui.add(
        egui::Button::new(RichText::new(text).size(size).strong().color(if active { pal::ACCENT } else { pal::FG_MUTED }))
            .fill(if active { pal::CARD_HOVER } else { pal::WELL })
            .stroke(Stroke::NONE),
    );
    resp.on_hover_cursor(egui::CursorIcon::PointingHand).clicked()
}

pub fn accent_button(ui: &mut Ui, text: &str) -> egui::Response {
    ui.add(
        egui::Button::new(RichText::new(text).strong().color(pal::BG_ROOT))
            .fill(pal::ACCENT)
            .stroke(Stroke::new(1.0, pal::ACCENT)),
    )
}

pub fn danger_button(ui: &mut Ui, text: &str) -> egui::Response {
    ui.add(
        egui::Button::new(RichText::new(text).strong().color(pal::DANGER))
            .fill(pal::DANGER_BG)
            .stroke(Stroke::new(1.0, rgb(0x54282e))),
    )
}

pub fn ghost_button(ui: &mut Ui, text: &str) -> egui::Response {
    ui.add(
        egui::Button::new(RichText::new(text).color(pal::FG_MUTED))
            .fill(pal::TITLEBAR)
            .stroke(Stroke::new(1.0, pal::BORDER)),
    )
}

pub fn keyframe_button(ui: &mut Ui, has_kf: bool) -> egui::Response {
    if has_kf {
        ui.add(
            egui::Button::new(RichText::new("◆").size(11.0).strong().color(pal::ACCENT))
                .fill(rgb(0x382918))
                .stroke(Stroke::new(1.0, pal::ACCENT)),
        )
    } else {
        ui.add(
            egui::Button::new(RichText::new("◇").size(11.0).strong().color(pal::FG_MUTED))
                .fill(pal::INPUT)
                .stroke(Stroke::new(1.0, pal::BORDER_LIGHT)),
        )
    }
}

pub fn keyframe_button_text(ui: &mut Ui, text: &str) -> egui::Response {
    ui.add(
        egui::Button::new(RichText::new(text).size(11.0).strong().color(pal::ACCENT))
            .fill(rgb(0x382918))
            .stroke(Stroke::new(1.0, pal::ACCENT)),
    )
}

pub fn transport_button(ui: &mut Ui, text: &str, accent: bool) -> egui::Response {
    if accent {
        ui.add(
            egui::Button::new(RichText::new(text).strong().color(pal::BG_ROOT))
                .fill(pal::ACCENT)
                .stroke(Stroke::new(1.0, pal::ACCENT))
                .min_size(egui::vec2(88.0, 0.0)),
        )
    } else {
        ui.add(egui::Button::new(RichText::new(text).strong()).fill(pal::CARD_HOVER).stroke(Stroke::new(1.0, pal::BORDER_LIGHT)))
    }
}
