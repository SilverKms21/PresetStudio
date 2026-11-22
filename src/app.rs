//! Application shell: profiles, file library, pages (Studio / JSON tree / raw JSON), dialogs.

use std::fs;
use std::path::{Path, PathBuf};

use eframe::egui::{self, Align2, Color32, FontId, Key, RichText, Stroke};
use serde_json::{json, Map, Value};

use crate::i18n::{tr, trf, Lang};
use crate::formats::{self, FormatState};
use crate::inspector::{self, InspAction, InspCtx, InspState, KfEditor};
use crate::templates;
use crate::theme::{self, pal};
use crate::viewer::Viewer;

// ------------------------------------------------------------------ small types

#[derive(Clone, PartialEq, Eq, Debug)]
enum Step {
    Key(String),
    Idx(usize),
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Page {
    Studio,
    Tree,
    Raw,
    Format,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Hint {
    None,
    Int,
    Float,
}

enum PromptKind {
    NewAppName,
    Duplicate,
    Rename,
    TreeEdit(Vec<Step>, Hint),
    TreeNewKey(Vec<Step>),
    TreeNewValue(Vec<Step>, String),
    TreeNewItem(Vec<Step>),
}

enum ConfirmKind {
    Schema { name: String, folder: String },
    Overwrite { src: PathBuf },
    Delete,
}

enum Dialog {
    Message { title: String, msg: String },
    Prompt { title: String, label: String, value: String, kind: PromptKind, first: bool },
    Confirm { title: String, msg: String, kind: ConfirmKind },
    NewPreset { name: String, kind_idx: usize, is_fc: bool },
}

enum Outcome {
    Keep,
    Close,
    Ok(String),
    Yes(bool),
    Create(String, usize),
}

// ------------------------------------------------------------------ config helpers

fn home_dir() -> PathBuf {
    std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
}

fn config_dir() -> PathBuf {
    home_dir().join(".config").join("universal-preset-manager")
}

fn profiles_file() -> PathBuf {
    config_dir().join("profiles.json")
}

fn settings_file() -> PathBuf {
    config_dir().join("settings.json")
}

fn with_json_ext(name: &str) -> String {
    if name.ends_with(".json") { name.to_string() } else { format!("{}.json", name) }
}

fn pretty(v: &Value) -> String {
    serde_json::to_string_pretty(v).unwrap_or_default()
}

fn file_name(p: &Path) -> String {
    p.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default()
}

fn file_stem(p: &Path) -> String {
    p.file_stem().map(|n| n.to_string_lossy().to_string()).unwrap_or_default()
}

fn smart_parse_value(text: &str, hint: Hint) -> Value {
    let s = text.trim();
    match s.to_lowercase().as_str() {
        "true" => return Value::Bool(true),
        "false" => return Value::Bool(false),
        "null" => return Value::Null,
        _ => {}
    }
    if let Ok(v) = serde_json::from_str::<Value>(s) {
        return v;
    }
    match hint {
        Hint::Int => {
            if let Ok(i) = s.parse::<i64>() {
                return json!(i);
            }
        }
        Hint::Float => {
            if let Ok(f) = s.parse::<f64>() {
                return json!(f);
            }
        }
        Hint::None => {}
    }
    Value::String(text.to_string())
}

fn get_by_path<'a>(root: &'a Value, path: &[Step]) -> Option<&'a Value> {
    let mut cur = root;
    for s in path {
        cur = match s {
            Step::Key(k) => cur.get(k.as_str())?,
            Step::Idx(i) => cur.get(*i)?,
        };
    }
    Some(cur)
}

fn get_by_path_mut<'a>(root: &'a mut Value, path: &[Step]) -> Option<&'a mut Value> {
    let mut cur = root;
    for s in path {
        cur = match s {
            Step::Key(k) => cur.get_mut(k.as_str())?,
            Step::Idx(i) => cur.get_mut(*i)?,
        };
    }
    Some(cur)
}

fn preset_mut(data: &mut Option<Value>, idx: usize) -> Option<&mut Value> {
    let d = data.as_mut()?;
    if !inspector::is_filmcraft_data(&Some(d.clone())) {
        return None;
    }
    let presets = d.get_mut("presets")?.as_array_mut()?;
    if presets.is_empty() {
        return None;
    }
    let i = idx.min(presets.len() - 1);
    presets.get_mut(i)
}

fn strip_json_err(e: &serde_json::Error) -> String {
    let s = e.to_string();
    match s.find(" at line ") {
        Some(i) => s[..i].to_string(),
        None => s,
    }
}

// ------------------------------------------------------------------ the app

pub struct App {
    lang: Lang,
    profiles: Map<String, Value>,
    current_profile: String,
    current_file: Option<PathBuf>,
    data: Option<Value>,
    sel_preset: usize,
    sel_effect: usize,
    modified: bool,
    page: Page,

    viewer: Viewer,
    insp_state: InspState,
    fmt_state: FormatState,
    generation: u64,
    kf_editor: Option<KfEditor>,

    search: String,
    files: Vec<PathBuf>,
    tree_sel: Option<Vec<Step>>,
    raw_text: String,

    status: String,
    dialog: Option<Dialog>,
    pending: Vec<InspAction>,
}

