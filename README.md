# Preset Studio (Rust / egui)

Port em Rust do app Python/Tkinter. Requer Rust 1.81+.

    cargo run --release

Módulos: engine (matemática), templates (JSON embutidos em src/templates/),
theme, i18n (EN/PT, gerado do i18n.py), viewer (gizmos/timeline/render),
inspector (parâmetros + editor de keyframes), app (perfis, biblioteca, JSON tree/raw).

Config compartilhada com a versão Python: ~/.config/universal-preset-manager/
No Linux, os diálogos de arquivo usam xdg-desktop-portal (via rfd).
