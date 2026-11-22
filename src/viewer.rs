//! NLE compositing viewer (DaVinci Resolve style):
//! oriented bounding-box gizmo (move / corner scale / edge scale / rotate), anchor gizmo,
//! spatial motion-path keyframe dragging, zoom & pan, magnetic snap guides, live HUD,
//! auto-key and an interactive keyframe timeline.

use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};

use eframe::egui::{
    self, text::LayoutJob, Align2, Color32, CursorIcon, FontId, Galley, Mesh, Painter, PointerButton, Pos2, Rect,
    RichText, Sense, Shape, Stroke, TextFormat, Vec2,
};
use serde_json::{json, Value};

use crate::engine::*;
use crate::i18n::{tr, Lang};
use crate::jsonx::*;
use crate::theme::{self, hex_color, pal};

pub const OBJ_KEYS: [&str; 9] = [
    "obj_auto", "obj_text", "obj_rect", "obj_square", "obj_circle", "obj_triangle", "obj_diamond", "obj_star",
    "obj_block_text",
];
pub const BG_KEYS: [&str; 3] = ["bg_dark", "bg_checker", "bg_chroma"];
const SPEEDS: [&str; 6] = ["1x", "2x", "5x", "10x", "50x", "100x"];
const ZOOMS: [&str; 6] = ["25%", "50%", "75%", "100%", "150%", "200%"];

