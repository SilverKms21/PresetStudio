//! Inspector panel (Filmcraft parameters / generic JSON properties) and the keyframe editor window.

use eframe::egui::{self, RichText};
use serde_json::{json, Value};

use crate::engine::*;
use crate::i18n::{tr, trf, Lang};
use crate::jsonx::*;
use crate::theme::{self, pal};

/// Side effects requested by the inspector; applied by the app after the frame.
pub enum InspAction {
    Modified,
    Sync { reset: bool },
    RenderAll { reset: bool },
    Pause,
    Status(String),
    Info(String, String),
    Error(String, String),
}

pub struct InspCtx {
    pub lang: Lang,
    pub cur_t: i64,
    pub frame_ns: f64,
    pub generation: u64,
}

#[derive(Default)]
pub struct InspState {
    pub res_w: String,
    pub res_h: String,
    key: Option<(u64, usize)>,
}

pub fn is_filmcraft_data(data: &Option<Value>) -> bool {
    match data {
        Some(d) => d.get("format").and_then(|v| v.as_str()) == Some("filmcraft.effect-presets") && d.get("presets").map(|p| p.is_array()).unwrap_or(false),
        None => false,
    }
}

pub fn show(
    ui: &mut egui::Ui, data: &mut Option<Value>, sel_preset: &mut usize, sel_effect: &mut usize, st: &mut InspState,
    cx: &InspCtx, out: &mut Vec<InspAction>,
) {
    egui::ScrollArea::vertical().auto_shrink([false, false]).show(ui, |ui| {
        ui.add_space(6.0);
        if data.is_none() {
            ui.add_space(14.0);
            ui.horizontal(|ui| {
                ui.add_space(14.0);
                ui.label(theme::muted(&tr(cx.lang, "inspector_empty")));
            });
            return;
        }
        if is_filmcraft_data(data) {
            filmcraft_editor(ui, data.as_mut().unwrap(), sel_preset, sel_effect, st, cx, out);
        } else {
            generic_editor(ui, data.as_mut().unwrap(), cx);
        }
    });
}

// ------------------------------------------------------------------ Filmcraft editor

