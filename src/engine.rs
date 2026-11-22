//! Pure mathematical engine: RGBA blending, cubic Bezier solver and 2D affine transforms.

use serde_json::{json, Value};

pub type Rgba = [f64; 4];

/// Numeric JSON value (bools are not numbers, like in the Python original).
pub fn num(v: &Value) -> Option<f64> {
    match v {
        Value::Number(n) => n.as_f64(),
        _ => None,
    }
}

/// Reads a JSON array `[r, g, b, (a)]` as an RGBA quadruple.
pub fn value_to_rgba(v: &Value) -> Option<Rgba> {
    let arr = v.as_array()?;
    if arr.len() < 3 {
        return None;
    }
    let g = |i: usize| arr.get(i).and_then(num).unwrap_or(0.0);
    let a = if arr.len() >= 4 { g(3) } else { 1.0 };
    Some([g(0), g(1), g(2), a])
}

pub fn rgba_to_hex(rgba: &Rgba) -> String {
    let c = |x: f64| (x * 255.0).round().clamp(0.0, 255.0) as u8;
    format!("#{:02x}{:02x}{:02x}", c(rgba[0]), c(rgba[1]), c(rgba[2]))
}

pub fn rgba_float_to_hex(v: &Value) -> String {
    match value_to_rgba(v) {
        Some(c) => rgba_to_hex(&c),
        None => "#ffffff".to_string(),
    }
}

pub fn hex_to_rgba_float(hex: &str, alpha: f64) -> Rgba {
    let (r, g, b) = parse_hex(hex);
    let r6 = |x: u8| ((x as f64 / 255.0) * 1e6).round() / 1e6;
    [r6(r), r6(g), r6(b), alpha]
}

pub fn parse_hex(hex: &str) -> (u8, u8, u8) {
    let h = hex.trim_start_matches('#');
    let p = |i: usize| h.get(i..i + 2).and_then(|s| u8::from_str_radix(s, 16).ok()).unwrap_or(0);
    (p(0), p(2), p(4))
}

pub fn blend_rgba_on_bg(rgba: &Rgba, opacity_pct: f64, bg_hex: &str) -> String {
    let alpha = (rgba[3] * (opacity_pct / 100.0)).clamp(0.0, 1.0);
    let (br, bg, bb) = parse_hex(bg_hex);
    let mix = |fg: f64, bgc: u8| (fg * 255.0 * alpha + bgc as f64 * (1.0 - alpha)).round().clamp(0.0, 255.0) as u8;
    format!("#{:02x}{:02x}{:02x}", mix(rgba[0], br), mix(rgba[1], bg), mix(rgba[2], bb))
}

pub fn cubic_bezier_ease(u: f64, out_influence: f64, in_influence: f64) -> f64 {
    if u <= 0.0 {
        return 0.0;
    }
    if u >= 1.0 {
        return 1.0;
    }
    let x1 = out_influence.clamp(0.0, 1.0);
    let x2 = (1.0 - in_influence).clamp(0.0, 1.0);

    let mut s = u;
    for _ in 0..6 {
        let inv = 1.0 - s;
        let x_s = 3.0 * inv * inv * s * x1 + 3.0 * inv * s * s * x2 + s * s * s;
        let dx_s = 3.0 * inv * inv * x1 + 6.0 * inv * s * (x2 - x1) + 3.0 * s * s * (1.0 - x2);
        if dx_s.abs() < 1e-6 {
            break;
        }
        s = (s - (x_s - u) / dx_s).clamp(0.0, 1.0);
    }
    let inv = 1.0 - s;
    3.0 * inv * s * s + s * s * s
}

fn kf_time(kf: &Value) -> f64 {
    kf.get("time").and_then(num).unwrap_or(0.0)
}

fn kf_val<'a>(kf: &'a Value, tag: &str, base: &'a Value) -> &'a Value {
    kf.get("value").and_then(|v| v.get(tag)).unwrap_or(base)
}