impl App {
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        theme::setup_theme(&cc.egui_ctx);
        let lang = Self::load_language_setting();
        let profiles = Self::load_profiles();
        let current_profile = profiles.keys().next().cloned().unwrap_or_default();
        let mut app = App {
            lang,
            profiles,
            current_profile,
            current_file: None,
            data: None,
            sel_preset: 0,
            sel_effect: 0,
            modified: false,
            page: Page::Studio,
            viewer: Viewer::new(),
            insp_state: InspState::default(),
            fmt_state: FormatState::default(),
            generation: 0,
            kf_editor: None,
            search: String::new(),
            files: vec![],
            tree_sel: None,
            raw_text: String::new(),
            status: String::new(),
            dialog: None,
            pending: vec![],
        };
        app.status = app.t("status_ready");
        app.refresh_file_list();
        app
    }

    fn t(&self, key: &str) -> String {
        tr(self.lang, key)
    }

    fn tf(&self, key: &str, args: &[(&str, String)]) -> String {
        trf(self.lang, key, args)
    }

    // ---------------------------------------------------------------- settings & profiles

    fn load_language_setting() -> Lang {
        let _ = fs::create_dir_all(config_dir());
        if let Ok(text) = fs::read_to_string(settings_file()) {
            if let Ok(v) = serde_json::from_str::<Value>(&text) {
                if let Some(l) = v.get("language").and_then(|l| l.as_str()).and_then(Lang::from_code) {
                    return l;
                }
            }
        }
        Lang::En
    }

    fn save_language_setting(lang: Lang) {
        let _ = fs::create_dir_all(config_dir());
        let _ = fs::write(settings_file(), pretty(&json!({"language": lang.code()})));
    }

    fn set_language(&mut self, lang: Lang) {
        if lang == self.lang {
            return;
        }
        self.lang = lang;
        Self::save_language_setting(lang);
        if self.current_file.is_none() && !self.modified {
            self.status = self.t("status_ready");
        }
    }

    fn load_profiles() -> Map<String, Value> {
        let _ = fs::create_dir_all(config_dir());
        if let Ok(text) = fs::read_to_string(profiles_file()) {
            if let Ok(Value::Object(m)) = serde_json::from_str::<Value>(&text) {
                if !m.is_empty() {
                    return m;
                }
            }
        }
        let home = home_dir();
        let mut presents_dir = home.join("Documentos").join("Presents");
        if !presents_dir.exists() {
            presents_dir = home.join("Documents").join("Presets");
        }
        let mut m = Map::new();
        m.insert(
            "Filmcraft (Effect Presets)".into(),
            json!({
                "folder": presents_dir.to_string_lossy(),
                "schema_type": "filmcraft",
                "template": templates::filmcraft_text_template(),
            }),
        );
        m.insert(
            "Generic (Any JSON App)".into(),
            json!({
                "folder": home.join("Documents").join("Presets_JSON").to_string_lossy(),
                "schema_type": "generic",
                "template": templates::generic_default_template(),
            }),
        );
        Self::write_profiles(&m);
        m
    }

    fn write_profiles(m: &Map<String, Value>) {
        let _ = fs::create_dir_all(config_dir());
        let _ = fs::write(profiles_file(), pretty(&Value::Object(m.clone())));
    }

    fn save_profiles(&self) {
        Self::write_profiles(&self.profiles);
    }

    fn profile_str(&self, key: &str) -> Option<String> {
        self.profiles.get(&self.current_profile)?.get(key)?.as_str().map(|s| s.to_string())
    }

    fn profile_folder(&self) -> PathBuf {
        PathBuf::from(self.profile_str("folder").unwrap_or_default())
    }

    fn profile_is_filmcraft(&self) -> bool {
        self.profile_str("schema_type").as_deref() == Some("filmcraft")
    }

    fn profile_template(&self, fallback: Value) -> Value {
        self.profiles
            .get(&self.current_profile)
            .and_then(|p| p.get("template"))
            .cloned()
            .unwrap_or(fallback)
    }

    // ---------------------------------------------------------------- status / flags

    fn set_status(&mut self, msg: String) {
        self.status = msg;
    }

    fn mark_modified(&mut self) {
        self.modified = true;
        if let Some(f) = &self.current_file {
            self.status = self.tf("status_editing", &[("name", file_name(f))]);
        }
    }

    fn info(&mut self, title: String, msg: String) {
        self.dialog = Some(Dialog::Message { title, msg });
    }

    // ---------------------------------------------------------------- views sync

    fn sync_preview(&mut self, reset_time: bool) {
        let idx = self.sel_preset;
        let preset = preset_mut(&mut self.data, idx).map(|p| &*p);
        self.viewer.set_preset(preset, reset_time);
    }

    fn render_all_views(&mut self, reset_preview: bool) {
        self.generation += 1;
        self.sync_preview(reset_preview);
        self.refresh_raw();
    }

    fn refresh_raw(&mut self) {
        self.raw_text = self.data.as_ref().map(pretty).unwrap_or_default();
    }

    // ---------------------------------------------------------------- file & profile operations

    fn refresh_file_list(&mut self) {
        let folder = self.profile_folder();
        let _ = fs::create_dir_all(&folder);
        let mut files: Vec<PathBuf> = fs::read_dir(&folder)
            .map(|rd| {
                rd.filter_map(|e| e.ok())
                    .map(|e| e.path())
                    .filter(|p| p.is_file() && p.extension().map(|x| x == "json").unwrap_or(false))
                    .collect()
            })
            .unwrap_or_default();
        files.sort_by_key(|p| file_name(p).to_lowercase());
        self.files = files;
    }

    fn on_profile_changed(&mut self) {
        self.current_file = None;
        self.data = None;
        self.modified = false;
        self.tree_sel = None;
        self.refresh_file_list();
        self.render_all_views(true);
    }

    fn add_new_profile(&mut self) {
        self.dialog = Some(Dialog::Prompt {
            title: self.t("dlg_new_app_title"),
            label: self.t("dlg_new_app_prompt"),
            value: String::new(),
            kind: PromptKind::NewAppName,
            first: true,
        });
    }

    fn change_profile_folder(&mut self) {
        let start = self.profile_str("folder").unwrap_or_else(|| home_dir().to_string_lossy().to_string());
        if let Some(new_folder) = rfd::FileDialog::new().set_title(self.t("dlg_choose_folder")).set_directory(start).pick_folder() {
            let folder = new_folder.to_string_lossy().to_string();
            if let Some(p) = self.profiles.get_mut(&self.current_profile).and_then(|p| p.as_object_mut()) {
                p.insert("folder".into(), json!(folder));
            }
            self.save_profiles();
            self.refresh_file_list();
            self.set_status(self.tf("status_folder_updated", &[("folder", folder)]));
        }
    }

    fn save_current_as_template(&mut self) {
        let Some(data) = self.data.clone() else {
            self.info(self.t("dlg_notice"), self.t("dlg_open_before_tpl"));
            return;
        };
        if let Some(p) = self.profiles.get_mut(&self.current_profile).and_then(|p| p.as_object_mut()) {
            p.insert("template".into(), data);
        }
        self.save_profiles();
        self.set_status(self.tf("status_tpl_updated", &[("profile", self.current_profile.clone())]));
    }

    fn load_file(&mut self, path: PathBuf) {
        let result = fs::read_to_string(&path).map_err(|e| e.to_string()).and_then(|t| serde_json::from_str::<Value>(&t).map_err(|e| e.to_string()));
        match result {
            Ok(data) => {
                self.current_file = Some(path.clone());
                self.data = Some(data);
                self.sel_preset = 0;
                self.sel_effect = 0;
                self.modified = false;
                self.tree_sel = None;
                self.kf_editor = None;
                self.fmt_state.reset();
                self.render_all_views(true);
                let is_fc = inspector::is_filmcraft_data(&self.data);
                let kind = formats::detect(self.data.as_ref().unwrap());
                if is_fc {
                    if self.page == Page::Format {
                        self.switch_page(Page::Studio);
                    }
                } else if kind != formats::Kind::Generic {
                    self.switch_page(Page::Format);
                }
                self.set_status(self.tf("status_loaded", &[("name", file_name(&path))]));
            }
            Err(err) => {
                let msg = self.tf("dlg_err_open_msg", &[("name", file_name(&path)), ("err", err)]);
                self.info(self.t("dlg_err_open_title"), msg);
            }
        }
    }

    fn create_new_preset(&mut self) {
        self.dialog = Some(Dialog::NewPreset { name: "New_Preset".into(), kind_idx: 0, is_fc: self.profile_is_filmcraft() });
    }

    fn confirm_new_preset(&mut self, name: String, kind_idx: usize, is_fc: bool) -> bool {
        let clean = name.trim().to_string();
        if clean.is_empty() {
            return false;
        }
        let filename = with_json_ext(&clean);
        let folder = self.profile_folder();
        let _ = fs::create_dir_all(&folder);
        let target = folder.join(&filename);
        if target.exists() {
            let msg = self.tf("dlg_file_exists_msg", &[("name", filename)]);
            self.info(self.t("dlg_file_exists_title"), msg);
            return false;
        }
        let mut new_data = if is_fc {
            match kind_idx {
                0 => templates::filmcraft_motion_template(),
                1 => templates::filmcraft_text_template(),
                _ => self.profile_template(templates::filmcraft_text_template()),
            }
        } else if kind_idx == 1 {
            formats::obs_collection_template()
        } else if kind_idx == 2 {
            formats::obs_stinger_template()
        } else {
            self.profile_template(templates::generic_default_template())
        };
        let bare = clean.replace(".json", "");
        if new_data.is_object() {
            let has_presets = new_data.get("presets").and_then(|p| p.as_array()).map(|a| !a.is_empty()).unwrap_or(false);
            if has_presets {
                new_data["presets"][0]["name"] = json!(bare);
            } else if new_data.get("name").is_some() && new_data.get("transitions").is_none() {
                new_data["name"] = json!(bare);
            }
        }
        if let Err(e) = fs::write(&target, pretty(&new_data)) {
            self.info(self.t("dlg_save_err_title"), self.tf("dlg_save_err_msg", &[("err", e.to_string())]));
            return false;
        }
        self.refresh_file_list();
        self.load_file(target);
        self.set_status(self.tf("status_created", &[("name", filename)]));
        true
    }

    fn duplicate_preset(&mut self) {
        let Some(path) = self.current_file.clone().filter(|_| self.data.is_some()) else {
            self.info(self.t("dlg_notice"), self.t("dlg_select_to_dup"));
            return;
        };
        self.dialog = Some(Dialog::Prompt {
            title: self.t("dlg_dup_title"),
            label: self.t("dlg_dup_prompt"),
            value: format!("{}_copy", file_stem(&path)),
            kind: PromptKind::Duplicate,
            first: true,
        });
    }

    fn import_preset(&mut self) {
        let Some(src) = rfd::FileDialog::new()
            .set_title(self.t("dlg_import_title"))
            .add_filter("JSON Files", &["json"])
            .add_filter("All", &["*"])
            .pick_file()
        else {
            return;
        };
        let check = fs::read_to_string(&src).map_err(|e| e.to_string()).and_then(|t| serde_json::from_str::<Value>(&t).map(|_| ()).map_err(|e| e.to_string()));
        if let Err(e) = check {
            self.info(self.t("dlg_invalid_json_title"), self.tf("dlg_invalid_json_msg", &[("err", e)]));
            return;
        }
        let dest = self.profile_folder().join(file_name(&src));
        if dest.exists() {
            self.dialog = Some(Dialog::Confirm {
                title: self.t("dlg_overwrite_title"),
                msg: self.tf("dlg_overwrite_msg", &[("name", file_name(&src))]),
                kind: ConfirmKind::Overwrite { src },
            });
        } else {
            self.finish_import(src);
        }
    }

    fn finish_import(&mut self, src: PathBuf) {
        let dest = self.profile_folder().join(file_name(&src));
        let _ = fs::create_dir_all(self.profile_folder());
        if let Err(e) = fs::copy(&src, &dest) {
            self.info(self.t("dlg_error"), e.to_string());
            return;
        }
        self.refresh_file_list();
        self.load_file(dest);
        self.set_status(self.tf("status_imported", &[("name", file_name(&src))]));
    }

    fn rename_file(&mut self) {
        let Some(path) = self.current_file.clone() else { return };
        self.dialog = Some(Dialog::Prompt {
            title: self.t("dlg_rename_title"),
            label: self.t("dlg_rename_prompt"),
            value: file_stem(&path),
            kind: PromptKind::Rename,
            first: true,
        });
    }

    fn delete_file(&mut self) {
        let Some(path) = self.current_file.clone() else { return };
        self.dialog = Some(Dialog::Confirm {
            title: self.t("dlg_delete_title"),
            msg: self.tf("dlg_delete_msg", &[("name", file_name(&path))]),
            kind: ConfirmKind::Delete,
        });
    }

    fn save_current_file(&mut self) {
        if self.current_file.is_none() || self.data.is_none() {
            self.info(self.t("dlg_notice"), self.t("dlg_no_file_save"));
            return;
        }
        if self.page == Page::Raw && !self.apply_raw_json(true) {
            return;
        }
        let path = self.current_file.clone().unwrap();
        let result = (|| -> std::io::Result<()> {
            if path.exists() {
                fs::copy(&path, PathBuf::from(format!("{}.bak", path.display())))?;
            }
            fs::write(&path, pretty(self.data.as_ref().unwrap()))
        })();
        match result {
            Ok(()) => {
                self.modified = false;
                self.set_status(self.tf("status_saved", &[("name", file_name(&path))]));
            }
            Err(e) => self.info(self.t("dlg_save_err_title"), self.tf("dlg_save_err_msg", &[("err", e.to_string())])),
        }
    }

    fn validate_current_json(&mut self) {
        if self.data.is_none() {
            self.info(self.t("dlg_val_title"), self.t("dlg_val_no_file"));
            return;
        }
        if self.page == Page::Raw && !self.apply_raw_json(true) {
            return;
        }
        let data = self.data.as_ref().unwrap();
        let mut issues: Vec<String> = vec![];
        if data.is_object()
            && (self.profile_is_filmcraft() || data.get("format").and_then(|f| f.as_str()) == Some("filmcraft.effect-presets"))
        {
            if data.get("format").and_then(|f| f.as_str()) != Some("filmcraft.effect-presets") {
                issues.push("- Missing or invalid 'format' field (expected 'filmcraft.effect-presets').".into());
            }
            if data.get("version").is_none() {
                issues.push("- Missing 'version' field (recommended: 1).".into());
            }
            match data.get("presets").and_then(|p| p.as_array()) {
                Some(presets) if !presets.is_empty() => {
                    for (i, p) in presets.iter().enumerate() {
                        if p.get("name").is_none() {
                            issues.push(format!("- Preset [{}] missing 'name' field.", i));
                        }
                        if !p.get("effects").map(|e| e.is_array()).unwrap_or(false) {
                            issues.push(format!("- Preset [{}] missing 'effects' array.", i));
                        }
                    }
                }
                _ => issues.push("- 'presets' array is missing or empty.".into()),
            }
        }
        if issues.is_empty() {
            self.info(self.t("dlg_val_ok_title"), self.t("dlg_val_ok_msg"));
        } else {
            let msg = self.tf("dlg_val_warn_msg", &[("issues", issues.join("\n"))]);
            self.info(self.t("dlg_val_warn_title"), msg);
        }
    }

    // ---------------------------------------------------------------- tree / raw operations

    fn tree_edit_selected(&mut self) {
        let Some(path) = self.tree_sel.clone().filter(|p| !p.is_empty()) else { return };
        let Some(cur) = self.data.as_ref().and_then(|d| get_by_path(d, &path)).cloned() else { return };
        if cur.is_object() || cur.is_array() {
            self.info(self.t("dlg_notice"), self.t("dlg_select_leaf"));
            return;
        }
        let hint = match &cur {
            Value::Number(n) if n.is_f64() => Hint::Float,
            Value::Number(_) => Hint::Int,
            _ => Hint::None,
        };
        let initial = match &cur {
            Value::String(s) => s.clone(),
            other => other.to_string(),
        };
        let key = match path.last() {
            Some(Step::Key(k)) => k.clone(),
            Some(Step::Idx(i)) => i.to_string(),
            None => String::new(),
        };
        self.dialog = Some(Dialog::Prompt {
            title: self.t("dlg_edit_val_title"),
            label: self.tf("dlg_edit_val_prompt", &[("key", key)]),
            value: initial,
            kind: PromptKind::TreeEdit(path, hint),
            first: true,
        });
    }

    fn tree_add_node(&mut self) {
        let Some(data) = self.data.as_ref() else { return };
        let mut path = self.tree_sel.clone().unwrap_or_default();
        let is_container = get_by_path(data, &path).map(|v| v.is_object() || v.is_array()).unwrap_or(false);
        if !is_container {
            path.pop();
        }
        match get_by_path(data, &path) {
            Some(Value::Object(_)) => {
                self.dialog = Some(Dialog::Prompt {
                    title: self.t("dlg_new_key_title"),
                    label: self.t("dlg_new_key_prompt"),
                    value: String::new(),
                    kind: PromptKind::TreeNewKey(path),
                    first: true,
                });
            }
            Some(Value::Array(_)) => {
                self.dialog = Some(Dialog::Prompt {
                    title: self.t("dlg_new_item_title"),
                    label: self.t("dlg_new_item_prompt"),
                    value: String::new(),
                    kind: PromptKind::TreeNewItem(path),
                    first: true,
                });
            }
            _ => {}
        }
    }

    fn tree_delete_node(&mut self) {
        let Some(path) = self.tree_sel.clone() else { return };
        if path.is_empty() {
            self.info(self.t("dlg_notice"), self.t("dlg_cannot_del_root"));
            return;
        }
        let (last, parent_path) = (path.last().unwrap().clone(), &path[..path.len() - 1]);
        if let Some(parent) = self.data.as_mut().and_then(|d| get_by_path_mut(d, parent_path)) {
            match (parent, last) {
                (Value::Object(m), Step::Key(k)) => {
                    m.shift_remove(&k);
                }
                (Value::Array(a), Step::Idx(i)) if i < a.len() => {
                    a.remove(i);
                }
                _ => {}
            }
        }
        self.tree_sel = None;
        self.mark_modified();
        self.render_all_views(false);
    }

    fn format_raw_json(&mut self) {
        let content = self.raw_text.trim().to_string();
        if content.is_empty() {
            return;
        }
        match serde_json::from_str::<Value>(&content) {
            Ok(v) => self.raw_text = pretty(&v),
            Err(e) => {
                let msg = self.tf(
                    "dlg_json_syntax_msg",
                    &[("line", e.line().to_string()), ("col", e.column().to_string()), ("msg", strip_json_err(&e))],
                );
                self.info(self.t("dlg_json_syntax_title"), msg);
            }
        }
    }

    fn apply_raw_json(&mut self, silent: bool) -> bool {
        let content = self.raw_text.trim().to_string();
        if content.is_empty() {
            return false;
        }
        match serde_json::from_str::<Value>(&content) {
            Ok(v) => {
                self.data = Some(v);
                self.mark_modified();
                self.generation += 1;
                self.sync_preview(false);
                if !silent {
                    self.set_status(self.t("status_raw_applied"));
                }
                true
            }
            Err(e) => {
                let msg = self.tf(
                    "dlg_json_fix_msg",
                    &[("line", e.line().to_string()), ("col", e.column().to_string()), ("msg", strip_json_err(&e))],
                );
                self.info(self.t("dlg_json_syntax_title"), msg);
                false
            }
        }
    }

    fn switch_page(&mut self, page: Page) {
        if self.page == page {
            return;
        }
        self.page = page;
        match page {
            Page::Studio => self.sync_preview(false),
            Page::Tree | Page::Format => {}
            Page::Raw => self.refresh_raw(),
        }
    }

    // ---------------------------------------------------------------- dialogs

    fn finish_prompt(&mut self, kind: PromptKind, value: String) {
        match kind {
            PromptKind::NewAppName => {
                let name = value.trim().to_string();
                if name.is_empty() {
                    return;
                }
                let Some(folder) = rfd::FileDialog::new().set_title(self.tf("dlg_select_folder", &[("app", name.clone())])).pick_folder() else {
                    return;
                };
                self.dialog = Some(Dialog::Confirm {
                    title: self.t("dlg_schema_title"),
                    msg: self.t("dlg_schema_msg"),
                    kind: ConfirmKind::Schema { name, folder: folder.to_string_lossy().to_string() },
                });
            }
            PromptKind::Duplicate => {
                let nm = value.trim();
                if nm.is_empty() {
                    return;
                }
                let filename = with_json_ext(nm);
                let Some(cur) = self.current_file.clone() else { return };
                let target = cur.parent().map(|p| p.join(&filename)).unwrap_or_else(|| PathBuf::from(&filename));
                if target.exists() {
                    self.info(self.t("dlg_file_exists_title"), self.tf("dlg_file_exists_msg", &[("name", filename)]));
                    return;
                }
                let mut dup = self.data.clone().unwrap_or(Value::Null);
                if dup.get("presets").and_then(|p| p.as_array()).map(|a| !a.is_empty()).unwrap_or(false) {
                    dup["presets"][0]["name"] = json!(file_stem(Path::new(&filename)));
                }
                if let Err(e) = fs::write(&target, pretty(&dup)) {
                    self.info(self.t("dlg_save_err_title"), self.tf("dlg_save_err_msg", &[("err", e.to_string())]));
                    return;
                }
                self.refresh_file_list();
                self.load_file(target);
                self.set_status(self.tf("status_duplicated", &[("name", filename)]));
            }
            PromptKind::Rename => {
                let nm = value.trim();
                let Some(cur) = self.current_file.clone() else { return };
                if nm.is_empty() {
                    return;
                }
                let filename = with_json_ext(nm);
                let new_path = cur.parent().map(|p| p.join(&filename)).unwrap_or_else(|| PathBuf::from(&filename));
                if new_path.exists() {
                    self.info(self.t("dlg_error"), self.t("dlg_name_exists"));
                    return;
                }
                if let Err(e) = fs::rename(&cur, &new_path) {
                    self.info(self.t("dlg_error"), e.to_string());
                    return;
                }
                self.current_file = Some(new_path);
                self.refresh_file_list();
                self.set_status(self.tf("status_renamed", &[("name", filename)]));
            }
            PromptKind::TreeEdit(path, hint) => {
                let new_val = smart_parse_value(&value, hint);
                if let Some(slot) = self.data.as_mut().and_then(|d| get_by_path_mut(d, &path)) {
                    *slot = new_val;
                }
                self.mark_modified();
                self.render_all_views(false);
            }
            PromptKind::TreeNewKey(path) => {
                if value.is_empty() {
                    return;
                }
                self.dialog = Some(Dialog::Prompt {
                    title: self.t("dlg_init_val_title"),
                    label: self.tf("dlg_init_val_prompt", &[("key", value.clone())]),
                    value: String::new(),
                    kind: PromptKind::TreeNewValue(path, value),
                    first: true,
                });
            }
            PromptKind::TreeNewValue(path, key) => {
                let v = smart_parse_value(&value, Hint::None);
                if let Some(Value::Object(m)) = self.data.as_mut().and_then(|d| get_by_path_mut(d, &path)) {
                    m.insert(key, v);
                }
                self.mark_modified();
                self.render_all_views(false);
            }
            PromptKind::TreeNewItem(path) => {
                let v = smart_parse_value(&value, Hint::None);
                if let Some(Value::Array(a)) = self.data.as_mut().and_then(|d| get_by_path_mut(d, &path)) {
                    a.push(v);
                }
                self.mark_modified();
                self.render_all_views(false);
            }
        }
    }

    fn finish_confirm(&mut self, kind: ConfirmKind, yes: bool) {
        match kind {
            ConfirmKind::Schema { name, folder } => {
                let is_fc = yes;
                let template = if is_fc { templates::filmcraft_text_template() } else { templates::generic_default_template() };
                self.profiles.insert(
                    name.clone(),
                    json!({"folder": folder, "schema_type": if is_fc { "filmcraft" } else { "generic" }, "template": template}),
                );
                self.save_profiles();
                self.current_profile = name.clone();
                self.refresh_file_list();
                self.set_status(self.tf("status_profile_created", &[("app", name)]));
            }
            ConfirmKind::Overwrite { src } => {
                if yes {
                    self.finish_import(src);
                }
            }
            ConfirmKind::Delete => {
                if !yes {
                    return;
                }
                let Some(path) = self.current_file.take() else { return };
                let name = file_name(&path);
                let _ = fs::remove_file(&path);
                self.data = None;
                self.modified = false;
                self.tree_sel = None;
                self.refresh_file_list();
                self.render_all_views(true);
                self.set_status(self.tf("status_deleted", &[("name", name)]));
            }
        }
    }

    fn show_dialog(&mut self, ctx: &egui::Context) {
        let Some(mut dialog) = self.dialog.take() else { return };
        let lang = self.lang;
        let mut out = Outcome::Keep;
        let esc = ctx.input(|i| i.key_pressed(Key::Escape));
        let enter = ctx.input(|i| i.key_pressed(Key::Enter));
        let (yes_lbl, no_lbl) = if lang == Lang::Pt { ("Sim", "Não") } else { ("Yes", "No") };

        let window = |title: &str| {
            egui::Window::new(title.to_string())
                .id(egui::Id::new("modal_dialog"))
                .anchor(Align2::CENTER_CENTER, [0.0, 0.0])
                .collapsible(false)
                .resizable(false)
                .min_width(380.0)
        };

        match &mut dialog {
            Dialog::Message { title, msg } => {
                window(title).show(ctx, |ui| {
                    ui.label(msg.as_str());
                    ui.add_space(8.0);
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if theme::accent_button(ui, "OK").clicked() || esc || enter {
                            out = Outcome::Close;
                        }
                    });
                });
            }
            Dialog::Prompt { title, label, value, first, .. } => {
                window(title).show(ctx, |ui| {
                    ui.label(label.as_str());
                    let resp = ui.add(egui::TextEdit::singleline(value).desired_width(f32::INFINITY));
                    if *first {
                        resp.request_focus();
                        *first = false;
                    }
                    let submitted = resp.lost_focus() && enter;
                    ui.add_space(8.0);
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if theme::accent_button(ui, "OK").clicked() || submitted {
                            out = Outcome::Ok(value.clone());
                        }
                        if ui.button(tr(lang, "btn_cancel")).clicked() || esc {
                            out = Outcome::Close;
                        }
                    });
                });
            }
            Dialog::Confirm { title, msg, .. } => {
                window(title).show(ctx, |ui| {
                    ui.label(msg.as_str());
                    ui.add_space(8.0);
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ui.button(no_lbl).clicked() {
                            out = Outcome::Yes(false);
                        }
                        if theme::accent_button(ui, yes_lbl).clicked() {
                            out = Outcome::Yes(true);
                        }
                        if esc {
                            out = Outcome::Yes(false);
                        }
                    });
                });
            }
            Dialog::NewPreset { name, kind_idx, is_fc } => {
                window(&tr(lang, "dlg_new_preset_title")).show(ctx, |ui| {
                    ui.label(tr(lang, "dlg_new_preset_lbl"));
                    let resp = ui.add(egui::TextEdit::singleline(name).desired_width(f32::INFINITY));
                    let submitted = resp.lost_focus() && enter;
                    {
                        ui.add_space(6.0);
                        ui.label(tr(lang, "dlg_fc_type_lbl"));
                        let kinds: Vec<String> = if *is_fc {
                            vec![tr(lang, "fc_type_motion"), tr(lang, "fc_type_text"), tr(lang, "fc_type_profile")]
                        } else {
                            vec![tr(lang, "fc_type_profile"), tr(lang, "fc_type_obs"), "OBS Stinger transition".to_string()]
                        };
                        egui::ComboBox::from_id_salt("fc_kind").width(300.0).selected_text(kinds[*kind_idx].clone()).show_ui(ui, |ui| {
                            for (i, k) in kinds.iter().enumerate() {
                                ui.selectable_value(kind_idx, i, k);
                            }
                        });
                    }
                    ui.add_space(8.0);
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ui.button(tr(lang, "btn_cancel")).clicked() || esc {
                            out = Outcome::Close;
                        }
                        if theme::accent_button(ui, &tr(lang, "btn_create_preset")).clicked() || submitted {
                            out = Outcome::Create(name.clone(), *kind_idx);
                        }
                    });
                });
            }
        }

        match out {
            Outcome::Keep => self.dialog = Some(dialog),
            Outcome::Close => {}
            Outcome::Ok(v) => {
                if let Dialog::Prompt { kind, .. } = dialog {
                    self.finish_prompt(kind, v);
                }
            }
            Outcome::Yes(yes) => {
                if let Dialog::Confirm { kind, .. } = dialog {
                    self.finish_confirm(kind, yes);
                }
            }
            Outcome::Create(name, idx) => {
                if let Dialog::NewPreset { is_fc, .. } = dialog {
                    if !self.confirm_new_preset(name.clone(), idx, is_fc) && self.dialog.is_none() {
                        // empty name: keep the dialog open
                        self.dialog = Some(Dialog::NewPreset { name, kind_idx: idx, is_fc });
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------------- actions from inspector / viewer

    fn process_actions(&mut self, ctx: &egui::Context) {
        if self.viewer.take_modified() {
            self.mark_modified();
            ctx.request_repaint();
        }
        let actions: Vec<InspAction> = std::mem::take(&mut self.pending);
        if actions.is_empty() {
            return;
        }
        for a in actions {
            match a {
                InspAction::Modified => self.mark_modified(),
                InspAction::Sync { reset } => self.sync_preview(reset),
                InspAction::RenderAll { reset } => self.render_all_views(reset),
                InspAction::Pause => self.viewer.pause(),
                InspAction::Status(s) => self.set_status(s),
                InspAction::Info(t, m) | InspAction::Error(t, m) => self.info(t, m),
            }
        }
        ctx.request_repaint();
    }

    fn inspector_ctx(&self) -> InspCtx {
        InspCtx { lang: self.lang, cur_t: self.viewer.current_time_ns, frame_ns: self.viewer.frame_ns(), generation: self.generation }
    }

    fn show_kf_window(&mut self, ctx: &egui::Context) {
        if let Some((eff, key, tag)) = inspector::take_open_kf_request(ctx) {
            let mut out = vec![];
            self.kf_editor = inspector::open_kf_editor(&mut self.data, self.sel_preset, eff, &key, &tag, &mut out);
            self.pending.extend(out);
        }
        let Some(mut ed) = self.kf_editor.take() else { return };
        let cx = self.inspector_ctx();
        let mut out = vec![];
        let mut seek = None;
        let keep = inspector::show_kf_editor(ctx, &mut ed, &mut self.data, self.sel_preset, &cx, &mut out, &mut seek);
        if let Some(t) = seek {
            self.viewer.seek(t);
        }
        self.pending.extend(out);
        if keep {
            self.kf_editor = Some(ed);
        }
    }

    // ---------------------------------------------------------------- shortcuts

    fn handle_shortcuts(&mut self, ctx: &egui::Context) {
        if ctx.input_mut(|i| i.consume_key(egui::Modifiers::COMMAND, Key::S)) {
            self.save_current_file();
        }
        if ctx.input_mut(|i| i.consume_key(egui::Modifiers::COMMAND, Key::N)) {
            self.create_new_preset();
        }
        if ctx.wants_keyboard_input() || self.dialog.is_some() {
            return;
        }
        let (space, left, right, home, end, shift, ctrl) = ctx.input(|i| {
            (
                i.key_pressed(Key::Space),
                i.key_pressed(Key::ArrowLeft),
                i.key_pressed(Key::ArrowRight),
                i.key_pressed(Key::Home),
                i.key_pressed(Key::End),
                i.modifiers.shift,
                i.modifiers.ctrl || i.modifiers.command,
            )
        });
        if space {
            self.viewer.toggle_play();
        }
        if self.page != Page::Studio {
            return;
        }
        let dir = if left { -1 } else if right { 1 } else { 0 };
        if home {
            self.viewer.go_to_start();
        } else if end {
            self.viewer.go_to_end();
        } else if dir != 0 {
            if ctrl {
                let idx = self.sel_preset;
                let preset = preset_mut(&mut self.data, idx).map(|p| &*p);
                self.viewer.jump_keyframe(dir, preset);
            } else {
                self.viewer.step_frames(dir as i64 * if shift { 10 } else { 1 });
            }
        }
    }

    // ---------------------------------------------------------------- panels

    fn titlebar(&mut self, ctx: &egui::Context) {
        egui::TopBottomPanel::top("titlebar")
            .frame(egui::Frame::none().fill(pal::TITLEBAR).inner_margin(egui::Margin::symmetric(14.0, 8.0)))
            .show_separator_line(false)
            .show(ctx, |ui| {
                let lang = self.lang;
                ui.horizontal(|ui| {
                    // window dots
                    let (rect, _) = ui.allocate_exact_size(egui::vec2(44.0, 16.0), egui::Sense::hover());
                    for (i, c) in [theme::rgb(0xff5f56), theme::rgb(0xffbd2e), theme::rgb(0x27c93f)].into_iter().enumerate() {
                        ui.painter().circle_filled(egui::pos2(rect.left() + 7.0 + i as f32 * 15.0, rect.center().y), 5.0, c);
                    }
                    ui.label(RichText::new(self.t("app_title")).size(14.0).strong());
                    ui.separator();

                    let mut new_profile: Option<String> = None;
                    egui::ComboBox::from_id_salt("profile_combo")
                        .width(180.0)
                        .selected_text(self.current_profile.clone())
                        .show_ui(ui, |ui| {
                            for k in self.profiles.keys() {
                                if ui.selectable_label(*k == self.current_profile, k).clicked() {
                                    new_profile = Some(k.clone());
                                }
                            }
                        });
                    if let Some(p) = new_profile {
                        if p != self.current_profile {
                            self.current_profile = p;
                            self.on_profile_changed();
                        }
                    }
                    if theme::ghost_button(ui, &tr(lang, "btn_add_app")).clicked() {
                        self.add_new_profile();
                    }
                    if theme::ghost_button(ui, &tr(lang, "btn_folder")).clicked() {
                        self.change_profile_folder();
                    }
                    if theme::ghost_button(ui, &tr(lang, "btn_template")).clicked() {
                        self.save_current_as_template();
                    }

                    ui.add_space(10.0);
                    let pill_text = match &self.current_file {
                        None => self.t("no_file_selected"),
                        Some(f) if self.modified => format!("{}  •", file_name(f)),
                        Some(f) => file_name(f),
                    };
                    egui::Frame::none()
                        .fill(pal::WELL)
                        .stroke(Stroke::new(1.0, pal::BORDER))
                        .inner_margin(egui::Margin::symmetric(14.0, 4.0))
                        .show(ui, |ui| {
                            ui.label(RichText::new(pill_text).size(12.0).strong());
                        });

                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if theme::accent_button(ui, &tr(lang, "btn_save")).clicked() {
                            self.save_current_file();
                        }
                        if ui.button(tr(lang, "btn_validate")).clicked() {
                            self.validate_current_json();
                        }
                        if ui.button(tr(lang, "btn_import")).clicked() {
                            self.import_preset();
                        }
                        if ui.button(tr(lang, "btn_duplicate")).clicked() {
                            self.duplicate_preset();
                        }
                        if ui.button(tr(lang, "btn_new")).clicked() {
                            self.create_new_preset();
                        }
                        egui::Frame::none()
                            .fill(pal::WELL)
                            .stroke(Stroke::new(1.0, pal::BORDER))
                            .inner_margin(egui::Margin::same(2.0))
                            .show(ui, |ui| {
                                ui.spacing_mut().item_spacing.x = 2.0;
                                for (l, label) in [(Lang::Pt, "PT"), (Lang::En, "EN")] {
                                    if theme::pill(ui, label, self.lang == l, 11.0) {
                                        self.set_language(l);
                                    }
                                }
                            });
                    });
                });
            });
        egui::TopBottomPanel::top("titlebar_line").exact_height(1.0).frame(egui::Frame::none().fill(pal::BORDER)).show(ctx, |_| {});
    }

    fn bottom_dock(&mut self, ctx: &egui::Context) {
        egui::TopBottomPanel::bottom("dock")
            .frame(egui::Frame::none().fill(pal::TITLEBAR).stroke(Stroke::new(1.0, pal::BORDER)).inner_margin(egui::Margin::symmetric(14.0, 6.0)))
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    let dot = if self.current_file.is_some() && self.modified { pal::ACCENT } else { pal::SUCCESS };
                    ui.label(RichText::new("●").size(11.0).color(dot));
                    ui.label(RichText::new(self.status.clone()).size(12.0).color(pal::FG_MUTED));
                    ui.add_space(12.0);
                    egui::Frame::none()
                        .fill(pal::WELL)
                        .stroke(Stroke::new(1.0, pal::BORDER))
                        .inner_margin(egui::Margin::same(3.0))
                        .show(ui, |ui| {
                            ui.spacing_mut().item_spacing.x = 4.0;
                            for (page, key) in [(Page::Studio, "page_studio"), (Page::Format, "page_format"), (Page::Tree, "page_tree"), (Page::Raw, "page_raw")] {
                                if theme::pill(ui, &self.t(key), self.page == page, 12.0) {
                                    self.switch_page(page);
                                }
                            }
                        });
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        ui.label(RichText::new(self.t("shortcuts_hint")).size(11.0).color(pal::FG_FAINT));
                    });
                });
            });
    }

    fn library_panel(&mut self, ctx: &egui::Context) {
        egui::SidePanel::left("library")
            .default_width(260.0)
            .width_range(200.0..=420.0)
            .frame(egui::Frame::none().fill(pal::PANEL).stroke(Stroke::new(1.0, pal::BORDER)))
            .show(ctx, |ui| {
                theme::header_frame().show(ui, |ui| {
                    ui.set_width(ui.available_width());
                    ui.label(theme::section_tag(&self.t("library_header")));
                });
                egui::Frame::none().inner_margin(egui::Margin::same(10.0)).show(ui, |ui| {
                    ui.horizontal(|ui| {
                        ui.add(egui::TextEdit::singleline(&mut self.search).desired_width(ui.available_width() - 34.0));
                        if theme::ghost_button(ui, "↻").clicked() {
                            self.refresh_file_list();
                        }
                    });
                    ui.add_space(4.0);

                    let query = self.search.trim().to_lowercase();
                    let list_h = (ui.available_height() - 80.0).max(80.0);
                    let mut to_load: Option<PathBuf> = None;
                    egui::Frame::none().fill(pal::INPUT).stroke(Stroke::new(1.0, pal::BORDER)).inner_margin(egui::Margin::same(4.0)).show(ui, |ui| {
                        egui::ScrollArea::vertical().max_height(list_h).min_scrolled_height(list_h).auto_shrink([false, false]).show(ui, |ui| {
                            ui.set_width(ui.available_width());
                            for f in &self.files {
                                let name = file_name(f);
                                if !query.is_empty() && !name.to_lowercase().contains(&query) {
                                    continue;
                                }
                                let selected = self.current_file.as_ref() == Some(f);
                                let r = ui.add_sized([ui.available_width(), 24.0], egui::SelectableLabel::new(selected, format!("  {}", name)));
                                if r.clicked() {
                                    to_load = Some(f.clone());
                                }
                            }
                        });
                    });
                    if let Some(p) = to_load {
                        self.load_file(p);
                    }

                    ui.add_space(6.0);
                    ui.horizontal(|ui| {
                        let w = (ui.available_width() - 6.0) / 2.0;
                        if ui.add_sized([w, 24.0], egui::Button::new(self.t("btn_rename"))).clicked() {
                            self.rename_file();
                        }
                        if ui
                            .add_sized(
                                [w, 24.0],
                                egui::Button::new(RichText::new(self.t("btn_delete")).strong().color(pal::DANGER))
                                    .fill(pal::DANGER_BG)
                                    .stroke(Stroke::new(1.0, theme::rgb(0x54282e))),
                            )
                            .clicked()
                        {
                            self.delete_file();
                        }
                    });
                    ui.label(RichText::new(format!("📁 {}", self.profile_folder().display())).size(10.5).color(pal::FG_MUTED));
                });
            });
    }

    fn studio_page(&mut self, ctx: &egui::Context) {
        egui::SidePanel::right("inspector")
            .default_width(420.0)
            .width_range(320.0..=640.0)
            .frame(egui::Frame::none().fill(pal::PANEL))
            .show(ctx, |ui| {
                theme::header_frame().show(ui, |ui| {
                    ui.set_width(ui.available_width());
                    ui.horizontal(|ui| {
                        ui.label(theme::section_tag(&self.t("inspector_header")));
                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            ui.label(theme::muted(&self.t("inspector_sub")));
                        });
                    });
                });
                theme::separator_line(ui);
                let cx = self.inspector_ctx();
                let mut out = vec![];
                inspector::show(ui, &mut self.data, &mut self.sel_preset, &mut self.sel_effect, &mut self.insp_state, &cx, &mut out);
                self.pending.extend(out);
            });

        egui::CentralPanel::default().frame(egui::Frame::none().fill(pal::PANEL)).show(ctx, |ui| {
            let idx = self.sel_preset;
            let preset = preset_mut(&mut self.data, idx);
            self.viewer.show(ui, preset, self.lang);
        });
    }

    fn format_page(&mut self, ctx: &egui::Context) {
        egui::CentralPanel::default().frame(egui::Frame::none().fill(pal::PANEL).inner_margin(egui::Margin::same(14.0))).show(ctx, |ui| {
            match self.data.as_mut() {
                Some(data) => {
                    if formats::show(ui, data, &mut self.fmt_state, self.lang, self.generation) {
                        self.pending.push(InspAction::Modified);
                    }
                }
                None => {
                    ui.label(theme::muted(&tr(self.lang, "fmt_empty")));
                }
            }
        });
    }

    fn tree_page(&mut self, ctx: &egui::Context) {
        egui::CentralPanel::default().frame(egui::Frame::none().fill(pal::PANEL)).show(ctx, |ui| {
            theme::header_frame().inner_margin(egui::Margin::symmetric(14.0, 8.0)).show(ui, |ui| {
                ui.set_width(ui.available_width());
                ui.horizontal(|ui| {
                    ui.label(theme::section_tag(&self.t("tree_header")));
                    ui.label(theme::muted(&self.t("tree_sub")));
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if theme::danger_button(ui, &self.t("btn_remove")).clicked() {
                            self.tree_delete_node();
                        }
                        if ui.button(self.t("btn_add_node")).clicked() {
                            self.tree_add_node();
                        }
                        if ui.button(self.t("btn_edit_val")).clicked() {
                            self.tree_edit_selected();
                        }
                    });
                });
            });
            theme::separator_line(ui);

            egui::Frame::none().inner_margin(egui::Margin::same(12.0)).show(ui, |ui| {
                // column headings
                let base_x = ui.min_rect().left();
                ui.horizontal(|ui| {
                    ui.label(RichText::new(self.t("col_key")).strong().color(pal::FG_MUTED));
                });
                let head_y = ui.min_rect().top() + 8.0;
                ui.painter().text(egui::pos2(base_x + 340.0, head_y), Align2::LEFT_CENTER, self.t("col_type"), FontId::proportional(12.0), pal::FG_MUTED);
                ui.painter().text(egui::pos2(base_x + 450.0, head_y), Align2::LEFT_CENTER, self.t("col_value"), FontId::proportional(12.0), pal::FG_MUTED);
                theme::separator_line(ui);

                let mut clicked: Option<(Vec<Step>, bool)> = None;
                if let Some(data) = &self.data {
                    egui::ScrollArea::both().auto_shrink([false, false]).show(ui, |ui| {
                        let mut path = vec![];
                        tree_node(ui, "root", data, &mut path, &self.tree_sel, &mut clicked, base_x, 0);
                    });
                }
                if let Some((p, double)) = clicked {
                    self.tree_sel = Some(p);
                    if double {
                        self.tree_edit_selected();
                    }
                }
            });
        });
    }

    fn raw_page(&mut self, ctx: &egui::Context) {
        egui::CentralPanel::default().frame(egui::Frame::none().fill(pal::PANEL)).show(ctx, |ui| {
            theme::header_frame().inner_margin(egui::Margin::symmetric(14.0, 8.0)).show(ui, |ui| {
                ui.set_width(ui.available_width());
                ui.horizontal(|ui| {
                    ui.label(theme::section_tag(&self.t("raw_header")));
                    ui.label(theme::muted(&self.t("raw_sub")));
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if theme::accent_button(ui, &self.t("btn_apply_json")).clicked() {
                            self.apply_raw_json(false);
                        }
                        if ui.button(self.t("btn_format_json")).clicked() {
                            self.format_raw_json();
                        }
                    });
                });
            });
            theme::separator_line(ui);
            egui::Frame::none().inner_margin(egui::Margin::same(12.0)).show(ui, |ui| {
                egui::Frame::none().fill(pal::WELL).stroke(Stroke::new(1.0, pal::BORDER)).inner_margin(egui::Margin::symmetric(14.0, 12.0)).show(ui, |ui| {
                    egui::ScrollArea::both().auto_shrink([false, false]).show(ui, |ui| {
                        ui.add(
                            egui::TextEdit::multiline(&mut self.raw_text)
                                .font(egui::TextStyle::Monospace)
                                .code_editor()
                                .desired_width(f32::INFINITY)
                                .desired_rows(40)
                                .lock_focus(true),
                        );
                    });
                });
            });
        });
    }
}