fn filmcraft_editor(
    ui: &mut egui::Ui, data: &mut Value, sel_preset: &mut usize, sel_effect: &mut usize, st: &mut InspState,
    cx: &InspCtx, out: &mut Vec<InspAction>,
) {
    let lang = cx.lang;
    let presets_len = data["presets"].as_array().map(|a| a.len()).unwrap_or(0);
    if presets_len == 0 {
        ui.label(tr(lang, "empty_presets_list"));
        return;
    }
    if *sel_preset >= presets_len {
        *sel_preset = 0;
    }

    // ---- Card 1: preset variations
    let names: Vec<String> = data["presets"]
        .as_array()
        .unwrap()
        .iter()
        .enumerate()
        .map(|(i, p)| format!("[{}] {}", i, p.get("name").and_then(|n| n.as_str()).unwrap_or("Untitled")))
        .collect();
    let (mut add_sub, mut del_sub) = (false, false);
    theme::hairline_card(ui, |ui| {
        ui.label(theme::card_section(&tr(lang, "card_variation")));
        ui.horizontal(|ui| {
            let mut idx = *sel_preset;
            egui::ComboBox::from_id_salt("preset_combo")
                .width((ui.available_width() - 70.0).max(80.0))
                .selected_text(names[*sel_preset].clone())
                .show_ui(ui, |ui| {
                    for (i, n) in names.iter().enumerate() {
                        ui.selectable_value(&mut idx, i, n);
                    }
                });
            if idx != *sel_preset {
                *sel_preset = idx;
                *sel_effect = 0;
                out.push(InspAction::Sync { reset: true });
            }
            if ui.button("+").clicked() {
                add_sub = true;
            }
            if theme::danger_button(ui, "✕").clicked() {
                del_sub = true;
            }
        });
    });
    if add_sub {
        let presets = data["presets"].as_array_mut().unwrap();
        let mut clone = presets[*sel_preset].clone();
        let nm = clone.get("name").and_then(|n| n.as_str()).unwrap_or("Preset").to_string();
        clone["name"] = json!(format!("{} (Copy)", nm));
        presets.push(clone);
        *sel_preset = presets.len() - 1;
        out.push(InspAction::Modified);
        out.push(InspAction::RenderAll { reset: true });
        return;
    }
    if del_sub {
        if presets_len <= 1 {
            out.push(InspAction::Info(tr(lang, "dlg_notice"), tr(lang, "dlg_keep_one_preset")));
        } else {
            data["presets"].as_array_mut().unwrap().remove(*sel_preset);
            *sel_preset = sel_preset.saturating_sub(1);
            out.push(InspAction::Modified);
            out.push(InspAction::RenderAll { reset: true });
        }
        return;
    }
    ui.add_space(4.0);

    let preset = &mut data["presets"][*sel_preset];

    // refresh resolution text boxes when the preset / document changed
    let key = (cx.generation, *sel_preset);
    if st.key != Some(key) {
        let (w, h) = src_size_ints(preset);
        st.res_w = w.to_string();
        st.res_h = h.to_string();
        st.key = Some(key);
    }

    // ---- Card 2: properties & resolution
    let mut scale_req = false;
    theme::hairline_card(ui, |ui| {
        ui.label(theme::card_section(&tr(lang, "card_properties")));
        egui::Grid::new("props_grid").num_columns(2).spacing([8.0, 6.0]).show(ui, |ui| {
            ui.label(theme::muted(&tr(lang, "lbl_name")));
            let mut name = preset.get("name").map(value_to_plain).unwrap_or_default();
            if ui.add(egui::TextEdit::singleline(&mut name).desired_width(f32::INFINITY)).changed() {
                preset["name"] = json!(name);
                out.push(InspAction::Modified);
            }
            ui.end_row();

            ui.label(theme::muted(&tr(lang, "lbl_kf_tag")));
            let mut tag = preset.get("keyframes").map(value_to_plain).unwrap_or_default();
            if ui.add(egui::TextEdit::singleline(&mut tag).desired_width(f32::INFINITY)).changed() {
                preset["keyframes"] = json!(tag);
                out.push(InspAction::Modified);
            }
            ui.end_row();

            ui.label(theme::muted(&tr(lang, "lbl_base_res")));
            ui.horizontal(|ui| {
                ui.add(egui::TextEdit::singleline(&mut st.res_w).desired_width(48.0));
                ui.label(theme::muted("×"));
                ui.add(egui::TextEdit::singleline(&mut st.res_h).desired_width(48.0));
                if ui.button(tr(lang, "btn_scale_res")).clicked() {
                    scale_req = true;
                }
            });
            ui.end_row();
        });
    });
    if scale_req {
        apply_resolution_scale(preset, st, cx, out);
    }
    ui.add_space(4.0);

    // ---- Card 3: active effect
    let effects_len = preset.get("effects").and_then(|e| e.as_array()).map(|e| e.len()).unwrap_or(0);
    if effects_len == 0 {
        return;
    }
    if *sel_effect >= effects_len {
        *sel_effect = 0;
    }
    let eff_names: Vec<String> = preset["effects"]
        .as_array()
        .unwrap()
        .iter()
        .enumerate()
        .map(|(i, e)| format!("[{}] {}", i, e.get("effect").and_then(|x| x.as_str()).unwrap_or("unknown")))
        .collect();
    let eff_idx = *sel_effect;

    theme::hairline_card(ui, |ui| {
        let effect = &mut preset["effects"][eff_idx];
        ui.horizontal(|ui| {
            ui.label(theme::card_section(&tr(lang, "card_active_effect")));
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                let mut en = effect.get("enabled").and_then(|v| v.as_bool()).unwrap_or(true);
                if ui.checkbox(&mut en, tr(lang, "chk_enabled")).changed() {
                    effect["enabled"] = json!(en);
                    out.push(InspAction::Modified);
                }
            });
        });
        let mut new_eff = eff_idx;
        egui::ComboBox::from_id_salt("effect_combo")
            .width(ui.available_width() - 8.0)
            .selected_text(eff_names[eff_idx].clone())
            .show_ui(ui, |ui| {
                for (i, n) in eff_names.iter().enumerate() {
                    ui.selectable_value(&mut new_eff, i, n);
                }
            });
        if new_eff != eff_idx {
            *sel_effect = new_eff;
        }
        theme::separator_line(ui);
        ui.add_space(4.0);

        let Some(params) = effect.get_mut("params").and_then(|p| p.as_object_mut()) else { return };
        let priority = [
            "text", "font", "font_style", "caps", "size", "position", "scale", "scale_width", "uniform_scale", "rotation",
            "anchor", "anti_flicker", "fill", "fill_color", "stroke", "stroke_color", "stroke_width", "background",
            "background_color", "background_opacity", "background_size", "shadow", "shadow_color", "shadow_distance", "opacity",
        ];
        let mut others: Vec<String> = params.keys().filter(|k| !priority.contains(&k.as_str())).cloned().collect();
        others.sort();
        let ordered: Vec<String> =
            priority.iter().filter(|k| params.contains_key(**k)).map(|k| k.to_string()).chain(others).collect();

        let group_order = ["Transform", "Text & Typography", "Fill & Outline", "Background & Shadow", "Other"];
        let mut groups: Vec<Vec<String>> = vec![vec![]; 5];
        for key in &ordered {
            let low = key.to_lowercase();
            let g = if ["position", "scale", "scale_width", "uniform_scale", "rotation", "anchor", "anti_flicker"].contains(&low.as_str()) {
                0
            } else if ["font", "text", "caps", "tracking", "kerning", "leading", "baseline", "vertical", "align", "size"]
                .iter()
                .any(|t| low.contains(t))
            {
                1
            } else if ["fill", "stroke", "color", "gradient", "opacity"].iter().any(|t| low.contains(t))
                && !low.starts_with("background")
                && !low.starts_with("shadow")
            {
                2
            } else if low.starts_with("background") || low.starts_with("shadow") {
                3
            } else {
                4
            };
            groups[g].push(key.clone());
        }
        let pt = lang == Lang::Pt;
        let titles = [
            if pt { "TRANSFORMAÇÃO" } else { "TRANSFORM" },
            if pt { "TEXTO E TIPOGRAFIA" } else { "TEXT & TYPOGRAPHY" },
            if pt { "PREENCHIMENTO E CONTORNO" } else { "FILL & OUTLINE" },
            if pt { "FUNDO E SOMBRA" } else { "BACKGROUND & SHADOW" },
            if pt { "OUTROS" } else { "OTHER" },
        ];

        for (gi, gname) in group_order.iter().enumerate() {
            let valid: Vec<&String> = groups[gi]
                .iter()
                .filter(|k| {
                    params
                        .get(k.as_str())
                        .and_then(|p| p.get("value"))
                        .and_then(|v| v.as_object())
                        .map(|o| !o.is_empty())
                        .unwrap_or(false)
                })
                .collect();
            if valid.is_empty() {
                continue;
            }
            ui.add_space(4.0);
            egui::Frame::none()
                .fill(pal::CARD)
                .stroke(egui::Stroke::new(1.0, pal::BORDER))
                .inner_margin(egui::Margin::same(8.0))
                .show(ui, |ui| {
                    ui.set_width(ui.available_width());
                    ui.label(theme::card_section(titles[gi]));
                    egui::Grid::new((*gname, eff_idx)).num_columns(2).spacing([8.0, 6.0]).show(ui, |ui| {
                        for key in valid {
                            let p = params.get_mut(key.as_str()).unwrap();
                            let has_kf = has_keyframes(p);
                            let label = if has_kf {
                                format!("{} ({})", key, p["keyframes"].as_array().map(|a| a.len()).unwrap_or(0))
                            } else {
                                key.clone()
                            };
                            ui.label(theme::muted(&label));
                            ui.horizontal(|ui| param_widget(ui, key, p, eff_idx, cx, out));
                            ui.end_row();
                        }
                    });
                });
        }
    });
}

