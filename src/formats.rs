//! Viewer for well-known (non-Filmcraft) JSON formats:
//! OBS transitions / scene collections (animated preview + editor), Lottie, GeoJSON,
//! speech-to-text transcripts and a generic structure / colour / numeric-array inspector.

use std::collections::BTreeMap;
use std::time::Instant;

use eframe::egui::{self, Align2, Color32, FontId, Pos2, Rect, RichText, Sense, Shape, Stroke, Vec2};
use serde_json::{json, Value};

use crate::engine::num;
use crate::i18n::Lang;
use crate::theme::{self, hex_color, pal};

pub fn l(lang: Lang, en: &str, pt: &str) -> String {
    if lang == Lang::Pt { pt } else { en }.to_string()
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Kind {
    Obs,
    Lottie,
    GeoJson,
    Transcript,
    Generic,
}

impl Kind {
    pub fn label(self) -> &'static str {
        match self {
            Kind::Obs => "OBS Studio (transitions / scene collection)",
            Kind::Lottie => "Lottie animation",
            Kind::GeoJson => "GeoJSON",
            Kind::Transcript => "Transcript / subtitles (segments)",
            Kind::Generic => "Generic JSON",
        }
    }
}

// ------------------------------------------------------------------ detection

fn is_obs_transition(v: &Value) -> bool {
    v.get("id").and_then(|i| i.as_str()).map(|s| s.ends_with("_transition")).unwrap_or(false)
}

fn transcript_segments(v: &Value) -> Option<&Vec<Value>> {
    let arr = v.get("segments").and_then(|s| s.as_array()).or_else(|| v.as_array())?;
    let ok = arr
        .first()
        .map(|s| s.get("start").and_then(num).is_some() && s.get("end").and_then(num).is_some() && s.get("text").is_some())
        .unwrap_or(false);
    if ok { Some(arr) } else { None }
}

pub fn detect(v: &Value) -> Kind {
    if v.is_object() {
        if v.get("transitions").map(|t| t.is_array()).unwrap_or(false)
            || (v.get("sources").map(|s| s.is_array()).unwrap_or(false) && v.get("scene_order").is_some())
            || is_obs_transition(v)
        {
            return Kind::Obs;
        }
        if v.get("layers").map(|l| l.is_array()).unwrap_or(false) && v.get("fr").and_then(num).is_some() {
            return Kind::Lottie;
        }
        if let Some(t) = v.get("type").and_then(|t| t.as_str()) {
            if ["FeatureCollection", "Feature", "Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon", "GeometryCollection"]
                .contains(&t)
            {
                return Kind::GeoJson;
            }
        }
    }
    if transcript_segments(v).is_some() {
        return Kind::Transcript;
    }
    Kind::Generic
}

// ------------------------------------------------------------------ state & caches

#[derive(Default, Clone)]
struct Stats {
    nodes: usize,
    max_depth: usize,
    counts: BTreeMap<&'static str, usize>,
    arrays: Vec<(String, usize)>,
    colors: Vec<(String, String)>,
    numeric: Vec<(String, Vec<f64>)>,
}

#[derive(Default, Clone)]
struct GeoData {
    points: Vec<(f64, f64)>,
    lines: Vec<Vec<(f64, f64)>>,
    polys: Vec<Vec<(f64, f64)>>,
    types: BTreeMap<String, usize>,
    features: usize,
}

pub struct FormatState {
    sel: usize,
    p: f32,
    playing: bool,
    last: Instant,
    dur_ms_single: f64,
    add_kind: usize,
    stats: Option<(u64, Stats)>,
    geo: Option<(u64, GeoData)>,
}

impl Default for FormatState {
    fn default() -> Self {
        FormatState { sel: 0, p: 0.0, playing: true, last: Instant::now(), dur_ms_single: 600.0, add_kind: 0, stats: None, geo: None }
    }
}

impl FormatState {
    pub fn reset(&mut self) {
        self.sel = 0;
        self.p = 0.0;
        self.stats = None;
        self.geo = None;
    }
}

// ------------------------------------------------------------------ entry point

/// Draws the viewer for `data`. Returns `true` when the document was modified (OBS editor).
pub fn show(ui: &mut egui::Ui, data: &mut Value, st: &mut FormatState, lang: Lang, generation: u64) -> bool {
    let kind = detect(data);
    let now = Instant::now();
    let dt = (now - st.last).as_secs_f32().min(0.25);
    st.last = now;

    ui.horizontal(|ui| {
        ui.label(theme::section_tag(&l(lang, "DETECTED FORMAT", "FORMATO DETECTADO")));
        ui.label(theme::mono(kind.label(), 12.0, pal::ACCENT));
    });
    ui.add_space(6.0);

    let mut modified = false;
    egui::ScrollArea::vertical().auto_shrink([false, false]).show(ui, |ui| match kind {
        Kind::Obs => modified = obs_ui(ui, data, st, lang, dt),
        Kind::Lottie => lottie_ui(ui, data, st, lang, dt),
        Kind::GeoJson => geo_ui(ui, data, st, lang, generation),
        Kind::Transcript => transcript_ui(ui, data, lang),
        Kind::Generic => generic_ui(ui, data, st, lang, generation),
    });
    modified
}

