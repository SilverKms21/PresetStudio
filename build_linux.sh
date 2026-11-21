#!/usr/bin/env bash
set -euo pipefail

APP_NAME="PresetStudio"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_ENV="$ROOT_DIR/.build-venv"

cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 was not found." >&2
    exit 1
fi

python3 -m venv "$BUILD_ENV"
"$BUILD_ENV/bin/python" -m pip install --upgrade pip pyinstaller

if ! "$BUILD_ENV/bin/python" -c "import tkinter" >/dev/null 2>&1; then
    echo "Error: Tkinter is missing. Install your distribution's python3-tk package." >&2
    exit 1
fi

"$BUILD_ENV/bin/python" -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --onedir \
    --name "$APP_NAME" \
    main.py

echo
echo "Build complete: $ROOT_DIR/dist/$APP_NAME/$APP_NAME"
echo "Run with: ./dist/$APP_NAME/$APP_NAME"
