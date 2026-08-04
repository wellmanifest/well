use napi::bindgen_prelude::Result;
use napi_derive::napi;

#[napi]
pub fn convert(
    source: String,
    from: String,
    to: String,
    pretty: Option<bool>,
) -> Result<String> {
    wellmanifest_core::convert(&source, &from, &to, pretty.unwrap_or(true))
        .map_err(|error| napi::Error::from_reason(error.to_string()))
}