#[allow(clippy::too_many_arguments)]
fn tree_node(
    ui: &mut egui::Ui, label: &str, node: &Value, path: &mut Vec<Step>, sel: &Option<Vec<Step>>,
    clicked: &mut Option<(Vec<Step>, bool)>, base_x: f32, depth: usize,
) {
    let is_sel = sel.as_ref() == Some(path);
    let (ty, val) = match node {
        Value::Object(m) => ("Object", format!("{{{}}}", m.len())),
        Value::Array(a) => ("Array", format!("[{}]", a.len())),
        Value::String(s) => ("str", s.clone()),
        Value::Number(n) => (if n.is_f64() { "float" } else { "int" }, n.to_string()),
        Value::Bool(b) => ("bool", b.to_string()),
        Value::Null => ("null", "null".to_string()),
    };
    let val: String = val.chars().take(140).collect::<String>().replace('\n', " ");

    let mut paint_cols = |ui: &egui::Ui, y: f32| {
        ui.painter().text(egui::pos2(base_x + 340.0, y), Align2::LEFT_CENTER, ty, FontId::proportional(12.0), pal::FG_MUTED);
        ui.painter().text(egui::pos2(base_x + 450.0, y), Align2::LEFT_CENTER, &val, FontId::monospace(12.0), pal::FG_TEXT);
    };

    match node {
        Value::Object(_) | Value::Array(_) => {
            let id = ui.make_persistent_id(format!("tree{:?}", path));
            let state = egui::collapsing_header::CollapsingState::load_with_default_open(ui.ctx(), id, depth < 3);
            let header = state.show_header(ui, |ui| {
                let r = ui.selectable_label(is_sel, label);
                paint_cols(ui, r.rect.center().y);
                if r.clicked() {
                    *clicked = Some((path.clone(), false));
                }
                if r.double_clicked() {
                    *clicked = Some((path.clone(), true));
                }
            });
            header.body(|ui| match node {
                Value::Object(m) => {
                    for (k, v) in m {
                        path.push(Step::Key(k.clone()));
                        tree_node(ui, k, v, path, sel, clicked, base_x, depth + 1);
                        path.pop();
                    }
                }
                Value::Array(a) => {
                    for (i, v) in a.iter().enumerate() {
                        path.push(Step::Idx(i));
                        tree_node(ui, &format!("[{}]", i), v, path, sel, clicked, base_x, depth + 1);
                        path.pop();
                    }
                }
                _ => {}
            });
        }
        _ => {
            ui.horizontal(|ui| {
                ui.add_space(ui.spacing().indent);
                let r = ui.selectable_label(is_sel, label);
                paint_cols(ui, r.rect.center().y);
                if r.clicked() {
                    *clicked = Some((path.clone(), false));
                }
                if r.double_clicked() {
                    *clicked = Some((path.clone(), true));
                }
            });
        }
    }
}

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.handle_shortcuts(ctx);
        self.titlebar(ctx);
        self.bottom_dock(ctx);
        self.library_panel(ctx);
        match self.page {
            Page::Studio => self.studio_page(ctx),
            Page::Tree => self.tree_page(ctx),
            Page::Raw => self.raw_page(ctx),
            Page::Format => self.format_page(ctx),
        }
        self.show_dialog(ctx);
        self.show_kf_window(ctx);
        self.process_actions(ctx);
        let _ = Color32::WHITE;
    }
}
