---
{"schema":"subactor.doc/v1","id":"platform.docs.digital-twin-router-orchestrator","version":3,"status":"current","updated":"2026-07-24"}
---

# Digital Twin, router and orchestrator

A Digital Twin is a portrait of an actor, not an additional identity. It carries
principal, role/queue, contract revision, permitted models/OQL/URI Processes,
derived specializations, workload, waiting-input state, contract gaps and a
revision hash. It is read-only, contains no secrets and cannot expand authority.

`delegationDecision()` first rejects actors without a current contract or full
requirement coverage. It then evaluates portrait fit and only afterward uses
workload. Humans, bots and services pass the same AQL and exact-URI gates.

The orchestrator advances a ticket DAG using accepted Intent Bindings or
verified dependency receipts and terminal EQL, not the word `done` alone. A
change of actor is an explicit handoff. A ready ticket whose preflight fails is
projected as false-ready/waiting-input and retried only after a relevant
revision changes.

See `docs/DIGITAL_TWINS.md` and the files under `examples/digital-twin/`.