fn play_bar(ui: &mut egui::Ui, st: &mut FormatState, lang: Lang, dt: f32, dur_s: f32) {
    if st.playing {
        st.p += dt / dur_s.max(0.05);
        if st.p > 1.0 {
            st.p = 0.0;
        }
        ui.ctx().request_repaint();
    }
    ui.horizontal(|ui| {
        let label = if st.playing { l(lang, "⏸ Pause", "⏸ Pausar") } else { l(lang, "▶ Play", "▶ Reproduzir") };
        if theme::transport_button(ui, &label, true).clicked() {
            st.playing = !st.playing;
        }
        ui.spacing_mut().slider_width = (ui.available_width() - 120.0).max(100.0);
        if ui.add(egui::Slider::new(&mut st.p, 0.0..=1.0).show_value(false)).changed() {
            st.playing = false;
        }
        ui.label(theme::mono(&format!("{:.0}%  /  {:.2}s", st.p * 100.0, dur_s * st.p), 11.0, pal::ACCENT));
    });
}

// ================================================================== OBS

const OBS_KINDS: [(&str, &str); 7] = [
    ("fade_transition", "Fade"),
    ("cut_transition", "Cut"),
    ("slide_transition", "Slide"),
    ("swipe_transition", "Swipe"),
    ("fade_to_color_transition", "Fade to Color"),
    ("luma_wipe_transition", "Luma Wipe"),
    ("obs_stinger_transition", "Stinger"),
];

pub fn obs_default(id: &str) -> Value {
    let name = OBS_KINDS.iter().find(|(i, _)| *i == id).map(|(_, n)| *n).unwrap_or("Transition");
    let settings = match id {
        "slide_transition" => json!({"direction": "left"}),
        "swipe_transition" => json!({"direction": "left", "swipe_in": false}),
        "fade_to_color_transition" => json!({"color": 4278190080u64, "switch_point": 50}),
        "luma_wipe_transition" => json!({"luma_image": "linear-horizontal.png", "luma_softness": 0.03, "luma_invert": false}),
        "obs_stinger_transition" => json!({
            "path": "", "transition_point_type": 0, "transition_point": 500, "audio_monitoring": 0,
            "audio_fade_style": 0, "invert_matte": false
        }),
        _ => json!({}),
    };
    json!({"name": name, "id": id, "settings": settings})
}

pub fn obs_collection_template() -> Value {
    json!({
        "name": "OBS Transitions",
        "current_transition": "Fade",
        "transition_duration": 300,
        "transitions": [obs_default("fade_transition"), obs_default("slide_transition"), obs_default("obs_stinger_transition")],
        "sources": [],
        "scene_order": []
    })
}

pub fn obs_stinger_template() -> Value {
    obs_default("obs_stinger_transition")
}

fn obs_color(c: u64) -> Color32 {
    Color32::from_rgb((c & 0xff) as u8, ((c >> 8) & 0xff) as u8, ((c >> 16) & 0xff) as u8)
}

fn obs_color_pack(rgb: [u8; 3]) -> u64 {
    0xff00_0000 | ((rgb[2] as u64) << 16) | ((rgb[1] as u64) << 8) | rgb[0] as u64
}

fn scene(p: &egui::Painter, r: Rect, is_b: bool, alpha: f32) {
    let a = (alpha.clamp(0.0, 1.0) * 255.0) as u8;
    let base = if is_b { (0xc9, 0x70, 0x3a) } else { (0x2b, 0x4c, 0x7e) };
    p.rect_filled(r, 0.0, Color32::from_rgba_unmultiplied(base.0, base.1, base.2, a));
    p.circle_filled(r.center(), r.height() * 0.22, Color32::from_rgba_unmultiplied(255, 255, 255, (a as f32 * 0.18) as u8));
    p.text(
        r.center(),
        Align2::CENTER_CENTER,
        if is_b { "Scene B" } else { "Scene A" },
        FontId::proportional((r.height() * 0.12).max(10.0)),
        Color32::from_rgba_unmultiplied(255, 255, 255, a),
    );
}

fn dir_vec(dir: &str) -> (f32, f32) {
    match dir {
        "right" => (1.0, 0.0),
        "up" => (0.0, -1.0),
        "down" => (0.0, 1.0),
        _ => (-1.0, 0.0),
    }
}