const TL_PAD: f64 = 12.0;
const TL_RULER_H: f64 = 24.0;
const TL_LABEL_W: f64 = 118.0;
const TL_ROW_H: f64 = 24.0;
const NS: f64 = 1_000_000_000.0;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Tool {
    Transform,
    Anchor,
    Path,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum DragMode {
    Move,
    ScaleCorner,
    ScaleX,
    ScaleY,
    Rotate,
    Anchor,
    PathKf,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Justify {
    Left,
    Center,
    Right,
}

#[derive(Clone, Copy, Debug)]
pub struct MotionTf {
    pub has_motion: bool,
    pub anchor_x: f64,
    pub anchor_y: f64,
    pub pos_x: f64,
    pub pos_y: f64,
    pub sx: f64,
    pub sy: f64,
    pub rot_deg: f64,
}

impl MotionTf {
    fn apply(&self, x: f64, y: f64) -> (f64, f64) {
        transform_point_2d(x, y, self.anchor_x, self.anchor_y, self.pos_x, self.pos_y, self.sx, self.sy, self.rot_deg)
    }
}

#[derive(Clone, Debug)]
pub struct BoxInfo {
    pub eff_idx: usize,
    pub is_motion: bool,
    pub base_w: f64,
    pub base_h: f64,
    pub anchor: (f64, f64),
    pub pos: (f64, f64),
    pub sx: f64,
    pub sy: f64,
    pub rot_deg: f64,
    pub world_corners: Vec<(f64, f64)>,
    pub pivot_world: (f64, f64),
}

/// Stage layout in canvas-local coordinates.
#[derive(Clone, Copy, Debug)]
struct Stage {
    src_w: f64,
    src_h: f64,
    x0: f64,
    y0: f64,
    ratio: f64,
}

struct Track {
    eff_idx: usize,
    eff_name: String,
    name: String,
    /// Indices (into the original keyframes array) of keyframes with a numeric time.
    kfs: Vec<usize>,
}

#[derive(Clone)]
struct DragState {
    mode: DragMode,
    /// (effect index, original keyframe index) when dragging a motion-path node.
    kf_ref: Option<(usize, usize)>,
    start_canvas: (f64, f64),
    start_pos: (f64, f64),
    start_anchor: (f64, f64),
}

#[derive(Clone)]
struct TlDrag {
    eff_idx: usize,
    param: String,
    kf_idx: usize,
}

struct PathNode {
    x: f64,
    y: f64,
    eff_idx: usize,
    kf_idx: usize,
    time: i64,
}

#[derive(Default)]
struct Gizmos {
    path_curve: Vec<(f64, f64)>,
    path_nodes: Vec<PathNode>,
    box_poly: Vec<(f64, f64)>,
    handles: HashMap<String, (f64, f64)>,
    box_info: Option<BoxInfo>,
}

fn or_nz(v: Option<f64>, default: f64) -> f64 {
    match v {
        Some(x) if x != 0.0 => x,
        _ => default,
    }
}

fn uniform_flag(eff: &Value, t: f64) -> bool {
    match param(eff, "uniform_scale") {
        Some(p) => eval_bool(Some(p), t),
        None => true,
    }
}

fn active_effect_index(preset: &Value) -> Option<usize> {
    let effs = effects(preset);
    for preferred in ["motion", "graphic_text"] {
        if let Some(i) = effs.iter().position(|e| eff_enabled(e) && eff_type(e) == preferred) {
            return Some(i);
        }
    }
    None
}

pub fn fmt_tc(seconds: f64) -> String {
    let mins = (seconds / 60.0).floor() as i64;
    let secs = seconds % 60.0;
    format!("{:02}:{:05.2}", mins, secs)
}

fn title_case(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut prev_alpha = false;
    for ch in s.chars() {
        if ch.is_alphabetic() {
            if prev_alpha {
                out.extend(ch.to_lowercase());
            } else {
                out.extend(ch.to_uppercase());
            }
            prev_alpha = true;
        } else {
            out.push(ch);
            prev_alpha = false;
        }
    }
    out
}

pub struct Viewer {
    pub is_playing: bool,
    pub current_time_ns: i64,
    pub duration_ns: i64,
    pub fps: i64,
    last_tick: Instant,

    zoom_factor: f64,
    zoom_fit: bool,
    zoom_text: String,
    pan: (f64, f64),
    panning: bool,

    pub guides: bool,
    pub thirds: bool,
    pub anchor_on: bool,
    pub path_on: bool,
    pub snap: bool,
    pub auto_key: bool,
    pub loop_play: bool,
    pub speed: String,
    pub bg_mode: usize,
    pub obj_mode: usize,
    pub example_color: [u8; 3],
    pub example_text: String,
    pub shape_w: String,
    pub shape_h: String,
    active_tool: Tool,

    res_badge: String,
    hud_metrics: String,
    cursor_coords: String,

    stage: Option<Stage>,
    gizmos: Gizmos,
    drag: Option<DragState>,
    snap_lines: Vec<(bool, f64)>, // (vertical?, coord)
    tl_dragging: bool,
    tl_drag: Option<TlDrag>,
    tl_sel: Option<TlDrag>,
    modified: bool,
    stage_bg_hex: String,
}

impl Default for Viewer {
    fn default() -> Self {
        Self::new()
    }
}

impl Viewer {
    pub fn new() -> Self {
        Viewer {
            is_playing: true,
            current_time_ns: 0,
            duration_ns: 3_000_000_000,
            fps: 30,
            last_tick: Instant::now(),
            zoom_factor: 1.0,
            zoom_fit: true,
            zoom_text: "100%".into(),
            pan: (0.0, 0.0),
            panning: false,
            guides: true,
            thirds: false,
            anchor_on: true,
            path_on: true,
            snap: true,
            auto_key: true,
            loop_play: true,
            speed: "1x".into(),
            bg_mode: 0,
            obj_mode: 0,
            example_color: [0xe8, 0x94, 0x3a],
            example_text: String::new(),
            shape_w: "460".into(),
            shape_h: "240".into(),
            active_tool: Tool::Transform,
            res_badge: "1920 × 1080  •  3.00s".into(),
            hud_metrics: String::new(),
            cursor_coords: "XY: 0, 0".into(),
            stage: None,
            gizmos: Gizmos::default(),
            drag: None,
            snap_lines: vec![],
            tl_dragging: false,
            tl_drag: None,
            tl_sel: None,
            modified: false,
            stage_bg_hex: "#0a0b0d".into(),
        }
    }

    /// Returns (and clears) the "preset was modified by the viewer" flag.
    pub fn take_modified(&mut self) -> bool {
        std::mem::take(&mut self.modified)
    }

    pub fn frame_ns(&self) -> f64 {
        NS / self.fps.max(1) as f64
    }

    fn example_color_hex(&self) -> String {
        format!("#{:02x}{:02x}{:02x}", self.example_color[0], self.example_color[1], self.example_color[2])
    }

    // ---------------------------------------------------------------- preset & duration

    pub fn set_preset(&mut self, preset: Option<&Value>, reset_time: bool) {
        self.recalculate_duration(preset);
        if reset_time || self.current_time_ns > self.duration_ns {
            self.current_time_ns = 0;
        }
        self.last_tick = Instant::now();
    }

    fn recalculate_duration(&mut self, preset: Option<&Value>) {
        let Some(preset) = preset.filter(|p| p.is_object()) else {
            self.duration_ns = 3_000_000_000;
            return;
        };
        let mut max_kf_ns: i64 = 0;
        for eff in effects(preset) {
            if let Some(params) = eff.get("params").and_then(|p| p.as_object()) {
                for p_obj in params.values() {
                    if let Some(kfs) = p_obj.get("keyframes").and_then(|k| k.as_array()) {
                        for kf in kfs {
                            if let Some(t) = kf.get("time").and_then(num) {
                                if t as i64 > max_kf_ns {
                                    max_kf_ns = t as i64;
                                }
                            }
                        }
                    }
                }
            }
        }
        let src_dur = preset.get("source_duration").and_then(num).map(|v| v as i64).unwrap_or(3_000_000_000);
        self.duration_ns = if max_kf_ns > 0 { max_kf_ns } else { 1_000_000_000.max(src_dur.min(10_000_000_000)) };

        let dur_sec = self.duration_ns as f64 / NS;
        if dur_sec > 120.0 && self.speed == "1x" {
            self.speed = "50x".into();
        } else if dur_sec <= 15.0 && (self.speed == "50x" || self.speed == "100x") {
            self.speed = "1x".into();
        }
        let (w, h) = src_size_ints(preset);
        self.res_badge = format!("{} × {}  •  {:.2}s", w, h, dur_sec);
    }

    // ---------------------------------------------------------------- playback

    fn tick(&mut self, ctx: &egui::Context, has_preset: bool) {
        let now = Instant::now();
        let dt = (now - self.last_tick).as_secs_f64().min(0.25);
        self.last_tick = now;
        if !(self.is_playing && has_preset) {
            return;
        }
        let speed_mult = self.speed.trim_end_matches('x').parse::<f64>().unwrap_or(1.0);
        self.current_time_ns += (dt * speed_mult * NS) as i64;
        if self.current_time_ns >= self.duration_ns {
            if self.loop_play {
                self.current_time_ns %= self.duration_ns.max(1);
            } else {
                self.current_time_ns = self.duration_ns;
                self.is_playing = false;
            }
        }
        if self.is_playing {
            ctx.request_repaint_after(Duration::from_millis(16));
        }
    }

    pub fn toggle_play(&mut self) {
        self.is_playing = !self.is_playing;
        self.last_tick = Instant::now();
    }

    pub fn pause(&mut self) {
        self.is_playing = false;
    }

    pub fn restart(&mut self) {
        self.current_time_ns = 0;
        self.last_tick = Instant::now();
    }

    pub fn seek(&mut self, t_ns: i64) {
        self.current_time_ns = t_ns.clamp(0, self.duration_ns);
        self.last_tick = Instant::now();
    }

    pub fn step_frames(&mut self, n: i64) {
        self.pause();
        let fps = self.fps.max(1) as f64;
        let idx = (self.current_time_ns as f64 * fps / NS).round() as i64;
        self.seek(((idx + n) as f64 * NS / fps).round() as i64);
    }

    pub fn jump_keyframe(&mut self, direction: i32, preset: Option<&Value>) {
        let Some(preset) = preset else { return };
        let mut times: Vec<i64> = Vec::new();
        for track in self.collect_tracks(preset) {
            let kfs = param(&effects(preset)[track.eff_idx], &track.name)
                .and_then(|p| p.get("keyframes"))
                .and_then(|k| k.as_array());
            if let Some(kfs) = kfs {
                times.extend(track.kfs.iter().filter_map(|&i| kfs.get(i)).map(|k| kf_time(k) as i64));
            }
        }
        times.sort_unstable();
        times.dedup();
        let cur = self.current_time_ns as f64;
        let tol = self.frame_ns() / 2.0;
        let target = if direction > 0 {
            times.iter().copied().find(|&t| t as f64 > cur + tol)
        } else {
            times.iter().copied().rev().find(|&t| (t as f64) < cur - tol)
        };
        if let Some(t) = target {
            self.pause();
            self.seek(t);
        }
    }

    pub fn go_to_start(&mut self) {
        self.pause();
        self.seek(0);
    }

    pub fn go_to_end(&mut self) {
        self.pause();
        self.seek(self.duration_ns);
    }

    // ---------------------------------------------------------------- tracks / timeline helpers

    fn collect_tracks(&self, preset: &Value) -> Vec<Track> {
        let mut tracks = Vec::new();
        for (eff_idx, eff) in effects(preset).iter().enumerate() {
            if !eff.is_object() || !eff_enabled(eff) {
                continue;
            }
            let eff_name = eff
                .get("effect")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string())
                .unwrap_or_else(|| format!("Effect {}", eff_idx + 1));
            if let Some(params) = eff.get("params").and_then(|p| p.as_object()) {
                for (key, p) in params {
                    let Some(kfs) = p.get("keyframes").and_then(|k| k.as_array()) else { continue };
                    let valid: Vec<usize> = kfs
                        .iter()
                        .enumerate()
                        .filter(|(_, kf)| kf.is_object() && kf.get("time").and_then(num).is_some())
                        .map(|(i, _)| i)
                        .collect();
                    if !valid.is_empty() {
                        tracks.push(Track { eff_idx, eff_name: eff_name.clone(), name: key.clone(), kfs: valid });
                    }
                }
            }
        }
        tracks
    }

    fn tl_span(&self, width: f64) -> f64 {
        (width - TL_LABEL_W - TL_PAD).max(1.0)
    }

    fn tl_x_of(&self, width: f64, t_ns: f64) -> f64 {
        TL_LABEL_W + self.tl_span(width) * (t_ns / self.duration_ns.max(1) as f64)
    }

    fn tl_time_of(&self, width: f64, x: f64) -> i64 {
        let frac = ((x - TL_LABEL_W) / self.tl_span(width)).clamp(0.0, 1.0);
        (frac * self.duration_ns as f64) as i64
    }

    /// Finds the keyframe (track index, kf index) under canvas position (x, y).
    fn kf_at_xy(&self, preset: &Value, tracks: &[Track], width: f64, x: f64, y: f64, radius: f64) -> Option<(usize, usize)> {
        let row = ((y - TL_RULER_H) / TL_ROW_H).floor();
        if row < 0.0 || row as usize >= tracks.len() {
            return None;
        }
        let track = &tracks[row as usize];
        let kfs = param(&effects(preset)[track.eff_idx], &track.name)?.get("keyframes")?.as_array()?;
        let mut best: Option<usize> = None;
        let mut best_dist = radius + 1.0;
        for &i in &track.kfs {
            let dx = (self.tl_x_of(width, kf_time(&kfs[i])) - x).abs();
            if dx <= radius && dx < best_dist {
                best = Some(i);
                best_dist = dx;
            }
        }
        best.map(|i| (row as usize, i))
    }

    // ---------------------------------------------------------------- transform evaluation

    fn motion_tf(&self, preset: &Value, src_w: f64, src_h: f64) -> MotionTf {
        let default_tf = MotionTf {
            has_motion: false,
            anchor_x: src_w / 2.0,
            anchor_y: src_h / 2.0,
            pos_x: src_w / 2.0,
            pos_y: src_h / 2.0,
            sx: 1.0,
            sy: 1.0,
            rot_deg: 0.0,
        };
        let t = self.current_time_ns as f64;
        for eff in effects(preset) {
            if eff_enabled(eff) && eff_type(eff) == "motion" {
                let anchor = eval_vec2(param(eff, "anchor"), t).unwrap_or((src_w / 2.0, src_h / 2.0));
                let pos = eval_vec2(param(eff, "position"), t).unwrap_or((src_w / 2.0, src_h / 2.0));
                let scale_pct = or_nz(eval_f64(param(eff, "scale"), t), 100.0);
                let scale_w_pct = or_nz(eval_f64(param(eff, "scale_width"), t), 100.0);
                let uniform = uniform_flag(eff, t);
                let rot_deg = eval_f64(param(eff, "rotation"), t).unwrap_or(0.0);
                let sy = scale_pct / 100.0;
                let sx = if uniform { sy } else { scale_w_pct / 100.0 };
                return MotionTf {
                    has_motion: true,
                    anchor_x: anchor.0,
                    anchor_y: anchor.1,
                    pos_x: pos.0,
                    pos_y: pos.1,
                    sx,
                    sy,
                    rot_deg,
                };
            }
        }
        default_tf
    }

    fn global_opacity(&self, preset: &Value) -> f64 {
        let t = self.current_time_ns as f64;
        for eff in effects(preset) {
            if eff_enabled(eff) && eff_type(eff) == "opacity" {
                if let Some(op) = eval_f64(param(eff, "opacity"), t) {
                    return op;
                }
            }
        }
        100.0
    }

    /// Oriented bounding box & transform parameters of the active effect.
    fn compute_box(&self, preset: &Value, src_w: f64, src_h: f64, m: &MotionTf) -> Option<BoxInfo> {
        let eff_idx = active_effect_index(preset)?;
        let eff = &effects(preset)[eff_idx];
        let t = self.current_time_ns as f64;
        let p = |k: &str| param(eff, k);

        if eff_type(eff) == "motion" {
            let (base_w, base_h) = match (self.shape_w.trim().parse::<f64>(), self.shape_h.trim().parse::<f64>()) {
                (Ok(w), Ok(h)) => (w.max(40.0), h.max(40.0)),
                _ => (460.0, 240.0),
            };
            let (ax, ay) = eval_vec2(p("anchor"), t).unwrap_or((src_w / 2.0, src_h / 2.0));
            let (px, py) = eval_vec2(p("position"), t).unwrap_or((src_w / 2.0, src_h / 2.0));
            let scale_pct = or_nz(eval_f64(p("scale"), t), 100.0);
            let scale_w_pct = or_nz(eval_f64(p("scale_width"), t), 100.0);
            let uniform = uniform_flag(eff, t);
            let rot_deg = eval_f64(p("rotation"), t).unwrap_or(0.0);
            let sy = scale_pct / 100.0;
            let sx = if uniform { sy } else { scale_w_pct / 100.0 };

            let (cx, cy) = (src_w / 2.0, src_h / 2.0);
            let (hw, hh) = (base_w / 2.0, base_h / 2.0);
            let local = [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)];
            let world: Vec<(f64, f64)> =
                local.iter().map(|&(lx, ly)| transform_point_2d(lx, ly, ax, ay, px, py, sx, sy, rot_deg)).collect();
            return Some(BoxInfo {
                eff_idx,
                is_motion: true,
                base_w,
                base_h,
                anchor: (ax, ay),
                pos: (px, py),
                sx,
                sy,
                rot_deg,
                world_corners: world,
                pivot_world: (px, py),
            });
        }

        // graphic_text
        let raw_text = eval_text(p("text"), t).filter(|s| !s.is_empty()).unwrap_or_else(|| "Text".into());
        let base_size = or_nz(eval_f64(p("size"), t), 100.0);
        let scale_pct = or_nz(eval_f64(p("scale"), t), 100.0);
        let scale_w_pct = or_nz(eval_f64(p("scale_width"), t), 100.0);
        let uniform = uniform_flag(eff, t);
        let rot_deg = eval_f64(p("rotation"), t).unwrap_or(0.0);
        let (px, py) = eval_vec2(p("position"), t).unwrap_or((src_w / 2.0, src_h / 2.0));
        let (ax, ay) = eval_vec2(p("anchor"), t).unwrap_or((0.0, 0.0));
        let sy = scale_pct / 100.0;
        let sx = if uniform { sy } else { scale_w_pct / 100.0 };

        let lines: Vec<&str> = raw_text.lines().collect();
        let lines = if lines.is_empty() { vec!["Text"] } else { lines };
        let max_chars = lines.iter().map(|l| l.chars().count()).max().unwrap_or(1).max(1) as f64;
        let base_w = (max_chars * base_size * 0.58 + 36.0).max(80.0);
        let base_h = (lines.len() as f64 * base_size * 1.25 + 24.0).max(50.0);
        let (hw, hh) = (base_w / 2.0, base_h / 2.0);

        let local = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)];
        let world: Vec<(f64, f64)> = local
            .iter()
            .map(|&(lx, ly)| {
                let (wx, wy) = transform_point_2d(lx, ly, ax, ay, px, py, sx, sy, rot_deg);
                if m.has_motion {
                    m.apply(wx, wy)
                } else {
                    (wx, wy)
                }
            })
            .collect();
        let pivot = if m.has_motion { m.apply(px, py) } else { (px, py) };
        Some(BoxInfo {
            eff_idx,
            is_motion: false,
            base_w,
            base_h,
            anchor: (ax, ay),
            pos: (px, py),
            sx,
            sy,
            rot_deg,
            world_corners: world,
            pivot_world: pivot,
        })
    }

    fn build_gizmos(&self, preset: &Value, st: &Stage, m: &MotionTf) -> Gizmos {
        let mut g = Gizmos::default();
        let (x0, y0, ratio) = (st.x0, st.y0, st.ratio);

        // Motion path overlay
        if self.path_on || self.active_tool == Tool::Path {
            if let Some(eff_idx) = active_effect_index(preset) {
                let pos_param = param(&effects(preset)[eff_idx], "position");
                let (curve, nodes) = sample_motion_path(pos_param, 16);
                if curve.len() >= 2 {
                    g.path_curve = curve.iter().map(|&(sx, sy)| (x0 + sx * ratio, y0 + sy * ratio)).collect();
                    for n in nodes {
                        g.path_nodes.push(PathNode {
                            x: x0 + n.x * ratio,
                            y: y0 + n.y * ratio,
                            eff_idx,
                            kf_idx: n.orig_index,
                            time: n.time,
                        });
                    }
                }
            }
        }

        // Transform gizmo
        let Some(b) = self.compute_box(preset, st.src_w, st.src_h, m) else { return g };
        let c_corners: Vec<(f64, f64)> = b.world_corners.iter().map(|&(wx, wy)| (x0 + wx * ratio, y0 + wy * ratio)).collect();
        g.box_poly = c_corners.clone();

        if self.anchor_on || self.active_tool == Tool::Anchor {
            g.handles.insert("anchor".into(), (x0 + b.pivot_world.0 * ratio, y0 + b.pivot_world.1 * ratio));
        }
        if self.active_tool == Tool::Transform {
            for (i, c) in c_corners.iter().enumerate() {
                g.handles.insert(format!("corner_{}", i), *c);
            }
            let names = ["edge_top", "edge_right", "edge_bottom", "edge_left"];
            let mut top_mid = (0.0, 0.0);
            for i in 0..4 {
                let (p1, p2) = (c_corners[i], c_corners[(i + 1) % 4]);
                let mid = ((p1.0 + p2.0) / 2.0, (p1.1 + p2.1) / 2.0);
                if i == 0 {
                    top_mid = mid;
                }
                g.handles.insert(names[i].into(), mid);
            }
            let rad = b.rot_deg.to_radians();
            g.handles.insert("rotate".into(), (top_mid.0 + rad.sin() * 26.0, top_mid.1 - rad.cos() * 26.0));
        }
        g.box_info = Some(b);
        g
    }

    // ---------------------------------------------------------------- writing transform changes

    fn write_param_value(&mut self, preset: &mut Value, eff: usize, key: &str, tag: &str, new_val: Value, force_kf: bool) {
        let t = self.current_time_ns;
        let tol = self.frame_ns() / 2.0;
        let auto_key = self.auto_key;
        let Some(p) = param_mut(preset, eff, key) else { return };
        if p.get("value").is_none() {
            return;
        }
        let should_kf = force_kf || has_keyframes(p) || auto_key;
        if should_kf {
            if !p.get("keyframes").map(|k| k.is_array()).unwrap_or(false) {
                p["keyframes"] = json!([]);
            }
            let kfs = p.get_mut("keyframes").and_then(|k| k.as_array_mut()).expect("keyframes array");
            let found = kfs.iter().position(|kf| {
                (kf.get("time").and_then(num).map(|v| v as i64).unwrap_or(-1) - t).abs() as f64 <= tol
            });
            match found {
                None => {
                    kfs.push(json!({
                        "time": t,
                        "value": { tag: new_val.clone() },
                        "interp": "AutoBezier",
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
                    kf["value"][tag] = new_val.clone();
                }
            }
        }
        set_in_value_obj(p, tag, new_val);
        self.modified = true;
    }

    fn stamp_all_transform_keyframes(&mut self, preset: &mut Value) {
        let Some(b) = self.gizmos.box_info.clone() else { return };
        self.pause();
        let e = b.eff_idx;
        let (px, py) = b.pos;
        let (ax, ay) = b.anchor;
        self.write_param_value(preset, e, "position", "Vec2", vec2(round_to(px, 3), round_to(py, 3)), true);
        self.write_param_value(preset, e, "scale", "Float", json!(round_to(b.sy * 100.0, 3)), true);
        self.write_param_value(preset, e, "rotation", "Float", json!(round_to(b.rot_deg, 3)), true);
        self.write_param_value(preset, e, "anchor", "Vec2", vec2(round_to(ax, 3), round_to(ay, 3)), true);
    }

    fn reset_active_transform(&mut self, preset: &mut Value) {
        let (Some(st), Some(b)) = (self.stage, self.gizmos.box_info.clone()) else { return };
        self.pause();
        let e = b.eff_idx;
        let def_pos = vec2(st.src_w / 2.0, st.src_h / 2.0);
        let def_anchor = if b.is_motion { vec2(st.src_w / 2.0, st.src_h / 2.0) } else { vec2(0.0, 0.0) };
        self.write_param_value(preset, e, "position", "Vec2", def_pos, false);
        self.write_param_value(preset, e, "anchor", "Vec2", def_anchor, false);
        self.write_param_value(preset, e, "scale", "Float", json!(100.0), false);
        self.write_param_value(preset, e, "scale_width", "Float", json!(100.0), false);
        if let Some(p) = param_mut(preset, e, "uniform_scale") {
            set_in_value_obj(p, "Bool", json!(true));
        }
        self.write_param_value(preset, e, "rotation", "Float", json!(0.0), false);
    }

    /// Deletes the keyframe selected in the timeline. Returns `true` when something was removed.
    pub fn delete_selected_keyframe(&mut self, preset: &mut Value) -> bool {
        let Some(sel) = self.tl_sel.take() else { return false };
        let mut removed = false;
        if let Some(p) = param_mut(preset, sel.eff_idx, &sel.param) {
            let now_empty = match p.get_mut("keyframes").and_then(|k| k.as_array_mut()) {
                Some(kfs) if sel.kf_idx < kfs.len() => {
                    kfs.remove(sel.kf_idx);
                    removed = true;
                    kfs.is_empty()
                }
                _ => false,
            };
            if now_empty {
                if let Some(o) = p.as_object_mut() {
                    o.shift_remove("keyframes");
                }
            }
        }
        if removed {
            self.modified = true;
            self.tl_drag = None;
            self.recalculate_duration(Some(&*preset));
            if self.current_time_ns > self.duration_ns {
                self.current_time_ns = self.duration_ns;
            }
        }
        removed
    }

    pub fn has_selected_keyframe(&self) -> bool {
        self.tl_sel.is_some()
    }

    // ---------------------------------------------------------------- hit-testing & drag

    fn hit_test(&self, x: f64, y: f64) -> (Option<DragMode>, Option<(usize, usize)>) {
        for n in &self.gizmos.path_nodes {
            if (x - n.x).hypot(y - n.y) <= 9.0 {
                return (Some(DragMode::PathKf), Some((n.eff_idx, n.kf_idx)));
            }
        }
        let h = &self.gizmos.handles;
        let near = |name: &str, r: f64| h.get(name).map(|p| (x - p.0).hypot(y - p.1) <= r).unwrap_or(false);

        if self.active_tool == Tool::Anchor && near("anchor", 14.0) {
            return (Some(DragMode::Anchor), None);
        }
        if self.active_tool == Tool::Transform {
            if near("rotate", 11.0) {
                return (Some(DragMode::Rotate), None);
            }
            if (0..4).any(|i| near(&format!("corner_{}", i), 10.0)) {
                return (Some(DragMode::ScaleCorner), None);
            }
            if near("edge_left", 10.0) || near("edge_right", 10.0) {
                return (Some(DragMode::ScaleX), None);
            }
            if near("edge_top", 10.0) || near("edge_bottom", 10.0) {
                return (Some(DragMode::ScaleY), None);
            }
            if near("anchor", 8.0) {
                return (Some(DragMode::Anchor), None);
            }
        }
        if !self.gizmos.box_poly.is_empty() && point_in_polygon(x, y, &self.gizmos.box_poly) {
            return (Some(if self.active_tool == Tool::Anchor { DragMode::Anchor } else { DragMode::Move }), None);
        }
        (None, None)
    }

    fn apply_snap(&mut self, mut px: f64, mut py: f64, src_w: f64, src_h: f64, disable: bool) -> (f64, f64) {
        self.snap_lines.clear();
        if disable || !self.snap {
            return (px, py);
        }
        let thresh = 10.0;
        let mut xs = vec![src_w * 0.5];
        let mut ys = vec![src_h * 0.5];
        if self.thirds {
            xs.extend([src_w / 3.0, src_w * 2.0 / 3.0]);
            ys.extend([src_h / 3.0, src_h * 2.0 / 3.0]);
        }
        if let Some(&tx) = xs.iter().find(|&&tx| (px - tx).abs() <= thresh) {
            px = tx;
            self.snap_lines.push((true, tx));
        }
        if let Some(&ty) = ys.iter().find(|&&ty| (py - ty).abs() <= thresh) {
            py = ty;
            self.snap_lines.push((false, ty));
        }
        (px, py)
    }

    fn handle_drag(&mut self, preset: &mut Value, st: &Stage, pointer: (f64, f64), shift: bool, ctrl: bool) -> bool {
        let Some(drag) = self.drag.clone() else { return false };
        let Some(b) = self.gizmos.box_info.clone() else { return false };
        let e = b.eff_idx;
        let (x0, y0, ratio) = (st.x0, st.y0, st.ratio);

        match drag.mode {
            DragMode::PathKf => {
                let Some((kf_eff, kf_idx)) = drag.kf_ref else { return false };
                let sx = (pointer.0 - x0) / ratio;
                let sy = (pointer.1 - y0) / ratio;
                let (sx, sy) = self.apply_snap(sx, sy, st.src_w, st.src_h, ctrl);
                let v = vec2(round_to(sx, 3), round_to(sy, 3));
                if let Some(pp) = param_mut(preset, kf_eff, "position") {
                    if let Some(kf) = pp.get_mut("keyframes").and_then(|k| k.get_mut(kf_idx)) {
                        if !kf.get("value").map(|v| v.is_object()).unwrap_or(false) {
                            kf["value"] = json!({});
                        }
                        kf["value"]["Vec2"] = v.clone();
                    }
                }
                if let Some(pp) = param_mut(preset, e, "position") {
                    set_in_value_obj(pp, "Vec2", v);
                }
                self.modified = true;
            }
            DragMode::Move => {
                let dx = (pointer.0 - drag.start_canvas.0) / ratio;
                let dy = (pointer.1 - drag.start_canvas.1) / ratio;
                let (nx, ny) = self.apply_snap(drag.start_pos.0 + dx, drag.start_pos.1 + dy, st.src_w, st.src_h, ctrl);
                self.write_param_value(preset, e, "position", "Vec2", vec2(round_to(nx, 3), round_to(ny, 3)), false);
            }
            DragMode::Anchor => {
                let dx = (pointer.0 - drag.start_canvas.0) / ratio;
                let dy = (pointer.1 - drag.start_canvas.1) / ratio;
                let (nax, nay) = (drag.start_anchor.0 + dx, drag.start_anchor.1 + dy);
                self.write_param_value(preset, e, "anchor", "Vec2", vec2(round_to(nax, 3), round_to(nay, 3)), false);
            }
            DragMode::Rotate => {
                let piv_x = x0 + b.pivot_world.0 * ratio;
                let piv_y = y0 + b.pivot_world.1 * ratio;
                let mut ang = (pointer.1 - piv_y).atan2(pointer.0 - piv_x).to_degrees() + 90.0;
                ang = (ang + 180.0).rem_euclid(360.0) - 180.0;
                if shift {
                    ang = (ang / 15.0).round() * 15.0;
                }
                self.write_param_value(preset, e, "rotation", "Float", json!(round_to(ang, 2)), false);
            }
            DragMode::ScaleCorner | DragMode::ScaleX | DragMode::ScaleY => {
                let wx = (pointer.0 - x0) / ratio;
                let wy = (pointer.1 - y0) / ratio;
                let (ux, uy) = inverse_rotate_offset(wx, wy, b.pos.0, b.pos.1, b.rot_deg);
                let hw = (b.base_w / 2.0).max(10.0);
                let hh = (b.base_h / 2.0).max(10.0);
                let new_sx = (ux.abs() / hw).clamp(0.05, 12.0);
                let new_sy = (uy.abs() / hh).clamp(0.05, 12.0);
                let has_uniform_param = param_mut(preset, e, "uniform_scale").is_some();
                let set_uniform_false = |preset: &mut Value| {
                    if let Some(p) = param_mut(preset, e, "uniform_scale") {
                        set_in_value_obj(p, "Bool", json!(false));
                    }
                };

                match drag.mode {
                    DragMode::ScaleCorner => {
                        if shift {
                            if has_uniform_param {
                                set_uniform_false(preset);
                            }
                            self.write_param_value(preset, e, "scale_width", "Float", json!(round_to(new_sx * 100.0, 2)), false);
                            self.write_param_value(preset, e, "scale", "Float", json!(round_to(new_sy * 100.0, 2)), false);
                        } else {
                            let uni = new_sx.max(new_sy);
                            self.write_param_value(preset, e, "scale", "Float", json!(round_to(uni * 100.0, 2)), false);
                            let uniform = preset
                                .get("effects")
                                .and_then(|x| x.get(e))
                                .and_then(|eff| param(eff, "uniform_scale"))
                                .and_then(|p| p.get("value"))
                                .and_then(|v| v.get("Bool"))
                                .and_then(|v| v.as_bool())
                                .unwrap_or(true);
                            if uniform {
                                self.write_param_value(preset, e, "scale_width", "Float", json!(round_to(uni * 100.0, 2)), false);
                            }
                        }
                    }
                    DragMode::ScaleX => {
                        if has_uniform_param {
                            set_uniform_false(preset);
                        }
                        self.write_param_value(preset, e, "scale_width", "Float", json!(round_to(new_sx * 100.0, 2)), false);
                    }
                    _ => {
                        self.write_param_value(preset, e, "scale", "Float", json!(round_to(new_sy * 100.0, 2)), false);
                    }
                }
                self.modified = true;
            }
        }
        true
    }

    // ================================================================= UI

    /// Draws the whole viewer (header, tool strip, stage, HUD, timeline, transport).
    pub fn show(&mut self, ui: &mut egui::Ui, mut preset: Option<&mut Value>, lang: Lang) {
        let ctx = ui.ctx().clone();
        self.tick(&ctx, preset.is_some());

        egui::TopBottomPanel::top("viewer_header")
            .frame(theme::header_frame())
            .show_separator_line(false)
            .show_inside(ui, |ui| self.header_ui(ui, lang));

        egui::TopBottomPanel::top("viewer_tools")
            .frame(egui::Frame::none().fill(pal::DECK).inner_margin(egui::Margin::symmetric(10.0, 5.0)))
            .show_separator_line(false)
            .show_inside(ui, |ui| self.toolstrip_ui(ui, lang, preset.as_deref_mut()));

        egui::TopBottomPanel::bottom("viewer_deck")
            .frame(egui::Frame::none().fill(pal::DECK).inner_margin(egui::Margin::symmetric(12.0, 7.0)))
            .show_inside(ui, |ui| self.deck_ui(ui, lang, preset.as_deref_mut()));

        egui::CentralPanel::default()
            .frame(egui::Frame::none().fill(pal::MONITOR_GUTTER).inner_margin(egui::Margin::same(8.0)))
            .show_inside(ui, |ui| {
                egui::TopBottomPanel::bottom("viewer_hud")
                    .frame(
                        egui::Frame::none()
                            .fill(pal::WELL)
                            .stroke(Stroke::new(1.0, pal::BORDER))
                            .inner_margin(egui::Margin::symmetric(8.0, 3.0)),
                    )
                    .show_separator_line(false)
                    .show_inside(ui, |ui| {
                        ui.horizontal(|ui| {
                            ui.label(theme::mono(&self.hud_metrics, 10.5, pal::ACCENT));
                            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                ui.label(RichText::new(&self.cursor_coords).monospace().size(10.5).color(pal::FG_MUTED));
                            });
                        });
                    });
                egui::CentralPanel::default().frame(egui::Frame::none()).show_inside(ui, |ui| {
                    self.stage_ui(ui, preset.as_deref_mut(), lang);
                });
            });
    }

    fn header_ui(&mut self, ui: &mut egui::Ui, lang: Lang) {
        ui.horizontal(|ui| {
            ui.label(theme::section_tag(&tr(lang, "viewer_header")));
            ui.label(theme::mono(&self.res_badge, 11.0, pal::ACCENT));
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                // Right-to-left: widgets are added in reverse visual order.
                egui::ComboBox::from_id_salt("bg_combo")
                    .width(120.0)
                    .selected_text(tr(lang, BG_KEYS[self.bg_mode]))
                    .show_ui(ui, |ui| {
                        for (i, k) in BG_KEYS.iter().enumerate() {
                            ui.selectable_value(&mut self.bg_mode, i, tr(lang, k));
                        }
                    });
                egui::ComboBox::from_id_salt("speed_combo")
                    .width(44.0)
                    .selected_text(self.speed.clone())
                    .show_ui(ui, |ui| {
                        for s in SPEEDS {
                            ui.selectable_value(&mut self.speed, s.to_string(), s);
                        }
                    });
                ui.label(theme::muted(&tr(lang, "lbl_speed")));
                ui.checkbox(&mut self.snap, tr(lang, "chk_snap"));
                ui.checkbox(&mut self.path_on, tr(lang, "chk_path"));
                ui.checkbox(&mut self.anchor_on, tr(lang, "chk_anchor"));
                ui.checkbox(&mut self.thirds, tr(lang, "chk_thirds"));
                ui.checkbox(&mut self.guides, tr(lang, "chk_safe_guides"));
            });
        });
    }

    fn toolstrip_ui(&mut self, ui: &mut egui::Ui, lang: Lang, preset: Option<&mut Value>) {
        ui.horizontal(|ui| {
            egui::Frame::none()
                .fill(pal::WELL)
                .stroke(Stroke::new(1.0, pal::BORDER))
                .inner_margin(egui::Margin::same(2.0))
                .show(ui, |ui| {
                    ui.spacing_mut().item_spacing.x = 2.0;
                    for (tool, key) in [(Tool::Transform, "tool_transform"), (Tool::Anchor, "tool_anchor"), (Tool::Path, "tool_path")] {
                        if theme::pill(ui, &tr(lang, key), self.active_tool == tool, 11.0) {
                            self.active_tool = tool;
                        }
                    }
                });

            ui.add_space(8.0);
            ui.label(theme::muted(&tr(lang, "lbl_zoom")));
            let shown = if self.zoom_fit { tr(lang, "zoom_fit") } else { self.zoom_text.clone() };
            egui::ComboBox::from_id_salt("zoom_combo").width(64.0).selected_text(shown).show_ui(ui, |ui| {
                if ui.selectable_label(self.zoom_fit, tr(lang, "zoom_fit")).clicked() {
                    self.zoom_fit = true;
                    self.pan = (0.0, 0.0);
                }
                for z in ZOOMS {
                    if ui.selectable_label(!self.zoom_fit && self.zoom_text == z, z).clicked() {
                        let pct: f64 = z.trim_end_matches('%').parse().unwrap_or(100.0);
                        self.zoom_fit = false;
                        self.zoom_factor = (pct / 100.0).clamp(0.1, 5.0);
                        self.zoom_text = z.to_string();
                    }
                }
            });

            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                let mut preset = preset;
                if theme::ghost_button(ui, &tr(lang, "btn_reset_tf")).clicked() {
                    if let Some(p) = preset.as_deref_mut() {
                        self.reset_active_transform(p);
                    }
                }
                if theme::keyframe_button_text(ui, &tr(lang, "btn_add_kf")).clicked() {
                    if let Some(p) = preset.as_deref_mut() {
                        self.stamp_all_transform_keyframes(p);
                    }
                }
                ui.checkbox(&mut self.auto_key, tr(lang, "chk_autokey"));
            });
        });
    }

    fn deck_ui(&mut self, ui: &mut egui::Ui, lang: Lang, mut preset: Option<&mut Value>) {
        // Timeline + timecode
        ui.horizontal_top(|ui| {
            let tl_w = (ui.available_width() - 130.0).max(200.0);
            ui.allocate_ui(Vec2::new(tl_w, 126.0), |ui| {
                self.timeline_ui(ui, preset.as_deref_mut(), lang);
            });
            let cur = self.current_time_ns as f64 / NS;
            let dur = self.duration_ns as f64 / NS;
            egui::Frame::none()
                .fill(pal::WELL)
                .stroke(Stroke::new(1.0, pal::BORDER))
                .inner_margin(egui::Margin::symmetric(8.0, 2.0))
                .show(ui, |ui| {
                    ui.label(theme::mono(&format!("{} / {}", fmt_tc(cur), fmt_tc(dur)), 12.0, pal::ACCENT));
                });
        });
        ui.add_space(4.0);

        // Transport + dummy-object controls
        ui.horizontal(|ui| {
            if theme::transport_button(ui, "⏮", false).clicked() {
                self.restart();
            }
            let label = if self.is_playing { tr(lang, "btn_pause") } else { tr(lang, "btn_play") };
            if theme::transport_button(ui, &label, true).clicked() {
                self.toggle_play();
            }
            ui.checkbox(&mut self.loop_play, tr(lang, "chk_loop"));
            if ui
                .add_enabled(self.tl_sel.is_some(), egui::Button::new(format!("🗑 {}", tr(lang, "btn_del_kf"))))
                .clicked()
            {
                if let Some(p) = preset.as_deref_mut() {
                    self.delete_selected_keyframe(p);
                }
            }

            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                let mut rgb = self.example_color;
                if egui::color_picker::color_edit_button_srgb(ui, &mut rgb).changed() {
                    self.example_color = rgb;
                }
                ui.add(egui::TextEdit::singleline(&mut self.shape_h).desired_width(34.0));
                ui.label(theme::muted("×"));
                ui.add(egui::TextEdit::singleline(&mut self.shape_w).desired_width(34.0));
                ui.add(
                    egui::TextEdit::singleline(&mut self.example_text)
                        .hint_text(tr(lang, "default_sample_text"))
                        .desired_width(110.0),
                );
                egui::ComboBox::from_id_salt("obj_combo")
                    .width(140.0)
                    .selected_text(tr(lang, OBJ_KEYS[self.obj_mode]))
                    .show_ui(ui, |ui| {
                        for (i, k) in OBJ_KEYS.iter().enumerate() {
                            ui.selectable_value(&mut self.obj_mode, i, tr(lang, k));
                        }
                    });
                ui.label(theme::muted(&tr(lang, "lbl_object")));
            });
        });
    }

    // ---------------------------------------------------------------- timeline

    fn timeline_ui(&mut self, ui: &mut egui::Ui, preset: Option<&mut Value>, lang: Lang) {
        let tracks = match preset.as_deref() {
            Some(p) => self.collect_tracks(p),
            None => vec![],
        };
        let h = TL_RULER_H + (tracks.len().max(1) as f64) * TL_ROW_H + 5.0;
        let mut preset = preset;

        egui::ScrollArea::vertical().max_height(126.0).min_scrolled_height(126.0).auto_shrink([false, false]).show(ui, |ui| {
            let w = (ui.available_width() as f64).max(180.0);
            let (resp, painter) = ui.allocate_painter(Vec2::new(w as f32, h.max(124.0) as f32), Sense::click_and_drag());
            let o = resp.rect.min;
            let pt = |x: f64, y: f64| Pos2::new(o.x + x as f32, o.y + y as f32);
            let full = Rect::from_min_size(o, Vec2::new(w as f32, h.max(124.0) as f32));
            painter.rect_filled(full, 0.0, pal::WELL);
            painter.rect_filled(Rect::from_min_max(full.min, pt(TL_LABEL_W, h.max(124.0))), 0.0, pal::PANEL_HEADER);
            let hh = h.max(124.0);
            painter.line_segment([pt(TL_LABEL_W, 0.0), pt(TL_LABEL_W, hh)], Stroke::new(1.0, pal::BORDER_LIGHT));

            let span = self.tl_span(w);
            let dur_s = (self.duration_ns as f64 / NS).max(0.01);
            let steps = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0];
            let step = steps.iter().copied().find(|v| span * v / dur_s >= 72.0).unwrap_or(3600.0);
            painter.line_segment([pt(TL_LABEL_W, TL_RULER_H), pt(w - TL_PAD, TL_RULER_H)], Stroke::new(1.0, pal::BORDER_LIGHT));
            let mut k = 0;
            while (k as f64) * step <= dur_s + 1e-9 {
                let sec = k as f64 * step;
                let x = TL_LABEL_W + span * sec / dur_s;
                painter.line_segment([pt(x, TL_RULER_H - 7.0), pt(x, hh)], Stroke::new(1.0, pal::BORDER));
                painter.text(pt(x + 3.0, 3.0), Align2::LEFT_TOP, fmt_tc(sec), FontId::monospace(9.0), pal::FG_FAINT);
                k += 1;
            }
            if tracks.is_empty() {
                painter.text(
                    pt(TL_LABEL_W + 12.0, TL_RULER_H + 12.0),
                    Align2::LEFT_CENTER,
                    "No animated properties",
                    FontId::proportional(10.0),
                    pal::FG_FAINT,
                );
            }

            if let Some(p) = preset.as_deref() {
                for (idx, track) in tracks.iter().enumerate() {
                    let y0 = TL_RULER_H + idx as f64 * TL_ROW_H;
                    let cy = y0 + TL_ROW_H / 2.0;
                    if idx % 2 == 0 {
                        painter.rect_filled(Rect::from_min_max(pt(1.0, y0), pt(w, y0 + TL_ROW_H)), 0.0, theme::rgb(0x17191f));
                    }
                    painter.line_segment([pt(0.0, y0 + TL_ROW_H), pt(w, y0 + TL_ROW_H)], Stroke::new(1.0, pal::BORDER));
                    let eff_short: String = track.eff_name.chars().take(11).collect();
                    let label: String = format!("{}  ›  {}", eff_short, track.name).chars().take(22).collect();
                    painter.text(pt(8.0, cy), Align2::LEFT_CENTER, label, FontId::proportional(10.0), pal::FG_MUTED);

                    let kfs = param(&effects(p)[track.eff_idx], &track.name)
                        .and_then(|x| x.get("keyframes"))
                        .and_then(|k| k.as_array());
                    let Some(kfs) = kfs else { continue };
                    let mut times: Vec<f64> = track.kfs.iter().map(|&i| kf_time(&kfs[i])).collect();
                    times.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
                    if times.len() > 1 {
                        painter.line_segment(
                            [pt(self.tl_x_of(w, times[0]), cy), pt(self.tl_x_of(w, times[times.len() - 1]), cy)],
                            Stroke::new(2.0, theme::rgb(0x51402c)),
                        );
                    }
                    for &i in &track.kfs {
                        let t = kf_time(&kfs[i]);
                        let x = self.tl_x_of(w, t);
                        let active = (t - self.current_time_ns as f64).abs() <= self.frame_ns() / 2.0;
                        let r = if active { 6.0 } else { 5.0 };
                        let selected = self
                            .tl_sel
                            .as_ref()
                            .map(|s| s.eff_idx == track.eff_idx && s.param == track.name && s.kf_idx == i)
                            .unwrap_or(false);
                        if selected {
                            painter.circle_stroke(pt(x, cy), 10.0, Stroke::new(2.0, pal::DANGER));
                        }
                        painter.add(Shape::convex_polygon(
                            vec![pt(x, cy - r), pt(x + r, cy), pt(x, cy + r), pt(x - r, cy)],
                            if active { pal::ACCENT } else { pal::CYAN },
                            Stroke::new(1.0, if active { pal::FG_TEXT } else { pal::BORDER_LIGHT }),
                        ));
                    }
                }
            }
            let px = self.tl_x_of(w, self.current_time_ns as f64);
            painter.line_segment([pt(px, 0.0), pt(px, hh)], Stroke::new(2.0, pal::ACCENT));
            painter.add(Shape::convex_polygon(vec![pt(px - 5.0, 0.0), pt(px + 5.0, 0.0), pt(px, 8.0)], pal::ACCENT, Stroke::NONE));

            // ---- delete (Delete / Backspace key or right-click menu)
            let (secondary, del_key) = ui.input(|i| {
                (i.pointer.secondary_pressed(), i.key_pressed(egui::Key::Delete) || i.key_pressed(egui::Key::Backspace))
            });
            if secondary && resp.hovered() {
                if let (Some(pos), Some(p)) = (ui.input(|i| i.pointer.latest_pos()), preset.as_deref()) {
                    let (lx, ly) = ((pos.x - o.x) as f64, (pos.y - o.y) as f64);
                    if let Some((ti, ki)) = self.kf_at_xy(p, &tracks, w, lx, ly, 10.0) {
                        let t = &tracks[ti];
                        self.tl_sel = Some(TlDrag { eff_idx: t.eff_idx, param: t.name.clone(), kf_idx: ki });
                    }
                }
            }
            let mut do_delete = del_key && !ui.ctx().wants_keyboard_input() && self.tl_sel.is_some();
            resp.context_menu(|ui| {
                if self.tl_sel.is_some() {
                    if ui.button(format!("🗑 {}", tr(lang, "btn_del_kf"))).clicked() {
                        do_delete = true;
                        ui.close_menu();
                    }
                } else {
                    ui.label(theme::muted("—"));
                }
            });
            if do_delete {
                if let Some(p) = preset.as_deref_mut() {
                    self.delete_selected_keyframe(p);
                }
            }

            // ---- interaction
            let (pressed, down, shift, latest) = ui.input(|i| {
                (i.pointer.primary_pressed(), i.pointer.primary_down(), i.modifiers.shift, i.pointer.latest_pos())
            });
            let local = latest.map(|p| ((p.x - o.x) as f64, (p.y - o.y) as f64));

            if resp.hovered() && !self.tl_dragging {
                if let (Some((lx, ly)), Some(p)) = (local, preset.as_deref()) {
                    let hit = self.kf_at_xy(p, &tracks, w, lx, ly, 10.0);
                    ui.ctx().set_cursor_icon(if hit.is_some() { CursorIcon::PointingHand } else { CursorIcon::ResizeHorizontal });
                }
            }

            if pressed && resp.hovered() {
                if let Some((lx, ly)) = local {
                    self.pause();
                    self.tl_dragging = true;
                    let hit = preset.as_deref().and_then(|p| self.kf_at_xy(p, &tracks, w, lx, ly, 10.0));
                    self.tl_drag = None;
                    self.tl_sel = None;
                    if let (Some((ti, ki)), Some(p)) = (hit, preset.as_deref()) {
                        let tr_ = &tracks[ti];
                        self.tl_drag = Some(TlDrag { eff_idx: tr_.eff_idx, param: tr_.name.clone(), kf_idx: ki });
                        self.tl_sel = self.tl_drag.clone();
                        if let Some(kf) = param(&effects(p)[tr_.eff_idx], &tr_.name)
                            .and_then(|x| x.get("keyframes"))
                            .and_then(|k| k.get(ki))
                        {
                            self.seek(kf_time(kf) as i64);
                        }
                    } else {
                        self.seek(self.tl_time_of(w, lx));
                    }
                }
            }
            if self.tl_dragging && down {
                if let Some((lx, _)) = local {
                    if let (Some(td), Some(p)) = (self.tl_drag.clone(), preset.as_deref_mut()) {
                        let mut new_time = self.tl_time_of(w, lx) as f64;
                        if !shift {
                            let frame = self.frame_ns().max(1.0);
                            new_time = (new_time / frame).round() * frame;
                        }
                        let new_time = new_time.clamp(0.0, self.duration_ns as f64) as i64;
                        if let Some(kfs) = param_mut(p, td.eff_idx, &td.param)
                            .and_then(|x| x.get_mut("keyframes"))
                            .and_then(|k| k.as_array_mut())
                        {
                            if let Some(kf) = kfs.get_mut(td.kf_idx) {
                                kf["time"] = json!(new_time);
                                let new_idx = sort_keyframes_tracking(kfs, td.kf_idx);
                                self.tl_drag = Some(TlDrag { kf_idx: new_idx, ..td });
                                self.tl_sel = self.tl_drag.clone();
                                self.modified = true;
                                self.seek(new_time);
                            }
                        }
                    } else {
                        self.seek(self.tl_time_of(w, lx));
                    }
                }
            }
            if self.tl_dragging && !down {
                self.tl_dragging = false;
                self.tl_drag = None;
            }
        });
    }

    // ---------------------------------------------------------------- stage

    fn compute_stage(&self, src_w: f64, src_h: f64, cw: f64, ch: f64) -> Stage {
        let margin = 18.0;
        let ratio = if self.zoom_fit {
            ((cw - margin * 2.0).max(20.0) / src_w).min((ch - margin * 2.0).max(20.0) / src_h)
        } else {
            self.zoom_factor
        };
        let (sw, sh) = (src_w * ratio, src_h * ratio);
        Stage {
            src_w,
            src_h,
            x0: (cw - sw) / 2.0 + self.pan.0,
            y0: (ch - sh) / 2.0 + self.pan.1,
            ratio,
        }
    }

    fn stage_ui(&mut self, ui: &mut egui::Ui, preset: Option<&mut Value>, lang: Lang) {
        let size = ui.available_size();
        let (resp, painter) = ui.allocate_painter(size, Sense::click_and_drag());
        let rect = resp.rect;
        let ctx = ui.ctx().clone();
        painter.rect_filled(rect, 0.0, pal::MONITOR_BG);
        painter.rect_stroke(rect, 0.0, Stroke::new(1.0, pal::BORDER));

        let Some(preset) = preset else {
            self.stage = None;
            self.gizmos = Gizmos::default();
            self.hud_metrics.clear();
            painter.text(rect.center(), Align2::CENTER_CENTER, tr(lang, "viewer_empty"), FontId::proportional(13.0), pal::FG_MUTED);
            return;
        };
        if !preset.is_object() {
            return;
        }

        let (cw, ch) = (rect.width() as f64, rect.height() as f64);
        let o = rect.min;
        let (src_w, src_h) = src_size(preset);
        let mut stage = self.compute_stage(src_w, src_h, cw, ch);

        // ---- zoom (wheel) & pan (middle button)
        let (scroll, mid_pressed, mid_down, delta) = ctx.input(|i| {
            (i.raw_scroll_delta.y, i.pointer.button_pressed(PointerButton::Middle), i.pointer.button_down(PointerButton::Middle), i.pointer.delta())
        });
        if resp.hovered() && scroll != 0.0 {
            let factor = if scroll > 0.0 { 1.15 } else { 1.0 / 1.15 };
            let new_ratio = (stage.ratio * factor).clamp(0.05, 4.0);
            self.zoom_fit = false;
            self.zoom_factor = new_ratio;
            self.zoom_text = format!("{}%", (new_ratio * 100.0).round() as i64);
            stage = self.compute_stage(src_w, src_h, cw, ch);
        }
        if resp.hovered() && mid_pressed {
            self.panning = true;
        }
        if self.panning {
            if mid_down {
                self.pan.0 += delta.x as f64;
                self.pan.1 += delta.y as f64;
                ctx.set_cursor_icon(CursorIcon::Grabbing);
                stage = self.compute_stage(src_w, src_h, cw, ch);
            } else {
                self.panning = false;
            }
        }
        self.stage = Some(stage);

        let mut motion = self.motion_tf(preset, src_w, src_h);
        self.gizmos = self.build_gizmos(preset, &stage, &motion);

        // ---- pointer interaction
        let (pressed, down, released, latest, shift, ctrl) = ctx.input(|i| {
            (
                i.pointer.primary_pressed(),
                i.pointer.primary_down(),
                i.pointer.primary_released(),
                i.pointer.latest_pos(),
                i.modifiers.shift,
                i.modifiers.ctrl || i.modifiers.command,
            )
        });
        let local = latest.map(|p| ((p.x - o.x) as f64, (p.y - o.y) as f64));
        let mut mutated = false;

        if resp.hovered() {
            if let Some((lx, ly)) = local {
                self.cursor_coords = format!("XY: {:.0}, {:.0}", (lx - stage.x0) / stage.ratio, (ly - stage.y0) / stage.ratio);
            }
        }

        if pressed && resp.hovered() && !self.panning {
            if let Some((lx, ly)) = local {
                let (mode, extra) = self.hit_test(lx, ly);
                if let (Some(mode), Some(b)) = (mode, self.gizmos.box_info.clone()) {
                    self.pause();
                    self.drag = Some(DragState { mode, kf_ref: extra, start_canvas: (lx, ly), start_pos: b.pos, start_anchor: b.anchor });
                    if mode == DragMode::PathKf {
                        if let Some((ei, ki)) = extra {
                            let t = param(&effects(preset)[ei], "position")
                                .and_then(|p| p.get("keyframes"))
                                .and_then(|k| k.get(ki))
                                .map(|kf| kf_time(kf) as i64);
                            if let Some(t) = t {
                                self.seek(t);
                            }
                        }
                    }
                }
            }
        }
        if self.drag.is_some() && down {
            if let Some(ptr) = local {
                mutated = self.handle_drag(preset, &stage, ptr, shift, ctrl);
            }
        }
        if self.drag.is_some() && (released || !down) {
            self.drag = None;
            self.snap_lines.clear();
            mutated = true;
        }
        if self.drag.is_none() && resp.hovered() && !self.panning {
            if let Some((lx, ly)) = local {
                let (mode, _) = self.hit_test(lx, ly);
                ctx.set_cursor_icon(match mode {
                    Some(DragMode::Move) => CursorIcon::Move,
                    Some(DragMode::Anchor) => CursorIcon::Crosshair,
                    Some(DragMode::PathKf) => CursorIcon::PointingHand,
                    Some(DragMode::Rotate) => CursorIcon::Alias,
                    Some(DragMode::ScaleCorner) => CursorIcon::ResizeNwSe,
                    Some(DragMode::ScaleX) => CursorIcon::ResizeHorizontal,
                    Some(DragMode::ScaleY) => CursorIcon::ResizeVertical,
                    None => CursorIcon::Default,
                });
            }
        }
        if mutated {
            motion = self.motion_tf(preset, src_w, src_h);
            self.gizmos = self.build_gizmos(preset, &stage, &motion);
            ctx.request_repaint();
        }

        // ---- drawing (clipped to the canvas)
        self.draw_stage(&painter, o, &stage, preset, &motion, lang);
        self.update_hud(&stage);
    }

    fn update_hud(&mut self, st: &Stage) {
        self.hud_metrics = match &self.gizmos.box_info {
            None => format!("Canvas: {}×{}", st.src_w as i64, st.src_h as i64),
            Some(b) => format!(
                "Pos: {:.1}, {:.1}  |  Scale: {:.1}% × {:.1}%  |  Rot: {:.1}°  |  Anchor: {:.1}, {:.1}",
                b.pos.0,
                b.pos.1,
                b.sx * 100.0,
                b.sy * 100.0,
                b.rot_deg,
                b.anchor.0,
                b.anchor.1
            ),
        };
    }

    fn draw_stage(&mut self, painter: &Painter, o: Pos2, st: &Stage, preset: &Value, motion: &MotionTf, lang: Lang) {
        let p = |x: f64, y: f64| Pos2::new(o.x + x as f32, o.y + y as f32);
        let (x0, y0, ratio) = (st.x0, st.y0, st.ratio);
        let (sw, sh) = (st.src_w * ratio, st.src_h * ratio);
        let (x1, y1) = (x0 + sw, y0 + sh);
        let stage_rect = Rect::from_min_max(p(x0, y0), p(x1, y1));

        // background
        match BG_KEYS[self.bg_mode] {
            "bg_chroma" => self.stage_bg_hex = "#00b140".into(),
            "bg_checker" => self.stage_bg_hex = "#1b1d22".into(),
            _ => self.stage_bg_hex = "#0a0b0d".into(),
        }
        painter.rect_filled(stage_rect, 0.0, hex_color(&self.stage_bg_hex));
        if BG_KEYS[self.bg_mode] == "bg_checker" {
            let tile = 20.0;
            let (cols, rows) = ((sw / tile) as i64 + 1, (sh / tile) as i64 + 1);
            for r in 0..rows {
                for c in 0..cols {
                    if (r + c) % 2 == 0 {
                        let (tx0, ty0) = (x0 + c as f64 * tile, y0 + r as f64 * tile);
                        painter.rect_filled(
                            Rect::from_min_max(p(tx0, ty0), p(x1.min(tx0 + tile), y1.min(ty0 + tile))),
                            0.0,
                            theme::rgb(0x252830),
                        );
                    }
                }
            }
        }
        painter.rect_stroke(stage_rect, 0.0, Stroke::new(1.0, pal::BORDER_LIGHT));

        let dashed = |a: Pos2, b: Pos2, col: Color32, dash: f32, gap: f32| {
            painter.extend(Shape::dashed_line(&[a, b], Stroke::new(1.0, col), dash, gap));
        };
        let dashed_rect = |ax: f64, ay: f64, bx: f64, by: f64, col: Color32, dash: f32, gap: f32| {
            let pts = [p(ax, ay), p(bx, ay), p(bx, by), p(ax, by), p(ax, ay)];
            painter.extend(Shape::dashed_line(&pts, Stroke::new(1.0, col), dash, gap));
        };
        if self.guides {
            let (cx, cy) = (x0 + sw / 2.0, y0 + sh / 2.0);
            dashed(p(cx, y0), p(cx, y1), theme::rgb(0x242730), 3.0, 4.0);
            dashed(p(x0, cy), p(x1, cy), theme::rgb(0x242730), 3.0, 4.0);
            dashed_rect(x0 + sw * 0.05, y0 + sh * 0.05, x1 - sw * 0.05, y1 - sh * 0.05, theme::rgb(0x23262f), 4.0, 4.0);
            dashed_rect(x0 + sw * 0.10, y0 + sh * 0.10, x1 - sw * 0.10, y1 - sh * 0.10, theme::rgb(0x1e2129), 2.0, 4.0);
        }
        if self.thirds {
            for frac in [1.0 / 3.0, 2.0 / 3.0] {
                let (tx, ty) = (x0 + sw * frac, y0 + sh * frac);
                dashed(p(tx, y0), p(tx, y1), theme::rgb(0x283244), 2.0, 3.0);
                dashed(p(x0, ty), p(x1, ty), theme::rgb(0x283244), 2.0, 3.0);
            }
        }

        // foreground content is clipped to the viewer canvas, not to the stage (like Tk)
        let stage_bg = self.stage_bg_hex.clone();
        let global_op = self.global_opacity(preset);
        let has_graphic_text = effects(preset).iter().any(|e| eff_enabled(e) && eff_type(e) == "graphic_text");
        let obj_key = OBJ_KEYS[self.obj_mode];

        let shape_kind = match obj_key {
            "obj_rect" => Some("rect"),
            "obj_square" => Some("square"),
            "obj_circle" => Some("circle"),
            "obj_triangle" => Some("triangle"),
            "obj_diamond" => Some("diamond"),
            "obj_star" => Some("star"),
            "obj_block_text" => Some("block_text"),
            _ => None,
        };
        if let Some(kind) = shape_kind {
            self.render_example_shape(painter, o, kind, st, motion, global_op, &stage_bg);
        }

        let gtext_effects: Vec<&Value> =
            effects(preset).iter().filter(|e| eff_enabled(e) && eff_type(e) == "graphic_text").collect();
        if obj_key == "obj_text" || obj_key == "obj_block_text" || (obj_key == "obj_auto" && !has_graphic_text) {
            if has_graphic_text {
                for eff in &gtext_effects {
                    self.render_graphic_text(painter, o, eff, st, &stage_bg, motion, global_op, Some(self.example_text.clone()));
                }
            } else {
                self.render_dummy_text_for_motion(painter, o, st, motion, global_op, &stage_bg, lang);
            }
        } else if has_graphic_text && obj_key == "obj_auto" {
            for eff in &gtext_effects {
                self.render_graphic_text(painter, o, eff, st, &stage_bg, motion, global_op, None);
            }
        }

        // snap guides
        for &(vertical, coord) in &self.snap_lines {
            let stroke = Stroke::new(1.0, pal::CYAN);
            if vertical {
                let sx = x0 + coord * ratio;
                painter.extend(Shape::dashed_line(&[p(sx, y0), p(sx, y1)], stroke, 4.0, 2.0));
            } else {
                let sy = y0 + coord * ratio;
                painter.extend(Shape::dashed_line(&[p(x0, sy), p(x1, sy)], stroke, 4.0, 2.0));
            }
        }

        self.draw_gizmos(painter, o);
    }

    fn draw_gizmos(&self, painter: &Painter, o: Pos2) {
        let p = |x: f64, y: f64| Pos2::new(o.x + x as f32, o.y + y as f32);
        let g = &self.gizmos;
        let tool = self.active_tool;

        // motion path
        if g.path_curve.len() >= 2 {
            let col = if tool == Tool::Path { pal::CYAN } else { theme::rgb(0x3a7ca5) };
            let pts: Vec<Pos2> = g.path_curve.iter().map(|&(x, y)| p(x, y)).collect();
            painter.extend(Shape::dashed_line(&pts, Stroke::new(if tool == Tool::Path { 2.0 } else { 1.0 }, col), 4.0, 3.0));
            let tol = self.frame_ns() / 2.0;
            for n in &g.path_nodes {
                let is_cur = (n.time as f64 - self.current_time_ns as f64).abs() <= tol;
                let r = if tool == Tool::Path { 6.0 } else { 4.0 };
                painter.add(Shape::convex_polygon(
                    vec![p(n.x, n.y - r), p(n.x + r, n.y), p(n.x, n.y + r), p(n.x - r, n.y)],
                    if is_cur { pal::ACCENT } else { pal::CYAN },
                    Stroke::new(1.0, Color32::WHITE),
                ));
            }
        }

        let Some(b) = &g.box_info else { return };
        let corners: Vec<Pos2> = g.box_poly.iter().map(|&(x, y)| p(x, y)).collect();
        let outline = if tool == Tool::Transform { pal::ACCENT } else { theme::rgb(0x5c6475) };
        let mut closed = corners.clone();
        closed.push(corners[0]);
        if tool == Tool::Transform {
            painter.add(Shape::closed_line(corners.clone(), Stroke::new(1.0, outline)));
        } else {
            painter.extend(Shape::dashed_line(&closed, Stroke::new(1.0, outline), 3.0, 3.0));
        }

        // anchor / pivot crosshair
        if let Some(&(ax, ay)) = g.handles.get("anchor") {
            let r = if tool == Tool::Anchor { 7.0 } else { 5.0 };
            let col = if tool == Tool::Anchor { pal::CYAN } else { pal::ACCENT };
            let c = p(ax, ay);
            painter.circle_stroke(c, r, Stroke::new(2.0, col));
            painter.line_segment([Pos2::new(c.x - r - 4.0, c.y), Pos2::new(c.x + r + 4.0, c.y)], Stroke::new(1.0, col));
            painter.line_segment([Pos2::new(c.x, c.y - r - 4.0), Pos2::new(c.x, c.y + r + 4.0)], Stroke::new(1.0, col));
        }
        if tool != Tool::Transform {
            return;
        }

        for c in &corners {
            let r = Rect::from_center_size(*c, Vec2::splat(8.0));
            painter.rect_filled(r, 0.0, Color32::WHITE);
            painter.rect_stroke(r, 0.0, Stroke::new(2.0, pal::ACCENT));
        }
        for name in ["edge_top", "edge_right", "edge_bottom", "edge_left"] {
            if let Some(&(mx, my)) = g.handles.get(name) {
                painter.circle_filled(p(mx, my), 4.0, pal::ACCENT);
                painter.circle_stroke(p(mx, my), 4.0, Stroke::new(1.0, Color32::WHITE));
            }
        }
        if let (Some(&(tx, ty)), Some(&(rx, ry))) = (g.handles.get("edge_top"), g.handles.get("rotate")) {
            painter.line_segment([p(tx, ty), p(rx, ry)], Stroke::new(2.0, pal::ACCENT));
            painter.circle_filled(p(rx, ry), 6.0, pal::CYAN);
            painter.circle_stroke(p(rx, ry), 6.0, Stroke::new(2.0, Color32::WHITE));
        }
        let _ = b;
    }

    // ---------------------------------------------------------------- content rendering

    fn render_example_shape(&self, painter: &Painter, o: Pos2, kind: &str, st: &Stage, m: &MotionTf, global_op: f64, stage_bg: &str) {
        let sw = self.shape_w.trim().parse::<f64>().map(|v| v.max(10.0)).unwrap_or(460.0);
        let sh = self.shape_h.trim().parse::<f64>().map(|v| v.max(10.0)).unwrap_or(240.0);
        let verts = build_shape_vertices(kind, st.src_w / 2.0, st.src_h / 2.0, sw, sh);
        let pts: Vec<Pos2> = verts
            .iter()
            .map(|&(vx, vy)| {
                let (tx, ty) = if m.has_motion { m.apply(vx, vy) } else { (vx, vy) };
                Pos2::new(o.x + (st.x0 + tx * st.ratio) as f32, o.y + (st.y0 + ty * st.ratio) as f32)
            })
            .collect();

        let fill = hex_color(&blend_rgba_on_bg(&hex_to_rgba_float(&self.example_color_hex(), 0.85), global_op, stage_bg));
        fill_fan(painter, &pts, fill);
        painter.add(Shape::closed_line(pts.clone(), Stroke::new(2.0, pal::FG_TEXT)));

        if matches!(kind, "rect" | "square" | "block_text") && pts.len() >= 4 {
            let col = theme::rgb(0x16181d);
            painter.extend(Shape::dashed_line(&[pts[0], pts[2]], Stroke::new(1.0, col), 3.0, 3.0));
            painter.extend(Shape::dashed_line(&[pts[1], pts[3]], Stroke::new(1.0, col), 3.0, 3.0));
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn render_dummy_text_for_motion(&self, painter: &Painter, o: Pos2, st: &Stage, m: &MotionTf, global_op: f64, stage_bg: &str, lang: Lang) {
        let txt = {
            let t = self.example_text.trim();
            if t.is_empty() { tr(lang, "default_sample_text") } else { t.to_string() }
        };
        let (cx, cy) = (st.src_w / 2.0, st.src_h / 2.0);
        let (tx, ty, avg_scale, rot_deg) = if m.has_motion {
            let (tx, ty) = m.apply(cx, cy);
            (tx, ty, (m.sx + m.sy) / 2.0, m.rot_deg)
        } else {
            (cx, cy, 1.0, 0.0)
        };
        let center = Pos2::new(o.x + (st.x0 + tx * st.ratio) as f32, o.y + (st.y0 + ty * st.ratio) as f32);
        let size = ((78.0 * avg_scale * st.ratio) as f32).clamp(2.0, 600.0);

        let fmt = TextStyle { size, bold: true, italic: false, underline: false, strike: false };
        let outline = layout_block(painter, &txt, &fmt, hex_color("#0a0b0d"));
        for i in 0..8 {
            let ang = 2.0 * std::f32::consts::PI * i as f32 / 8.0;
            paint_block(painter, &outline, center, Vec2::new(ang.cos() * 2.0, ang.sin() * 2.0), rot_deg as f32, Justify::Center, false);
        }
        let base = if OBJ_KEYS[self.obj_mode] == "obj_block_text" { "#ffffff".to_string() } else { self.example_color_hex() };
        let col = hex_color(&blend_rgba_on_bg(&hex_to_rgba_float(&base, 1.0), global_op, stage_bg));
        let fill = layout_block(painter, &txt, &fmt, col);
        paint_block(painter, &fill, center, Vec2::ZERO, rot_deg as f32, Justify::Center, true);
    }

    #[allow(clippy::too_many_arguments)]
    fn render_graphic_text(
        &self, painter: &Painter, o: Pos2, eff: &Value, st: &Stage, stage_bg: &str, m: &MotionTf, global_op: f64,
        override_text: Option<String>,
    ) {
        let t = self.current_time_ns as f64;
        let p = |k: &str| param(eff, k);

        let mut raw_text = match override_text {
            Some(s) => s,
            None => eval_text(p("text"), t).unwrap_or_default(),
        };
        if raw_text.is_empty() {
            return;
        }
        match eval_choice(p("caps"), t) {
            Some(1) => raw_text = raw_text.to_uppercase(),
            Some(2) => raw_text = title_case(&raw_text),
            _ => {}
        }

        let font_style = eval_text(p("font_style"), t).unwrap_or_else(|| "Regular".into()).to_lowercase();
        let bold = font_style.contains("bold") || eval_bool(p("faux_bold"), t);
        let italic = font_style.contains("italic") || eval_bool(p("faux_italic"), t);

        let base_size = or_nz(eval_f64(p("size"), t), 100.0);
        let mut scale_pct = or_nz(eval_f64(p("scale"), t), 100.0);
        let opacity_pct = eval_f64(p("opacity"), t).unwrap_or(100.0) * (global_op / 100.0);
        let mut rotation_deg = eval_f64(p("rotation"), t).unwrap_or(0.0);

        let (mut src_px, mut src_py) = eval_vec2(p("position"), t).unwrap_or((960.0, 540.0));
        if m.has_motion {
            let (nx, ny) = m.apply(src_px, src_py);
            src_px = nx;
            src_py = ny;
            scale_pct *= (m.sx + m.sy) / 2.0;
            rotation_deg += m.rot_deg;
        }

        let px = st.x0 + src_px * st.ratio;
        let py = st.y0 + src_py * st.ratio;
        let center = Pos2::new(o.x + px as f32, o.y + py as f32);
        let size = ((base_size * (scale_pct / 100.0) * st.ratio) as f32).clamp(2.0, 600.0);

        let style = TextStyle {
            size,
            bold,
            italic,
            underline: eval_bool(p("underline"), t),
            strike: eval_bool(p("strikethrough"), t),
        };
        let justify = match eval_choice(p("align"), t) {
            Some(0) => Justify::Left,
            Some(2) => Justify::Right,
            _ => Justify::Center,
        };
        let rot = rotation_deg as f32;
        let sc = scale_pct / 100.0;

        // background box
        if eval_bool(p("background"), t) {
            let probe = layout_block(painter, &raw_text, &style, Color32::TRANSPARENT);
            let bg_pad = or_nz(eval_f64(p("background_size"), t), 12.0) * st.ratio * sc;
            let bg_rgba = eval_color(p("background_color"), t).unwrap_or([0.0, 0.0, 0.0, 1.0]);
            let bg_op = eval_f64(p("background_opacity"), t).unwrap_or(75.0);
            let bg = hex_color(&blend_rgba_on_bg(&bg_rgba, bg_op * (opacity_pct / 100.0), stage_bg));
            let (hw, hh) = (probe.w as f64 / 2.0 + bg_pad, probe.h as f64 / 2.0 + bg_pad * 0.6);
            painter.rect_filled(
                Rect::from_min_max(
                    Pos2::new(o.x + (px - hw) as f32, o.y + (py - hh) as f32),
                    Pos2::new(o.x + (px + hw) as f32, o.y + (py + hh) as f32),
                ),
                0.0,
                bg,
            );
        }

        // shadow
        if eval_bool(p("shadow"), t) {
            let ang = eval_f64(p("shadow_angle"), t).unwrap_or(135.0).to_radians();
            let dist = or_nz(eval_f64(p("shadow_distance"), t), 10.0) * st.ratio * sc;
            let rgba = eval_color(p("shadow_color"), t).unwrap_or([0.0, 0.0, 0.0, 1.0]);
            let op = eval_f64(p("shadow_opacity"), t).unwrap_or(75.0);
            let col = hex_color(&blend_rgba_on_bg(&rgba, op * (opacity_pct / 100.0), stage_bg));
            let block = layout_block(painter, &raw_text, &style, col);
            paint_block(painter, &block, center, Vec2::new((ang.cos() * dist) as f32, (ang.sin() * dist) as f32), rot, justify, false);
        }

        // stroke (ring of offset copies, like the Tk original)
        if eval_bool(p("stroke"), t) {
            let width = or_nz(eval_f64(p("stroke_width"), t), 7.0) * st.ratio * sc;
            let rgba = eval_color(p("stroke_color"), t).unwrap_or([0.0, 0.0, 0.0, 1.0]);
            let col = hex_color(&blend_rgba_on_bg(&rgba, opacity_pct, stage_bg));
            let r_px = width.max(1.0) as f32;
            let steps = if r_px >= 2.5 { 12 } else { 8 };
            let block = layout_block(painter, &raw_text, &style, col);
            for i in 0..steps {
                let ang = 2.0 * std::f32::consts::PI * i as f32 / steps as f32;
                paint_block(painter, &block, center, Vec2::new(ang.cos() * r_px, ang.sin() * r_px), rot, justify, false);
            }
        }

        // fill
        let fill_enabled = match p("fill") {
            Some(f) => eval_bool(Some(f), t),
            None => true,
        };
        if fill_enabled {
            let rgba = eval_color(p("fill_color"), t).unwrap_or([1.0, 1.0, 1.0, 1.0]);
            let col = hex_color(&blend_rgba_on_bg(&rgba, opacity_pct, stage_bg));
            let block = layout_block(painter, &raw_text, &style, col);
            paint_block(painter, &block, center, Vec2::ZERO, rot, justify, style.bold);
        }
    }
}

// ===================================================================== drawing helpers

struct TextStyle {
    size: f32,
    bold: bool,
    italic: bool,
    underline: bool,
    strike: bool,
}

struct Block {
    lines: Vec<Arc<Galley>>,
    w: f32,
    h: f32,
    color: Color32,
}

fn layout_block(painter: &Painter, text: &str, style: &TextStyle, color: Color32) -> Block {
    let fmt = TextFormat {
        font_id: FontId::proportional(style.size),
        color,
        italics: style.italic,
        underline: if style.underline { Stroke::new(1.0, color) } else { Stroke::NONE },
        strikethrough: if style.strike { Stroke::new(1.0, color) } else { Stroke::NONE },
        ..Default::default()
    };
    let src: Vec<&str> = if text.is_empty() { vec![""] } else { text.lines().collect() };
    let lines: Vec<Arc<Galley>> =
        src.iter().map(|l| painter.layout_job(LayoutJob::single_section(l.to_string(), fmt.clone()))).collect();
    let w = lines.iter().map(|g| g.size().x).fold(0.0, f32::max);
    let h = lines.iter().map(|g| g.size().y.max(style.size * 1.15)).sum();
    Block { lines, w, h, color }
}

/// Paints a text block centred on `center + offset`, rotated clockwise by `rot_deg`.
fn paint_block(painter: &Painter, block: &Block, center: Pos2, offset: Vec2, rot_deg: f32, justify: Justify, faux_bold: bool) {
    let rad = rot_deg.to_radians();
    let (sin, cos) = rad.sin_cos();
    let mut y = -block.h / 2.0;
    for g in &block.lines {
        let lw = g.size().x;
        let lh = g.size().y.max(1.0);
        let x = match justify {
            Justify::Left => -block.w / 2.0,
            Justify::Center => -lw / 2.0,
            Justify::Right => block.w / 2.0 - lw,
        };
        let rotated = Vec2::new(x * cos - y * sin, x * sin + y * cos);
        let pos = center + offset + rotated;
        painter.add(egui::epaint::TextShape::new(pos, g.clone(), block.color).with_angle(rad));
        if faux_bold {
            let extra = Vec2::new(cos, sin) * 0.8;
            painter.add(egui::epaint::TextShape::new(pos + extra, g.clone(), block.color).with_angle(rad));
        }
        y += lh.max(block.h / block.lines.len() as f32);
    }
}

/// Fills a (star-shaped) polygon by fanning triangles from its centroid.
fn fill_fan(painter: &Painter, pts: &[Pos2], color: Color32) {
    if pts.len() < 3 {
        return;
    }
    let n = pts.len() as f32;
    let centroid = Pos2::new(pts.iter().map(|p| p.x).sum::<f32>() / n, pts.iter().map(|p| p.y).sum::<f32>() / n);
    let mut mesh = Mesh::default();
    mesh.colored_vertex(centroid, color);
    for p in pts {
        mesh.colored_vertex(*p, color);
    }
    for i in 0..pts.len() {
        mesh.add_triangle(0, 1 + i as u32, 1 + ((i + 1) % pts.len()) as u32);
    }
    painter.add(Shape::mesh(mesh));
}
