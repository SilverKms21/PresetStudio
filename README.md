# Preset Studio
Read in [Portuguese][README.pt-BR.md]
**Universal JSON Preset Manager & Real-Time NLE Keyframe Viewer**

Preset Studio is a lightweight, zero-dependency desktop application built with Python and Tkinter, featuring a dark interface inspired by **DaVinci Resolve Studio** and **macOS**. It provides native visual editing and real-time keyframe animation previewing for **Filmcraft** (`filmcraft.effect-presets`), alongside a universal JSON tree and raw code editor compatible with any JSON-based software.

---

## Features

* **Real-Time NLE Viewer & Transport Deck**:
  * Evaluates `graphic_text` and `motion` effects with **Cubic Bézier** (`AutoBezier`, `ContinuousBezier`), `Linear`, and `Hold` keyframe interpolation.
  * Interactive **on-screen gizmos** to drag **Position**, **Scale**, and **Rotation** directly on the canvas—automatically creating or updating keyframes at the playhead.
  * Interactive timeline ruler with diamond keyframe markers (`◆`), magnetic keyframe snapping (`Shift` to bypass), playback speed multipliers (`1x` to `100x`), and loop toggle.
  * Viewport options including Dark Monitor, Transparency Grid, Chroma Green, Center Guides, and Action/Title Safe zones (`95%` / `90%`).
  * Built-in test objects (Sample Text, Rectangle, Square, Circle, Triangle, Diamond, Star, Block + Text) to preview motion presets.
* **Dynamic NLE Inspector**:
  * Automatically builds typed controls (`Bool`, `Text`, `Float`, `Choice`, `Color` picker, `Vec2` X/Y) with live parameter readout during playback.
  * Dedicated **Keyframe Editor** modal for fine-tuning timestamps, values, and interpolation curves.
  * **Proportional Resolution Scaling**: Changing `source_size` automatically recalculates all `position` and `anchor` coordinates across every keyframe.
* **Three Synchronized Workspaces**:
  1. **🎛 Inspector & Viewer**: Visual NLE editing and live preview.
  2. **🌲 JSON Tree**: Hierarchical editor for any arbitrary JSON schema (add, edit, or delete keys and array items).
  3. **</> Raw JSON**: Direct source editing with syntax validation and instant sync back to the Viewer.
* **Multi-App Profiles & Safe File Management**:
  * Organize presets by application profile (Filmcraft, OBS, EasyEffects, Godot, etc.) stored in `~/.config/universal-preset-manager/profiles.json`.
  * Built-in search filter, template creation, duplication, schema validation, and automatic `.json.bak` backups on save.

---

## Requirements & Installation

Preset Studio uses **only the Python standard library**—no `pip install` required.

* **Python 3.8+**
* **Tkinter** (included by default on Windows/macOS; on Debian/Ubuntu/Linux Mint, install via `sudo apt install python3-tk`)

### Running from Source

```bash
git clone [https://github.com/your-username/preset-studio.git](https://github.com/your-username/preset-studio.git)
cd preset-studio
python3 preset_manager.py
```

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + S` | Save current preset (creates a `.json.bak` backup) |
| `Ctrl + N` | Create a new preset from template |
| `Space` | Play / Pause preview |
| `←` / `→` | Step backward / forward 1 frame (30 FPS) |
| `Shift + ←` / `→` | Step backward / forward 10 frames |
| `Ctrl + ←` / `→` | Jump to previous / next keyframe |
| `Home` / `End` | Jump to start / end of timeline |
| `Shift + Drag` (Timeline) | Scrub freely without keyframe snapping |

---

## License

This project is open-source and available under the [MIT License](LICENSE).
