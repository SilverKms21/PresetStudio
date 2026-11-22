//! Preset Studio — Universal JSON Preset Manager & Visual Compositing Editor.
//! Rust / egui port. Default language: English, instant switch to Portuguese.

mod app;
mod engine;
mod formats;
mod i18n;
mod inspector;
mod jsonx;
mod templates;
mod theme;
mod viewer;

fn main() -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        viewport: eframe::egui::ViewportBuilder::default()
            .with_inner_size([1460.0, 900.0])
            .with_min_inner_size([1140.0, 720.0])
            .with_title("Preset Studio"),
        ..Default::default()
    };
    eframe::run_native("Preset Studio", options, Box::new(|cc| Ok(Box::new(app::App::new(cc)))))
}
