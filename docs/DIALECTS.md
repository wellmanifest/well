# Dialects

WellManifest uses one runtime with several parser frontends. They converge on a
common document model; they are not forced into one ambiguous grammar.

## Dialect table

| Dialect | Input | Data export | IR export | Notes |
|---|---:|---:|---:|---|
| `json@rfc8259` | yes | yes | yes | Strict JSON; no shebang/comments. |
| `yaml@1.2/json-compatible` | yes | yes | yes | JSON-compatible profile; duplicate keys rejected. |
| `toml@1.0` | yes | yes | yes | Basic tables, arrays and scalar values. |
| `typescript@wellm-1` | yes | yes | yes | Restricted non-executing data module. |
| `toon@1` | yes | normalized YAML/map | yes | Compact JSON-model/structural maps; code2llm map import. |
| `hcl@2` | yes | yes | yes | Static data subset plus blocks; external schema supplies types. |
| `typed@1` | yes | yes | yes | `name: Type = value`, type declarations and hints. |
| `policy-sh@1` | yes | no | yes | `RULE/WHEN/DO/FORBID/ASSERT/NEXT`; never executed by Bash. |
| `proto3` | yes | limited | yes | Basic parser in Python; `protoc` remains build authority. |

The HCL and proto identifiers follow their public language major, but the
implementation remains a compatibility frontend: version `0.2.0rc4` does not
claim every application-specific HCL evaluator or every `protoc` nuance.
Original source can be retained in IR and production builds can delegate to the
authoritative compiler.

## Shebang and dialect directives

Executable text dialects may use:

```text
#!/usr/bin/env -S wellmanifest run --dialect typed@1
#@wellmanifest kind="data" schema="./status.schema.json"
```

A portable installation may expose aliases such as `wellmanifest-typed` and use
`#!/usr/bin/env wellmanifest-typed`.

Strict JSON cannot contain a shebang. Proto files intended for direct `protoc`
use a comment marker:

```proto
//#!wellmanifest-proto3
syntax = "proto3";
```

## Four status syntaxes

### 1. HCL-compatible assignment

```hcl
status {
  operation = "002-cv-pdf2md"
  value = "SUCCEEDED"
  errors = []
}
```

The object type comes from an external schema or consuming application.

### 2. Split declaration and assignment

```wellmanifest
status {
  operation: FolderOperationId
  operation = "002-cv-pdf2md"
  value: OperationState
  value = "SUCCEEDED"
  errors = []
}
```

Accepted for migration. The formatter should collapse it into canonical form.
An orphan declaration or duplicate conflicting type is an error.

### 3. Canonical typed assignment

```wellmanifest
status {
  operation: FolderOperationId = "002-cv-pdf2md"
  value: OperationState = "SUCCEEDED"
  errors: [OperationError] = []
}
```

This is the preferred atomic form for a standalone typed value.

### 4. HCL comment hint

```hcl
status {
  operation = "002-cv-pdf2md" #folder
  value = "SUCCEEDED" #state
  errors = []
}
```

The parser can retain hints and emits `WM-TYPE-102`. A comment cannot override a
schema or typed declaration and must not be treated as authority.

## Typed module

```wellmanifest
#!/usr/bin/env -S wellmanifest run --dialect typed@1

type Status {
  type OperationId = String

  enum State {
    PENDING
    RUNNING
    SUCCEEDED
    FAILED
  }

  type Error {
    code: String
    message: String
    details?: Map<String, String>
  }

  operation: OperationId
  value: State
  errors: [Error]
}

data status: Status = {
  operation = "002-cv-pdf2md"
  value = SUCCEEDED
  errors = []
}
```

Nested names are addressable as `Status.OperationId`, `Status.State` and
`Status.Error`.

## TOON and code2llm maps

The `toon@1` frontend accepts JSON-compatible YAML/TOON data and the compact
structural layout used by `map.toon.yaml` from code2llm. It normalizes module
rows, imports and exports into a regular Wellm data/IR projection:

```bash
wellm convert examples/toon/map.toon.yaml --from toon --to json -o map.json
```

The semantic module map is preserved, while compact row spelling and whitespace
are normalized rather than byte-round-tripped.

## Procedural policy

```bash
RULE C-CONTEXT-001
WHEN ROOT_REPOSITORY = "wellmanifest/new-project"
DO SET TASK_CONTEXT = GOVERNANCE_HUB_MAINTENANCE
DO REQUIRE EXACTLY_ONE_MATCHING_TICKET IN "project/ticket-{NNN}"
FORBID IMPORT_TARGET_SYSTEM_TICKET_TASK_OR_LOG
ASSERT HUB_CHANGE_IS_TRACKED_WITHIN_HUB
```

The syntax is shell-shaped for readability but has no shell expansion,
pipelines, command substitution, redirection or arbitrary process execution.
Symbols are resolved from a contract symbol table. The parser can extract
normative `dsl` code blocks directly from Markdown.

## Proto3

```proto
syntax = "proto3";
package proto;

message Request {
  int64 id = 1;
  string firstname = 2;
}

service RegisterService {
  rpc RegisterUser(Request) returns (Response) {}
}
```

Plain data projection cannot preserve field numbers, services or RPCs. Use IR
or a descriptor set for lossless exchange.

## Import and export examples

```bash
wellm convert examples/dialects/status.hcl --from hcl --to yaml
wellm convert examples/dialects/status.yaml --from yaml --to typed --types infer
wellm convert examples/toon/map.toon.yaml --from toon --to json
wellm parse examples/policy/CONTRIBUTING.policy --dialect policy --projection ir
wellm parse examples/proto/register.proto --dialect proto3 --projection ir
```
