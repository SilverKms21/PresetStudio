#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure mathematical engine: RGBA blending, Cubic Bezier solver, and 2D affine transforms."""

import math


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
    """Applies 2D affine transform (Anchor -> Scale X/Y -> Rotation -> Position)."""
    dx = (px - anchor_x) * sx
    dy = (py - anchor_y) * sy
    rad = math.radians(rot_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    rx = dx * cos_a - dy * sin_a
    ry = dx * sin_a + dy * cos_a
    return pos_x + rx, pos_y + ry


def inverse_rotate_offset(wx, wy, pos_x, pos_y, rot_deg):
    """Converts world point (wx, wy) into unrotated offset (ux, uy) relative to (pos_x, pos_y)."""
    vx = wx - pos_x
    vy = wy - pos_y
    rad = math.radians(rot_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    ux = vx * cos_a + vy * sin_a
    uy = -vx * sin_a + vy * cos_a
    return ux, uy


def point_in_polygon(x, y, poly_pts):
    """Ray-casting point-in-polygon check for 2D hit testing."""
    inside = False
    n = len(poly_pts)
    if n < 3:
        return False
    p1x, p1y = poly_pts[0]
    for i in range(1, n + 1):
        p2x, p2y = poly_pts[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    else:
                        xinters = p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def sample_motion_path(param_obj, samples_per_seg=18):
    """Samples a Vec2 keyframed parameter into polyline points and keyframe nodes."""
    if not isinstance(param_obj, dict):
        return [], []
    keyframes = param_obj.get("keyframes")
    if not isinstance(keyframes, list) or len(keyframes) < 2:
        return [], []

    kfs = sorted(keyframes, key=lambda k: k.get("time", 0))
    kf_nodes = []
    for idx, kf in enumerate(kfs):
        vec = kf.get("value", {}).get("Vec2")
        if isinstance(vec, dict):
            kf_nodes.append({
                "index": idx,
                "kf": kf,
                "time": int(kf.get("time", 0)),
                "x": float(vec.get("x", 0.0)),
                "y": float(vec.get("y", 0.0)),
            })

    if len(kf_nodes) < 2:
        return [], kf_nodes

    curve_pts = []
    for i in range(len(kf_nodes) - 1):
        t0 = kf_nodes[i]["time"]
        t1 = kf_nodes[i + 1]["time"]
        steps = 1 if t1 <= t0 else samples_per_seg
        for s in range(steps):
            t = t0 + (t1 - t0) * (s / float(steps))
            val = evaluate_filmcraft_param(param_obj, t)
            if isinstance(val, dict):
                curve_pts.append((float(val.get("x", 0.0)), float(val.get("y", 0.0))))

    curve_pts.append((kf_nodes[-1]["x"], kf_nodes[-1]["y"]))
    return curve_pts, kf_nodes


def build_shape_vertices(shape_kind, cx, cy, width, height):
    """Generates local vertices for dummy shapes."""
    hw = width / 2.0
    hh = height / 2.0

    if shape_kind in ("rect", "block_text"):
        return [
            (cx - hw, cy - hh),
            (cx + hw, cy - hh),
            (cx + hw, cy + hh),
            (cx - hw, cy + hh),
        ]
    if shape_kind == "square":
        side = min(hw, hh)
        return [
            (cx - side, cy - side),
            (cx + side, cy - side),
            (cx + side, cy + side),
            (cx - side, cy + side),
        ]
    if shape_kind == "triangle":
        return [
            (cx, cy - hh),
            (cx + hw, cy + hh),
            (cx - hw, cy + hh),
        ]
    if shape_kind == "diamond":
        return [
            (cx, cy - hh),
            (cx + hw, cy),
            (cx, cy + hh),
            (cx - hw, cy),
        ]
    if shape_kind == "star":
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