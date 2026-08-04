# WellManifest LLM benchmark — plesk-project-format-selection

Fingerprint: `dfebb43c31f249f8c745b698cc66e87267ebb542fce75944be57343e38805f4d`

Selected model: `mock/typed-efficient`
Selected operational format: `typed`

| Rank | Candidate | Score | Cost USD | Avg latency ms | Capable | Format score / cost / latency |
|---:|---|---:|---:|---:|:---:|---|
| 1 | `typed-efficient` / `mock/typed-efficient` | 1.000 | 0.00004800 | 7.0 | yes | json=1.00/$0.00001200/7.0ms, typed=1.00/$0.00001200/7.0ms, typescript=1.00/$0.00001200/7.0ms, yaml=1.00/$0.00001200/7.0ms |
| 2 | `premium-general` / `mock/premium-general` | 1.000 | 0.00024000 | 15.0 | yes | json=1.00/$0.00006000/15.0ms, typed=1.00/$0.00006000/15.0ms, typescript=1.00/$0.00006000/15.0ms, yaml=1.00/$0.00006000/15.0ms |
| 3 | `cheap-json-only` / `mock/cheap-json-only` | 0.500 | 0.00001200 | 3.0 | no | json=1.00/$0.00000300/3.0ms, typed=0.00/$0.00000300/3.0ms, typescript=0.00/$0.00000300/3.0ms, yaml=1.00/$0.00000300/3.0ms |

## Method

- Selection is based on deterministic parsing, JSON Schema validation and exact semantic comparison; no judge LLM is used.
- A model with unknown price remains measurable but is ranked after equally capable models with measured cost when cost is preferred.

Scores: syntax 25%, JSON Schema 25%, deterministic semantic result 50%.
The benchmark records provider-reported token usage and cost when available.