fn value_to_plain(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        other => other.to_string(),
    }
}

fn apply_resolution_scale(preset: &mut Value, st: &mut InspState, cx: &InspCtx, out: &mut Vec<InspAction>) {
    let lang = cx.lang;
    let parsed = (st.res_w.trim().parse::<i64>(), st.res_h.trim().parse::<i64>());
    let (new_w, new_h) = match parsed {
        (Ok(w), Ok(h)) if w > 0 && h > 0 => (w, h),
        _ => {
            out.push(InspAction::Error(tr(lang, "dlg_error"), tr(lang, "dlg_invalid_res")));
            return;
        }
    };
    let (old_w, old_h) = match preset.get("source_size").and_then(|v| v.as_array()) {
        Some(a) if a.len() >= 2 => (a[0].as_f64().unwrap_or(1920.0), a[1].as_f64().unwrap_or(1080.0)),
        _ => (1920.0, 1080.0),
    };
    let scale_x = new_w as f64 / if old_w == 0.0 { 1920.0 } else { old_w };
    let scale_y = new_h as f64 / if old_h == 0.0 { 1080.0 } else { old_h };

    preset["source_size"] = json!([new_w, new_h]);
    let scale_vec = |v: &mut Value| {
        if let Some(obj) = v.as_object_mut() {
            let x = obj.get("x").and_then(num).unwrap_or(0.0);
            let y = obj.get("y").and_then(num).unwrap_or(0.0);
            obj.insert("x".into(), json!(round_to(x * scale_x, 4)));
            obj.insert("y".into(), json!(round_to(y * scale_y, 4)));
        }
    };
    if let Some(effs) = preset.get_mut("effects").and_then(|e| e.as_array_mut()) {
        for eff in effs {
            let Some(params) = eff.get_mut("params").and_then(|p| p.as_object_mut()) else { continue };
            for vec_key in ["position", "anchor"] {
                let Some(v_obj) = params.get_mut(vec_key) else { continue };
                if let Some(vec) = v_obj.get_mut("value").and_then(|v| v.get_mut("Vec2")) {
                    scale_vec(vec);
                }
                if let Some(kfs) = v_obj.get_mut("keyframes").and_then(|k| k.as_array_mut()) {
                    for kf in kfs {
                        if let Some(kvec) = kf.get_mut("value").and_then(|v| v.get_mut("Vec2")) {
                            scale_vec(kvec);
                        }
                    }
                }
            }
        }
    }
    out.push(InspAction::Modified);
    out.push(InspAction::RenderAll { reset: false });
    out.push(InspAction::Status(trf(lang, "status_res_scaled", &[("w", new_w.to_string()), ("h", new_h.to_string())])));
}