/// Evaluates a Filmcraft parameter (`{"value": {Tag: v}, "keyframes": [...]}`) at `time_ns`.
pub fn evaluate_filmcraft_param(param: Option<&Value>, time_ns: f64) -> Option<Value> {
    let param = param?;
    let val_wrapper = param.get("value")?.as_object()?;
    let (type_tag, base_val) = val_wrapper.iter().next()?;

    let keyframes = match param.get("keyframes").and_then(|k| k.as_array()) {
        Some(k) if !k.is_empty() => k,
        _ => return Some(base_val.clone()),
    };

    let mut kfs: Vec<&Value> = keyframes.iter().collect();
    kfs.sort_by(|a, b| kf_time(a).partial_cmp(&kf_time(b)).unwrap_or(std::cmp::Ordering::Equal));

    if time_ns <= kf_time(kfs[0]) {
        return Some(kf_val(kfs[0], type_tag, base_val).clone());
    }
    if time_ns >= kf_time(kfs[kfs.len() - 1]) {
        return Some(kf_val(kfs[kfs.len() - 1], type_tag, base_val).clone());
    }

    for i in 0..kfs.len() - 1 {
        let (kf0, kf1) = (kfs[i], kfs[i + 1]);
        let (t0, t1) = (kf_time(kf0), kf_time(kf1));
        if t0 <= time_ns && time_ns <= t1 {
            if t1 == t0 {
                return Some(kf_val(kf1, type_tag, base_val).clone());
            }
            let u = (time_ns - t0) / (t1 - t0);
            let interp = kf0.get("interp").and_then(|v| v.as_str()).unwrap_or("Linear");
            let eased = match interp {
                "Hold" | "Step" => 0.0,
                "Linear" => u,
                _ => cubic_bezier_ease(
                    u,
                    kf0.get("out_influence").and_then(num).unwrap_or(0.33333333),
                    kf1.get("in_influence").and_then(num).unwrap_or(0.33333333),
                ),
            };
            let v0 = kf_val(kf0, type_tag, base_val);
            let v1 = kf_val(kf1, type_tag, base_val);

            if type_tag == "Float" {
                if let (Some(a), Some(b)) = (num(v0), num(v1)) {
                    return Some(json!(a + (b - a) * eased));
                }
            }
            if type_tag == "Vec2" && v0.is_object() && v1.is_object() {
                let g = |v: &Value, k: &str| v.get(k).and_then(num).unwrap_or(0.0);
                let (x0, y0, x1, y1) = (g(v0, "x"), g(v0, "y"), g(v1, "x"), g(v1, "y"));
                return Some(json!({"x": x0 + (x1 - x0) * eased, "y": y0 + (y1 - y0) * eased}));
            }
            return Some(v0.clone());
        }
    }
    Some(base_val.clone())
}

// ---- Typed convenience wrappers around `evaluate_filmcraft_param` ----

pub fn eval_f64(param: Option<&Value>, t: f64) -> Option<f64> {
    evaluate_filmcraft_param(param, t).and_then(|v| num(&v))
}

pub fn eval_vec2(param: Option<&Value>, t: f64) -> Option<(f64, f64)> {
    let v = evaluate_filmcraft_param(param, t)?;
    if !v.is_object() {
        return None;
    }
    Some((
        v.get("x").and_then(num).unwrap_or(0.0),
        v.get("y").and_then(num).unwrap_or(0.0),
    ))
}

pub fn eval_bool(param: Option<&Value>, t: f64) -> bool {
    match evaluate_filmcraft_param(param, t) {
        Some(Value::Bool(b)) => b,
        Some(Value::Number(n)) => n.as_f64().map(|x| x != 0.0).unwrap_or(false),
        Some(Value::String(s)) => !s.is_empty(),
        _ => false,
    }
}