fn draw_transition(painter: &egui::Painter, rect: Rect, id: &str, s: &Value, p: f32, dur_ms: f64) {
    let painter = painter.with_clip_rect(rect);
    painter.rect_filled(rect, 0.0, pal::MONITOR_BG);
    let sget = |k: &str| s.get(k);
    let (w, h) = (rect.width(), rect.height());
    match id {
        "cut_transition" => scene(&painter, rect, p > 0.5, 1.0),
        "slide_transition" => {
            let (dx, dy) = dir_vec(sget("direction").and_then(|d| d.as_str()).unwrap_or("left"));
            let off = Vec2::new(dx * w * p, dy * h * p);
            scene(&painter, rect.translate(off), false, 1.0);
            scene(&painter, rect.translate(off + Vec2::new(-dx * w, -dy * h)), true, 1.0);
        }
        "swipe_transition" => {
            let (dx, dy) = dir_vec(sget("direction").and_then(|d| d.as_str()).unwrap_or("left"));
            let swipe_in = sget("swipe_in").and_then(|b| b.as_bool()).unwrap_or(false);
            if swipe_in {
                scene(&painter, rect, false, 1.0);
                scene(&painter, rect.translate(Vec2::new(-dx * w * (1.0 - p), -dy * h * (1.0 - p))), true, 1.0);
            } else {
                scene(&painter, rect, true, 1.0);
                scene(&painter, rect.translate(Vec2::new(dx * w * p, dy * h * p)), false, 1.0);
            }
        }
        "fade_to_color_transition" => {
            let col = obs_color(sget("color").and_then(num).map(|c| c as u64).unwrap_or(0xff000000));
            let sp = (sget("switch_point").and_then(num).unwrap_or(50.0) / 100.0).clamp(0.01, 0.99) as f32;
            let (is_b, k) = if p < sp { (false, p / sp) } else { (true, 1.0 - (p - sp) / (1.0 - sp)) };
            scene(&painter, rect, is_b, 1.0);
            painter.rect_filled(rect, 0.0, Color32::from_rgba_unmultiplied(col.r(), col.g(), col.b(), ((1.0 - (1.0 - k).max(0.0).min(1.0)) * 255.0) as u8));
        }
        "luma_wipe_transition" => {
            let soft = sget("luma_softness").and_then(num).unwrap_or(0.03).clamp(0.01, 1.0) as f32;
            let invert = sget("luma_invert").and_then(|b| b.as_bool()).unwrap_or(false);
            scene(&painter, rect, false, 1.0);
            let n = 64;
            for i in 0..n {
                let mut f = i as f32 / n as f32;
                if invert {
                    f = 1.0 - f;
                }
                let a = ((p * (1.0 + soft) - f) / soft).clamp(0.0, 1.0);
                if a > 0.0 {
                    let strip = Rect::from_min_max(
                        Pos2::new(rect.left() + w * i as f32 / n as f32, rect.top()),
                        Pos2::new(rect.left() + w * (i as f32 + 1.0) / n as f32 + 1.0, rect.bottom()),
                    );
                    let clip = painter.with_clip_rect(strip.intersect(rect));
                    scene(&clip, rect, true, a);
                }
            }
        }
        "obs_stinger_transition" => {
            let ty = sget("transition_point_type").and_then(num).unwrap_or(0.0) as i64;
            let tp = sget("transition_point").and_then(num).unwrap_or(500.0);
            let cut = if ty == 1 { (tp / 100.0) as f32 } else { (tp / dur_ms.max(1.0)) as f32 }.clamp(0.0, 1.0);
            scene(&painter, rect, p >= cut, 1.0);
            let cx = rect.left() + w * (-0.25 + 1.5 * p);
            let band = Rect::from_center_size(Pos2::new(cx, rect.center().y), Vec2::new(w * 0.45, h));
            painter.rect_filled(band, 0.0, Color32::from_rgba_unmultiplied(10, 10, 14, 215));
            painter.text(band.center(), Align2::CENTER_CENTER, "STINGER", FontId::proportional(h * 0.08), Color32::from_rgb(0xe8, 0x94, 0x3a));
        }
        _ => {
            scene(&painter, rect, false, 1.0);
            scene(&painter, rect, true, p);
        }
    }
}