fn write_keyframed(p: &mut Value, tag: &str, new_val: Value, cx: &InspCtx, out: &mut Vec<InspAction>) {
    out.push(InspAction::Pause);
    let t = cx.cur_t;
    let tol = (cx.frame_ns / 2.0) as i64;
    if !p.get("keyframes").map(|k| k.is_array()).unwrap_or(false) {
        p["keyframes"] = json!([]);
    }
    let kfs = p.get_mut("keyframes").and_then(|k| k.as_array_mut()).unwrap();
    match kfs.iter().position(|kf| (kf_time(kf) as i64 - t).abs() <= tol) {
        None => {
            let prev_interp = kfs
                .iter()
                .filter(|kf| (kf_time(kf) as i64) < t)
                .max_by(|a, b| kf_time(a).partial_cmp(&kf_time(b)).unwrap_or(std::cmp::Ordering::Equal))
                .and_then(|kf| kf.get("interp").and_then(|v| v.as_str()).map(|s| s.to_string()))
                .unwrap_or_else(|| "AutoBezier".into());
            kfs.push(json!({
                "time": t,
                "value": { tag: new_val },
                "interp": prev_interp,
                "out_influence": 1.0 / 3.0,
                "in_influence": 1.0 / 3.0,
            }));
            sort_keyframes(kfs);
        }
        Some(i) => {
            let kf = &mut kfs[i];
            if !kf.get("value").map(|v| v.is_object()).unwrap_or(false) {
                kf["value"] = json!({});
            }
            kf["value"][tag] = new_val;
        }
    }
    out.push(InspAction::Modified);
    out.push(InspAction::Sync { reset: false });
}

