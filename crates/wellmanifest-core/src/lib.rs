//! Native core for the WellManifest protocol.
//!
//! The Python implementation is the feature-complete reference runtime in
//! v0.1. This crate supplies a small, deterministic JSON/YAML conversion core
//! shared by CLI, WASM, Python and Node bindings. Additional dialects plug into
//! the same IR contract instead of duplicating transport semantics.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "UPPERCASE")]
pub enum Severity {
    Error,
    Warning,
    Info,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Diagnostic {
    pub code: String,
    pub severity: Severity,
    pub message: String,
    #[serde(default)]
    pub phase: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RuntimeTarget {
    pub runtime_ref: String,
    pub environment: String,
    pub execution: String,
    #[serde(default)]
    pub resources: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Envelope {
    pub spec: String,
    pub id: String,
    pub timestamp: String,
    pub kind: String,
    pub operation: String,
    pub content_type: String,
    #[serde(default)]
    pub accept: Vec<String>,
    #[serde(default)]
    pub contract_ref: Option<String>,
    #[serde(default)]
    pub idempotency_key: Option<String>,
    pub runtime: RuntimeTarget,
    pub payload: Value,
    #[serde(default)]
    pub diagnostics: Vec<Diagnostic>,
}

#[derive(Debug, Error)]
pub enum WellManifestError {
    #[error("unsupported dialect: {0}")]
    UnsupportedDialect(String),
    #[error("JSON parse failed: {0}")]
    Json(#[from] serde_json::Error),
    #[error("YAML parse or serialization failed: {0}")]
    Yaml(#[from] serde_yaml::Error),
}

pub fn parse_value(source: &str, dialect: &str) -> Result<Value, WellManifestError> {
    match normalize_dialect(dialect).as_str() {
        "json" => Ok(serde_json::from_str(source)?),
        "yaml" => Ok(serde_yaml::from_str(source)?),
        other => Err(WellManifestError::UnsupportedDialect(other.to_owned())),
    }
}

pub fn emit_value(
    value: &Value,
    dialect: &str,
    pretty: bool,
) -> Result<String, WellManifestError> {
    match normalize_dialect(dialect).as_str() {
        "json" if pretty => Ok(format!("{}\n", serde_json::to_string_pretty(value)?)),
        "json" => Ok(serde_json::to_string(value)?),
        "yaml" => Ok(serde_yaml::to_string(value)?),
        other => Err(WellManifestError::UnsupportedDialect(other.to_owned())),
    }
}

pub fn convert(
    source: &str,
    from: &str,
    to: &str,
    pretty: bool,
) -> Result<String, WellManifestError> {
    let value = parse_value(source, from)?;
    emit_value(&value, to, pretty)
}

pub fn normalize_dialect(value: &str) -> String {
    match value.to_ascii_lowercase().as_str() {
        "json" | "json@rfc8259" | "application/json" | "application/wellmanifest+json" => {
            "json".to_owned()
        }
        "yaml"
        | "yml"
        | "yaml@1.2/json-compatible"
        | "application/yaml"
        | "application/wellmanifest+yaml" => "yaml".to_owned(),
        _ => value.to_owned(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn converts_json_to_yaml_and_back() {
        let yaml = convert(
            r#"{"status":{"state":"SUCCEEDED","errors":[]}}"#,
            "json",
            "yaml",
            true,
        )
        .unwrap();
        let json = convert(&yaml, "yaml", "json", true).unwrap();
        let value: Value = serde_json::from_str(&json).unwrap();
        assert_eq!(value["status"]["state"], "SUCCEEDED");
    }
}
