//! Small helpers for navigating / mutating Filmcraft JSON (`serde_json::Value`).

use serde_json::{json, Value};

use crate::engine::num;

pub fn effects(preset: &Value) -> &[Value] {
    preset.get("effects").and_then(|e| e.as_array()).map(|v| v.as_slice()).unwrap_or(&[])
}

pub fn eff_enabled(e: &Value) -> bool {
    e.get("enabled").and_then(|v| v.as_bool()).unwrap_or(true)
}

pub fn eff_type(e: &Value) -> &str {
    e.get("effect").and_then(|v| v.as_str()).unwrap_or("")
}

pub fn param<'a>(eff: &'a Value, key: &str) -> Option<&'a Value> {
    eff.get("params").and_then(|p| p.get(key))
}

pub fn param_mut<'a>(preset: &'a mut Value, eff: usize, key: &str) -> Option<&'a mut Value> {
    preset.get_mut("effects")?.get_mut(eff)?.get_mut("params")?.get_mut(key)
}

pub fn kf_time(kf: &Value) -> f64 {
    kf.get("time").and_then(num).unwrap_or(0.0)
}

pub fn has_keyframes(param: &Value) -> bool {
    param.get("keyframes").and_then(|k| k.as_array()).map(|k| !k.is_empty()).unwrap_or(false)
}

/// `(width, height)` of the preset's `source_size` with Filmcraft defaults.
pub fn src_size(preset: &Value) -> (f64, f64) {
    let arr = preset.get("source_size").and_then(|v| v.as_array());
    match arr {
        Some(a) if a.len() >= 2 => {
            let w = a[0].as_f64().filter(|v| *v > 0.0).unwrap_or(1920.0);
            let h = a[1].as_f64().filter(|v| *v > 0.0).unwrap_or(1080.0);
            (w, h)
        }
        _ => (1920.0, 1080.0),
    }
}

pub fn vec2(x: f64, y: f64) -> Value {
    json!({"x": x, "y": y})
}

pub fn round_to(x: f64, decimals: i32) -> f64 {
    let m = 10f64.powi(decimals);
    (x * m).round() / m
}

/// Stable-sorts a keyframe array by time and returns the new index of the keyframe
/// that used to be at `tracked`.
pub fn sort_keyframes_tracking(kfs: &mut Vec<Value>, tracked: usize) -> usize {
    let mut order: Vec<usize> = (0..kfs.len()).collect();
    order.sort_by(|&a, &b| kf_time(&kfs[a]).partial_cmp(&kf_time(&kfs[b])).unwrap_or(std::cmp::Ordering::Equal));
    let new_index = order.iter().position(|&i| i == tracked).unwrap_or(tracked);
    let sorted: Vec<Value> = order.iter().map(|&i| kfs[i].clone()).collect();
    *kfs = sorted;
    new_index
}

pub fn sort_keyframes(kfs: &mut Vec<Value>) {
    sort_keyframes_tracking(kfs, 0);
}

pub fn set_in_value_obj(param: &mut Value, type_tag: &str, v: Value) {
    if let Some(obj) = param.get_mut("value").and_then(|v| v.as_object_mut()) {
        obj.insert(type_tag.to_string(), v);
    }
}

/// Integer `(width, height)` for display (falls back to 1920x1080).
pub fn src_size_ints(preset: &Value) -> (i64, i64) {
    match preset.get("source_size").and_then(|v| v.as_array()) {
        Some(a) if a.len() >= 2 => (
            a[0].as_f64().map(|v| v as i64).unwrap_or(1920),
            a[1].as_f64().map(|v| v as i64).unwrap_or(1080),
        ),
        _ => (1920, 1080),
    }
}