pub fn eval_text(param: Option<&Value>, t: f64) -> Option<String> {
    match evaluate_filmcraft_param(param, t) {
        Some(Value::String(s)) => Some(s),
        _ => None,
    }
}

pub fn eval_choice(param: Option<&Value>, t: f64) -> Option<i64> {
    evaluate_filmcraft_param(param, t).and_then(|v| num(&v)).map(|x| x as i64)
}

pub fn eval_color(param: Option<&Value>, t: f64) -> Option<Rgba> {
    evaluate_filmcraft_param(param, t).and_then(|v| value_to_rgba(&v))
}

// ---- 2D geometry ----

/// Applies a 2D affine transform (Anchor -> Scale X/Y -> Rotation -> Position).
#[allow(clippy::too_many_arguments)]
pub fn transform_point_2d(
    px: f64, py: f64, anchor_x: f64, anchor_y: f64, pos_x: f64, pos_y: f64, sx: f64, sy: f64, rot_deg: f64,
) -> (f64, f64) {
    let dx = (px - anchor_x) * sx;
    let dy = (py - anchor_y) * sy;
    let rad = rot_deg.to_radians();
    let (sin_a, cos_a) = rad.sin_cos();
    (pos_x + dx * cos_a - dy * sin_a, pos_y + dx * sin_a + dy * cos_a)
}

/// Converts world point into unrotated offset relative to `(pos_x, pos_y)`.
pub fn inverse_rotate_offset(wx: f64, wy: f64, pos_x: f64, pos_y: f64, rot_deg: f64) -> (f64, f64) {
    let (vx, vy) = (wx - pos_x, wy - pos_y);
    let rad = rot_deg.to_radians();
    let (sin_a, cos_a) = rad.sin_cos();
    (vx * cos_a + vy * sin_a, -vx * sin_a + vy * cos_a)
}