/// One parameter row: value editor + keyframe toggle (opens the keyframe editor).
fn param_widget(ui: &mut egui::Ui, key: &str, p: &mut Value, eff_idx: usize, cx: &InspCtx, out: &mut Vec<InspAction>) {
    let lang = cx.lang;
    let t = cx.cur_t as f64;
    let Some((tag, raw)) = p.get("value").and_then(|v| v.as_object()).and_then(|o| o.iter().next()).map(|(k, v)| (k.clone(), v.clone())) else {
        return;
    };
    let has_kf = has_keyframes(p);

    match tag.as_str() {
        "Bool" => {
            let mut b = raw.as_bool().unwrap_or(false);
            let label = if b { tr(lang, "chk_active") } else { tr(lang, "chk_inactive") };
            if ui.checkbox(&mut b, label).changed() {
                set_in_value_obj(p, "Bool", json!(b));
                out.push(InspAction::Modified);
            }
        }
        "Text" => {
            let mut s = value_to_plain(&raw);
            if ui.add(egui::TextEdit::singleline(&mut s).desired_width(ui.available_width().max(60.0) - 30.0)).changed() {
                set_in_value_obj(p, "Text", json!(s));
                out.push(InspAction::Modified);
            }
        }
        "Float" => {
            let mut v = eval_f64(Some(p), t).or_else(|| num(&raw)).unwrap_or(0.0);
            if ui.add(egui::DragValue::new(&mut v).speed(0.5).max_decimals(4)).changed() {
                if has_kf {
                    write_keyframed(p, "Float", json!(v), cx, out);
                } else {
                    set_in_value_obj(p, "Float", json!(v));
                    out.push(InspAction::Modified);
                }
            }
        }
        "Choice" => {
            let mut v = num(&raw).map(|x| x as i64).unwrap_or(0);
            if ui.add(egui::DragValue::new(&mut v)).changed() {
                set_in_value_obj(p, "Choice", json!(v));
                out.push(InspAction::Modified);
            }
        }
        "Color" => {
            let hex = rgba_float_to_hex(&raw);
            let (r, g, b) = parse_hex(&hex);
            let mut rgb = [r, g, b];
            if egui::color_picker::color_edit_button_srgb(ui, &mut rgb).changed() {
                let alpha = value_to_rgba(&raw).map(|c| c[3]).unwrap_or(1.0);
                let new_hex = format!("#{:02x}{:02x}{:02x}", rgb[0], rgb[1], rgb[2]);
                set_in_value_obj(p, "Color", json!(hex_to_rgba_float(&new_hex, alpha)));
                out.push(InspAction::Modified);
            }
            let shown = rgba_float_to_hex(p.get("value").and_then(|v| v.get("Color")).unwrap_or(&raw)).to_uppercase();
            ui.label(RichText::new(shown).monospace().size(11.0));
        }
        "Vec2" if raw.is_object() => {
            let (mut x, mut y) = eval_vec2(Some(p), t)
                .unwrap_or((raw.get("x").and_then(num).unwrap_or(0.0), raw.get("y").and_then(num).unwrap_or(0.0)));
            ui.label(theme::muted("X"));
            let cx_ = ui.add(egui::DragValue::new(&mut x).speed(0.5).max_decimals(4)).changed();
            ui.label(theme::muted("Y"));
            let cy_ = ui.add(egui::DragValue::new(&mut y).speed(0.5).max_decimals(4)).changed();
            if cx_ || cy_ {
                if has_kf {
                    write_keyframed(p, "Vec2", vec2(x, y), cx, out);
                } else if let Some(v) = p.get_mut("value").and_then(|v| v.get_mut("Vec2")).and_then(|v| v.as_object_mut()) {
                    v.insert("x".into(), json!(x));
                    v.insert("y".into(), json!(y));
                    out.push(InspAction::Modified);
                }
            }
        }
        _ => {
            ui.label(theme::muted(&raw.to_string()));
        }
    }

    if tag == "Float" || tag == "Vec2" {
        if theme::keyframe_button(ui, has_kf).clicked() {
            out.push(InspAction::Pause);
            ui.memory_mut(|m| {
                m.data.insert_temp(egui::Id::new("open_kf_editor"), (eff_idx, key.to_string(), tag.clone()));
            });
        }
    }
}

