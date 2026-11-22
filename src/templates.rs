//! Default preset templates for Filmcraft and generic JSON schemas.

use serde_json::Value;

fn parse(src: &str) -> Value {
    serde_json::from_str(src).expect("embedded template is valid JSON")
}

pub fn filmcraft_text_template() -> Value {
    parse(include_str!("templates/filmcraft_text.json"))
}

pub fn filmcraft_motion_template() -> Value {
    parse(include_str!("templates/filmcraft_motion.json"))
}

pub fn generic_default_template() -> Value {
    parse(include_str!("templates/generic_default.json"))
}
