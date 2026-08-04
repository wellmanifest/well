# LiteLLM format and logic benchmark

`wellm.llmbench` is an optional internal package that compares LLM candidates on
the formats used by the WellManifest protocol. Its purpose is not to rank
models generally. It answers a narrower deployment question:

> Which configured candidate can reliably read and generate the required
> WellManifest representations, preserve deterministic logic and satisfy the
> schema, at the lowest measured cost for this workload?

The live adapter is loaded only with the `benchmark` extra:

```bash
python -m pip install 'wellm[benchmark]'
```

## Formats

The default example covers:

- JSON;
- YAML 1.2 JSON-compatible profile;
- canonical typed WellManifest (`field: Type = value`);
- restricted, round-trippable TypeScript data module.

HCL can be added to `formats` when the target workflow requires it.

## Deterministic scoring

The benchmark does not ask another LLM to judge the output. Each completion is
checked by the WellManifest runtime:

| Check | Weight | Evidence |
|---|---:|---|
| syntax/parse | 25% | target dialect parser |
| schema | 25% | JSON Schema Draft 2020-12 |
| semantics | 50% | exact normalized equality with the deterministic expected result |

The built-in tasks test three properties:

1. project registry round-trip without dropping or inventing fields;
2. URI Process permission logic — wildcard scopes grant permission but never
   become executable addresses;
3. publication gate logic — mutation remains blocked when TLS is not ready,
   the apply hash differs from the dry-run hash, or the signed grant is absent.

A model is considered capable only when its total score and every required
format score meet configured thresholds.

## Offline reproducible benchmark

```bash
wellm benchmark-llm examples/benchmark/config.yaml \
  --mock \
  --output-dir .wellm/benchmark
```

The mock adapter is deterministic and allows CI to verify the complete runner,
format parsers, schemas, selection policy and cache without network credentials.
The example intentionally defines:

- a very cheap model that fails typed/TypeScript outputs;
- an efficient model that passes every format;
- a more expensive model that also passes.

The expected winner is the cheapest capable candidate, not the cheapest
candidate overall.

## Live LiteLLM benchmark

Create a local configuration from
[`examples/benchmark/config.live.example.yaml`](../examples/benchmark/config.live.example.yaml):

```yaml
schema: wellmanifest.llm-benchmark/v1
id: plesk-format-live
fixture_file: ../plesk/projects.json
formats: [json, yaml, typed, typescript]
repetitions: 1
selection:
  minimum_total_score: 0.90
  minimum_format_score: 0.75
  prefer: lowest_cost
  cache_ttl_seconds: 86400
models:
  - id: candidate-a
    model: provider/model-a
    temperature: 0
    max_tokens: 5000
  - id: candidate-b
    model: provider/model-b
    temperature: 0
    max_tokens: 5000
```

Then run:

```bash
wellm benchmark-llm .wellm/benchmark.live.yaml \
  --output-dir .wellm/benchmark/live
```

Provider credentials remain in environment variables supported by the selected
LiteLLM provider. They must not be added to the benchmark file or report.

The report records, when supplied by the provider/LiteLLM response:

- prompt and completion tokens;
- latency;
- estimated or reported response cost;
- per-case syntax/schema/semantic outcome;
- per-format score;
- selected model and selection reason.

Unknown cost is never silently treated as zero. With `prefer: lowest_cost`, a
capable candidate with known measured cost is preferred over one whose cost is
unknown; score and latency are deterministic tie-breakers.

## First-request selection without leaking the request

`FirstRequestModelSelector` benchmarks fixed synthetic fixtures, caches the
winner by a fingerprint of configuration and cases, and only then sends the real
application request to the selected model.

```python
import json
from pathlib import Path

import yaml

from wellm.llmbench import (
    BenchmarkConfig,
    FirstRequestModelSelector,
    LiteLLMAdapter,
    build_cases,
)

config_path = Path(".wellm/benchmark.live.yaml")
config = BenchmarkConfig.model_validate(
    yaml.safe_load(config_path.read_text(encoding="utf-8"))
)
fixture_path = (config_path.parent / str(config.fixture_file)).resolve()
fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
cases = build_cases(fixture, list(config.formats))
selector = FirstRequestModelSelector(
    LiteLLMAdapter(),
    cache_path=Path(".wellm/benchmark/selection.json"),
)

candidate, selected_format, completion, benchmark_report = selector.complete_selected_route(
    config,
    cases,
    [
        {"role": "system", "content": "Return only a validated WellManifest document."},
        {"role": "user", "content": actual_request},
    ],
    metadata={"workflow": "plesk-publication-plan"},
)
```

The real user request is therefore not broadcast to every candidate. The cache
stores both the selected model and the operational representation. A new
benchmark runs only when the configuration/case fingerprint changes or the
cache expires.
 The selector prepends a deterministic format instruction to the
real request, so the selected `typed`, `typescript`, `json`, `yaml` or `hcl`
route is actually used rather than stored only as report metadata.

A complete executable example is in
[`examples/benchmark/first_request_router.py`](../examples/benchmark/first_request_router.py).

## TypeScript as a benchmark format

WellManifest emits a constrained module:

```ts
export type WellManifestDocument =
  Readonly<Record<string, unknown>> | readonly unknown[];

export default {
  "schema": "subactor.projects/v1",
  "projects": [
    {
      "id": "obslugabiurowa-pl"
    }
  ]
} as const satisfies WellManifestDocument;
```

The runtime parser accepts the emitted data subset and does not execute imports,
functions, getters, template expressions or arbitrary JavaScript. This allows a
model to work in a familiar TypeScript representation without turning model
output into code execution.

## Python API

```python
import json
from pathlib import Path

import yaml

from wellm.llmbench import BenchmarkConfig, BenchmarkRunner, LiteLLMAdapter, build_cases

config = BenchmarkConfig.model_validate(
    yaml.safe_load(Path(".wellm/benchmark.live.yaml").read_text(encoding="utf-8"))
)
fixture = json.loads(Path("examples/plesk/projects.json").read_text(encoding="utf-8"))
cases = build_cases(fixture, list(config.formats))
report = BenchmarkRunner(LiteLLMAdapter()).run(config, cases)
print(report.model_dump_json(indent=2))
```

## Docker

The offline benchmark can run in the main image without API keys:

```bash
docker compose -f compose.e2e.yml run --rm plesk-benchmark-e2e
```

A live benchmark should use a separate profile and infrastructure secret
injection. Never bake provider keys into an image or Compose file.

## Limitations

- Results characterize the supplied cases, prompts, model versions and provider
  route; they are not a universal intelligence ranking.
- Provider aliases can change their underlying model. Pin versions where the
  provider supports it and retain the report fingerprint.
- Price metadata may be absent or change; keep cost provenance in the report and
  rerun selection when pricing/configuration changes.
- A passing benchmark does not grant URI Process authority. Generated output is
  still parsed, schema-validated, policy-checked and executed only through a
  concrete authorized adapter.
