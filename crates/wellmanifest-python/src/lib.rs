use pyo3::prelude::*;

#[pyfunction]
fn convert(source: &str, from: &str, to: &str, pretty: Option<bool>) -> PyResult<String> {
    wellmanifest_core::convert(source, from, to, pretty.unwrap_or(true))
        .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))
}

#[pymodule]
fn _wellmanifest_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(convert, module)?)?;
    Ok(())
}
