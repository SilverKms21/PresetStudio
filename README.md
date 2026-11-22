# Preset Studio

[English](README.md) · [Português (BR)](README.pt-BR.md)

A desktop editor and manager for JSON presets, written in Rust with [egui](https://github.com/emilk/egui).
It started as a Python/Tkinter tool for **Filmcraft effect presets** and grew into a small
workbench for any JSON file: a visual compositing viewer with keyframes, a tree editor,
a raw editor and viewers for several well-known formats.

> Dark UI inspired by DaVinci Resolve / macOS. English by default, switch to Portuguese instantly (EN/PT button).

## Features

### Studio (Filmcraft presets)
- **Compositing viewer** with a transform gizmo: move, corner/edge scale, rotate, anchor point.
- **Motion-path overlay**: drag position keyframes directly on the canvas.
- **Magnetic snap** to center and thirds, safe-area guides, zoom, pan and background modes (dark, checker, chroma green).
- **Live HUD** with position, scale, rotation and anchor.
- **Auto-key** and "add keyframes" on all transform properties.
- **Interactive timeline**: scrub, drag keyframes (frame-snapped, hold `Shift` for free time), **select and delete keyframes** (`Delete` / `Backspace`, right-click menu, or the toolbar button).
- **Inspector** grouped by Transform / Text / Fill & Outline / Background & Shadow, with live animated values and a per-parameter keyframe editor (time, interpolation, values).
- Preview of `graphic_text` (fill, stroke, shadow, background, caps, alignment) and `motion` on dummy shapes (rect, square, circle, triangle, diamond, star, text).
- Base resolution rescaling that also scales position/anchor keyframes.

### Format Viewer
Detected automatically when you open a file:

| Format | What you get |
|---|---|
| **OBS Studio** (scene collection or single transition) | Animated preview of Fade, Cut, Slide, Swipe, Fade to Color, Luma Wipe and Stinger; editor for settings, default duration, add/remove transitions |
| **Lottie** | Composition info and a layer timeline with playhead |
| **GeoJSON** | Drawing of points, lines and polygons, bounding box, geometry counts |
| **Transcripts** (Whisper-style `segments`) | Segment list with timestamps, timeline bar, word count |
| **Any other JSON** | Structure statistics, largest arrays, hex color swatches, numeric-array plots |

### Library & editing
- Multiple **profiles** (apps), each with its own folder, schema type and template.
- File library with search, new / duplicate / import / rename / delete.
- **JSON tree** editor (edit values, add/remove nodes) and **raw JSON** editor with format and validate.
- Automatic `.bak` backup on save.

## Install & run

Requires **Rust 1.81+**.

```bash
git clone https://github.com/SilverKms21/PresetStudio.git
cd preset-studio
cargo run --release
```

Run the tests:

```bash
cargo test
```

On Linux, file dialogs use `xdg-desktop-portal` (through [`rfd`](https://github.com/PolyMeilex/rfd)), so make sure a portal backend is installed (it is on most desktops).

## Shortcuts

| Action | Shortcut |
|---|---|
| Save / New preset | `Ctrl+S` / `Ctrl+N` |
| Play / pause | `Space` |
| Step frame (×10 with `Shift`) | `←` `→` |
| Jump to previous / next keyframe | `Ctrl+←` `Ctrl+→` |
| Go to start / end | `Home` / `End` |
| Delete selected keyframe | `Delete` / `Backspace` |
| Zoom / pan viewer | Mouse wheel / middle button drag |
| Disable snap while dragging | Hold `Ctrl` |
| Snap rotation to 15° / non-uniform corner scale | Hold `Shift` |

## Configuration

Settings and profiles are stored in `~/.config/universal-preset-manager/`
(`profiles.json`, `settings.json`) and are compatible with the original Python version.

## Project layout

```
src/
├── main.rs        entry point
├── app.rs         profiles, library, pages, dialogs
├── viewer.rs      compositing viewer, gizmos, timeline, rendering
├── inspector.rs   parameter inspector and keyframe editor
├── formats.rs     OBS / Lottie / GeoJSON / transcript / generic viewers
├── engine.rs      RGBA blending, Bézier easing, 2D transforms, hit-testing
├── jsonx.rs       JSON helpers
├── templates.rs   embedded default presets (src/templates/*.json)
├── i18n.rs        English / Portuguese strings
└── theme.rs       palette and UI helpers
```

## Known limitations

- Fonts: egui only ships its default fonts, so the font family set in a preset is ignored (bold is simulated; italic, underline and strikethrough work).
- OBS previews approximate the built-in transitions; stinger videos and luma images are not loaded.
- Lottie files are inspected, not rendered.
- Some symbols (⏮ ◆ ◇ …) depend on glyphs available in the embedded egui font.

## License

distributed under the MIT License
