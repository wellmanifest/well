use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn convert(source: &str, from: &str, to: &str, pretty: bool) -> Result<String, JsValue> {
    wellmanifest_core::convert(source, from, to, pretty)
        .map_err(|error| JsValue::from_str(&error.to_string()))
}