fn obs_ui(ui: &mut egui::Ui, data: &mut Value, st: &mut FormatState, lang: Lang, dt: f32) -> bool {
    let mut modified = false;
    let single = !data.get("transitions").map(|t| t.is_array()).unwrap_or(false) && is_obs_transition(data);

    let count = if single { 1 } else { data.get("transitions").and_then(|t| t.as_array()).map(|a| a.len()).unwrap_or(0) };
    if st.sel >= count.max(1) {
        st.sel = 0;
    }

    // ---- collection-level info
    if !single {
        theme::hairline_card(ui, |ui| {
            ui.label(theme::card_section(&l(lang, "SCENE COLLECTION", "COLEÇÃO DE CENAS")));
            let name = data.get("name").and_then(|n| n.as_str()).unwrap_or("-");
            let scenes = data.get("scene_order").and_then(|s| s.as_array()).map(|a| a.len()).unwrap_or(0);
            let sources = data.get("sources").and_then(|s| s.as_array()).map(|a| a.len()).unwrap_or(0);
            ui.label(format!("{}: {}   |   {}: {}   |   {}: {}", l(lang, "Name", "Nome"), name, l(lang, "Scenes", "Cenas"), scenes, l(lang, "Sources", "Fontes"), sources));
            ui.horizontal(|ui| {
                ui.label(theme::muted(&l(lang, "Default duration (ms)", "Duração padrão (ms)")));
                let mut d = data.get("transition_duration").and_then(num).unwrap_or(300.0);
                if ui.add(egui::DragValue::new(&mut d).speed(5.0).range(0.0..=20000.0)).changed() {
                    data["transition_duration"] = json!(d as i64);
                    modified = true;
                }
                ui.label(theme::muted(&l(lang, "Current transition", "Transição atual")));
                let cur = data.get("current_transition").and_then(|c| c.as_str()).unwrap_or("-").to_string();
                ui.label(RichText::new(cur).strong());
            });
        });
        ui.add_space(6.0);
    }

    // ---- transition list / add / delete
    let names: Vec<String> = if single {
        vec![format!("{} ({})", data.get("name").and_then(|n| n.as_str()).unwrap_or("transition"), data["id"].as_str().unwrap_or(""))]
    } else {
        data.get("transitions")
            .and_then(|t| t.as_array())
            .map(|a| {
                a.iter()
                    .map(|t| {
                        format!("{} ({})", t.get("name").and_then(|n| n.as_str()).unwrap_or("?"), t.get("id").and_then(|n| n.as_str()).unwrap_or("?"))
                    })
                    .collect()
            })
            .unwrap_or_default()
    };

    let (mut add, mut del) = (false, false);
    ui.horizontal(|ui| {
        ui.label(theme::section_tag(&l(lang, "TRANSITION", "TRANSIÇÃO")));
        if !names.is_empty() {
            egui::ComboBox::from_id_salt("obs_sel").width(300.0).selected_text(names[st.sel].clone()).show_ui(ui, |ui| {
                for (i, n) in names.iter().enumerate() {
                    if ui.selectable_value(&mut st.sel, i, n).clicked() {
                        st.p = 0.0;
                    }
                }
            });
        }
        if !single {
            egui::ComboBox::from_id_salt("obs_add").width(140.0).selected_text(OBS_KINDS[st.add_kind].1).show_ui(ui, |ui| {
                for (i, (_, n)) in OBS_KINDS.iter().enumerate() {
                    ui.selectable_value(&mut st.add_kind, i, *n);
                }
            });
            if ui.button(l(lang, "+ Add", "+ Adicionar")).clicked() {
                add = true;
            }
            if theme::danger_button(ui, &l(lang, "✕ Remove", "✕ Remover")).clicked() && count > 0 {
                del = true;
            }
        }
    });
    if add {
        let new_t = obs_default(OBS_KINDS[st.add_kind].0);
        if !data.get("transitions").map(|t| t.is_array()).unwrap_or(false) {
            data["transitions"] = json!([]);
        }
        let arr = data["transitions"].as_array_mut().unwrap();
        arr.push(new_t);
        st.sel = arr.len() - 1;
        modified = true;
    }
    if del {
        if let Some(arr) = data.get_mut("transitions").and_then(|t| t.as_array_mut()) {
            if st.sel < arr.len() {
                arr.remove(st.sel);
                st.sel = st.sel.saturating_sub(1);
                modified = true;
            }
        }
    }
    ui.add_space(6.0);

    // ---- selected transition
    let default_ms = data.get("transition_duration").and_then(num).unwrap_or(300.0);
    let t_val: &mut Value = if single {
        data
    } else {
        match data.get_mut("transitions").and_then(|t| t.get_mut(st.sel)) {
            Some(t) => t,
            None => {
                ui.label(theme::muted(&l(lang, "No transitions in this file. Use “+ Add”.", "Nenhuma transição neste arquivo. Use “+ Adicionar”.")));
                return modified;
            }
        }
    };
    let id = t_val.get("id").and_then(|i| i.as_str()).unwrap_or("").to_string();
    let settings_snapshot = t_val.get("settings").cloned().unwrap_or(json!({}));

    let dur_ms = if single { st.dur_ms_single } else { default_ms };
    let preview_ms = if id == "obs_stinger_transition" {
        let tp = settings_snapshot.get("transition_point").and_then(num).unwrap_or(500.0);
        if settings_snapshot.get("transition_point_type").and_then(num).unwrap_or(0.0) == 0.0 { (tp * 2.0).max(1000.0) } else { 1500.0 }
    } else {
        dur_ms.max(50.0)
    };

    // preview
    let avail_w = ui.available_width().min(720.0);
    let (rect, _) = ui.allocate_exact_size(Vec2::new(avail_w, avail_w * 9.0 / 16.0), Sense::hover());
    let painter = ui.painter_at(rect);
    draw_transition(&painter, rect, &id, &settings_snapshot, st.p, preview_ms);
    painter.rect_stroke(rect, 0.0, Stroke::new(1.0, pal::BORDER_LIGHT));
    play_bar(ui, st, lang, dt, (preview_ms / 1000.0) as f32 * 1.0 + 0.6);
    if single {
        ui.horizontal(|ui| {
            ui.label(theme::muted(&l(lang, "Preview duration (ms)", "Duração do preview (ms)")));
            ui.add(egui::DragValue::new(&mut st.dur_ms_single).speed(10.0).range(50.0..=20000.0));
        });
    }
    ui.label(theme::muted(&l(
        lang,
        "Preview is an approximation of OBS's built-in transitions (stinger video and luma image files are not loaded).",
        "O preview é uma aproximação das transições nativas do OBS (vídeo do stinger e imagens de luma não são carregados).",
    )));
    ui.add_space(6.0);

    // settings editor
    let Some(settings) = t_val.get_mut("settings").and_then(|s| s.as_object_mut()) else { return modified };
    theme::hairline_card(ui, |ui| {
        ui.label(theme::card_section(&l(lang, "SETTINGS", "CONFIGURAÇÕES")));
        egui::Grid::new("obs_settings").num_columns(2).spacing([8.0, 6.0]).show(ui, |ui| {
            for (k, v) in settings.iter_mut() {
                ui.label(theme::muted(k));
                match v {
                    Value::Bool(b) => {
                        if ui.checkbox(b, "").changed() {
                            modified = true;
                        }
                    }
                    Value::String(s) => {
                        if ui.add(egui::TextEdit::singleline(s).desired_width(360.0)).changed() {
                            modified = true;
                        }
                    }
                    Value::Number(n) if k == "color" => {
                        let c = obs_color(n.as_u64().or_else(|| n.as_i64().map(|i| i as u64)).unwrap_or(0));
                        let mut rgb = [c.r(), c.g(), c.b()];
                        if egui::color_picker::color_edit_button_srgb(ui, &mut rgb).changed() {
                            *v = json!(obs_color_pack(rgb));
                            modified = true;
                        }
                    }
                    Value::Number(n) => {
                        if n.is_f64() {
                            let mut f = n.as_f64().unwrap_or(0.0);
                            if ui.add(egui::DragValue::new(&mut f).speed(0.01).max_decimals(4)).changed() {
                                *v = json!(f);
                                modified = true;
                            }
                        } else {
                            let mut i = n.as_i64().unwrap_or(0);
                            if ui.add(egui::DragValue::new(&mut i)).changed() {
                                *v = json!(i);
                                modified = true;
                            }
                        }
                    }
                    other => {
                        ui.label(theme::muted(&other.to_string()));
                    }
                }
                ui.end_row();
            }
        });
        if settings.is_empty() {
            ui.label(theme::muted(&l(lang, "This transition has no settings.", "Esta transição não possui configurações.")));
        }
    });
    modified
}

