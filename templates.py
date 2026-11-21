#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Default preset templates for Filmcraft and generic JSON schemas."""

FILMCRAFT_TEXT_TEMPLATE = {
    "format": "filmcraft.effect-presets",
    "version": 1,
    "presets": [
        {
            "name": "Quick Caption - Micro Pop",
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
                        "text": {"value": {"Text": "Hello"}},
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
            "name": "Smooth Motion Zoom",
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
    "name": "New Preset",
    "version": 1,
    "enabled": True,
    "parameters": {
        "intensity": 1.0,
        "mode": "standard",
        "label": "Example",
    },
}