/// Returns a pending "open keyframe editor" request raised by `param_widget`.
pub fn take_open_kf_request(ctx: &egui::Context) -> Option<(usize, String, String)> {
    ctx.memory_mut(|m| m.data.remove_temp::<(usize, String, String)>(egui::Id::new("open_kf_editor")))
}

// ------------------------------------------------------------------ generic JSON editor

fn generic_editor(ui: &mut egui::Ui, data: &mut Value, cx: &InspCtx) {
    let lang = cx.lang;
    theme::hairline_card(ui, |ui| {
        ui.label(theme::card_section(&tr(lang, "card_generic_props")));
        ui.add_space(4.0);
        let Some(obj) = data.as_object_mut() else {
            ui.label(tr(lang, "generic_non_dict"));
            return;
        };
        egui::Grid::new("generic_grid").num_columns(2).spacing([8.0, 6.0]).show(ui, |ui| {
            for (key, val) in obj.iter_mut() {
                match val {
                    Value::Object(sub) => {
                        ui.label(theme::card_section(&key.to_uppercase()));
                        ui.label("");
                        ui.end_row();
                        for (sk, sv) in sub.iter_mut() {
                            if is_primitive(sv) {
                                ui.label(theme::muted(&format!("  {}", sk)));
                                primitive_editor(ui, sv, lang);
                                ui.end_row();
                            }
                        }
                    }
                    v if is_primitive(v) => {
                        ui.label(theme::muted(key));
                        primitive_editor(ui, v, lang);
                        ui.end_row();
                    }
                    _ => {}
                }
            }
        });
    });
}

fn is_primitive(v: &Value) -> bool {
    matches!(v, Value::String(_) | Value::Number(_) | Value::Bool(_))
}

fn primitive_editor(ui: &mut egui::Ui, v: &mut Value, lang: Lang) {
    match v {
        Value::Bool(b) => {
            ui.checkbox(b, tr(lang, "chk_enabled"));
        }
        Value::String(s) => {
            ui.add(egui::TextEdit::singleline(s).desired_width(f32::INFINITY));
        }
        Value::Number(n) => {
            if n.is_i64() || n.is_u64() {
                let mut i = n.as_i64().unwrap_or(0);
                if ui.add(egui::DragValue::new(&mut i)).changed() {
                    *v = json!(i);
                }
            } else {
                let mut f = n.as_f64().unwrap_or(0.0);
                if ui.add(egui::DragValue::new(&mut f).speed(0.05).max_decimals(6)).changed() {
                    *v = json!(f);
                }
            }
        }
        _ => {}
    }
}

// ------------------------------------------------------------------ keyframe editor window

#[derive(Clone, Default)]
struct KfRow {
    t: String,
    a: String,
    b: String,
}

pub struct KfEditor {
    eff: usize,
    key: String,
    tag: String,
    rows: Vec<KfRow>,
}

fn param_of<'a>(data: &'a mut Option<Value>, preset: usize, eff: usize, key: &str) -> Option<&'a mut Value> {
    data.as_mut()?.get_mut("presets")?.get_mut(preset)?.get_mut("effects")?.get_mut(eff)?.get_mut("params")?.get_mut(key)
}