// ================================================================== Lottie

fn lottie_ui(ui: &mut egui::Ui, data: &Value, st: &mut FormatState, lang: Lang, dt: f32) {
    let g = |k: &str| data.get(k).and_then(num).unwrap_or(0.0);
    let (fr, ip, op, w, h) = (g("fr").max(1.0), g("ip"), g("op"), g("w"), g("h"));
    let dur = ((op - ip) / fr).max(0.01);
    let layers = data.get("layers").and_then(|l| l.as_array()).cloned().unwrap_or_default();

    theme::hairline_card(ui, |ui| {
        ui.label(theme::card_section(&l(lang, "COMPOSITION", "COMPOSIÇÃO")));
        ui.label(format!(
            "{}: {}   |   {}×{}   |   {} fps   |   {:.2}s ({} → {})   |   {}: {}   |   assets: {}",
            l(lang, "Name", "Nome"),
            data.get("nm").and_then(|n| n.as_str()).unwrap_or("-"),
            w as i64,
            h as i64,
            fr,
            dur,
            ip,
            op,
            l(lang, "Layers", "Camadas"),
            layers.len(),
            data.get("assets").and_then(|a| a.as_array()).map(|a| a.len()).unwrap_or(0)
        ));
    });
    ui.add_space(6.0);
    play_bar(ui, st, lang, dt, dur as f32);
    let frame = ip + (op - ip) * st.p as f64;

    let row_h = 22.0;
    let label_w = 220.0;
    let width = ui.available_width();
    let (resp, painter) = ui.allocate_painter(Vec2::new(width, 28.0 + row_h * layers.len().max(1) as f32), Sense::hover());
    let o = resp.rect.min;
    painter.rect_filled(resp.rect, 0.0, pal::WELL);
    let span = (width - label_w - 12.0).max(10.0);
    let x_of = |f: f64| o.x + label_w + span * ((f - ip) / (op - ip).max(1.0)) as f32;
    painter.text(Pos2::new(o.x + 8.0, o.y + 8.0), Align2::LEFT_CENTER, format!("frame {:.0}", frame), FontId::monospace(11.0), pal::ACCENT);
    for (i, layer) in layers.iter().enumerate() {
        let y = o.y + 28.0 + i as f32 * row_h;
        let (lip, lop) = (layer.get("ip").and_then(num).unwrap_or(ip), layer.get("op").and_then(num).unwrap_or(op));
        let active = frame >= lip && frame <= lop;
        let ty = match layer.get("ty").and_then(num).unwrap_or(-1.0) as i64 {
            0 => "precomp",
            1 => "solid",
            2 => "image",
            3 => "null",
            4 => "shape",
            5 => "text",
            _ => "?",
        };
        let name = layer.get("nm").and_then(|n| n.as_str()).unwrap_or("-");
        painter.text(
            Pos2::new(o.x + 8.0, y + row_h / 2.0),
            Align2::LEFT_CENTER,
            format!("{}  [{}]", name.chars().take(24).collect::<String>(), ty),
            FontId::proportional(11.0),
            if active { pal::FG_TEXT } else { pal::FG_FAINT },
        );
        let bar = Rect::from_min_max(Pos2::new(x_of(lip), y + 4.0), Pos2::new(x_of(lop).max(x_of(lip) + 2.0), y + row_h - 4.0));
        painter.rect_filled(bar, 3.0, if active { pal::ACCENT } else { theme::rgb(0x4a3a28) });
    }
    let px = x_of(frame);
    painter.line_segment([Pos2::new(px, o.y + 18.0), Pos2::new(px, resp.rect.bottom())], Stroke::new(2.0, pal::CYAN));
}

