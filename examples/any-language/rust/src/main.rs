use serde_json::json;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let base = std::env::var("WELLMANIFEST_URL").unwrap_or_else(|_| "http://localhost:8080".into());
    let result: serde_json::Value = reqwest::blocking::Client::new()
        .post(format!("{base}/v1/convert"))
        .json(&json!({
            "source": "status:\n  value: SUCCEEDED\n  errors: []\n",
            "source_dialect": "yaml",
            "target_dialect": "json",
            "projection": "data"
        }))
        .send()?
        .error_for_status()?
        .json()?;
    println!("{}", serde_json::to_string_pretty(&result)?);
    Ok(())
}