/// Ray-casting point-in-polygon check.
pub fn point_in_polygon(x: f64, y: f64, poly: &[(f64, f64)]) -> bool {
    let n = poly.len();
    if n < 3 {
        return false;
    }
    let mut inside = false;
    let (mut p1x, mut p1y) = poly[0];
    for i in 1..=n {
        let (p2x, p2y) = poly[i % n];
        if y > p1y.min(p2y) && y <= p1y.max(p2y) && x <= p1x.max(p2x) {
            let xinters = if p1y != p2y { (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x } else { p1x };
            if p1x == p2x || x <= xinters {
                inside = !inside;
            }
        }
        p1x = p2x;
        p1y = p2y;
    }
    inside
}

/// A Vec2 keyframe sampled from a motion path.
#[derive(Clone, Debug)]
pub struct KfNode {
    /// Index inside the *original* (possibly unsorted) `keyframes` array.
    pub orig_index: usize,
    pub time: i64,
    pub x: f64,
    pub y: f64,
}

/// Samples a Vec2 keyframed parameter into polyline points and keyframe nodes.
pub fn sample_motion_path(param: Option<&Value>, samples_per_seg: usize) -> (Vec<(f64, f64)>, Vec<KfNode>) {
    let kfs = match param.and_then(|p| p.get("keyframes")).and_then(|k| k.as_array()) {
        Some(k) if k.len() >= 2 => k,
        _ => return (vec![], vec![]),
    };
    let mut order: Vec<usize> = (0..kfs.len()).collect();
    order.sort_by(|&a, &b| kf_time(&kfs[a]).partial_cmp(&kf_time(&kfs[b])).unwrap_or(std::cmp::Ordering::Equal));

    let mut nodes = Vec::new();
    for &idx in &order {
        let kf = &kfs[idx];
        if let Some(vec) = kf.get("value").and_then(|v| v.get("Vec2")).filter(|v| v.is_object()) {
            nodes.push(KfNode {
                orig_index: idx,
                time: kf_time(kf) as i64,
                x: vec.get("x").and_then(num).unwrap_or(0.0),
                y: vec.get("y").and_then(num).unwrap_or(0.0),
            });
        }
    }
    if nodes.len() < 2 {
        return (vec![], nodes);
    }

    let mut curve = Vec::new();
    for i in 0..nodes.len() - 1 {
        let (t0, t1) = (nodes[i].time, nodes[i + 1].time);
        let steps = if t1 <= t0 { 1 } else { samples_per_seg };
        for s in 0..steps {
            let t = t0 as f64 + (t1 - t0) as f64 * (s as f64 / steps as f64);
            if let Some((x, y)) = eval_vec2(param, t) {
                curve.push((x, y));
            }
        }
    }
    let last = &nodes[nodes.len() - 1];
    curve.push((last.x, last.y));
    (curve, nodes)
}

/// Generates vertices for the dummy shapes.
pub fn build_shape_vertices(kind: &str, cx: f64, cy: f64, width: f64, height: f64) -> Vec<(f64, f64)> {
    let (hw, hh) = (width / 2.0, height / 2.0);
    match kind {
        "rect" | "block_text" => vec![(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)],
        "square" => {
            let s = hw.min(hh);
            vec![(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)]
        }
        "triangle" => vec![(cx, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)],
        "diamond" => vec![(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)],
        "star" => (0..10)
            .map(|i| {
                let ang = -std::f64::consts::FRAC_PI_2 + i as f64 * std::f64::consts::PI / 5.0;
                let (rx, ry) = if i % 2 == 0 { (hw, hh) } else { (hw * 0.42, hh * 0.42) };
                (cx + ang.cos() * rx, cy + ang.sin() * ry)
            })
            .collect(),
        _ => (0..48)
            .map(|i| {
                let ang = 2.0 * std::f64::consts::PI * i as f64 / 48.0;
                (cx + ang.cos() * hw, cy + ang.sin() * hh)
            })
            .collect(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bezier_endpoints_and_monotonic() {
        assert_eq!(cubic_bezier_ease(0.0, 0.33, 0.33), 0.0);
        assert_eq!(cubic_bezier_ease(1.0, 0.33, 0.33), 1.0);
        let mid = cubic_bezier_ease(0.5, 0.33333333, 0.33333333);
        assert!((mid - 0.5).abs() < 1e-3);
    }

    #[test]
    fn keyframe_interpolation() {
        let p = json!({"value": {"Float": 0.0}, "keyframes": [
            {"time": 0, "value": {"Float": 0.0}, "interp": "Linear"},
            {"time": 1000, "value": {"Float": 10.0}, "interp": "Linear"}]});
        assert_eq!(eval_f64(Some(&p), 500.0), Some(5.0));
        assert_eq!(eval_f64(Some(&p), 5000.0), Some(10.0));
    }

    #[test]
    fn transform_roundtrip() {
        let (x, y) = transform_point_2d(10.0, 0.0, 0.0, 0.0, 100.0, 100.0, 1.0, 1.0, 90.0);
        assert!((x - 100.0).abs() < 1e-9 && (y - 110.0).abs() < 1e-9);
        let (ux, uy) = inverse_rotate_offset(x, y, 100.0, 100.0, 90.0);
        assert!((ux - 10.0).abs() < 1e-9 && uy.abs() < 1e-9);
    }

    #[test]
    fn blend_and_polygon() {
        assert_eq!(blend_rgba_on_bg(&[1.0, 1.0, 1.0, 1.0], 50.0, "#000000"), "#808080");
        let sq = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)];
        assert!(point_in_polygon(5.0, 5.0, &sq) && !point_in_polygon(15.0, 5.0, &sq));
    }

    #[test]
    fn templates_parse() {
        let t = crate::templates::filmcraft_text_template();
        assert_eq!(t["presets"][0]["effects"][0]["effect"], "graphic_text");
        let (curve, nodes) = sample_motion_path(t["presets"][0]["effects"][0]["params"].get("position"), 16);
        assert!(curve.len() > 3 && nodes.len() == 3);
    }
}