// ================================================================== GeoJSON

fn pt_of(v: &Value) -> Option<(f64, f64)> {
    let a = v.as_array()?;
    Some((num(a.first()?)?, num(a.get(1)?)?))
}

fn ring_of(v: &Value) -> Vec<(f64, f64)> {
    v.as_array().map(|a| a.iter().filter_map(pt_of).collect()).unwrap_or_default()
}

fn collect_geo(v: &Value, g: &mut GeoData) {
    let Some(t) = v.get("type").and_then(|t| t.as_str()) else { return };
    *g.types.entry(t.to_string()).or_insert(0) += 1;
    let c = v.get("coordinates");
    match t {
        "FeatureCollection" => {
            for f in v.get("features").and_then(|f| f.as_array()).into_iter().flatten() {
                collect_geo(f, g);
            }
        }
        "Feature" => {
            g.features += 1;
            if let Some(geom) = v.get("geometry") {
                collect_geo(geom, g);
            }
        }
        "GeometryCollection" => {
            for f in v.get("geometries").and_then(|f| f.as_array()).into_iter().flatten() {
                collect_geo(f, g);
            }
        }
        "Point" => g.points.extend(c.and_then(pt_of)),
        "MultiPoint" => g.points.extend(c.map(ring_of).unwrap_or_default()),
        "LineString" => g.lines.push(c.map(ring_of).unwrap_or_default()),
        "MultiLineString" => g.lines.extend(c.and_then(|c| c.as_array()).into_iter().flatten().map(ring_of)),
        "Polygon" => g.polys.extend(c.and_then(|c| c.as_array()).into_iter().flatten().map(ring_of)),
        "MultiPolygon" => {
            for poly in c.and_then(|c| c.as_array()).into_iter().flatten() {
                g.polys.extend(poly.as_array().into_iter().flatten().map(ring_of));
            }
        }
        _ => {}
    }
}

fn geo_ui(ui: &mut egui::Ui, data: &Value, st: &mut FormatState, lang: Lang, generation: u64) {
    if st.geo.as_ref().map(|(g, _)| *g != generation).unwrap_or(true) {
        let mut g = GeoData::default();
        collect_geo(data, &mut g);
        st.geo = Some((generation, g));
    }
    let geo = &st.geo.as_ref().unwrap().1;

    let all: Vec<(f64, f64)> =
        geo.points.iter().copied().chain(geo.lines.iter().flatten().copied()).chain(geo.polys.iter().flatten().copied()).collect();
    theme::hairline_card(ui, |ui| {
        ui.label(theme::card_section(&l(lang, "GEOMETRY", "GEOMETRIA")));
        let types: Vec<String> = geo.types.iter().map(|(k, v)| format!("{}×{}", v, k)).collect();
        ui.label(format!("features: {}   |   {}", geo.features, types.join(", ")));
        if let Some(first) = all.first() {
            let (mut x0, mut y0, mut x1, mut y1) = (first.0, first.1, first.0, first.1);
            for &(x, y) in &all {
                x0 = x0.min(x);
                x1 = x1.max(x);
                y0 = y0.min(y);
                y1 = y1.max(y);
            }
            ui.label(theme::muted(&format!("bbox: [{:.4}, {:.4}] → [{:.4}, {:.4}]", x0, y0, x1, y1)));
        }
    });
    ui.add_space(6.0);
    if all.is_empty() {
        ui.label(theme::muted(&l(lang, "No drawable coordinates.", "Nenhuma coordenada para desenhar.")));
        return;
    }
    let (mut x0, mut y0, mut x1, mut y1) = (f64::MAX, f64::MAX, f64::MIN, f64::MIN);
    for &(x, y) in &all {
        x0 = x0.min(x);
        x1 = x1.max(x);
        y0 = y0.min(y);
        y1 = y1.max(y);
    }
    let (bw, bh) = ((x1 - x0).max(1e-9), (y1 - y0).max(1e-9));
    let size = Vec2::new(ui.available_width(), (ui.available_height() - 10.0).max(360.0));
    let (resp, painter) = ui.allocate_painter(size, Sense::hover());
    painter.rect_filled(resp.rect, 0.0, pal::MONITOR_BG);
    let pad = 24.0;
    let scale = ((resp.rect.width() as f64 - pad * 2.0) / bw).min((resp.rect.height() as f64 - pad * 2.0) / bh);
    let (ox, oy) = (
        resp.rect.left() as f64 + (resp.rect.width() as f64 - bw * scale) / 2.0,
        resp.rect.top() as f64 + (resp.rect.height() as f64 - bh * scale) / 2.0,
    );
    let map = |(x, y): (f64, f64)| Pos2::new((ox + (x - x0) * scale) as f32, (oy + (y1 - y) * scale) as f32);
    for poly in &geo.polys {
        if poly.len() >= 2 {
            painter.add(Shape::closed_line(poly.iter().map(|&p| map(p)).collect(), Stroke::new(1.2, pal::ACCENT)));
        }
    }
    for line in &geo.lines {
        if line.len() >= 2 {
            painter.add(Shape::line(line.iter().map(|&p| map(p)).collect(), Stroke::new(1.5, pal::CYAN)));
        }
    }
    for &p in &geo.points {
        painter.circle_filled(map(p), 3.5, pal::SUCCESS);
    }
}

