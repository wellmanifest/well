# Adaptive LLM format benchmark

Offline, deterministic demonstration:

```bash
wellm benchmark-llm examples/benchmark/config.yaml --mock \
  --output-dir .wellm/benchmark
```

Live LiteLLM run:

```bash
python -m pip install 'wellm[benchmark]'
cp examples/benchmark/config.live.example.yaml .wellm/models.yaml
# Set only the provider key environment variables referenced by the file.
wellm benchmark-llm .wellm/models.yaml --output-dir .wellm/benchmark
```

The first-request selector benchmarks fixed synthetic fixtures and caches the
winner. It does **not** send the user's real first request to every provider.
The real request is sent only to the selected model.

The deterministic expected report is checked in at
`examples/benchmark/expected/benchmark-report.md`. The example selects both a
model and an operational format; the chosen format is inserted into the first
real request prompt.
