# Preset Studio
[🇧🇷 Português](README.pt-BR.md)
**A desktop JSON preset manager with a Filmcraft-focused animation viewer.**

Preset Studio is a Python/Tkinter application for organizing, inspecting, editing, and previewing JSON presets. It includes dedicated support for the `filmcraft.effect-presets` format, while also providing generic JSON editing tools for other applications.

> **Status:** Early release / beta. Back up important preset files before editing them.

## Features

- **Preset library and profiles**
  - Organize presets in application-specific profiles.
  - Choose a presets folder for each profile.
  - Create, duplicate, import, rename, and delete preset files.
  - Save a profile-specific template for creating new presets.
- **Filmcraft support**
  - Built-in templates for `graphic_text` and `motion` presets.
  - Inspect and edit preset variations, effects, and parameters.
  - Edit keyframed values and preview animated parameters.
  - Validate important parts of the Filmcraft preset structure.
- **Animation viewer**
  - Real-time preview of supported Filmcraft text and motion effects.
  - Timeline with separate tracks for animated parameters.
  - Transform gizmos for moving, scaling, and rotating objects.
  - Dedicated anchor and motion-path editing tools.
  - Auto-Key, keyframe stamping, and transform reset actions.
  - Viewport zoom, pan, snapping guides, and safe-area guides.
  - Sample text and geometric objects for previewing motion.
- **JSON editing**
  - Structured JSON tree editor.
  - Raw JSON editor with formatting and apply actions.
  - Generic JSON preset support for applications with different schemas.
- **Safety and workflow**
  - Creates a `.json.bak` backup when saving over an existing preset.
  - Keyboard shortcuts for common editing and playback actions.
- **Localization**
  - English and Brazilian Portuguese interface translations.

## Requirements

- Linux, Windows, or macOS with Python 3.10+ recommended.
- Tkinter / Tcl-Tk.
- No third-party Python packages are required to run the source version.

On Debian/Ubuntu, install Tkinter with:

```bash
sudo apt update
sudo apt install python3 python3-tk python3-venv
```

## Run from source

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/preset-studio.git
cd preset-studio
```

Run the application:

```bash
python3 main.py
```

If your distribution separates Tkinter from the base Python package, install its Tkinter package first.

## Build a Linux executable

The repository includes `build_linux.sh`. It uses PyInstaller to create an application folder containing the executable and its bundled runtime.

```bash
chmod +x build_linux.sh
./build_linux.sh
```

The output is created under:

```text
dist/PresetStudio/
```

Run it with:

```bash
./dist/PresetStudio/PresetStudio
```

The build script installs PyInstaller into the active Python environment if it is not already available. The build machine must have Tkinter development/runtime support installed.

To build manually:

```bash
python3 -m pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --onedir \
  --name PresetStudio \
  main.py
```

Build on the target operating system. A Linux build is not a Windows or macOS executable, and PyInstaller does not guarantee compatibility with every Linux distribution.

## User data

Preset Studio stores its profile and language settings under:

```text
~/.config/universal-preset-manager/
```

Your preset files remain in the folders configured in the application profiles. The application does not automatically move your preset library into its configuration directory.

## Project structure

```text
.
├── main.py       # Application window, profiles, library, inspector, JSON editors
├── viewer.py     # Animation viewer, timeline, transform and path tools
├── engine.py     # Keyframe evaluation, interpolation, geometry and transforms
├── i18n.py       # English and Portuguese translations
├── templates.py  # Filmcraft and generic JSON templates
├── theme.py      # Tkinter theme and reusable UI components
├── README.md
├── README.pt-BR.md
└── build_linux.sh
```

## Supported format notes

The specialized animation viewer targets Filmcraft presets using the `filmcraft.effect-presets` structure, especially `graphic_text` and `motion` effects. Generic JSON files can be edited through the tree and raw-code views, but their application-specific behavior is not interpreted by the Filmcraft viewer.

Always test exported or modified presets in the target application. Preset Studio is an editor and preview tool, not an official Filmcraft product.

## Keyboard shortcuts

The application displays its current shortcut hints in the interface. Common actions include:

- `Ctrl + S` — Save
- `Ctrl + N` — New preset
- `Space` — Play / pause
- `Left` / `Right` — Step through frames

## Contributing

Bug reports, reproducible examples, and pull requests are welcome. When reporting an issue, include:

1. Operating system and Python version.
2. Steps to reproduce the issue.
3. A sanitized sample JSON preset, if possible.
4. Any traceback printed in the terminal.

## License

No license has been declared in this repository yet. Until a license is added, all rights remain with the copyright holder and reuse should not be assumed to be permitted.