// ================================================================== Transcript

fn fmt_time(s: f64) -> String {
    format!("{:02}:{:05.2}", (s / 60.0) as i64, s % 60.0)
}

fn transcript_ui(ui: &mut egui::Ui, data: &Value, lang: Lang) {
    let Some(segs) = transcript_segments(data) else { return };
    let total = segs.iter().filter_map(|s| s.get("end").and_then(num)).fold(0.0, f64::max).max(0.01);
    let words: usize = segs.iter().filter_map(|s| s.get("text").and_then(|t| t.as_str())).map(|t| t.split_whitespace().count()).sum();
    theme::hairline_card(ui, |ui| {
        ui.label(theme::card_section(&l(lang, "TRANSCRIPT", "TRANSCRIÇÃO")));
        ui.label(format!(
            "{}: {}   |   {}: {}   |   {}: {}",
            l(lang, "Segments", "Segmentos"),
            segs.len(),
            l(lang, "Words", "Palavras"),
            words,
            l(lang, "Duration", "Duração"),
            fmt_time(total)
        ));
    });
    ui.add_space(6.0);
    let (resp, painter) = ui.allocate_painter(Vec2::new(ui.available_width(), 30.0), Sense::hover());
    painter.rect_filled(resp.rect, 0.0, pal::WELL);
    for (i, s) in segs.iter().enumerate() {
        let (a, b) = (s.get("start").and_then(num).unwrap_or(0.0), s.get("end").and_then(num).unwrap_or(0.0));
        let x = |t: f64| resp.rect.left() + resp.rect.width() * (t / total) as f32;
        let r = Rect::from_min_max(Pos2::new(x(a), resp.rect.top() + 4.0), Pos2::new(x(b).max(x(a) + 1.0), resp.rect.bottom() - 4.0));
        painter.rect_filled(r, 2.0, if i % 2 == 0 { pal::ACCENT } else { pal::CYAN });
    }
    ui.add_space(6.0);
    egui::Grid::new("transcript_grid").num_columns(2).spacing([14.0, 4.0]).striped(true).show(ui, |ui| {
        for s in segs {
            let (a, b) = (s.get("start").and_then(num).unwrap_or(0.0), s.get("end").and_then(num).unwrap_or(0.0));
            ui.label(RichText::new(format!("{} → {}", fmt_time(a), fmt_time(b))).monospace().color(pal::ACCENT));
            ui.label(s.get("text").and_then(|t| t.as_str()).unwrap_or("").trim());
            ui.end_row();
        }
    });
}

// ================================================================== Generic

fn is_hex_color(s: &str) -> bool {
    let h = s.strip_prefix('#').unwrap_or("");
    (h.len() == 6 || h.len() == 8) && h.chars().all(|c| c.is_ascii_hexdigit())
}

fn walk(v: &Value, depth: usize, path: &str, st: &mut Stats) {
    st.nodes += 1;
    st.max_depth = st.max_depth.max(depth);
    let kind = match v {
        Value::Object(_) => "object",
        Value::Array(_) => "array",
        Value::String(_) => "string",
        Value::Number(_) => "number",
        Value::Bool(_) => "bool",
        Value::Null => "null",
    };
    *st.counts.entry(kind).or_insert(0) += 1;
    match v {
        Value::Object(m) => {
            for (k, c) in m {
                walk(c, depth + 1, &if path.is_empty() { k.clone() } else { format!("{}.{}", path, k) }, st);
            }
        }
        Value::Array(a) => {
            st.arrays.push((path.to_string(), a.len()));
            if a.len() >= 4 && st.numeric.len() < 4 && a.iter().all(|x| x.is_number()) {
                st.numeric.push((path.to_string(), a.iter().filter_map(num).collect()));
            }
            for (i, c) in a.iter().enumerate() {
                walk(c, depth + 1, &format!("{}[{}]", path, i), st);
            }
        }
        Value::String(s) if is_hex_color(s) && st.colors.len() < 240 => st.colors.push((path.to_string(), s.clone())),
        _ => {}
    }
}

