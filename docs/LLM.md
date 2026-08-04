# LLM integration

## Role

An LLM can help propose a typed manifest, map an unfamiliar format, summarize
diagnostics, select a known process plan or produce a human-reviewable patch.
It is not a parser authority, schema validator, contract authority or direct
effect executor.

```text
untrusted prompt/context
        |
        v
LLM proposal (text/JSON)
        |
        v
WellManifest parser -> schema/type validator -> policy checks
        |
        +-- ERROR --> reject with diagnostics
        |
        v
human/contract gate for effects
        |
        v
concrete registered URI Process + receipt
```

## Planner URI

The reference runtime exposes a deterministic demonstration:

```text
llm://planner/manifest/query/propose
```

It returns a proposal envelope and explicitly labels the result as a mock. The
adapter can be replaced with an OpenAI-compatible, local or other provider
implementation, but provider output must pass the same parser and validators.

Run:

```bash
PYTHONPATH=src python examples/llm/planner.py
```

## Provider adapter contract

```python
class PlannerProvider(Protocol):
    async def propose(self, *, objective, context, output_schema): ...
```

The adapter should return:

```json
{
  "proposal": {},
  "model": "provider/model",
  "prompt_hash": "sha256:...",
  "context_refs": [],
  "diagnostics": [],
  "requires_approval": true
}
```

Do not put secrets or entire vault values into prompts. Use references and
minimal scoped data.

## Complex example: public-site bootstrap

1. A snapshot is imported as JSON, YAML or protobuf.
2. The situation profile computes metrics and deterministic assessments.
3. The LLM may explain gaps or propose a ticket DAG.
4. WellManifest validates every proposed ticket/process against schemas.
5. The digital-twin router chooses eligible actors only after AQL coverage.
6. Read-only URI queries collect evidence.
7. Mutating steps wait for required human approval and signed grant.
8. Each step emits receipts; EQL verifies terminal effects.

The LLM cannot convert `not_ready` into authority. It can only propose work that
is subsequently checked.

## Retrieval and provenance

An LLM request should include stable `context_refs`, content hashes and source
revisions. Generated manifests should retain model/provider and prompt hashes
in non-authoritative metadata. The canonical contract and current filesystem
remain authoritative.

## Validation loop

```text
proposal -> parse -> diagnostics
              ^          |
              |          v
          constrained repair prompt
```

Limit repair iterations and token/latency budgets. Never allow a model to
suppress an `ERROR`; only corrected source or an explicit contract/schema
change can remove it.