fn build_rows(kfs: &[Value], tag: &str) -> Vec<KfRow> {
    kfs.iter()
        .map(|kf| {
            let t = format!("{:.3}", kf_time(kf) / 1e9);
            if tag == "Float" {
                let v = kf.get("value").and_then(|v| v.get("Float")).and_then(num).unwrap_or(0.0);
                KfRow { t, a: format!("{:?}", v), b: String::new() }
            } else {
                let vec = kf.get("value").and_then(|v| v.get("Vec2"));
                let g = |k: &str| vec.and_then(|v| v.get(k)).and_then(num).unwrap_or(0.0);
                KfRow { t, a: format!("{:?}", g("x")), b: format!("{:?}", g("y")) }
            }
        })
        .collect()
}

/// Opens the editor; creates two default keyframes when the parameter has none.
pub fn open_kf_editor(
    data: &mut Option<Value>, sel_preset: usize, eff: usize, key: &str, tag: &str, out: &mut Vec<InspAction>,
) -> Option<KfEditor> {
    let p = param_of(data, sel_preset, eff, key)?;
    if !has_keyframes(p) {
        let base = p.get("value").and_then(|v| v.get(tag)).cloned().unwrap_or(json!(0.0));
        p["keyframes"] = json!([
            {"time": 0, "value": {tag: base.clone()}, "interp": "AutoBezier", "out_influence": 1.0 / 3.0, "in_influence": 1.0 / 3.0},
            {"time": 1500000000, "value": {tag: base}, "interp": "ContinuousBezier", "out_influence": 1.0 / 3.0, "in_influence": 1.0 / 3.0},
        ]);
        out.push(InspAction::Modified);
        out.push(InspAction::Sync { reset: false });
    }
    let rows = build_rows(p["keyframes"].as_array().unwrap(), tag);
    Some(KfEditor { eff, key: key.to_string(), tag: tag.to_string(), rows })
}