fn generic_ui(ui: &mut egui::Ui, data: &Value, st: &mut FormatState, lang: Lang, generation: u64) {
    if st.stats.as_ref().map(|(g, _)| *g != generation).unwrap_or(true) {
        let mut s = Stats::default();
        walk(data, 0, "", &mut s);
        s.arrays.sort_by(|a, b| b.1.cmp(&a.1));
        st.stats = Some((generation, s));
    }
    let s = &st.stats.as_ref().unwrap().1;

    theme::hairline_card(ui, |ui| {
        ui.label(theme::card_section(&l(lang, "STRUCTURE", "ESTRUTURA")));
        let counts: Vec<String> = s.counts.iter().map(|(k, v)| format!("{} {}", v, k)).collect();
        ui.label(format!("{}: {}   |   {}: {}", l(lang, "Nodes", "Nós"), s.nodes, l(lang, "Max depth", "Profundidade"), s.max_depth));
        ui.label(theme::muted(&counts.join("  ·  ")));
        if !s.arrays.is_empty() {
            ui.add_space(4.0);
            ui.label(theme::muted(&l(lang, "Largest arrays:", "Maiores arrays:")));
            for (p, n) in s.arrays.iter().take(5) {
                ui.label(RichText::new(format!("  {}  ({} items)", if p.is_empty() { "root" } else { p }, n)).monospace().size(11.5));
            }
        }
    });

    if !s.colors.is_empty() {
        ui.add_space(6.0);
        theme::hairline_card(ui, |ui| {
            ui.label(theme::card_section(&format!("{} ({})", l(lang, "COLORS FOUND", "CORES ENCONTRADAS"), s.colors.len())));
            ui.horizontal_wrapped(|ui| {
                for (path, hex) in &s.colors {
                    let (r, _) = ui.allocate_exact_size(Vec2::splat(30.0), Sense::hover());
                    ui.painter().rect_filled(r, 4.0, hex_color(hex));
                    ui.painter().rect_stroke(r, 4.0, Stroke::new(1.0, pal::BORDER_LIGHT));
                    ui.interact(r, ui.id().with(path), Sense::hover()).on_hover_text(format!("{}\n{}", hex, path));
                }
            });
        });
    }

    for (path, vals) in &s.numeric {
        ui.add_space(6.0);
        theme::hairline_card(ui, |ui| {
            ui.label(theme::card_section(&format!("{}  ({} {})", if path.is_empty() { "root" } else { path }, vals.len(), l(lang, "values", "valores"))));
            let (resp, painter) = ui.allocate_painter(Vec2::new(ui.available_width(), 80.0), Sense::hover());
            painter.rect_filled(resp.rect, 0.0, pal::WELL);
            let (mn, mx) = vals.iter().fold((f64::MAX, f64::MIN), |(a, b), &v| (a.min(v), b.max(v)));
            let rng = (mx - mn).max(1e-9);
            let pts: Vec<Pos2> = vals
                .iter()
                .enumerate()
                .map(|(i, &v)| {
                    Pos2::new(
                        resp.rect.left() + 6.0 + (resp.rect.width() - 12.0) * i as f32 / (vals.len().max(2) - 1) as f32,
                        resp.rect.bottom() - 6.0 - (resp.rect.height() - 12.0) * ((v - mn) / rng) as f32,
                    )
                })
                .collect();
            painter.add(Shape::line(pts, Stroke::new(1.5, pal::ACCENT)));
            painter.text(resp.rect.left_top() + Vec2::new(6.0, 2.0), Align2::LEFT_TOP, format!("min {:.3}  max {:.3}", mn, mx), FontId::monospace(10.0), pal::FG_MUTED);
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_formats() {
        assert_eq!(detect(&obs_collection_template()), Kind::Obs);
        assert_eq!(detect(&obs_stinger_template()), Kind::Obs);
        assert_eq!(detect(&json!({"v":"5.7","fr":30,"ip":0,"op":60,"w":100,"h":100,"layers":[]})), Kind::Lottie);
        assert_eq!(detect(&json!({"type":"FeatureCollection","features":[]})), Kind::GeoJson);
        assert_eq!(detect(&json!({"segments":[{"start":0.0,"end":1.0,"text":"hi"}]})), Kind::Transcript);
        assert_eq!(detect(&json!({"a":1})), Kind::Generic);
    }

    #[test]
    fn obs_color_roundtrip() {
        let packed = obs_color_pack([10, 20, 30]);
        let c = obs_color(packed);
        assert_eq!((c.r(), c.g(), c.b()), (10, 20, 30));
    }
}
