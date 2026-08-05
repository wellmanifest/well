# todo2code integration: intent across file formats

Wellm analyzes representation drift before `todo2code` builds its wider Intent
Evidence graph.

```text
intent.json ─┐
intent.yaml ─┤
intent.wm ───┤ parse + one schema + semantic digest + pairwise diff
intent.hcl ──┤
intent.wm.ts ┤
intent.toon ─┘
               ↓
wellm.todo2code-format-evidence/v1
               ↓
t2c extract config → link → diagnose → diff / compare-workspace
```

Run the Wellm-only comparison:

```bash
make intent-demo
```

When the `t2c` CLI is installed, run the direct configuration-extraction bridge:

```bash
make todo2code-intent
# optionally:
TODO2CODE_BIN=/path/to/t2c TODO2CODE_OUTPUT_DIR=.intent/formats \
  make todo2code-intent
```

Generated Wellm-only files:

```text
.wellm/intent-demo/report.json
.wellm/intent-demo/todo2code-evidence.json
```

The direct bridge additionally creates:

```text
.intent/wellm-formats/wellm-format-analysis.json
.intent/wellm-formats/input/wellm-format-evidence.json
.intent/wellm-formats/configuration.intent.jsonl
```

The evidence records exact artifact hashes, one semantic hash per
representation, schema validity and pairwise changes. It is a deterministic
observation; an LLM is not allowed to declare two unequal representations
equivalent.

For file-based integration, copy the evidence into the repository analyzed by
`todo2code`, then run its deterministic configuration extractor:

```bash
t2c extract config .intent/wellm-formats/input \
  --out .intent/wellm-formats/configuration.intent.jsonl
t2c link .intent/wellm-formats/configuration.intent.jsonl other.intent.jsonl \
  --out .intent/intent.graph.json
t2c diagnose .intent/intent.graph.json --out .intent/diagnostics.json
```

`todo2code` can then connect format drift with Git, AST, TODO, changelog,
documentation and communication evidence. Its `compare-workspace` flow can
compare a base revision and current workspace without checking out over the
user's working tree. Wellm remains responsible for format-level equivalence and
schema validation; todo2code remains responsible for the wider intent/reality
graph.

## Integration boundary in `0.2.0rc4`

The implemented bridge is deterministic and file/CLI based. Wellm produces and
validates format-level evidence; `t2c extract config` is pointed directly at the
evidence input directory, so `.intentignore` rules for generated run artifacts do
not hide the evidence. It turns the evidence configuration into `t2c.intent/v1`
records. A future native A2A/MCP action can
avoid the intermediate file, but this release does not claim that direct plugin
as implemented or tested.