/// Draws the editor window. Returns `false` once it should be closed.
pub fn show_kf_editor(
    ctx: &egui::Context, ed: &mut KfEditor, data: &mut Option<Value>, sel_preset: usize, cx: &InspCtx,
    out: &mut Vec<InspAction>, viewer_seek: &mut Option<i64>,
) -> bool {
    let lang = cx.lang;
    let mut open = true;
    let mut close_after = false;
    let title = trf(lang, "kf_win_title", &[("param", ed.key.clone()), ("tag", ed.tag.clone())]);
    egui::Window::new(title)
        .id(egui::Id::new("kf_editor_window"))
        .default_size([640.0, 400.0])
        .collapsible(false)
        .open(&mut open)
        .show(ctx, |ui| {
            ui.label(theme::section_tag(&trf(lang, "kf_header", &[("param", ed.key.to_uppercase())])));
            ui.add_space(4.0);

            let Some(p) = param_of(data, sel_preset, ed.eff, &ed.key) else {
                close_after = true;
                return;
            };
            let tag = ed.tag.clone();
            let mut remove: Option<usize> = None;

            egui::ScrollArea::vertical().max_height(300.0).auto_shrink([false, true]).show(ui, |ui| {
                let kfs_len = p.get("keyframes").and_then(|k| k.as_array()).map(|a| a.len()).unwrap_or(0);
                if ed.rows.len() != kfs_len {
                    ed.rows = build_rows(p["keyframes"].as_array().unwrap(), &tag);
                }
                for idx in 0..kfs_len {
                    theme::hairline_card(ui, |ui| {
                        ui.horizontal(|ui| {
                            let mut changed = false;
                            let lbl = ui.add(
                                egui::Label::new(RichText::new(trf(lang, "kf_time_lbl", &[("idx", (idx + 1).to_string())])))
                                    .sense(egui::Sense::click()),
                            );
                            if lbl.clicked() {
                                out.push(InspAction::Pause);
                                let t = kf_time(&p["keyframes"][idx]) as i64;
                                *viewer_seek = Some(t);
                            }
                            let row = &mut ed.rows[idx];
                            changed |= ui.add(egui::TextEdit::singleline(&mut row.t).desired_width(56.0)).changed();

                            let mut interp = p["keyframes"][idx].get("interp").and_then(|v| v.as_str()).unwrap_or("AutoBezier").to_string();
                            let before = interp.clone();
                            egui::ComboBox::from_id_salt(("interp", idx)).width(120.0).selected_text(interp.clone()).show_ui(ui, |ui| {
                                for o in ["AutoBezier", "ContinuousBezier", "Linear", "Hold"] {
                                    ui.selectable_value(&mut interp, o.to_string(), o);
                                }
                            });
                            let interp_changed = interp != before;
                            changed |= interp_changed;

                            if tag == "Float" {
                                ui.label(theme::muted(&tr(lang, "kf_val_lbl")));
                                changed |= ui.add(egui::TextEdit::singleline(&mut row.a).desired_width(70.0)).changed();
                            } else {
                                ui.label(theme::muted("X:"));
                                changed |= ui.add(egui::TextEdit::singleline(&mut row.a).desired_width(60.0)).changed();
                                ui.label(theme::muted("Y:"));
                                changed |= ui.add(egui::TextEdit::singleline(&mut row.b).desired_width(60.0)).changed();
                            }

                            if changed {
                                let t_ok = row.t.trim().parse::<f64>().ok();
                                let a_ok = row.a.trim().parse::<f64>().ok();
                                let b_ok = if tag == "Float" { Some(0.0) } else { row.b.trim().parse::<f64>().ok() };
                                if let (Some(tt), Some(a), Some(b)) = (t_ok, a_ok, b_ok) {
                                    let kf = &mut p["keyframes"][idx];
                                    kf["time"] = json!((tt * 1e9).round() as i64);
                                    if !kf.get("value").map(|v| v.is_object()).unwrap_or(false) {
                                        kf["value"] = json!({});
                                    }
                                    if tag == "Float" {
                                        kf["value"]["Float"] = json!(a);
                                    } else {
                                        kf["value"]["Vec2"] = vec2(a, b);
                                    }
                                    kf["interp"] = json!(interp);
                                    out.push(InspAction::Modified);
                                    out.push(InspAction::Sync { reset: false });
                                }
                            }

                            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                if theme::danger_button(ui, "✕").clicked() {
                                    remove = Some(idx);
                                }
                            });
                        });
                    });
                    ui.add_space(2.0);
                }
            });

            if let Some(i) = remove {
                let kfs = p["keyframes"].as_array_mut().unwrap();
                if kfs.len() <= 1 {
                    if let Some(o) = p.as_object_mut() {
                        o.shift_remove("keyframes");
                    }
                    out.push(InspAction::Modified);
                    out.push(InspAction::RenderAll { reset: false });
                    close_after = true;
                } else {
                    kfs.remove(i);
                    ed.rows = build_rows(p["keyframes"].as_array().unwrap(), &tag);
                    out.push(InspAction::Modified);
                    out.push(InspAction::Sync { reset: false });
                }
            }

            ui.add_space(6.0);
            ui.horizontal(|ui| {
                if theme::accent_button(ui, &tr(lang, "btn_add_kf_row")).clicked() {
                    if !p.get("keyframes").map(|k| k.is_array()).unwrap_or(false) {
                        p["keyframes"] = json!([]);
                    }
                    let base_val = p.get("value").cloned().unwrap_or(json!({}));
                    let kfs = p["keyframes"].as_array_mut().unwrap();
                    let mut last = kfs.last().cloned().unwrap_or_else(|| json!({"time": 0, "value": base_val}));
                    last["time"] = json!(kf_time(&last) as i64 + 500_000_000);
                    kfs.push(last);
                    ed.rows = build_rows(p["keyframes"].as_array().unwrap(), &tag);
                    out.push(InspAction::Modified);
                    out.push(InspAction::Sync { reset: false });
                }
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.button(tr(lang, "btn_done")).clicked() {
                        close_after = true;
                    }
                });
            });
        });
    open && !close_after
}
